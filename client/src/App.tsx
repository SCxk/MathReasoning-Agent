import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowUp, Check, ChevronRight, Circle, Copy, FileJson, LoaderCircle, Menu,
  MessageSquare, PanelRightOpen, Plus, RotateCcw, Sigma, SlidersHorizontal, Square, X,
} from 'lucide-react';
import {
  ApiError, cancelTask, createSession, errorMessage, getHealth, getTask, getSessions, getSessionTasks, resumeTask,
  stageNames, statusNames, STAGES, submitTask, startQuestionBatch, taskPath, terminal, watchTask,
  type Health, type ResponseStyle, type Task, type TraceEvent,
} from './api';
import { mergeTasks, readHistory, readSelected, saveHistory, saveSelected, type SessionRef } from './history';
import MathMarkdown from './MathMarkdown';
import QuestionBatches, { type QuestionState } from './QuestionBatches';

interface RecordView { task?: Task; events: TraceEvent[]; started: string[]; completed: string[]; error?: string }
const blank = (): RecordView => ({ events: [], started: [], completed: [] });
const keyFor = (session: string, id: string) => `${session}/${id}`;
const timeLabel = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;

export default function App() {
  const [sessions, setSessions] = useState<SessionRef[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [historyBusy, setHistoryBusy] = useState(true);
  const [historyError, setHistoryError] = useState('');
  const [sessionCursor, setSessionCursor] = useState<string | null>(null);
  const [historyVersion, setHistoryVersion] = useState(0);
  const [taskHistoryVersion, setTaskHistoryVersion] = useState(0);
  const [taskHistoryBusy, setTaskHistoryBusy] = useState(false);
  const [taskHistoryError, setTaskHistoryError] = useState('');
  const [records, setRecords] = useState<Record<string, RecordView>>({});
  const [health, setHealth] = useState<Health | null>(null);
  const [ready, setReady] = useState(false);
  const [draft, setDraft] = useState('');
  const [responseStyle, setResponseStyle] = useState<ResponseStyle>('auto');
  const [questionState, setQuestionState] = useState<QuestionState>({ session: null, uploading: false, busy: false, count: 0 });
  const [questionVersion, setQuestionVersion] = useState(0);
  const [questionUploadTarget, setQuestionUploadTarget] = useState<HTMLDivElement | null>(null);
  const [sending, setSending] = useState(false);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState('');
  const [connection, setConnection] = useState('未连接');
  const [watchVersion, setWatchVersion] = useState(0);
  const [drawer, setDrawer] = useState<'sessions' | 'progress' | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());
  const pending = useRef<{ session: string; problem: string; style?: ResponseStyle; key: string } | null>(null);
  const olderRequest = useRef<AbortController | null>(null);
  const sendingRef = useRef(false);
  const scrollArea = useRef<HTMLDivElement>(null);
  const followScroll = useRef(true);
  const composer = useRef<HTMLTextAreaElement>(null);
  const drawerElement = useRef<HTMLDivElement>(null);
  const currentSession = sessions.find(session => session.id === selected);
  const questionBusy = questionState.session === selected && questionState.busy;
  const textRef = currentSession?.tasks.at(-1);
  const questionTask = questionState.session === selected ? questionState.task : null;
  const batchTask = questionTask && (questionBusy || !textRef || Date.parse(questionTask.accepted_at) >= Date.parse(textRef.createdAt)) ? questionTask : null;
  const latestRef = batchTask || currentSession?.tasks.at(-1);
  const latestKey = selected && latestRef ? keyFor(selected, latestRef.id) : '';
  const latestRecord = records[latestKey];
  const latest = latestRecord?.task;
  const active = !!latest && !terminal(latest.status);
  const loading = !!latestRef && !latest && !latestRecord?.error;
  const supportsPresentation = health?.response_styles?.includes('auto') === true;
  const supportsHistory = health?.server_history === true;
  const supportsQuestions = health?.question_attachments === true && health.question_submission === 'explicit_send';
  const attachment = questionState.session === selected ? questionState.attachment : null;
  const draftLimit = attachment ? 4000 : 24000;
  useEffect(() => {
    if (batchTask?.id && supportsHistory) setHistoryVersion(value => value + 1);
  }, [batchTask?.id, supportsHistory]);
  const fileUploading = questionState.uploading;
  const needsRestart = !!health && !supportsPresentation;
  const canSend = (attachment ? supportsQuestions && attachment.status === 'ready' : !!draft.trim()) && draft.length <= draftLimit && !sending && !active && !loading && !questionBusy && !fileUploading && ready && !historyBusy
    && !historyError && !taskHistoryBusy && !taskHistoryError
    && (!selected || !supportsHistory || currentSession?.tasksLoaded === true);

  const updateTask = useCallback((task: Task) => {
    setRecords(previous => {
      const key = keyFor(task.session_id, task.id), before = previous[key] || blank();
      // A late stage frame must not roll back a confirmed cancellation or terminal result.
      if (before.task && terminal(before.task.status) && before.task.status !== 'interrupted' && !terminal(task.status)) return previous;
      const incoming = before.task?.status === 'cancelling' && ['queued', 'running'].includes(task.status)
        ? { ...task, status: 'cancelling' as const } : task;
      return { ...previous, [key]: { ...before, task: incoming, error: undefined } };
    });
  }, []);

  const questionSession = useCallback((id: string) => {
    setSessions(previous => [{ id, title: '', tasks: [], tasksLoaded: true, taskCount: 0 }, ...previous]);
    setSelected(id);
  }, []);

  useEffect(() => { if (batchTask) updateTask(batchTask); }, [batchTask, updateTask]);

  useEffect(() => {
    if (!health) return;
    if (supportsHistory) {
      if (!historyBusy && !historyError) saveSelected(selected);
    } else if (!historyBusy && !saveHistory(sessions)) setError('浏览器无法保存会话记录，刷新后可能丢失。');
  }, [sessions, selected, supportsHistory, health, historyBusy, historyError]);
  useEffect(() => {
    if (!health) return;
    if (!supportsHistory) {
      const cached = readHistory(); setSessions(cached); setSelected(cached[0]?.id || null); setHistoryBusy(false);
      return;
    }
    const controller = new AbortController();
    setHistoryBusy(true); setHistoryError('');
    void getSessions(null, controller.signal).then(page => {
      if (controller.signal.aborted) return;
      setSessions(previous => {
        const rows = page.items.map(item => ({ id: item.id, title: item.title, taskCount: item.task_count,
          tasks: previous.find(session => session.id === item.id)?.tasks || [],
          tasksLoaded: previous.find(session => session.id === item.id)?.tasksLoaded,
          nextCursor: previous.find(session => session.id === item.id)?.nextCursor }));
        return [...rows, ...previous.filter(item => !rows.some(row => row.id === item.id))];
      });
      setSessionCursor(page.next_cursor);
      if (historyVersion === 0) {
        const remembered = readSelected();
        setSelected(page.items.some(item => item.id === remembered) ? remembered : page.items[0]?.id || null);
      }
    }).catch(failure => {
      if (!controller.signal.aborted) setHistoryError(errorMessage(failure));
    }).finally(() => { if (!controller.signal.aborted) setHistoryBusy(false); });
    return () => controller.abort();
  // Health is polled; only a capability change or explicit refresh reloads history.
  }, [supportsHistory, !!health, historyVersion]);
  useEffect(() => {
    olderRequest.current?.abort();
    setTaskHistoryError('');
    if (!selected || !supportsHistory) { setTaskHistoryBusy(false); return; }
    const controller = new AbortController();
    setTaskHistoryBusy(true); setTaskHistoryError('');
    void getSessionTasks(selected, null, controller.signal).then(page => {
      if (controller.signal.aborted) return;
      page.items.filter(task => !task.question_source).forEach(updateTask);
      setSessions(previous => previous.map(item => item.id !== selected ? item : { ...item,
        tasks: mergeTasks(item.tasks, page.items.filter(task => !task.question_source).map(task => ({ id: task.id, problem: task.problem, createdAt: task.accepted_at }))),
        tasksLoaded: true, nextCursor: page.next_cursor }));
    }).catch(failure => { if (!controller.signal.aborted) setTaskHistoryError(errorMessage(failure)); })
      .finally(() => { if (!controller.signal.aborted) setTaskHistoryBusy(false); });
    return () => { controller.abort(); olderRequest.current?.abort(); };
  }, [selected, supportsHistory, taskHistoryVersion, updateTask]);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const value = await getHealth(controller.signal);
        if (!controller.signal.aborted) { setHealth(value); setReady(value.status === 'ready'); }
      } catch { if (!controller.signal.aborted) setReady(false); }
      if (!controller.signal.aborted) timer = setTimeout(() => void refresh(), 15000);
    };
    void refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);
  useEffect(() => {
    if (!drawer) return;
    const previous = document.activeElement as HTMLElement | null;
    const trap = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setDrawer(null); return; }
      if (event.key !== 'Tab' || !drawerElement.current) return;
      const elements = Array.from(drawerElement.current.querySelectorAll<HTMLElement>('button:not(:disabled), a[href]'));
      const first = elements[0], last = elements.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    drawerElement.current?.querySelector<HTMLElement>('button')?.focus();
    document.addEventListener('keydown', trap);
    return () => { document.removeEventListener('keydown', trap); previous?.focus(); };
  }, [drawer]);
  useEffect(() => {
    const element = composer.current;
    if (element) { element.style.height = '0px'; element.style.height = `${Math.min(element.scrollHeight, 160)}px`; }
  }, [draft, !!attachment]);
  useEffect(() => {
    if (followScroll.current && scrollArea.current) scrollArea.current.scrollTop = scrollArea.current.scrollHeight;
  }, [records, selected]);

  useEffect(() => {
    if (!selected || !latestRef) { setConnection('未连接'); return; }
    const key = keyFor(selected, latestRef.id);
    return watchTask(selected, latestRef.id, {
      task: updateTask,
      event: event => setRecords(previous => {
        const before = previous[key] || blank();
        if (before.events.some(item => item.sequence === event.sequence)) return previous;
        const completed = event.event_type === 'stage.completed' && !before.completed.includes(event.stage_id)
          ? [...before.completed, event.stage_id] : before.completed;
        const started = event.event_type === 'stage.started' && !before.started.includes(event.stage_id)
          ? [...before.started, event.stage_id] : before.started;
        return { ...previous, [key]: { ...before, started, completed, events: [...before.events, event].slice(-120) } };
      }),
      connection: setConnection,
      error: failure => setRecords(previous => ({ ...previous,
        [key]: { ...(previous[key] || blank()), error: errorMessage(failure) },
      })),
    });
  }, [selected, latestRef?.id, watchVersion, updateTask]);

  useEffect(() => {
    if (!selected || !currentSession || supportsHistory) return;
    const controller = new AbortController();
    const load = async () => {
      for (const reference of currentSession.tasks.slice(0, -1)) {
        if (controller.signal.aborted) return;
        try { updateTask(await getTask(selected, reference.id, controller.signal)); }
        catch (failure) {
          if (!controller.signal.aborted) {
            const key = keyFor(selected, reference.id);
            setRecords(previous => ({ ...previous, [key]: { ...(previous[key] || blank()), error: errorMessage(failure) } }));
          }
        }
        await new Promise(resolve => setTimeout(resolve, 150));
      }
    };
    void load();
    return () => controller.abort();
  }, [selected, currentSession?.tasks.length, supportsHistory, updateTask]);

  async function moreSessions() {
    if (!sessionCursor || historyBusy) return;
    setHistoryBusy(true); setHistoryError('');
    try {
      const page = await getSessions(sessionCursor);
      setSessions(previous => [...previous, ...page.items.filter(item => !previous.some(row => row.id === item.id))
        .map(item => ({ id: item.id, title: item.title, taskCount: item.task_count, tasks: [] }))]);
      setSessionCursor(page.next_cursor);
    } catch (failure) { setHistoryError(errorMessage(failure)); }
    finally { setHistoryBusy(false); }
  }
  async function olderTasks() {
    if (!selected || !currentSession?.nextCursor || taskHistoryBusy) return;
    const session = selected;
    const controller = new AbortController();
    olderRequest.current = controller;
    setTaskHistoryBusy(true); setTaskHistoryError(''); followScroll.current = false;
    try {
      const page = await getSessionTasks(session, currentSession.nextCursor, controller.signal);
      if (controller.signal.aborted) return;
      page.items.filter(task => !task.question_source).forEach(updateTask);
      setSessions(previous => previous.map(item => item.id !== session ? item : { ...item,
        tasks: mergeTasks(item.tasks, page.items.filter(task => !task.question_source).map(task => ({ id: task.id, problem: task.problem, createdAt: task.accepted_at }))),
        nextCursor: page.next_cursor }));
    } catch (failure) { if (!controller.signal.aborted) setTaskHistoryError(errorMessage(failure)); }
    finally { if (!controller.signal.aborted) setTaskHistoryBusy(false); }
  }

  function selectSession(id: string | null) {
    setSelected(id); setDraft(''); setError(''); setDrawer(null); followScroll.current = true;
    pending.current = null;
  }
  async function send() {
    if (!canSend || sendingRef.current) return;
    sendingRef.current = true; setSending(true); setError(''); followScroll.current = true;
    const problem = draft.trim();
    const style = supportsPresentation ? responseStyle : undefined;
    try {
      if (selected && attachment) {
        await startQuestionBatch(selected, attachment.id, problem, responseStyle);
        setQuestionState(previous => ({ ...previous, busy: true, attachment: null, batch: previous.batch ? { ...previous.batch, status: 'solving', user_instruction: problem } : null }));
        setQuestionVersion(value => value + 1); setDraft('');
        return;
      }
      let session = selected;
      if (!session) {
        session = (await createSession()).id;
        setSessions(previous => [{ id: session!, title: problem.slice(0, 40), tasks: [], tasksLoaded: true, taskCount: 0 }, ...previous]);
        setSelected(session);
      }
      if (!pending.current || pending.current.session !== session || pending.current.problem !== problem || pending.current.style !== style) {
        pending.current = { session, problem, style, key: crypto.randomUUID() };
      }
      const task = await submitTask(session, problem, pending.current.key, style);
      updateTask(task);
      setSessions(previous => {
        const item = previous.find(value => value.id === session)!;
        const tasks = item.tasks.some(value => value.id === task.id) ? item.tasks :
          mergeTasks(item.tasks, [{ id: task.id, problem, createdAt: task.accepted_at }]);
        return [{ ...item, title: item.title || problem.slice(0, 40), tasks,
          taskCount: (item.taskCount ?? item.tasks.length) + (item.tasks.some(value => value.id === task.id) ? 0 : 1) },
          ...previous.filter(value => value.id !== session)];
      });
      pending.current = null; setDraft(''); setCopied(null);
    } catch (failure) { setError(errorMessage(failure)); }
    finally { sendingRef.current = false; setSending(false); composer.current?.focus(); }
  }
  async function mutate(action: 'cancel' | 'resume') {
    if (!latest || mutating) return;
    setMutating(true); setError('');
    try {
      const task = await (action === 'cancel' ? cancelTask : resumeTask)(latest.session_id, latest.id);
      if (action === 'resume') {
        setRecords(previous => ({ ...previous, [latestKey]: { ...(previous[latestKey] || blank()), task, error: undefined } }));
        setWatchVersion(value => value + 1);
      } else updateTask(task);
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 409) {
        try { updateTask(await getTask(latest.session_id, latest.id)); } catch { /* Preserve the last confirmed state. */ }
      }
      setError(errorMessage(failure));
    } finally { setMutating(false); }
  }
  async function copy(task: Task) {
    try { await navigator.clipboard.writeText(task.final_response || ''); setCopied(task.id); }
    catch { setError('复制未成功。'); }
  }
  const isDemo = health?.runtime_mode.includes('fake');
  const isReal = health?.runtime_mode === 'langgraph_staged';
  const elapsed = latest?.started_at ? Math.max(0, ((latest.finished_at ? Date.parse(latest.finished_at) : now)
    - Date.parse(latest.started_at)) / 1000) : 0;

  const sessionSidebar = <>
    <div className="brand"><span className="brand-mark"><Sigma size={22} /></span><span>MathReasoning-Agent<small>数学推理工作台</small></span></div>
    <button className="new-session" onClick={() => selectSession(null)} disabled={sending || historyBusy || fileUploading}><Plus size={18} />新建会话</button>
    <div className="nav-heading">会话{supportsHistory && <button className="icon-button" title="刷新会话" aria-label="刷新会话"
      disabled={historyBusy || sending} onClick={() => setHistoryVersion(value => value + 1)}><RotateCcw size={14} /></button>}</div>
    {historyBusy && <p className="muted" role="status">载入会话中</p>}
    {historyError && <p className="message-error" role="alert">{historyError}</p>}
    <nav aria-label="会话列表" className="session-list">
      {sessions.map(session => <button key={session.id} disabled={sending || fileUploading}
        aria-current={selected === session.id ? 'page' : undefined}
        className={`session-item ${selected === session.id ? 'selected' : ''}`}
        onClick={() => selectSession(session.id)} title={session.title}>
        <MessageSquare size={16} /><span>{session.title || '新会话'}<small>{session.taskCount ?? session.tasks.length} 个问题</small></span>
      </button>)}
      {sessionCursor && <button className="secondary" disabled={historyBusy} onClick={() => void moreSessions()}><ChevronRight size={14} />更多会话</button>}
    </nav>
    <div className="sidebar-bottom"><a href="/trace-viewer" target="_blank" rel="noopener noreferrer"><FileJson size={16} />Trace 工作台</a>
      <span className="local-label">{health?.restart_durable ? '持久存储' : '进程内存储'}</span></div>
  </>;

  const progressPanel = <>
    <div className="panel-heading"><h2>执行进度</h2><span className={`connection ${connection === '重连中' ? 'warning' : ''}`}>{connection}</span></div>
    {latest ? <>
      <div className="task-summary"><span className={`status status-${latest.status}`} data-testid="task-status">{statusNames[latest.status]}</span>
        <span className="duration">{timeLabel(elapsed)}</span></div>
      {latest.status === 'queued' && <p className="muted">队列位置 {latest.queue_position}</p>}
      <ol className="stage-list" aria-label="执行阶段">
        {STAGES.map(stage => {
          const done = latestRecord?.completed.includes(stage);
          const running = active && latest.current_stage === stage;
          const started = latestRecord?.started.includes(stage);
          const skipped = !!latest && terminal(latest.status) && !done;
          return <li key={stage} className={`${done ? 'done' : ''} ${running ? 'current' : ''}`}>
            <span className="stage-icon">{running ? <LoaderCircle size={15} className="spin" /> : done ? <Check size={15} /> : <Circle size={12} />}</span>
            <span>{stageNames[stage]}</span><small>{running ? '执行中' : done ? '已执行' : started ? '未完成' : skipped ? '未执行' : '待执行'}</small>
          </li>;
        })}
      </ol>
      <div className="task-actions">
        {active && <button className="secondary cancel-action" disabled={mutating || latest.status === 'cancelling'} onClick={() => void mutate('cancel')}><Square size={14} />取消任务</button>}
        {latest.status === 'interrupted' && latest.checkpoint_available && latest.error_code !== 'checkpoint_incompatible'
          && <button className="secondary" disabled={mutating} onClick={() => void mutate('resume')}><RotateCcw size={15} />恢复任务</button>}
        <a className="trace-link" target="_blank" rel="noopener noreferrer"
          href={`/trace-viewer#session=${latest.session_id}&task=${latest.id}`}><FileJson size={15} />查看 Trace<ChevronRight size={14} /></a>
      </div>
      <div className="event-heading"><h3>最近事件</h3><span>{latestRecord?.events.length || 0}</span></div>
      <ul className="event-list">{latestRecord?.events.slice(-6).reverse().map(event => <li key={event.sequence}>
        <span>{stageNames[event.stage_id] || '任务事件'}</span><code>{event.event_type}</code>
      </li>)}</ul>
      <div className="task-id">{latest.id}</div>
    </> : <div className="panel-empty"><Circle size={18} /><span>{loading ? '载入任务中' : '暂无任务'}</span></div>}
  </>;

  return <div className="app-shell">
    <aside className="sidebar">{sessionSidebar}</aside>
    <div className="workspace">
      <header className="topbar">
        <button className="icon-button mobile-menu" title="会话列表" aria-label="会话列表" onClick={() => setDrawer('sessions')}><Menu size={20} /></button>
        <div className="page-title"><span>数学解题</span><span className="title-divider" />{currentSession?.title || '新会话'}</div>
        <div className={`runtime-badge ${!ready ? 'offline' : isDemo ? 'demo' : isReal ? 'real' : ''}`}
          title={health ? `${health.runtime_mode} · ${health.storage}` : '服务连接中'} data-testid="runtime-mode">
          <span />{!health ? '连接服务中' : !ready ? '服务未就绪' : isDemo ? '演示运行时' : isReal ? '真实运行时' : health.runtime_mode}
        </div>
        <button className="icon-button mobile-progress" title="执行进度" aria-label="执行进度" onClick={() => setDrawer('progress')}><PanelRightOpen size={20} /></button>
      </header>
      <div className="workspace-body">
        <main className="conversation">
          <div className="message-scroll" ref={scrollArea} onScroll={event => {
            const area = event.currentTarget; followScroll.current = area.scrollHeight - area.scrollTop - area.clientHeight < 100;
          }}>
            <QuestionBatches session={selected} enabled={supportsQuestions}
              disabled={!ready || sending || active || loading || historyBusy || taskHistoryBusy || !!historyError || !!taskHistoryError}
              style={responseStyle} refreshVersion={questionVersion} uploadTarget={questionUploadTarget}
              onSessionCreated={questionSession} onStateChange={setQuestionState} />
            {supportsHistory && <div className="history-controls">
              {taskHistoryBusy && <span className="muted" role="status">载入历史中</span>}
              {taskHistoryError && <><span className="message-error" role="alert">{taskHistoryError}</span>
                <button className="icon-button" title="重试历史加载" aria-label="重试历史加载" onClick={() => setTaskHistoryVersion(value => value + 1)}><RotateCcw size={16} /></button></>}
              {currentSession?.nextCursor && <button className="secondary" disabled={taskHistoryBusy} onClick={() => void olderTasks()}><RotateCcw size={14} />更早的问题</button>}
            </div>}
            {!currentSession?.tasks.length ? !questionState.count && <div className="empty-chat"><span className="empty-mark"><Sigma size={34} strokeWidth={1.6} /></span>
              <h1>MathReasoning-Agent</h1><span className="empty-category">数学解题</span></div> : <div className="messages">
              {currentSession.tasks.map(reference => {
                const record = records[keyFor(currentSession.id, reference.id)], task = record?.task;
                return <section className="exchange" key={reference.id} data-testid="exchange">
                  <div className="user-message"><span className="message-label">问题</span><div className="user-body"><MathMarkdown content={reference.problem} /></div></div>
                  <div className="assistant-message"><div className="message-label"><Sigma size={14} />MathReasoning-Agent
                    <span className="answer-kind">{task?.final_response ? task.status === 'succeeded' ? '最终答案' : '保留候选' : task ? statusNames[task.status] : '载入中'}</span></div>
                    {task?.final_response ? <div className="answer" data-testid="answer"><MathMarkdown content={task.final_response} />
                      <div className="answer-toolbar"><span>{statusNames[task.status]}</span><button className="icon-button" title="复制答案" aria-label="复制答案" onClick={() => void copy(task)}>
                        {copied === task.id ? <Check size={16} /> : <Copy size={16} />}</button></div></div>
                      : record?.error ? <p className="message-error" role="alert">{record.error}</p>
                        : task && !terminal(task.status) ? <div className="waiting" role="status"><LoaderCircle size={17} className="spin" />
                          <span>{task.status === 'queued' ? '等待执行' : task.status === 'cancelling' ? '正在取消' : stageNames[task.current_stage || 'system'] || '正在执行'}</span></div>
                          : task?.status === 'cancelled' ? <p className="muted">任务已取消。</p>
                            : task?.status === 'failed' ? <p className="message-error">{errorMessage(new ApiError(task.error_code || 'failed', 0))}</p>
                              : task?.status === 'interrupted' ? <p className="muted">任务已中断。</p>
                                : task?.status === 'succeeded' ? <p className="message-error">任务已完成，但未收到最终答案。</p>
                                  : <div className="waiting"><LoaderCircle size={16} className="spin" /><span>载入中</span></div>}
                  </div>
                </section>;
              })}
            </div>}
          </div>
          <div className="composer-area">
            {(error || latestRecord?.error || !ready || needsRestart) && <div className="error-banner" role="alert">
              <span>{error || latestRecord?.error || (!ready ? !health ? '正在连接服务。' : '服务暂不可用。' : '当前后端需重启才能启用解题过程展示。')}</span>
              {latestRecord?.error && <button className="icon-button" title="重连任务" aria-label="重连任务" onClick={() => setWatchVersion(value => value + 1)}><RotateCcw size={16} /></button>}
              {error && <button className="icon-button" title="关闭提示" aria-label="关闭提示" onClick={() => setError('')}><X size={16} /></button>}
            </div>}
            <div className="composer-options"><label><SlidersHorizontal size={14} />解答方式
              <select aria-label="解答方式" value={responseStyle} disabled={sending || active || questionBusy || fileUploading || !supportsPresentation}
                onChange={event => setResponseStyle(event.target.value as ResponseStyle)}>
                <option value="auto">按问题要求</option><option value="answer">仅答案</option>
                <option value="brief">简要过程</option><option value="detailed">详细讲解</option>
              </select>
            </label></div>
            <div ref={setQuestionUploadTarget} data-testid="question-upload-slot" />
            <form className="composer" onSubmit={event => { event.preventDefault(); void send(); }}>
              <textarea ref={composer} aria-label="数学问题" placeholder={attachment ? '补充解题要求（可留空）…' : '输入数学问题…'} maxLength={draftLimit} value={draft}
                onChange={event => setDraft(event.target.value)} rows={1} onKeyDown={event => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) {
                    event.preventDefault(); void send();
                  }
                }} />
              {active ? <button className="send-button cancel-button" type="button" title="取消任务" aria-label="取消任务"
                disabled={mutating || latest.status === 'cancelling'} onClick={() => void mutate('cancel')}><Square size={17} fill="currentColor" /></button>
                : <button className="send-button" type="submit" title="发送问题" aria-label="发送问题" disabled={!canSend}>
                  {sending ? <LoaderCircle size={20} className="spin" /> : <ArrowUp size={20} />}</button>}
            </form>
            <div className="composer-meta"><span>{active ? stageNames[latest.current_stage || 'system'] || statusNames[latest.status] : 'MathReasoning-Agent'}</span>
              <span>{draft.length.toLocaleString()} / {draftLimit.toLocaleString()}</span></div>
          </div>
        </main>
        <aside className="progress-panel">{progressPanel}</aside>
      </div>
    </div>
    {drawer && <div className="drawer-backdrop" onClick={() => setDrawer(null)}>
      <div ref={drawerElement} className={`drawer drawer-${drawer}`} role="dialog" aria-modal="true" aria-label={drawer === 'sessions' ? '会话列表' : '执行进度'}
        onClick={event => event.stopPropagation()} onKeyDown={event => { if (event.key === 'Escape') setDrawer(null); }}>
        <button className="icon-button drawer-close" autoFocus title="关闭面板" aria-label="关闭面板" onClick={() => setDrawer(null)}><X size={20} /></button>
        {drawer === 'sessions' ? sessionSidebar : progressPanel}
      </div>
    </div>}
  </div>;
}
