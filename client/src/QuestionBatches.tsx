import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Download, FileText, FileUp, LoaderCircle, RotateCcw, Square, X } from 'lucide-react';
import { ApiError, cancelQuestionBatch, cancelTask, createSession, errorMessage, getQuestionBatch, getQuestionBatches,
  resumeTask, retryQuestion, stageNames, statusNames, terminal, uploadQuestions, validateFile, type QuestionBatch, type ResponseStyle, type Task } from './api';
import MathMarkdown from './MathMarkdown';

export interface QuestionState { session: string | null; uploading: boolean; busy: boolean; count: number; task?: Task | null; batch?: QuestionBatch | null; attachment?: QuestionBatch | null }
interface Props { session: string | null; enabled: boolean; disabled: boolean;
  style: ResponseStyle; refreshVersion?: number; uploadTarget: HTMLElement | null;
  onSessionCreated: (id: string) => void; onStateChange: (state: QuestionState) => void }
const names = { parsing: '正在拆题', ready: '待提交', solving: '逐题解答中', completed: '处理结束', failed: '处理失败', cancelled: '已取消' };

export function batchMarkdown(batch: QuestionBatch): string {
  return `# ${batch.original_name}\n\n状态：${names[batch.status]}\n\n` + (batch.user_instruction ? `## 解题要求\n\n${batch.user_instruction}\n\n` : '') + (batch.questions || []).map(question =>
    `## 第 ${question.number} 题\n\n${question.problem}\n\n### 解答\n\n` +
    (question.task?.final_response || `状态：${question.status === 'pending' ? '待执行' : statusNames[question.status]}`) + '\n\n').join('');
}

export default function QuestionBatches({ session, enabled, disabled, style, refreshVersion, uploadTarget, onSessionCreated, onStateChange }: Props) {
  const [batches, setBatches] = useState<QuestionBatch[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [attachmentId, setAttachmentId] = useState<string | null>(null);
  const [detail, setDetail] = useState<QuestionBatch | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const current = useRef(session);
  current.current = session;
  const selection = useRef(selected);
  selection.current = selected;
  const controller = useRef<AbortController | null>(null);
  const firstPage = useRef<string | null>(null);
  const cached = useRef<QuestionBatch[]>([]);
  cached.current = batches;

  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => { setBatches([]); setSelected(null); setAttachmentId(null); setDetail(null); setCursor(null); setError(''); setLoaded(!session); firstPage.current = null; }, [session]);
  useEffect(() => {
    if (!enabled || !session) { setLoaded(true); return; }
    setLoaded(false);
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const page = await getQuestionBatches(session!, null, abort.signal);
        const older = cached.current.filter(batch => ['parsing', 'solving'].includes(batch.status) && !page.items.some(row => row.id === batch.id));
        const changes: QuestionBatch[] = [];
        for (const batch of older) changes.push(await getQuestionBatch(session!, batch.id, abort.signal));
        if (abort.signal.aborted) return;
        setBatches(previous => [...new Map([...page.items, ...changes, ...previous.filter(row => !page.items.some(item => item.id === row.id) && !changes.some(item => item.id === row.id))].map(item => [item.id, item])).values()]);
        if (firstPage.current !== session) {
          setCursor(page.next_cursor); firstPage.current = session;
          setAttachmentId(previous => previous || page.items.find(batch => ['ready', 'parsing'].includes(batch.status))?.id || null);
        }
        if (!selection.current && page.items[0]) setSelected(page.items.find(batch => ['ready', 'parsing'].includes(batch.status))?.id || page.items[0].id);
        setLoaded(true); setError('');
      } catch (failure) { if (!abort.signal.aborted) setError(errorMessage(failure)); }
      if (!abort.signal.aborted) timer = setTimeout(() => void refresh(), 3000);
    }
    void refresh();
    return () => { abort.abort(); clearTimeout(timer); };
  }, [session, enabled, version, refreshVersion]);
  useEffect(() => {
    setDetail(null);
    if (!session || !selected || !enabled) return;
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const value = await getQuestionBatch(session!, selected!, abort.signal);
        if (abort.signal.aborted) return;
        setDetail(value);
        setBatches(previous => previous.map(batch => batch.id === value.id ? value : batch));
      } catch (failure) { if (!abort.signal.aborted) setError(errorMessage(failure)); }
      if (!abort.signal.aborted) timer = setTimeout(() => void refresh(), 3000);
    }
    void refresh();
    return () => { abort.abort(); clearTimeout(timer); };
  }, [session, selected, enabled, version, refreshVersion]);
  const busy = batches.some(batch => ['parsing', 'solving'].includes(batch.status));
  const attachment = batches.find(batch => batch.id === attachmentId && ['ready', 'parsing'].includes(batch.status)) || null;
  useEffect(() => { onStateChange({ session, uploading, busy: enabled && (!loaded || busy || !!error), count: batches.length,
    batch: detail, attachment, task: detail?.questions?.find(question => question.task && !terminal(question.task.status))?.task
      || detail?.questions?.filter(question => question.task).at(-1)?.task || null }); },
    [session, enabled, uploading, busy, loaded, error, batches.length, detail, attachment, onStateChange]);

  async function upload(file: File) {
    if (disabled || busy || uploading || controller.current) return;
    try { validateFile(file); } catch (failure) { setError(errorMessage(failure)); if (input.current) input.current.value = ''; return; }
    const abort = new AbortController(); controller.current = abort;
    setUploading(true); setError('');
    try {
      let target = session;
      if (!target) { target = (await createSession(abort.signal)).id; onSessionCreated(target); }
      const value = await uploadQuestions(target, file, style, abort.signal);
      if (!abort.signal.aborted && current.current === target) {
        setBatches(previous => [value, ...previous.filter(item => item.id !== value.id)]);
        setSelected(value.id); setAttachmentId(value.id); setVersion(value => value + 1);
      }
    } catch (failure) { if (!abort.signal.aborted) setError(errorMessage(failure)); }
    finally { controller.current = null; if (!abort.signal.aborted) setUploading(false); if (input.current) input.current.value = ''; }
  }
  async function mutate(action: () => Promise<unknown>) {
    if (mutating) return;
    const target = session;
    setMutating(true); setError('');
    try { await action(); if (current.current === target) setVersion(value => value + 1); }
    catch (failure) { if (current.current === target) setError(errorMessage(failure)); }
    finally { setMutating(false); }
  }
  async function more() {
    if (!session || !cursor || mutating) return;
    const target = session;
    setMutating(true);
    try {
      const page = await getQuestionBatches(target, cursor);
      if (current.current !== target) return;
      setBatches(previous => [...previous, ...page.items.filter(item => !previous.some(row => row.id === item.id))]);
      setCursor(page.next_cursor);
    } catch (failure) { if (current.current === target) setError(errorMessage(failure)); }
    finally { setMutating(false); }
  }
  function download() {
    if (!detail) return;
    const url = URL.createObjectURL(new Blob([batchMarkdown(detail)], { type: 'text/markdown;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = 'question-results.md'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  if (!enabled) return null;
  return <section className="question-workspace" aria-label="题目附件">
    {uploadTarget && createPortal(<div className="question-upload"><button className="secondary" type="button" title="上传题目附件"
      disabled={disabled || busy || uploading || !loaded} onClick={() => input.current?.click()}>
      {uploading ? <LoaderCircle size={16} className="spin" /> : <FileUp size={16} />}上传题目附件</button><span>PDF / Markdown · 最多 20 题</span>
    {attachment && <div className="pending-attachment" data-testid="pending-attachment"><FileText size={15} /><span>{attachment.original_name}<small>{names[attachment.status]} · {attachment.question_count} 题</small></span>
      <button className="icon-button" type="button" title="移除本次附件" aria-label="移除本次附件" disabled={disabled || uploading}
        onClick={() => setAttachmentId(null)}><X size={15} /></button></div>}
    <input ref={input} className="file-input" type="file" accept=".pdf,.md,.markdown" aria-label="题目附件文件"
      onChange={event => { if (event.target.files?.[0]) void upload(event.target.files[0]); }} /></div>, uploadTarget)}
    {error && <div className="question-error"><p className="message-error" role="alert">{error}</p><button className="icon-button" title="刷新题目附件" aria-label="刷新题目附件" onClick={() => setVersion(value => value + 1)}><RotateCcw size={14} /></button></div>}
    {batches.length > 0 && <nav className="question-files" aria-label="题目文件列表">{batches.map(batch => <button type="button" key={batch.id}
      aria-current={selected === batch.id ? 'page' : undefined} onClick={() => { setSelected(batch.id); setAttachmentId(['ready', 'parsing'].includes(batch.status) ? batch.id : null); }} disabled={uploading || disabled}>
      <FileText size={15} /><span>{batch.original_name}<small>{names[batch.status]} · {batch.question_count} 题</small></span></button>)}
      {cursor && <button type="button" disabled={mutating} onClick={() => void more()}><ChevronDown size={14} />更多文件</button>}</nav>}
    {detail && <div className="question-detail" data-testid="question-batch"><div className="question-heading"><h2>{detail.original_name}</h2>
      <span data-testid="batch-status">{names[detail.status]}</span><button className="icon-button" title="导出 Markdown" aria-label="导出题目结果" onClick={download}><Download size={16} /></button>
      {['parsing', 'ready', 'solving'].includes(detail.status) && <button className="secondary" type="button" disabled={mutating} onClick={() => void mutate(() => cancelQuestionBatch(session!, detail.id))}><Square size={13} />取消整批</button>}</div>
      {detail.user_instruction && <div className="user-message"><span className="message-label">解题要求</span><div className="user-body"><MathMarkdown content={detail.user_instruction} /></div></div>}
      <div className="question-counts"><span>已完成 {detail.counts.succeeded || 0} / {detail.question_count}</span>
        {(detail.counts.failed || 0) > 0 && <span>失败 {detail.counts.failed}</span>}{(detail.counts.cancelled || 0) > 0 && <span>取消 {detail.counts.cancelled}</span>}</div>
      {detail.error_code && <p className="message-error" role="alert">{errorMessage(new ApiError(detail.error_code, 0))}</p>}
      {detail.status === 'parsing' && <div className="waiting" role="status"><LoaderCircle size={16} className="spin" />正在解析题目</div>}
      {detail.questions?.map(question => <section className="question-result exchange" key={question.number} data-testid="question-result">
        <div className="question-row"><h3>第 {question.number} 题</h3><span>{question.status === 'pending' ? '待执行' : statusNames[question.status]}</span>
          {question.page_start !== null && <small>第 {question.page_start}{question.page_end !== question.page_start ? `-${question.page_end}` : ''} 页</small>}
          {question.task && !terminal(question.task.status) && <button className="icon-button" title="取消本题" aria-label={`取消第 ${question.number} 题`} disabled={mutating}
            onClick={() => void mutate(() => cancelTask(session!, question.task!.id))}><Square size={13} /></button>}
          {question.task?.status === 'interrupted' && question.task.checkpoint_available && question.task.error_code !== 'checkpoint_incompatible' && <button className="icon-button" title="恢复本题" aria-label={`恢复第 ${question.number} 题`} disabled={mutating}
            onClick={() => void mutate(() => resumeTask(session!, question.task!.id))}><RotateCcw size={14} /></button>}
          {['failed', 'cancelled'].includes(question.status) && detail.status !== 'cancelled' && question.attempt < 2 && <button className="icon-button" title="重新解答本题" aria-label={`重试第 ${question.number} 题`} disabled={mutating}
            onClick={() => void mutate(() => retryQuestion(session!, detail.id, question.number))}><RotateCcw size={14} /></button>}</div>
        <details className="question-stem" open><summary>题目</summary><MathMarkdown content={question.problem} /></details>
        {question.task?.final_response ? <div className="answer" data-testid="question-answer"><MathMarkdown content={question.task.final_response} /></div>
          : question.task?.error_code ? <p className="message-error">{errorMessage(new ApiError(question.task.error_code, 0))}</p>
            : question.task && !terminal(question.task.status) ? <div className="waiting"><LoaderCircle size={15} className="spin" />{stageNames[question.task.current_stage || 'system'] || '等待执行'}</div> : null}
        {question.task && <a className="trace-link" href={`/trace-viewer#session=${session}&task=${question.task.id}`} target="_blank" rel="noopener noreferrer">查看 Trace</a>}
      </section>)}
    </div>}
  </section>;
}
