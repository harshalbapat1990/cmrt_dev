import React, { useEffect, useId, useMemo, useRef, useState } from "react";

/** Shape for value: 1-based month (1..12) and full year */
export type YearMonth = { year: number; month: number };

type Placement = "bottom-start" | "bottom-end" | "top-start" | "top-end";

export interface MonthYearPickerProps {
  value?: YearMonth;
  defaultValue?: YearMonth;
  onChange?: (ym: YearMonth) => void;
  min?: YearMonth;
  max?: YearMonth;
  locale?: string;
  formatButtonLabel?: (ym: YearMonth) => string;
  placeholder?: string;
  disabled?: boolean;
  ariaLabel?: string;
  placement?: Placement;
  className?: string;
}

/** Utility: compare YearMonth (year-major) */
function compareYM(a: YearMonth, b: YearMonth): number {
  if (a.year !== b.year) return a.year - b.year;
  return a.month - b.month;
}

/** Utility: clamp YearMonth to [min, max] if provided */
function clampYM(ym: YearMonth, min?: YearMonth, max?: YearMonth): YearMonth {
  let res = { ...ym };
  if (min && compareYM(res, min) < 0) res = { ...min };
  if (max && compareYM(res, max) > 0) res = { ...max };
  return res;
}

function isWithin(ym: YearMonth, min?: YearMonth, max?: YearMonth) {
  if (min && compareYM(ym, min) < 0) return false;
  if (max && compareYM(ym, max) > 0) return false;
  return true;
}

const DEFAULT_PLACEHOLDER = "Select month…";

export const DatePicker: React.FC<MonthYearPickerProps> = ({
  value,
  defaultValue,
  onChange,
  min,
  max,
  locale,
  formatButtonLabel,
  placeholder = DEFAULT_PLACEHOLDER,
  disabled,
  ariaLabel = "Choose month and year",
  placement = "bottom-start",
  className,
}) => {
  const inputId = useId();
  const popoverId = useId();

  const isControlled = value !== undefined;
  const [internal, setInternal] = useState<YearMonth | undefined>(() => {
    const base =
      defaultValue ??
      clampYM(
        {
          year: new Date().getFullYear(),
          month: new Date().getMonth() + 1,
        },
        min,
        max
      );
    return base;
  });
  const selected = isControlled ? value : internal;

  // View state for the popover (year scroller)
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState<number>(
    () =>
      selected?.year ??
      clampYM(
        { year: new Date().getFullYear(), month: new Date().getMonth() + 1 },
        min,
        max
      ).year
  );
  const [activeMonth, setActiveMonth] = useState<number>(
    () => selected?.month ?? new Date().getMonth() + 1
  );

  const inputRef = useRef<HTMLInputElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const firstInteractiveRef = useRef<HTMLButtonElement | null>(null);

  // Locale-aware month names
  const monthFormatter = useMemo(() => {
    try {
      return new Intl.DateTimeFormat(locale || undefined, { month: "short" });
    } catch {
      return new Intl.DateTimeFormat(undefined, { month: "short" });
    }
  }, [locale]);

  const fullFormatter = useMemo(() => {
    if (formatButtonLabel) return null;
    try {
      return new Intl.DateTimeFormat(locale || undefined, {
        year: "numeric",
        month: "long",
      });
    } catch {
      return new Intl.DateTimeFormat(undefined, {
        year: "numeric",
        month: "long",
      });
    }
  }, [locale, formatButtonLabel]);

  const inputText = useMemo(() => {
    if (!selected) return "";
    if (formatButtonLabel) return formatButtonLabel(selected);
    const dt = new Date(selected.year, selected.month - 1, 1);
    return fullFormatter!.format(dt);
  }, [selected, fullFormatter, formatButtonLabel]);

  // Open/close management
  const openPopover = () => {
    if (disabled) return;
    setViewYear(selected?.year ?? viewYear);
    setActiveMonth(selected?.month ?? activeMonth);
    setOpen(true);
  };
  const closePopover = () => setOpen(false);

  // Close on outside click / Escape
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      const t = e.target as Node;
      if (
        popoverRef.current &&
        !popoverRef.current.contains(t) &&
        inputRef.current &&
        !inputRef.current.contains(t)
      ) {
        closePopover();
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        closePopover();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  // Focus the first interactive element when opened (the first month button)
  useEffect(() => {
    if (open) {
      const id = window.setTimeout(() => {
        firstInteractiveRef.current?.focus();
      }, 0);
      return () => window.clearTimeout(id);
    }
  }, [open]);

  // Helper: commit selection
  const commit = (ym: YearMonth) => {
    if (!isWithin(ym, min, max)) return;
    if (!isControlled) setInternal(ym);
    onChange?.(ym);
    closePopover();
    // Return focus to input for better a11y
    inputRef.current?.focus();
  };

  // Helper: whether a month is disabled
  const isMonthDisabled = (y: number, m: number) =>
    !isWithin({ year: y, month: m }, min, max);

  // Keyboard handling for input trigger
  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    switch (e.key) {
      case "Enter":
      case " ":
      case "ArrowDown":
        e.preventDefault();
        openPopover();
        break;
      case "Escape":
        if (open) {
          e.preventDefault();
          closePopover();
        }
        break;
      default:
        break;
    }
  };

  // Keyboard handling inside the grid (months)
  const handleMonthKeyDown = (
    e: React.KeyboardEvent<HTMLButtonElement>,
    m: number
  ) => {
    let nextYear = viewYear;
    let nextMonth = m;

    switch (e.key) {
      case "ArrowRight":
        nextMonth = m === 12 ? 1 : m + 1;
        if (m === 12) nextYear = viewYear + 1;
        e.preventDefault();
        break;
      case "ArrowLeft":
        nextMonth = m === 1 ? 12 : m - 1;
        if (m === 1) nextYear = viewYear - 1;
        e.preventDefault();
        break;
      case "ArrowDown":
        nextMonth = m + 3;
        if (nextMonth > 12) {
          nextMonth = ((nextMonth - 1) % 12) + 1;
          nextYear = viewYear + 1;
        }
        e.preventDefault();
        break;
      case "ArrowUp":
        nextMonth = m - 3;
        if (nextMonth < 1) {
          nextMonth = 12 - (-nextMonth % 12);
          nextYear = viewYear - 1;
        }
        e.preventDefault();
        break;
      case "Home":
        nextMonth = 1;
        e.preventDefault();
        break;
      case "End":
        nextMonth = 12;
        e.preventDefault();
        break;
      case "PageUp":
        nextYear = viewYear - 1;
        e.preventDefault();
        break;
      case "PageDown":
        nextYear = viewYear + 1;
        e.preventDefault();
        break;
      case "Enter":
      case " ":
        {
          const ym = { year: viewYear, month: m };
          if (!isMonthDisabled(viewYear, m)) commit(ym);
        }
        e.preventDefault();
        return;
      case "Escape":
        closePopover();
        inputRef.current?.focus();
        e.preventDefault();
        return;
      default:
        return;
    }

    setViewYear(nextYear);
    setActiveMonth(nextMonth);

    requestAnimationFrame(() => {
      const btn = document.querySelector<HTMLButtonElement>(
        `#${popoverId}-m-${nextYear}-${nextMonth}`
      );
      btn?.focus();
    });
  };

  // Month label for a given index
  const monthLabel = (m: number) => {
    const dt = new Date(2000, m - 1, 1); // Year doesn't matter for month name
    return monthFormatter.format(dt);
  };

  // Tailwind classes for popover placement (no inline styles)
  const placementClass =
    placement === "bottom-start"
      ? "left-0 top-full mt-2"
      : placement === "bottom-end"
      ? "right-0 top-full mt-2"
      : placement === "top-start"
      ? "left-0 bottom-full mb-2"
      : "right-0 bottom-full mb-2";

  // Bound year navigation to min/max years (optional, UX nicety)
  const canGoPrev = !min || viewYear > min.year;
  const canGoNext = !max || viewYear < max.year;

  // Ensure viewYear stays in range if min/max change
  useEffect(() => {
    if (min && viewYear < min.year) setViewYear(min.year);
    if (max && viewYear > max.year) setViewYear(max.year);
  }, [min, max, viewYear]);

  return (
    <div className={["relative inline-block w-full", className].filter(Boolean).join(" ")}>
      {/* Read-only input that opens the popover */}
      <div className="relative w-full min-w-0">
        <input
          ref={inputRef}
          id={inputId}
          type="text"
          value={inputText}
          readOnly
          placeholder={placeholder}
          disabled={disabled}
          aria-haspopup="dialog"
          aria-controls={popoverId}
          aria-expanded={open}
          aria-label={ariaLabel}
          onClick={openPopover}
          onKeyDown={handleInputKeyDown}
          className={[
            "w-full rounded-[var(--radius-3)] border border-border-input bg-white",
            "pl-3 pr-10 py-2.25 text-sm text-text-base",
            "placeholder:text-text-faint",
            "focus:outline-none focus:ring-1 focus:ring-border focus:border-neutral-90",
            disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer",
          ].join(" ")}
        />

        {/* Calendar icon button (purely decorative trigger) */}
        <button
          type="button"
          tabIndex={-1}
          aria-hidden="true"
          onClick={openPopover}
          className={[
            "absolute inset-y-0 right-0 flex items-center",
            "px-2 text-text-base hover:text-text-dark",
            disabled ? "pointer-events-none" : "pointer-events-auto",
          ].join(" ")}
        >
          <span className="material-symbols-rounded text-base">calendar_today</span>
        </button>
      </div>

      {/* Popover */}
      {open && (
        <div
          ref={popoverRef}
          role="dialog"
          aria-modal="false"
          aria-labelledby={inputId}
          id={popoverId}
          className={[
            "absolute z-50 rounded-[var(--radius-3)] border border-slate-200 bg-white shadow-lg ring-1 ring-black/5",
            // Responsive width constraints:
            // On small screens, cap width to viewport (90vw).
            "w-[min(90vw,28rem)] sm:w-auto sm:min-w-64 sm:max-w-md",
            // Prevent viewport overflow vertically.
            "max-h-[70vh] overflow-auto",
            placementClass,
          ].join(" ")}
        >
          {/* Header with year navigation */}
          <div className="flex items-center justify-between p-4 pb-0 sticky top-0 bg-white">
            <button
              type="button"
              aria-label="Previous year"
              onClick={() =>
                canGoPrev && setViewYear((y) => Math.max(min?.year ?? -Infinity, y - 1))
              }
              disabled={!canGoPrev}
              className={[
                "inline-flex items-center justify-center rounded-[var(--radius-3)] px-2 py-1 text-text-dark",
                "hover:bg-neutral-90 focus:outline-none cursor-pointer",
                !canGoPrev ? "opacity-50 cursor-not-allowed" : "",
              ].join(" ")}
            >
              <span className="material-symbols-rounded">chevron_left</span>
            </button>
            <div className="text-sm text-text-dark" aria-live="polite">
              {viewYear}
            </div>
            <button
              type="button"
              aria-label="Next year"
              onClick={() =>
                canGoNext && setViewYear((y) => Math.min(max?.year ?? Infinity, y + 1))
              }
              disabled={!canGoNext}
              className={[
                "inline-flex items-center justify-center rounded-[var(--radius-3)] px-2 py-1 text-text-dark",
                "hover:bg-neutral-90 focus:outline-none",
                !canGoNext ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
              ].join(" ")}
            >
              <span className="material-symbols-rounded">
                chevron_right
              </span>
            </button>
          </div>

          {/* Month grid: responsive (3 cols on mobile, 4 cols from sm up) */}
          <div
            role="grid"
            aria-label={`Months of ${viewYear}`}
            className="grid grid-cols-3 sm:grid-cols-4 gap-2 sm:gap-4 px-3 sm:px-4 py-3 sm:py-4"
          >
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m, idx) => {
              const disabledMonth = isMonthDisabled(viewYear, m);
              const selectedMonth =
                selected?.year === viewYear && selected?.month === m;

              const btnId = `${popoverId}-m-${viewYear}-${m}`;

              return (
                <button
                  key={m}
                  id={btnId}
                  ref={idx === 0 ? firstInteractiveRef : undefined}
                  type="button"
                  role="gridcell"
                  aria-selected={selectedMonth}
                  disabled={disabledMonth}
                  onClick={() => !disabledMonth && commit({ year: viewYear, month: m })}
                  onKeyDown={(e) => handleMonthKeyDown(e, m)}
                  tabIndex={activeMonth === m ? 0 : -1}
                  aria-label={`${monthLabel(m)} ${viewYear}`}
                  className={[
                    "w-full select-none rounded-[var(--radius-3)] p-2 text-sm text-center",
                    "text-text-dark",
                    selectedMonth
                      ? "bg-primary text-white"
                      : " hover:bg-border-neutral hover:text-white",
                    disabledMonth ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
                    "focus:outline-none",
                  ].join(" ")}
                >
                  {monthLabel(m)}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};