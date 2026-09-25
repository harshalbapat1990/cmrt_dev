
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

type Option = { label: string; value: string; disabled?: boolean; status?: string };
type SelectListboxProps = {
  value: string;
  label?: string;
  onBlur?: () => void;
  onChange: (v: string) => void;
  onKeyDown?: (e: React.KeyboardEvent) => void;
  options: Option[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;       // button classes
  menuClassName?: string;   // extra menu classes
  "aria-label"?: string;
  autoFocus?: boolean;
  onOpen?: () => void;
  loading?: boolean;
  noOptionsLabel?: string;
  status?: string;
  minMenuWidth?: number;
};

export const SelectListbox: React.FC<SelectListboxProps> = ({
  value,
  label,
  onBlur,
  onChange,
  onKeyDown,
  options,
  placeholder = "",
  disabled = false,
  className = "",
  menuClassName = "",
  onOpen,
  loading = false,
  noOptionsLabel = "No options",
  status,
  minMenuWidth = 240,
  ...rest
}) => {
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [menuStyles, setMenuStyles] = useState<React.CSSProperties>({});
  const menuRef = useRef<HTMLDivElement | null>(null);

  const [activeIndex, setActiveIndex] = useState<number>(() =>
    Math.max(0, options.findIndex(o => o.value === value))
  );
  const [searchText, setSearchText] = useState("");

  // Prevent closing on input blur when the user is clicking inside the menu
  const ignoreBlurRef = useRef(false);
  const skipNextOpenRef = useRef(false);

  const selected = useMemo(() => options.find(o => o.value === value), [options, value]);

  const filteredOptions = useMemo(() => {
    if (!searchText.trim()) return options;
    const lower = searchText.toLowerCase();
    return options.filter(o => o.label.toLowerCase().includes(lower));
  }, [options, searchText]);

  useEffect(() => {
    setActiveIndex(0);
  }, [filteredOptions]);

  useEffect(() => {
    if (open) {
      onOpen?.();
    }
  }, [open, onOpen]);

  const updateMenuPosition = () => {
    const btn = inputRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const viewportH = window.innerHeight;
    const menuMaxHeight = Math.min(240, Math.max(160, viewportH * 0.5));
    const TOP_OFFSET = 4;
    const top = Math.round(rect.bottom + TOP_OFFSET);
    const left = Math.round(rect.left);
    const width = Math.max(Math.round(rect.width), minMenuWidth ?? 240);

    setMenuStyles({
      position: "fixed",
      left,
      top,
      width,
      maxHeight: menuMaxHeight,
      zIndex: 9999,
    });
  };

  const closeAndNotify = () => {
    setOpen(false);
    setSearchText("");
    if (onBlur) setTimeout(() => onBlur(), 0);
    ignoreBlurRef.current = false;
  };

  useLayoutEffect(() => {
    if (!open) return;
    updateMenuPosition();

    const onScroll = () => updateMenuPosition();
    const onResize = () => updateMenuPosition();

    const ro = new ResizeObserver(() => updateMenuPosition());
    if (inputRef.current) ro.observe(inputRef.current);

    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onResize);
      ro.disconnect();
    };
  }, [open]);

  // Click outside → close & notify
  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!open) return;
      const t = e.target as Node;
      if (inputRef.current?.contains(t)) return;
      if (menuRef.current?.contains(t)) return;
      closeAndNotify();
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  //  NEW: mark when pointer goes into the menu so button onBlur doesn't close prematurely
  useEffect(() => {
    if (!open || !menuRef.current) return;
    const onMenuMouseDown = () => {
      ignoreBlurRef.current = true;
    };
    const node = menuRef.current;
    node.addEventListener("mousedown", onMenuMouseDown);
    return () => node.removeEventListener("mousedown", onMenuMouseDown);
  }, [open]);

  // Keyboard support (when open) — arrows/Enter/Escape operate on filteredOptions
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      const max = filteredOptions.length - 1;
      if (e.key === "ArrowDown") {
        e.preventDefault(); setActiveIndex(i => Math.min(max, i + 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault(); setActiveIndex(i => Math.max(0, i - 1));
      } else if (e.key === "Home") {
        e.preventDefault(); setActiveIndex(0);
      } else if (e.key === "End") {
        e.preventDefault(); setActiveIndex(max);
      } else if (e.key === "Enter") {
        e.preventDefault();
        const opt = filteredOptions[activeIndex];
        if (opt) {
          onChange(opt.value);
          skipNextOpenRef.current = true;
          closeAndNotify();
          inputRef.current?.focus();
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        skipNextOpenRef.current = true;
        closeAndNotify();
        inputRef.current?.focus();
      } else if (e.key === "Tab") {
        closeAndNotify();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, filteredOptions, activeIndex, onChange]);

  useEffect(() => {
    const idx = options.findIndex(o => o.value === value);
    if (idx >= 0) setActiveIndex(idx);
  }, [value, options]);

  const statusBadgeClass = (s: string) =>
    s === "Approved" ? "bg-light-green text-success"
    : s === "In Progress" ? "bg-info-bg text-in-progress"
    : s === "Awaiting Approval" ? "bg-warning-bg text-warning"
    : s === "Rejected" ? "bg-error-bg text-error"
    : "bg-neutral-90 text-text-faint";

  return (
    <div className="block">
      {label && <label className="block text-sm text-text-base mb-2">{label}</label>}
      <div className="relative">
        {/* Combobox input */}
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-autocomplete="list"
          aria-label={rest["aria-label"]}
          autoFocus={(rest as any).autoFocus}
          disabled={disabled}
          placeholder={open ? "Search…" : (selected?.label ? "" : placeholder)}
          value={open ? searchText : (selected?.label ?? "")}
          className={[
            "w-full h-10 bg-white pl-3 pr-16 py-1 border border-border-input rounded-[var(--radius-3)]",
            "text-sm text-text-base focus:outline-none focus:ring-1 focus:ring-border focus:border-transparent",
            disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer",
            className
          ].join(" ")}
          onClick={() => {
            if (disabled) return;
            inputRef.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
            if (!open) { setSearchText(""); setOpen(true); }
          }}
          onFocus={() => {
            if (disabled) return;
            if (skipNextOpenRef.current) { skipNextOpenRef.current = false; return; }
            setSearchText("");
            setOpen(true);
          }}
          onChange={(e) => {
            if (disabled) return;
            setSearchText(e.target.value);
            if (!open) setOpen(true);
          }}
          onBlur={() => {
            if (open && !ignoreBlurRef.current) {
              closeAndNotify();
            }
          }}
          onKeyDown={(e) => {
            if (disabled) return;
            if (e.key === "ArrowDown" || e.key === "ArrowUp") {
              e.preventDefault();
              if (!open) { setSearchText(""); setOpen(true); }
              return;
            }
            onKeyDown?.(e);
          }}
        />

        {/* Status badge — shown on the closed trigger when the selected option has a status */}
        {!open && selected?.status && (
          <span
            className={`absolute right-8 top-1/2 -translate-y-1/2 px-2 py-0.5 text-xs rounded-full font-medium pointer-events-none ${statusBadgeClass(selected.status)}`}
          >
            {selected.status}
          </span>
        )}
        <span className="material-symbols-rounded absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-text-faint select-none">
          keyboard_arrow_down
        </span>

        {/* Portalled Menu (overlay) */}
        {open && createPortal(
          <div
            ref={menuRef}
            role="listbox"
            tabIndex={-1}
            style={menuStyles}
            className={[
              "fixed z-9999 max-h-60 overflow-auto rounded-[var(--radius-3)] border border-neutral-90",
              "bg-white shadow-md will-change-transform",
              menuClassName
            ].join(" ")}
          >
            {loading ? (
              <div className="px-3 py-2 text-sm text-text-base">Loading...</div>
            ) : filteredOptions.length === 0 ? (
              <div className="px-3 py-2 text-sm text-text-base">{noOptionsLabel}</div>
            ) : (
              filteredOptions.map((opt, idx) => {
                const isSelected = value === opt.value;
                const isActive = idx === activeIndex;
                return (
                  <div
                    key={opt.value}
                    role="option"
                    aria-selected={isSelected}
                    aria-disabled={opt.disabled}
                    className={[
                      "flex items-center justify-between px-3 py-2 text-sm select-none",
                      opt.disabled
                        ? "opacity-40 cursor-not-allowed text-gray-400"
                        : "cursor-pointer",
                      !opt.disabled && isActive ? "bg-neutral-95" : "",
                      !opt.disabled && isSelected ? "bg-neutral-90" : "",
                      "text-text-base"
                    ].join(" ")}
                    onMouseEnter={() => !opt.disabled && setActiveIndex(idx)}
                    onClick={() => {
                      if (opt.disabled) return;
                      onChange(opt.value);
                      skipNextOpenRef.current = true;
                      closeAndNotify();
                      inputRef.current?.focus();
                    }}
                  >
                    <div className="flex items-center justify-between w-full gap-2">
                      <span className="whitespace-normal break-words min-w-0 leading-snug">{opt.label}</span>

                      {opt.status && (
                        <span className={`px-2 py-0.5 text-xs rounded-full font-medium shrink-0 ${statusBadgeClass(opt.status)}`}>
                          {opt.status}
                        </span>
                      )}
                    </div>

                    {isSelected && (
                      <span className="material-symbols-rounded text-[rgba(0,0,0,0.54)]">check</span>
                    )}
                  </div>
                );
              })
            )}
          </div>,
          document.body
        )}
      </div>
    </div>
  );
};
