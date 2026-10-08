export const STAGES = ['profile', 'retrieve', 'plan', 'solve', 'tool', 'verify', 'repair', 'finalize'] as const;
export const stageNames: Record<string, string> = {
  profile: '题意分析', retrieve: '策略检索', plan: '解题规划', solve: '推导求解',
  tool: '工具验证', verify: '独立审查', repair: '定向修复', finalize: '整理答案', system: '任务调度',
};
export const statusNames: Record<TaskStatus, string> = {
  queued: '等待执行', running: '正在解题', cancelling: '正在取消', cancelled: '已取消',
  succeeded: '已完成', failed: '执行失败', interrupted: '执行中断',
};
export type TaskStatus = 'queued' | 'running' | 'cancelling' | 'cancelled' | 'succeeded' | 'failed' | 'interrupted';
export type ResponseStyle = 'auto' | 'answer' | 'brief' | 'detailed';
export interface Task {
  id: string; session_id: string; status: TaskStatus; runtime_mode: string;
  current_stage: string | null; final_response: string | null; error_code: string | null;
  accepted_at: string; started_at: string | null; finished_at: string | null;
  deadline_at: string | null; queue_position: number; checkpoint_available: boolean;
  response_style?: ResponseStyle | null;
  question_source?: { batch_id: string; number: number; label: string; filename: string; page_start: number | null; page_end: number | null } | null;
}
export interface TraceEvent {
  task_id: string; session_id: string; sequence: number; stage_id: string;
  event_type: string; created_at: string; payload: Record<string, unknown>;
}
export interface Health { status: string; runtime_mode: string; storage: string; restart_durable: boolean; response_styles?: ResponseStyle[]; server_history?: boolean; document_search?: string; question_attachments?: boolean; question_submission?: string | null }
export interface QuestionItem { number: number; label: string; problem: string; page_start: number | null; page_end: number | null;
  status: TaskStatus | 'pending'; attempt: number; task: Task | null }
export interface QuestionBatch { id: string; session_id: string; original_name: string;
  status: 'parsing' | 'ready' | 'solving' | 'completed' | 'failed' | 'cancelled'; question_count: number; user_instruction?: string | null;
  created_at: string; error_code: string | null; counts: Record<string, number>; questions?: QuestionItem[] }
export interface Page<T> { items: T[]; next_cursor: string | null }
export interface SessionSummary { id: string; title: string; created_at: string; last_activity_at: string; task_count: number }
export interface HistoricalTask extends Task { problem: string }
export const terminal = (status: TaskStatus) => ['succeeded', 'failed', 'cancelled', 'interrupted'].includes(status);
export const taskPath = (session: string, task: string) => `/v1/sessions/${encodeURIComponent(session)}/tasks/${encodeURIComponent(task)}`;

export class ApiError extends Error {
  constructor(public code: string, public status: number) { super(code); }
}
const messages: Record<string, string> = {
  rate_limit_exceeded: '请求过于频繁，请稍后重试。', session_not_found: '会话已不可用，请新建会话。',
  task_not_found: '任务已不可用，服务可能已重启。', not_ready: '服务暂未就绪，请稍后重试。',
  task_already_terminal: '任务已经结束，无法取消。', checkpoint_incompatible: '检查点与当前版本不兼容。',
  invalid_request: '请求内容不符合要求。', task_deadline_exceeded: '任务已达到执行时限。',
  task_not_interrupted: '任务当前不可恢复。', runtime_mismatch: '当前服务与任务的运行模式不一致。',
  unsupported_media_type: '仅支持 PDF 和 Markdown 文件。', file_too_large: '文件不能超过 20 MB。',
  empty_document: '文件内容为空。', media_mismatch: '文件内容与格式不一致。',
  no_extractable_text: '未找到可提取的文本，扫描件暂不支持。',
  storage_capacity_exceeded: '题目附件存储空间不足。', parser_timeout: '文档解析超时。',
  question_service_unavailable: '题目附件暂未启用。', question_batch_active: '本会话已有正在处理的题目附件。',
  question_capacity_exceeded: '待处理题目附件过多，请稍后重试。', question_batch_not_found: '题目批次已不可用。',
  question_upload_conflict: '相同文件已按其他解答设置上传。', ambiguous_question_structure: '题目分隔不明确，请使用“第1题”或“Question 1”等题号。',
  question_not_ready: '题目仍在解析，请稍后提交。', question_start_conflict: '该附件已提交或取消，不能更改本次解题要求。',
  too_many_questions: '每个文件最多包含 20 道题。', question_too_long: '单道题目超过 24,000 字符。',
  empty_question: '发现只有题号、没有内容的题目。', incomplete_pdf_text: 'PDF 存在未提取出文字的页面，请检查扫描页或缺失内容。',
  question_file_contains_solutions: '文件包含答案或解析章节，请上传仅含题目的文件。',
  unreliable_question_text: '文字提取不完整，请检查编码或 PDF 字体。', question_processing_failed: '题目附件处理失败。',
  question_batch_terminal: '题目批次已经结束。', question_not_retryable: '这道题当前不能重试或已达到重试上限。',
  invalid_utf8: 'Markdown 需要使用 UTF-8 编码。', encrypted_pdf: '暂不支持加密 PDF。',
  unclosed_formula_or_fence: '文件中的公式或代码块未闭合。', parse_failed: '文件解析失败，请检查文件内容。',
};
export const errorMessage = (error: unknown) => error instanceof ApiError
  ? messages[error.code] || '请求未成功，请稍后重试。' : '连接未成功，请检查服务后重试。';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(10000);
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
  const headers = options.body instanceof FormData ? options.headers : { 'Content-Type': 'application/json', ...options.headers };
  const response = await fetch(path, { ...options, signal, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(typeof body?.error?.code === 'string' ? body.error.code : 'request_failed', response.status);
  }
  return response.json();
}
export const getHealth = (signal?: AbortSignal) => request<Health>('/health/ready', { signal });
export const createSession = (signal?: AbortSignal) => request<{ id: string }>('/v1/sessions', { method: 'POST', body: '{}', signal });
export const getTask = (session: string, id: string, signal?: AbortSignal) => request<Task>(taskPath(session, id), { signal });
export const getSessions = (cursor?: string | null, signal?: AbortSignal) => request<Page<SessionSummary>>(
  `/v1/sessions?limit=30${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`, { signal });
export const getSessionTasks = (session: string, cursor?: string | null, signal?: AbortSignal) => request<Page<HistoricalTask>>(
  `/v1/sessions/${encodeURIComponent(session)}/tasks?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`, { signal });
export const submitTask = (session: string, problem: string, key: string, responseStyle?: ResponseStyle, signal?: AbortSignal) => request<Task>(
  `/v1/sessions/${encodeURIComponent(session)}/tasks`, {
    method: 'POST', body: JSON.stringify({ problem, response_style: responseStyle,
      metadata: { document_ids: [] } }), headers: { 'Idempotency-Key': key }, signal,
  });
export function validateFile(file: File): string {
  const extension = file.name.toLowerCase().split('.').at(-1);
  const type = extension === 'pdf' ? 'application/pdf' : ['md', 'markdown'].includes(extension || '') ? 'text/markdown' : '';
  if (!type) throw new ApiError('unsupported_media_type', 415);
  if (!file.size) throw new ApiError('empty_document', 400);
  if (file.size > 20 * 1024 * 1024) throw new ApiError('file_too_large', 413);
  return type;
}
export const questionBatchPath = (session: string, id?: string) => `/v1/sessions/${encodeURIComponent(session)}/question-batches${id ? `/${encodeURIComponent(id)}` : ''}`;
export const getQuestionBatches = (session: string, cursor?: string | null, signal?: AbortSignal) => request<Page<QuestionBatch>>(
  `${questionBatchPath(session)}?limit=10${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`, { signal });
export const getQuestionBatch = (session: string, id: string, signal?: AbortSignal) => request<QuestionBatch>(questionBatchPath(session, id), { signal });
export function uploadQuestions(session: string, file: File, style: ResponseStyle, signal?: AbortSignal) {
  const form = new FormData();
  form.append('file', new Blob([file], { type: validateFile(file) }), file.name);
  form.append('response_style', style);
  form.append('document_ids', '[]');
  return request<QuestionBatch>(questionBatchPath(session), { method: 'POST', body: form, signal });
}
export const cancelQuestionBatch = (session: string, id: string) => request<QuestionBatch>(`${questionBatchPath(session, id)}/cancel`, { method: 'POST' });
export const startQuestionBatch = (session: string, id: string, prompt: string, style: ResponseStyle) => request<QuestionBatch>(
  `${questionBatchPath(session, id)}/start`, { method: 'POST', body: JSON.stringify({ prompt, response_style: style }) });
export const retryQuestion = (session: string, id: string, number: number) => request<QuestionBatch>(`${questionBatchPath(session, id)}/questions/${number}/retry`, { method: 'POST' });
export const cancelTask = (session: string, id: string) => request<Task>(`${taskPath(session, id)}/cancel`, { method: 'POST', body: '{}' });
export const resumeTask = (session: string, id: string) => request<Task>(`${taskPath(session, id)}/resume`, { method: 'POST' });

export interface SSEFrame { event: string; data: string; id: string }
// Parse the SSE wire protocol, retaining incomplete frames between network chunks.
export class SSEDecoder {
  private buffer = '';
  push(chunk: string): SSEFrame[] {
    this.buffer += chunk;
    if (this.buffer.length > 1024 * 1024) throw new ApiError('invalid_stream', 0);
    const frames: SSEFrame[] = [];
    let match: RegExpExecArray | null;
    while ((match = /\r?\n\r?\n/.exec(this.buffer))) {
      const block = this.buffer.slice(0, match.index);
      this.buffer = this.buffer.slice(match.index + match[0].length);
      let event = 'message', id = '';
      const data: string[] = [];
      for (const line of block.split(/\r?\n/)) {
        if (!line || line.startsWith(':')) continue;
        const colon = line.indexOf(':');
        const field = colon < 0 ? line : line.slice(0, colon);
        const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
        if (field === 'event') event = value;
        if (field === 'id') id = value;
        if (field === 'data') data.push(value);
      }
      if (data.length) frames.push({ event, data: data.join('\n'), id });
    }
    return frames;
  }
}

export function parseEvent(raw: unknown, session: string, task: string): TraceEvent | null {
  if (!raw || typeof raw !== 'object') return null;
  const value = raw as TraceEvent;
  if (value.session_id !== session || value.task_id !== task || !Number.isSafeInteger(value.sequence)
      || value.sequence < 1 || typeof value.stage_id !== 'string' || typeof value.event_type !== 'string'
      || typeof value.created_at !== 'string' || !value.payload || typeof value.payload !== 'object'
      || Array.isArray(value.payload)) return null;
  return value;
}
export function taskFromEvent(task: Task, event: TraceEvent): Task {
  if ((terminal(task.status) && !(task.status === 'interrupted' && event.event_type === 'task.resumed'))
      || event.task_id !== task.id || event.session_id !== task.session_id) return task;
  const payload = event.payload;
  // Tool/model statuses describe an operation, not the enclosing task.
  const taskEvent = event.event_type.startsWith('task.');
  const status = taskEvent && typeof payload.status === 'string' && Object.hasOwn(statusNames, payload.status)
    ? payload.status as TaskStatus : task.status;
  return { ...task, status,
    current_stage: event.stage_id === 'system' ? task.current_stage : event.stage_id,
    final_response: taskEvent && typeof payload.final_response === 'string' ? payload.final_response : task.final_response,
    error_code: taskEvent && typeof payload.error_code === 'string' ? payload.error_code : task.error_code,
  };
}

export function watchTask(session: string, id: string, callbacks: {
  task: (value: Task) => void; event: (value: TraceEvent) => void;
  connection: (value: string) => void; error: (error: unknown) => void;
}): () => void {
  const controller = new AbortController();
  const { signal } = controller;
  let current: Task | undefined, sequence = 0, poll: ReturnType<typeof setTimeout> | undefined;
  const deliver = (raw: unknown, apply = true) => {
    const event = parseEvent(raw, session, id);
    if (!event || event.sequence <= sequence || signal.aborted) return;
    sequence = event.sequence;
    callbacks.event(event);
    if (current && apply) {
      current = taskFromEvent(current, event);
      callbacks.task(current);
    }
  };
  const sync = async () => {
    const incoming = await getTask(session, id, signal);
    if (!current || !terminal(current.status) || current.status === 'interrupted' || terminal(incoming.status)) current = incoming;
    if (!signal.aborted) callbacks.task(current);
  };
  const stopIfDone = () => {
    if (current && terminal(current.status)) {
      callbacks.connection('已结束');
      controller.abort();
      if (poll) clearTimeout(poll);
      return true;
    }
    return signal.aborted;
  };
  const pollStatus = async () => {
    try { await sync(); } catch (error) {
      if (!signal.aborted) callbacks.error(error);
      if (error instanceof ApiError && error.status === 404) { controller.abort(); return; }
    }
    if (!stopIfDone()) poll = setTimeout(() => void pollStatus(), 3000);
  };
  const run = async () => {
    try {
      await sync();
      for (let page = 0; page < 10 && !signal.aborted; page++) {
        const trace = await request<{ events: unknown[]; next_sequence: number }>(
          `${taskPath(session, id)}/trace?after_sequence=${sequence}&limit=500`, { signal });
        trace.events.forEach(raw => deliver(raw, false));
        if (trace.events.length < 500) break;
      }
      if (!signal.aborted) await sync();
      if (stopIfDone()) return;
      poll = setTimeout(() => void pollStatus(), 3000);
      let retry = 1000;
      while (!signal.aborted) {
        callbacks.connection('连接中');
        try {
          const response = await fetch(`${taskPath(session, id)}/events?after=${sequence}`, { signal });
          if (!response.ok || !response.body) throw new ApiError('stream_unavailable', response.status);
          callbacks.connection('已连接');
          retry = 1000;
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          const sse = new SSEDecoder();
          try {
            while (!signal.aborted) {
              const { value, done } = await reader.read();
              if (done) break;
              for (const frame of sse.push(decoder.decode(value, { stream: true }))) {
                deliver(JSON.parse(frame.data));
              }
              if (current && terminal(current.status)) break;
            }
          } finally {
            await reader.cancel().catch(() => {});
            reader.releaseLock();
          }
          if (!signal.aborted) await sync();
          if (stopIfDone()) return;
        } catch (error) {
          if (signal.aborted) return;
          if (error instanceof ApiError && error.status === 404) throw error;
        }
        callbacks.connection('重连中');
        await new Promise<void>(resolve => {
          const done = () => { clearTimeout(timer); signal.removeEventListener('abort', done); resolve(); };
          const timer = setTimeout(done, retry);
          signal.addEventListener('abort', done, { once: true });
        });
        retry = Math.min(retry * 2, 8000);
      }
    } catch (error) {
      if (!signal.aborted) { callbacks.error(error); callbacks.connection('连接失败'); }
      controller.abort();
      if (poll) clearTimeout(poll);
    }
  };
  void run();
  return () => { controller.abort(); if (poll) clearTimeout(poll); };
}
