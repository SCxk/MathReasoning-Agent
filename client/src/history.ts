export interface TaskRef { id: string; problem: string; createdAt: string }
export interface SessionRef { id: string; title: string; tasks: TaskRef[]; taskCount?: number; tasksLoaded?: boolean; nextCursor?: string | null }
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const KEY = 'maths-chat-history-v1';
const SELECTED_KEY = 'maths-chat-selected-v1';
export const readSelected = () => {
  try { const value = localStorage.getItem(SELECTED_KEY); return value && uuid.test(value) ? value : null; }
  catch { return null; }
};
export const saveSelected = (id: string | null) => {
  try {
    if (id) localStorage.setItem(SELECTED_KEY, id); else localStorage.removeItem(SELECTED_KEY);
    localStorage.removeItem(KEY);
  } catch { /* Preferences must not block server-backed history. */ }
};
export function mergeTasks(before: TaskRef[], incoming: TaskRef[]): TaskRef[] {
  return [...new Map([...before, ...incoming].map(task => [task.id, task])).values()]
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt) || a.id.localeCompare(b.id));
}
export function parseHistory(raw: string | null): SessionRef[] {
  try {
    if (!raw || raw.length > 2_000_000) return [];
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return [];
    return value.slice(0, 30).filter((item): item is SessionRef => !!item && uuid.test(item.id)
      && typeof item.title === 'string' && Array.isArray(item.tasks))
      .map(item => ({ id: item.id, title: item.title.slice(0, 60), tasks: item.tasks.slice(-20)
        .filter(task => task && uuid.test(task.id) && typeof task.problem === 'string'
          && typeof task.createdAt === 'string')
        .map(task => ({ id: task.id, problem: task.problem.slice(0, 24000), createdAt: task.createdAt })) }));
  } catch { return []; }
}
export const readHistory = () => { try { return parseHistory(localStorage.getItem(KEY)); } catch { return []; } };
export const saveHistory = (sessions: SessionRef[]) => {
  try {
    const bounded = sessions.slice(0, 30).map(session => ({ ...session, tasks: session.tasks.slice(-20) }));
    let value = JSON.stringify(bounded);
    while (value.length > 1_500_000 && bounded.length > 1) {
      bounded.pop(); value = JSON.stringify(bounded);
    }
    localStorage.setItem(KEY, value);
    return true;
  } catch { return false; }
};
