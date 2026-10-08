import { describe, expect, it } from 'vitest';
import { batchMarkdown } from './QuestionBatches';
import type { QuestionBatch } from './api';

describe('question batch exports', () => {
  it('preserves the submitted instruction and represents a ready batch without answers', () => {
    const batch = { original_name: 'ready.md', status: 'ready', user_instruction: 'Explain in Chinese.' } as QuestionBatch;
    expect(batchMarkdown(batch)).toContain('待提交');
    expect(batchMarkdown(batch)).toContain('Explain in Chinese.');
    expect(batchMarkdown(batch)).not.toContain('### 解答');
  });
  it('exports only supplied problems and actual answers, not fabricated completions', () => {
    const batch: QuestionBatch = { id: 'batch', session_id: 'session', original_name: 'exercise.md', status: 'solving',
      question_count: 2, created_at: '', error_code: null, counts: {}, questions: [
        { number: 1, label: 'Q1', problem: '$x+1=3$', status: 'succeeded', page_start: null, page_end: null, attempt: 0,
          task: { final_response: 'Synthetic public answer' } as never },
        { number: 2, label: 'Q2', problem: '$y^2$', status: 'pending', page_start: null, page_end: null, attempt: 0, task: null },
      ] };
    const text = batchMarkdown(batch);
    expect(text).toContain('Synthetic public answer');
    expect(text).toContain('$x+1=3$');
    expect(text).toContain('状态：待执行');
    expect(text).not.toContain('undefined');
  });
  it('exports a failed parse as status rather than an answer', () => {
    const batch = { original_name: 'bad.md', status: 'failed' } as QuestionBatch;
    expect(batchMarkdown(batch)).toContain('处理失败');
    expect(batchMarkdown(batch)).not.toContain('解答');
  });
});
