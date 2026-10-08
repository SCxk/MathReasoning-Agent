import { afterEach, describe, expect, it, vi } from 'vitest';
import { mergeTasks, parseHistory, readSelected, saveHistory, saveSelected } from './history';

const id = '00000000-0000-4000-8000-000000000001';
afterEach(() => vi.unstubAllGlobals());
describe('bounded browser history', () => {
  it.each([null, 'invalid json', '{}', 'null', JSON.stringify([{ id: '../foreign', title: '', tasks: [] }])])('handles corrupt history: %s', raw => {
    expect(parseHistory(raw)).toEqual([]);
  });
  it('keeps local references only and drops additional fields', () => {
    const parsed = parseHistory(JSON.stringify([{ id, title: 'session', secret: 'not retained', tasks: [
      { id, problem: 'Question', createdAt: 'date', response: 'not retained' }, { id: 'invalid', problem: 'foreign', createdAt: 'date' },
    ] }]));
    expect(parsed).toEqual([{ id, title: 'session', tasks: [{ id, problem: 'Question', createdAt: 'date' }] }]);
  });
  it('caps questions, titles, session count and task count', () => {
    const values = Array.from({ length: 40 }, () => ({ id, title: 'a'.repeat(70),
      tasks: Array.from({ length: 25 }, () => ({ id, problem: 'b'.repeat(25000), createdAt: 'date' })) }));
    // Stay within the raw input cap when checking the count bounds.
    const result = parseHistory(JSON.stringify(values.map(value => ({ ...value,
      tasks: value.tasks.map(task => ({ ...task, problem: 'short' })) }))));
    expect(result).toHaveLength(30);
    expect(result[0].title).toHaveLength(60);
    expect(result[0].tasks).toHaveLength(20);
    expect(parseHistory(JSON.stringify([values[0]]))[0].tasks[0].problem).toHaveLength(24000);
  });
  it('rejects oversized history before parsing', () => {
    expect(parseHistory(' '.repeat(2_000_001))).toEqual([]);
  });
  it('keeps large saved history within the readable cap', () => {
    const setItem = vi.fn();
    vi.stubGlobal('localStorage', { setItem });
    const session = { id, title: 'fixture', tasks: Array.from({ length: 20 }, () => ({ id, problem: 'x'.repeat(24000), createdAt: 'date' })) };
    expect(saveHistory(Array.from({ length: 30 }, () => session))).toBe(true);
    const serialized = setItem.mock.calls[0][1];
    expect(serialized.length).toBeLessThan(1_500_000);
    expect(parseHistory(serialized).length).toBeGreaterThan(0);
  });
  it('reports storage quota failure without throwing', () => {
    vi.stubGlobal('localStorage', { setItem: () => { throw new Error('quota'); } });
    expect(saveHistory([])).toBe(false);
  });
});

describe('server-backed history preferences', () => {
  it('stores only a selected ID and removes the legacy question cache', () => {
    const setItem = vi.fn(), removeItem = vi.fn();
    vi.stubGlobal('localStorage', { setItem, removeItem, getItem: () => id });
    saveSelected(id);
    expect(setItem).toHaveBeenCalledExactlyOnceWith('maths-chat-selected-v1', id);
    expect(removeItem).toHaveBeenCalledWith('maths-chat-history-v1');
    expect(readSelected()).toBe(id);
    saveSelected(null);
    expect(removeItem).toHaveBeenCalledWith('maths-chat-selected-v1');
  });
  it('does not make preference failures fatal', () => {
    vi.stubGlobal('localStorage', { getItem: () => { throw Error(); }, setItem: () => { throw Error(); } });
    expect(readSelected()).toBeNull();
    expect(() => saveSelected(id)).not.toThrow();
  });
  it('merges older pages chronologically and deduplicates task IDs', () => {
    const latest = { id, problem: 'Latest', createdAt: '2026-10-05T02:00:00Z' };
    const older = { id: 'older', problem: 'Older', createdAt: '2026-10-05T01:00:00Z' };
    expect(mergeTasks([latest], [latest, older])).toEqual([older, latest]);
  });
});
