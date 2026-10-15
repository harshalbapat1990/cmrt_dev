import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useSaveStatus } from "./useSaveStatus";

describe("useSaveStatus", () => {
  afterEach(() => vi.useRealTimers());

  it("returns to idle after a successful save and cancels the reset when saving again", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSaveStatus(2000));

    act(() => result.current[1]("saved"));
    expect(result.current[0]).toBe("saved");
    act(() => vi.advanceTimersByTime(1500));
    act(() => result.current[1]("saving"));
    act(() => vi.advanceTimersByTime(1000));
    expect(result.current[0]).toBe("saving");
    act(() => result.current[1]("saved"));
    act(() => vi.advanceTimersByTime(2000));
    expect(result.current[0]).toBe("idle");
  });

  it("clears the pending reset when the owner unmounts", () => {
    vi.useFakeTimers();
    const { result, unmount } = renderHook(() => useSaveStatus());
    act(() => result.current[1]("saved"));

    unmount();

    expect(vi.getTimerCount()).toBe(0);
  });
});
