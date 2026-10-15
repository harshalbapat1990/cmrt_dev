import { afterEach, describe, expect, it, vi } from "vitest";
import { scheduleDebouncedTask, type TimerRegistry } from "./roadUserDebounce";

describe("scheduleDebouncedTask", () => {
  afterEach(() => vi.useRealTimers());

  it("runs only the latest scheduled edit for a row after the debounce interval", () => {
    vi.useFakeTimers();
    const timers: TimerRegistry = {};
    const first = vi.fn();
    const latest = vi.fn();

    scheduleDebouncedTask(timers, "2030-rail-1", 800, first);
    vi.advanceTimersByTime(500);
    scheduleDebouncedTask(timers, "2030-rail-1", 800, latest);
    vi.advanceTimersByTime(799);

    expect(first).not.toHaveBeenCalled();
    expect(latest).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(first).not.toHaveBeenCalled();
    expect(latest).toHaveBeenCalledOnce();
  });

  it("keeps pending tasks for different rows independent", () => {
    vi.useFakeTimers();
    const timers: TimerRegistry = {};
    const firstRow = vi.fn();
    const secondRow = vi.fn();

    scheduleDebouncedTask(timers, "rail-1", 800, firstRow);
    scheduleDebouncedTask(timers, "rail-2", 800, secondRow);
    vi.advanceTimersByTime(800);

    expect(firstRow).toHaveBeenCalledOnce();
    expect(secondRow).toHaveBeenCalledOnce();
  });
});
