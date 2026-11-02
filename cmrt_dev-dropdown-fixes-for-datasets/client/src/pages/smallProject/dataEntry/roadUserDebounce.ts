export type TimerRegistry = Record<string, ReturnType<typeof setTimeout> | undefined>;

/** Replace a pending task for the same road or rail row. */
export function scheduleDebouncedTask(
  timers: TimerRegistry,
  key: string,
  delayMs: number,
  task: () => void,
): void {
  const pending = timers[key];
  if (pending) clearTimeout(pending);
  timers[key] = setTimeout(task, delayMs);
}
