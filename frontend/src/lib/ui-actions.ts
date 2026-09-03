export async function runOnce<T>(lock: { current: boolean }, action: () => T | Promise<T>) {
  if (lock.current) return;
  lock.current = true;
  try { return await action(); }
  finally { lock.current = false; }
}
