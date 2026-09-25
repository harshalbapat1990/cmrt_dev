import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import CancelFill from "../../assets/icons/cancel-fill.svg";

export type MSOption = { label: string; value: string };

export type MultiSelectDropdownProps = {
  label?: string;
  options: MSOption[];

  /** Controlled selection */
  selected: string[];
  onChange: (next: string[]) => void;

  /** UX */
  placeholder?: string;
  disabled?: boolean;
  error?: string | null;
  maxChips?: number;       // collapse into +N after this count (default 3)
  clearable?: boolean;     // show clear-all cross (default true)
  className?: string;
  id?: string;
  ariaLabel?: string;

  /** Behavior */
  closeOnSelect?: boolean; // default false for multi
  withSearch?: boolean;    // default false
};

const K = {
  Enter: "Enter",
  Space: " ",
  Spacebar: "Spacebar",
  Escape: "Escape",
  ArrowUp: "ArrowUp",
  ArrowDown: "ArrowDown",
};

const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  label,
  options,
  selected,
  onChange,
  placeholder = "Select all that apply",
  disabled = false,
  error = null,
  maxChips = 3,
  clearable = true,
  className,
  id,
  ariaLabel,
  closeOnSelect = false,
  withSearch = false,
}) => {
  const listboxId = useId();
  const buttonId = id ?? useId();

  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const [query, setQuery] = useState("");

  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // quick lookup for chip labels
  const labelByValue = useMemo(() => {
    const m = new Map<string, string>();
    for (const o of options) m.set(o.value, o.label);
    return m;
  }, [options]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!withSearch || q === "") return options;
    return options.filter(
      (o) =>
        o.label.toLowerCase().includes(q) ||
        o.value.toLowerCase().includes(q)
    );
  }, [options, query, withSearch]);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!rootRef.current) return;
      if (e.target instanceof Node && rootRef.current.contains(e.target)) return;
      setOpen(false);
    };
    if (open) document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const isSelected = (v: string) => selected.includes(v);

  const toggle = (v: string) => {
    if (disabled) return;
    const next = isSelected(v)
      ? selected.filter((x) => x !== v)
      : [...selected, v];
    onChange(next);
    if (closeOnSelect) setOpen(false);
  };

  const remove = (v: string) => {
    if (disabled) return;
    onChange(selected.filter((x) => x !== v));
  };

  const clearAll = () => onChange([]);

  const visibleChips = selected.slice(0, maxChips);
  const hidden = Math.max(0, selected.length - visibleChips.length);

  const ensureActiveVisible = () => {
    requestAnimationFrame(() => {
      const list = listRef.current;
      if (!list) return;
      const li = list.querySelector<HTMLLIElement>(
        `li[data-index="${activeIndex}"]`
      );
      if (!li) return;
      const liRect = li.getBoundingClientRect();
      const listRect = list.getBoundingClientRect();
      if (liRect.top < listRect.top) list.scrollTop += liRect.top - listRect.top - 4;
      if (liRect.bottom > listRect.bottom) list.scrollTop += liRect.bottom - listRect.bottom + 4;
    });
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;

    switch (e.key) {
      case K.Enter:
      case K.Space:
      case K.Spacebar: {
        e.preventDefault();
        if (!open) {
          setOpen(true);
          setActiveIndex((i) => (i >= 0 ? i : 0));
        } else if (activeIndex >= 0 && activeIndex < filtered.length) {
          toggle(filtered[activeIndex].value);
        }
        break;
      }
      case K.ArrowDown: {
        e.preventDefault();
        if (!open) {
          setOpen(true);
          setActiveIndex(0);
        } else {
          setActiveIndex((i) => Math.min(filtered.length - 1, Math.max(0, i + 1)));
          ensureActiveVisible();
        }
        break;
      }
      case K.ArrowUp: {
        e.preventDefault();
        if (open) {
          setActiveIndex((i) => Math.max(0, (i < 0 ? 1 : i) - 1));
          ensureActiveVisible();
        }
        break;
      }
      case K.Escape: {
        if (open) {
          e.preventDefault();
          setOpen(false);
        }
        break;
      }
    }
  };

  return (
    <div ref={rootRef} className={clsx("w-full", className)}>
      {label && (
        <label htmlFor={buttonId} className="mb-1 block text-text-base text-sm">
          {label}
        </label>
      )}

      {/* Field with chips (no checkboxes anywhere) */}
      <div
        id={buttonId}
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-haspopup="listbox"
        aria-label={ariaLabel || label}
        tabIndex={disabled ? -1 : 0}
        onClick={() => !disabled && setOpen((o) => !o)}
        onKeyDown={onKeyDown}
        className={clsx(
          "relative flex min-h-10 w-full cursor-pointer items-center gap-2  rounded-[var(--radius-3)] border bg-white p-2.5 text-sm",
          "border-border-input text-text-dark focus:outline-none focus:ring-1",
          disabled && "cursor-not-allowed opacity-60",
          error && "border-danger"
        )}
      >
        <div className="flex flex-1 flex-wrap items-center gap-2">
          {selected.length === 0 ? (
            <span className="text-neutral-500">{placeholder}</span>
          ) : (
            <>
              {visibleChips.map((v) => (
                <span
                  key={v}
                  className="group inline-flex items-center gap-1 rounded-[var(--radius-3)] border border-border-neutral bg-border-neutral pl-2 text-xs text-white cursor-pointer"
                  onClick={(e) => e.stopPropagation()}
                >
                  <span className="truncate max-w-40">
                    {labelByValue.get(v) ?? v}
                  </span>
                  <button
                    type="button"
                    aria-label={`Remove ${labelByValue.get(v) ?? v}`}
                    className="material-symbols-rounded text-xs p-1 text-white cursor-pointer "
                    onClick={(e) => {
                      e.stopPropagation();
                      remove(v);
                    }}
                  >  close
                  </button>
                </span>
              ))}
              {hidden > 0 && (
                <span className="inline-flex items-center rounded-full border border-neutral-300 bg-neutral-100 px-2 py-0.5 text-xs text-text-dark">
                  +{hidden}
                </span>
              )}
            </>
          )}
        </div>

        {clearable && selected.length > 0 && !disabled && (
          <button
            type="button"
            className="text-sm text-text-base cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              clearAll();
            }}
            aria-label="Clear selection"
          >
            <img src={CancelFill} alt="Clear selection" className="w-4 h-4" />
          </button>
        )}

        <span
          aria-hidden
          className={clsx(
            "ml-1 select-none text-neutral-500 transition-transform",
            open ? "rotate-180" : "rotate-0"
          )}
        >
          <span className="material-symbols-rounded">
            keyboard_arrow_down
          </span>
        </span>
      </div>

      {error && <p className="mt-1 text-xs text-danger">{error}</p>}

      {open && (
        <div className="relative z-20">
          <div className="absolute mt-1 w-full overflow-hidden rounded-[var(--radius-3)] bg-white shadow-lg">
            {/* Optional search strip */}
            {withSearch && (
              <div className="border-b border-neutral-200 p-2">
                <input
                  type="text"
                  className="w-full rounded-[var(--radius-3)] border border-border-input bg-white px-2 py-1.5 text-sm text-text-dark focus:outline-none focus:ring-1 cursor-pointer"
                  placeholder="Search…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            )}

            <ul
              id={listboxId}
              role="listbox"
              aria-multiselectable
              ref={listRef}
              className="max-h-60 overflow-auto py-1 text-base"
            >
              {filtered.length === 0 && (
                <li className="px-3 py-2 text-sm text-text-base">No results</li>
              )}

              {filtered.map((opt, i) => {
                const selectedHere = isSelected(opt.value);
                const active = i === activeIndex;
                return (
                  <li
                    key={opt.value}
                    role="option"
                    aria-selected={selectedHere}
                    data-index={i}
                    className={clsx(
                      "flex cursor-pointer items-center justify-between px-3 py-2 text-sm",
                      active ? "bg-neutral-90" : "",
                      "hover:bg-neutral-95"
                    )}
                    onMouseEnter={() => setActiveIndex(i)}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle(opt.value);
                    }}
                  >
                    <span className={clsx("truncate", selectedHere && "font-medium text-text-base")}>
                      {opt.label}
                    </span>

                    {/* Subtle tick indicator (no checkbox)
                    {selectedHere && (
                      <span
                        aria-hidden
                        className="ml-3 text-text-dark"
                        title="Selected"
                      >
                        ✓
                      </span>
                    )} */}
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default MultiSelectDropdown;
