import { useCallback, useEffect, useRef, useState } from "react";

export type SaveStatus = "idle" | "saving" | "saved";

export function useSaveStatus(resetAfterMs = 2000): [SaveStatus, (status: SaveStatus) => void] {
  const [status, setStatus] = useState<SaveStatus>("idle");
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const setSaveStatus = useCallback((next: SaveStatus) => {
    if (resetTimer.current) clearTimeout(resetTimer.current);
    resetTimer.current = null;
    setStatus(next);
    if (next === "saved") {
      resetTimer.current = setTimeout(() => {
        resetTimer.current = null;
        setStatus("idle");
      }, resetAfterMs);
    }
  }, [resetAfterMs]);

  useEffect(() => () => {
    if (resetTimer.current) clearTimeout(resetTimer.current);
  }, []);

  return [status, setSaveStatus];
}
