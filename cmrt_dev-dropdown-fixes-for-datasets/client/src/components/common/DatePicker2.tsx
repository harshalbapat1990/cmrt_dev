import { useEffect, useMemo, useRef, useState, forwardRef } from "react";

export type DisabledDateFn = (date: Date) => boolean;

export interface DatePickerProps {
  value?: Date | null;
  onChange?: (date: Date | null) => void;
  /** Provide your own formatter (defaults to yyyy-MM-dd) */
  formatFn?: (date: Date) => string;
  /** Provide your own parser (defaults to yyyy-MM-dd) */
  parseFn?: (raw: string) => Date | null;
  placeholder?: string;
  minDate?: Date;
  maxDate?: Date;
  disabledDate?: DisabledDateFn;
  /** 0 (Sun) … 6 (Sat). Default = 1 (Mon) */
  firstDayOfWeek?: 0 | 1 | 2 | 3 | 4 | 5 | 6;
  allowClear?: boolean;
  disabled?: boolean;
  className?: string;
  name?: string;
  id?: string;
  closeOnSelect?: boolean;
  openOnFocus?: boolean;
  popupZIndex?: number;
  ariaLabel?: string;
  ariaDescribedBy?: string;
}

/** Default format yyyy-MM-dd */
function defaultFormat(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Default parse yyyy-MM-dd */
function defaultParse(s: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s.trim());
  if (!m) return null;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  const date = new Date(y, mo - 1, d);
  if (
    date.getFullYear() === y &&
    date.getMonth() === mo - 1 &&
    date.getDate() === d
  ) {
    return date;
  }
  return null;
}

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}
function endOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}
function startOfWeek(d: Date, weekStartsOn: number) {
  const day = d.getDay();
  const diff = (day - weekStartsOn + 7) % 7;
  const res = new Date(d);
  res.setDate(d.getDate() - diff);
  res.setHours(0, 0, 0, 0);
  return res;
}
function endOfWeek(d: Date, weekStartsOn: number) {
  const start = startOfWeek(d, weekStartsOn);
  const res = new Date(start);
  res.setDate(start.getDate() + 6);
  res.setHours(23, 59, 59, 999);
  return res;
}
function addMonths(d: Date, count: number) {
  const res = new Date(d);
  const day = res.getDate();
  res.setMonth(res.getMonth() + count);
  // Adjust for month overflow
  if (res.getDate() < day) res.setDate(0);
  return res;
}

function addYears(d: Date, count: number) {
  const res = new Date(d);
  res.setFullYear(res.getFullYear() + count);
  return res;
}

function isSameDay(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function isSameMonth(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
}

function isBefore(a: Date, b: Date) {
  return a.getTime() < b.getTime();
}
function isAfter(a: Date, b: Date) {
  return a.getTime() > b.getTime();
}
function isOutOfRange(date: Date, minDate?: Date, maxDate?: Date) {
  if (minDate && isBefore(date, minDate)) return true;
  if (maxDate && isAfter(date, maxDate)) return true;
  return false;
}
function buildCalendarGrid(currentMonth: Date, firstDayOfWeek: number): Date[] {
  const monthStart = startOfMonth(currentMonth);
  const start = startOfWeek(monthStart, firstDayOfWeek);
  const monthEnd = endOfMonth(currentMonth);
  const end = endOfWeek(monthEnd, firstDayOfWeek);
  const days: Date[] = [];
  const cur = new Date(start);
  while (cur <= end) {
    days.push(new Date(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return days;
}

const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export const DatePicker2 = forwardRef<HTMLInputElement, DatePickerProps>((props, ref) => {
  const {
    value = null,
    onChange,
    formatFn = defaultFormat,
    parseFn = defaultParse,
    placeholder,
    minDate,
    maxDate,
    disabledDate,
    firstDayOfWeek = 1,
    allowClear = true,
    disabled = false,
    className = "",
    name,
    id,
    closeOnSelect = true,
    openOnFocus = true,
    popupZIndex = 30,
    ariaLabel,
    ariaDescribedBy,
  } = props;

  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState<string>(
    value ? formatFn(value) : ""
  );
  const [viewMonth, setViewMonth] = useState<Date>(() => {
    const base = value ?? new Date();
    return new Date(base.getFullYear(), base.getMonth(), 1);
  });

  const rootRef = useRef<HTMLDivElement | null>(null);

  // Internal ref to handle cases where parent doesn't provide one
  const internalInputRef = useRef<HTMLInputElement | null>(null);

  // Merge the forwarded ref with our internal ref logic
  const resolvedRef = (node: HTMLInputElement | null) => {
    internalInputRef.current = node;
    if (typeof ref === "function") {
      ref(node);
    } else if (ref) {
      ref.current = node;
    }
  };

  const isInteractingPopupRef = useRef(false);

  useEffect(() => {
    if (!value) {
      setInputValue("");
      return;
    }
    setInputValue(formatFn(value));
    setViewMonth(new Date(value.getFullYear(), value.getMonth(), 1));
  }, [value, formatFn]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const gridDays = useMemo(
    () => buildCalendarGrid(viewMonth, firstDayOfWeek),
    [viewMonth, firstDayOfWeek]
  );

  function handleCommitFromInput(raw: string) {
    const parsed = parseFn(raw);
    if (
      parsed &&
      !isOutOfRange(parsed, minDate, maxDate) &&
      !disabledDate?.(parsed)
    ) {
      onChange?.(parsed);
      if (closeOnSelect) setOpen(false);
    }
  }

  function handleDayClick(day: Date) {
    if (isOutOfRange(day, minDate, maxDate)) return;
    if (disabledDate?.(day)) return;
    if (!isSameMonth(day, viewMonth)) return;
    onChange?.(day);
    setInputValue(formatFn(day));
    if (closeOnSelect) setOpen(false);
  }

  function gotoPrevMonth() { setViewMonth(addMonths(viewMonth, -1)); }
  function gotoNextMonth() { setViewMonth(addMonths(viewMonth, +1)); }

  function gotoPrevYear() {
    setViewMonth(addYears(viewMonth, -1));
  }
  function gotoNextYear() {
    setViewMonth(addYears(viewMonth, +1));
  }

  const weekdayNames = useMemo(() => {
    const arr = [...WEEKDAY_LABELS];
    const head = arr.splice(0, firstDayOfWeek);
    return [...arr, ...head];
  }, [firstDayOfWeek]);

  const selected = value ?? null;

  return (
    <div ref={rootRef} className={`relative block w-full ${className}`}>
      <div className="flex items-center gap-2">
        <div className="relative h-10 w-full">
          <input
            ref={resolvedRef} // Use the resolved ref here
            id={id}
            name={name}
            type="text"
            placeholder={placeholder ?? "yyyy-mm-dd"}
            className={`w-full rounded-[var(--radius-3)] border border-border-input bg-white px-3 py-2.25 pr-9 text-sm outline-none transition focus:border-text-dark focus:ring-1 focus:ring-text-dark disabled:bg-border-input ${disabled ? "cursor-not-allowed opacity-70" : ""
              }`}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onBlur={(e) => {
              const nextTarget = e.relatedTarget as Node | null;
              if (nextTarget && rootRef.current?.contains(nextTarget)) return;
              if (isInteractingPopupRef.current) return;

              const raw = e.currentTarget.value.trim();
              if (raw === "" && allowClear) {
                onChange?.(null);
                return;
              }
              handleCommitFromInput(raw);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleCommitFromInput(inputValue.trim());
              }
              if (e.key === "ArrowDown" && !open) setOpen(true);
              if (e.key === "Escape" && open) setOpen(false);
            }}
            aria-label={ariaLabel ?? "Date input"}
            aria-describedby={ariaDescribedBy}
            disabled={disabled}
            onFocus={() => openOnFocus && setOpen(true)}
          />
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-text-base cursor-pointer focus:outline-none"
            onClick={() => !disabled && setOpen((o) => !o)}
            aria-label={open ? "Close calendar" : "Open calendar"}
            disabled={disabled}
          >
            <span className="material-symbols-rounded text-text-base">
              calendar_today
            </span>
          </button>
        </div>
      </div>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          className="absolute left-0 mt-2 w-fit rounded-[var(--radius-3)] border border-border-input bg-white p-4 shadow-lgoverflow-auto"
          style={{ zIndex: popupZIndex }}
          onMouseDown={() => { isInteractingPopupRef.current = true; }}
          onMouseUp={() => { setTimeout(() => (isInteractingPopupRef.current = false), 0); }}
        >
          {/* ... (rest of calendar rendering remains same as your code) */}
          <div className="mb-4 grid items-center grid-cols-[1fr_auto_1fr] gap-1">
            <div className="flex items-center justify-self-start gap-1">
              <button type="button" onClick={gotoPrevYear} className="rounded-[var(--radius-3)] p-1 hover:bg-light-grey">
                <span className="material-symbols-rounded">keyboard_double_arrow_left</span>
              </button>
              <button
                type="button"
                onClick={gotoPrevMonth}
                className="rounded-[var(--radius-3)] p-1 hover:bg-light-grey cursor-pointer"
                aria-label="Previous month"
              >
                <span className="material-symbols-rounded">chevron_left</span>
              </button>
            </div>

            <div className="justify-self-center text-sm font-medium whitespace-nowrap px-1 text-text-base">
              {new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(viewMonth)}
            </div>

            <div className="flex items-center justify-self-end gap-1">
              <button
                type="button"
                onClick={gotoNextMonth}
                className="rounded-[var(--radius-3)] p-1 hover:bg-light-grey cursor-pointer"
                aria-label="Next month"
              >
                <span className="material-symbols-rounded">chevron_right</span>
              </button>
              <button
                type="button"
                onClick={gotoNextYear}
                className="rounded-[var(--radius-3)] p-1 hover:bg-light-grey cursor-pointer"
                aria-label="Next year"
              >
                <span className="material-symbols-rounded">keyboard_double_arrow_right</span>
              </button>
            </div>

          </div>
          {/* Weekday and Days logic... */}
          <div className="my-2.25 grid grid-cols-7 gap-1 text-center text-xs sm:text-xs uppercase tracking-wide text-text-base">
            {weekdayNames.map((w) => <div key={w}>{w}</div>)}
          </div>
          <div className="grid grid-cols-7 gap-1">

            {gridDays.map((day, idx) => {
              const isCurrentMonth = isSameMonth(day, viewMonth);
              const isSelected =
                selected && isSameDay(day, selected);
              const outOfRange =
                isOutOfRange(day, minDate, maxDate) || !!disabledDate?.(day);

              const baseClasses =
                "h-8 w-8 sm:h-9 sm:w-9 flex items-center justify-center rounded-[var(--radius-3)] text-sm focus:outline-none";
              const mutedClasses = "text-text-faint/60";
              const normalClasses = "text-text-base";
              const hoverClasses = !outOfRange && isCurrentMonth
                ? "hover:bg-text-dark hover:text-white cursor-pointer"
                : "cursor-default";
              const selectedClasses = isSelected
                ? "bg-primary text-white"
                : "";

              const textClass = isCurrentMonth ? normalClasses : mutedClasses;

              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleDayClick(day)}
                  className={[baseClasses, textClass, hoverClasses, selectedClasses].join(" ").trim()}
                  aria-label={day.toDateString()}
                  aria-disabled={!isCurrentMonth || outOfRange}
                  disabled={!isCurrentMonth || outOfRange}
                >
                  {day.getDate()}
                </button>
              );
            })}

          </div>
        </div>
      )}
    </div>
  );
});

DatePicker2.displayName = "DatePicker2";
