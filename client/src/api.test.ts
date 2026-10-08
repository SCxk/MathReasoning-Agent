import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, getSessions, getSessionTasks, parseEvent, SSEDecoder, submitTask, startQuestionBatch, taskFromEvent, uploadQuestions, validateFile, watchTask, type Task, type TraceEvent } from './api';

const session = '00000000-0000-4000-8000-000000000001';
const id = '00000000-0000-4000-8000-000000000002';
const task: Task = { id, session_id: session, status: 'running', runtime_mode: 'fake',
  current_stage: 'solve', final_response: null, error_code: null, accepted_at: new Date().toISOString(),
  started_at: null, finished_at: null, deadline_at: null, queue_position: 0, checkpoint_available: false };
const event: TraceEvent = { task_id: id, session_id: session, sequence: 1,
  stage_id: 'solve', event_type: 'stage.completed', created_at: new Date().toISOString(), payload: {} };
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe('server history requests', () => {
  it('uses bounded pages and encodes opaque cursors', async () => {
    const fetch = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ items: [], next_cursor: null })));
    vi.stubGlobal('fetch', fetch);
    await getSessions('cursor+/=');
    await getSessionTasks(session, 'cursor+/=');
    expect(fetch.mock.calls[0][0]).toBe('/v1/sessions?limit=30&cursor=cursor%2B%2F%3D');
    expect(fetch.mock.calls[1][0]).toBe(`/v1/sessions/${session}/tasks?limit=20&cursor=cursor%2B%2F%3D`);
  });
  it('reports a server outage instead of returning an empty history', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'storage_unavailable' } }), { status: 503 })));
    await expect(getSessions()).rejects.toMatchObject({ code: 'storage_unavailable', status: 503 });
  });
});

describe('question attachment requests without reference documents', () => {
  it('starts only through a separate explicit prompt request', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('{"status":"solving"}'));
    vi.stubGlobal('fetch', fetch);
    await startQuestionBatch(session, id, 'Explain each step.', 'detailed');
    expect(fetch.mock.calls[0][0]).toBe(`/v1/sessions/${session}/question-batches/${id}/start`);
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ prompt: 'Explain each step.', response_style: 'detailed' });
  });
  it('allows explicitly sending a question attachment without an instruction', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('{"status":"solving"}'));
    vi.stubGlobal('fetch', fetch);
    await startQuestionBatch(session, id, '', 'auto');
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ prompt: '', response_style: 'auto' });
  });
  it.each(['notes.md', 'NOTES.MARKDOWN', 'book.PDF'])('normalizes browser MIME by file extension: %s', async name => {
    const file = new File(['Fixture content'], name, { type: '' });
    const expected = name.toLowerCase().endsWith('.pdf') ? 'application/pdf' : 'text/markdown';
    expect(validateFile(file)).toBe(expected);
    const fetch = vi.fn().mockResolvedValue(new Response('{}'));
    vi.stubGlobal('fetch', fetch);
    await uploadQuestions(session, file, 'detailed');
    const options = fetch.mock.calls[0][1];
    expect(options.headers).toBeUndefined();
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get('file').type).toBe(expected);
    expect(options.body.get('file').name).toBe(name);
    expect(fetch.mock.calls[0][0]).toBe(`/v1/sessions/${session}/question-batches`);
    expect(options.body.get('response_style')).toBe('detailed');
    expect(options.body.get('document_ids')).toBe('[]');
  });
  it('rejects empty, unsupported and oversized files before uploading', () => {
    expect(() => validateFile(new File([], 'empty.md'))).toThrow(ApiError);
    expect(() => validateFile(new File(['fixture'], 'archive.zip'))).toThrow(ApiError);
    expect(() => validateFile({ name: 'big.pdf', size: 20 * 1024 * 1024 + 1 } as File)).toThrow(ApiError);
  });
  it('always disables document retrieval, including on an older RAG-enabled backend', async () => {
    const fetch = vi.fn().mockImplementation(async () => new Response('{}'));
    vi.stubGlobal('fetch', fetch);
    await submitTask(session, 'fixture', 'key', 'brief');
    expect(JSON.parse(fetch.mock.calls[0][1].body).metadata).toEqual({ document_ids: [] });
    await submitTask(session, 'fixture', 'key');
    expect(JSON.parse(fetch.mock.calls[1][1].body).metadata).toEqual({ document_ids: [] });
  });
});

describe('SSE wire protocol', () => {
  it('handles CRLF split across chunks, comments and multiline data', () => {
    const decoder = new SSEDecoder();
    expect(decoder.push(': heartbeat\r\n\r\n')).toEqual([]);
    expect(decoder.push('id: 4\r\nevent: stage.completed\r\ndata: {\r\ndata: "ok":true}\r')).toEqual([]);
    expect(decoder.push('\n\r\n')).toEqual([{ id: '4', event: 'stage.completed', data: '{\n"ok":true}' }]);
  });
  it('retains the last incomplete frame and accepts unknown fields', () => {
    const decoder = new SSEDecoder();
    expect(decoder.push('retry: 10\ndata: one\n\ndata: tw')).toEqual([{ id: '', event: 'message', data: 'one' }]);
    expect(decoder.push('o\n\n')).toEqual([{ id: '', event: 'message', data: 'two' }]);
  });
  it('bounds incomplete payloads', () => {
    expect(() => new SSEDecoder().push('x'.repeat(1024 * 1024 + 1))).toThrow(ApiError);
  });
});
describe('event isolation and state', () => {
  it.each([null, [], { ...event, task_id: 'other' }, { ...event, session_id: 'other' },
    { ...event, sequence: 0 }, { ...event, sequence: 1.5 }, { ...event, payload: [] },
    { ...event, stage_id: 1 }])('rejects foreign or invalid events: %j', raw => {
    expect(parseEvent(raw, session, id)).toBeNull();
  });
  it('keeps valid events', () => { expect(parseEvent(event, session, id)).toEqual(event); });
  it('keeps a terminal snapshot when historical events replay', () => {
    const completed = { ...task, status: 'succeeded' as const, final_response: 'Final fixture.' };
    expect(taskFromEvent(completed, { ...event, payload: { status: 'running' } })).toBe(completed);
  });
  it('applies actual final results and ignores unknown statuses', () => {
    const taskEvent = { ...event, event_type: 'task.succeeded' };
    expect(taskFromEvent(task, { ...taskEvent, payload: { status: 'succeeded', final_response: '$x=2$' } })).toMatchObject({ status: 'succeeded', final_response: '$x=2$' });
    expect(taskFromEvent(task, { ...taskEvent, payload: { status: 'imaginary' } }).status).toBe('running');
    expect(taskFromEvent(task, { ...taskEvent, payload: { status: '__proto__' } }).status).toBe('running');
    expect(taskFromEvent(task, { ...event, session_id: 'other' })).toBe(task);
  });
  it.each(['tool.completed', 'tool.failed', 'model.failed', 'retrieval.completed', 'stage.completed'])(
    'isolates task status, answer and error from %s', event_type => {
      for (const status of ['succeeded', 'failed']) {
        expect(taskFromEvent(task, { ...event, event_type,
          payload: { status, final_response: 'Operation output.', error_code: 'operation_failed' },
        })).toMatchObject({ status: 'running', final_response: null, error_code: null });
      }
    },
  );
  it('still applies task cancellation, failure and resume events', () => {
    expect(taskFromEvent(task, { ...event, event_type: 'task.cancelling', payload: { status: 'cancelling' } }).status).toBe('cancelling');
    expect(taskFromEvent(task, { ...event, event_type: 'task.failed', payload: { status: 'failed', error_code: 'runtime_failed' } })).toMatchObject({ status: 'failed', error_code: 'runtime_failed' });
    expect(taskFromEvent({ ...task, status: 'interrupted' }, { ...event,
      event_type: 'task.resumed', payload: { status: 'queued' },
    }).status).toBe('queued');
  });
});
it.each(['succeeded', 'failed'])('keeps SSE open after a tool %s event until the task finishes', async status => {
  const operation = { ...event, stage_id: 'retrieve', event_type: status === 'succeeded' ? 'tool.completed' : 'tool.failed',
    payload: { status, error_code: 'operation_fixture' } };
  const completed = { ...event, sequence: 2, event_type: 'task.succeeded',
    payload: { status: 'succeeded', final_response: 'Final fixture after tool execution.' } };
  let stream!: ReadableStreamDefaultController<Uint8Array>;
  const encoder = new TextEncoder();
  const fetcher = vi.fn(async (path: string) => {
    if (path.includes('/trace?')) return new Response(JSON.stringify({ events: [] }));
    if (path.includes('/events?')) return new Response(new ReadableStream<Uint8Array>({ start(controller) {
      stream = controller;
      controller.enqueue(encoder.encode(`data: ${JSON.stringify(operation)}\n\n`));
    } }));
    return new Response(JSON.stringify(task));
  });
  vi.stubGlobal('fetch', fetcher);
  const callbacks = { task: vi.fn(), event: vi.fn(), connection: vi.fn(), error: vi.fn() };
  const stop = watchTask(session, id, callbacks);
  try {
    await vi.waitFor(() => expect(callbacks.event).toHaveBeenCalledWith(operation));
    expect(callbacks.task.mock.calls.at(-1)?.[0]).toMatchObject({ status: 'running', final_response: null, error_code: null });
    expect(callbacks.connection).not.toHaveBeenCalledWith('已结束');
    stream.enqueue(encoder.encode(`data: ${JSON.stringify(completed)}\n\n`));
    stream.close();
    await vi.waitFor(() => expect(callbacks.connection).toHaveBeenCalledWith('已结束'));
    expect(callbacks.event).toHaveBeenCalledWith(completed);
    expect(callbacks.task.mock.calls.at(-1)?.[0]).toMatchObject({ status: 'succeeded', final_response: completed.payload.final_response });
    expect(callbacks.error).not.toHaveBeenCalled();
  } finally { stop(); }
});
it('submits through the existing endpoint and retains the supplied idempotency key', async () => {
  const fetcher = vi.fn(async () => new Response(JSON.stringify(task), { status: 202 }));
  vi.stubGlobal('fetch', fetcher);
  await submitTask(session, 'Test protocol input.', 'fixed-key');
  await submitTask(session, 'Test protocol input.', 'fixed-key');
  expect(fetcher.mock.calls).toHaveLength(2);
  const [path, options] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
  expect(path).toBe(`/v1/sessions/${session}/tasks`);
  expect(options.headers).toMatchObject({ 'Idempotency-Key': 'fixed-key' });
  expect(JSON.parse(options.body as string)).toEqual({ problem: 'Test protocol input.', metadata: { document_ids: [] } });
});
it.each(['auto', 'answer', 'brief', 'detailed'] as const)('submits the selected %s presentation as a task field', async style => {
  const fetcher = vi.fn(async () => new Response(JSON.stringify(task), { status: 202 }));
  vi.stubGlobal('fetch', fetcher);
  await submitTask(session, 'User presentation request.', 'style-key', style);
  const [, options] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
  expect(JSON.parse(options.body as string)).toEqual({ problem: 'User presentation request.', response_style: style, metadata: { document_ids: [] } });
});
it('deduplicates events and closes after a terminal task', async () => {
  const terminalEvent = { ...event, sequence: 2, event_type: 'task.succeeded', payload: { status: 'succeeded', final_response: 'Fixture completed.' } };
  let statusCalls = 0;
  const fetcher = vi.fn(async (path: string) => {
    if (path.includes('/trace?')) return new Response(JSON.stringify({ events: [], next_sequence: 0 }));
    if (path.includes('/events?')) return new Response([event, event, terminalEvent].map(item =>
      `event: ${item.event_type}\ndata: ${JSON.stringify(item)}\n\n`).join(''), { headers: { 'Content-Type': 'text/event-stream' } });
    statusCalls++;
    return new Response(JSON.stringify(statusCalls <= 2 ? task : { ...task, status: 'succeeded', final_response: 'Fixture completed.' }));
  });
  vi.stubGlobal('fetch', fetcher);
  const callbacks = { task: vi.fn(), event: vi.fn(), connection: vi.fn(), error: vi.fn() };
  const stop = watchTask(session, id, callbacks);
  await vi.waitFor(() => expect(callbacks.connection).toHaveBeenCalledWith('已结束'));
  expect(callbacks.event.mock.calls).toHaveLength(2);
  expect(callbacks.task.mock.calls.at(-1)?.[0].status).toBe('succeeded');
  expect(callbacks.error).not.toHaveBeenCalled();
  stop();
});
it('does not open SSE for an already completed task', async () => {
  const fetcher = vi.fn(async (path: string) => new Response(JSON.stringify(path.includes('/trace?')
    ? { events: [event], next_sequence: 1 } : { ...task, status: 'cancelled' })));
  vi.stubGlobal('fetch', fetcher);
  const callbacks = { task: vi.fn(), event: vi.fn(), connection: vi.fn(), error: vi.fn() };
  const stop = watchTask(session, id, callbacks);
  await vi.waitFor(() => expect(callbacks.connection).toHaveBeenCalledWith('已结束'));
  expect(fetcher.mock.calls.some(([path]) => path.includes('/events?'))).toBe(false);
  expect(callbacks.event).toHaveBeenCalledTimes(1);
  stop();
});
it('does not let interrupted historical events stop an already resumed task', async () => {
  const interrupted = { ...event, event_type: 'task.interrupted', payload: { status: 'interrupted' } };
  const completed = { ...event, sequence: 2, event_type: 'task.succeeded', payload: { status: 'succeeded', final_response: 'Resumed fixture.' } };
  const fetcher = vi.fn(async (path: string) => {
    if (path.includes('/trace?')) return new Response(JSON.stringify({ events: [interrupted] }));
    if (path.includes('/events?')) return new Response(`data: ${JSON.stringify(completed)}\n\n`);
    return new Response(JSON.stringify(task));
  });
  vi.stubGlobal('fetch', fetcher);
  const callbacks = { task: vi.fn(), event: vi.fn(), connection: vi.fn(), error: vi.fn() };
  const stop = watchTask(session, id, callbacks);
  await vi.waitFor(() => expect(callbacks.connection).toHaveBeenCalledWith('已结束'));
  expect(fetcher.mock.calls.some(([path]) => path.endsWith('/events?after=1'))).toBe(true);
  expect(callbacks.task.mock.calls.at(-1)?.[0].status).toBe('succeeded');
  stop();
});
