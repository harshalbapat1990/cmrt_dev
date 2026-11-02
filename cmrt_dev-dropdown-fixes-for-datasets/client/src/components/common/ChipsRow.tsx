import React, { useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";

export type ChipItem = {
  id: string;         // stable id (e.g., value)
  label: string;      // visible text
};

export type ChipsRowProps = {
  items: ChipItem[];                 // chips to render
  activeId: string | null;           // which chip is "active" (highlighted)
  onActivate: (id: string) => void;  // when user clicks/presses a chip
  onRemove?: (id: string) => void;   // when (X) is clicked or Delete pressed

  /** Layout */
  wrap?: boolean;        // if true, chips wrap to multiple rows; else horizontal scroll
  align?: "left" | "center" | "right" | "between";
  className?: string;

  /** Accessibility/labels */
  ariaLabel?: string;
  chipAriaLabel?: (item: ChipItem, isActive: boolean) => string; // accessible label per chip

  /** Style variations */
  size?: "sm" | "md";
  removable?: boolean;  // show (X) button
  selectable?: boolean; // chips can be activated
};

const ChipsRow: React.FC<ChipsRowProps> = ({
  items,
  activeId,
  onActivate,
  onRemove,
  wrap = false,
  align = "left",
  className,
  ariaLabel = "Selected items",
  chipAriaLabel,
  size = "md",
  removable = true,
  selectable = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [focusIndex, setFocusIndex] = useState<number>(-1);

  const gap = "gap-3";
  const sizeClasses = size === "sm"
    ? {
        chip: "px-3 py-1 text-xs",
        close: "p-0.5 text-[11px]",
        icon: "w-3 h-3",         // ~12px
        gapX: "gap-1.5",

      }
    : {
        chip: "px-4 py-1.5 text-sm",
        close: "p-1 text-xs",
        icon: "w-4 h-4",         // ~16px
        gapX: "gap-2",

      };

  // Layout classes
  const layoutCls = useMemo(() => {
    const base = wrap
      ? "flex flex-wrap"
      : "flex overflow-x-auto scrollbar-thin scrollbar-thumb-neutral-300 scrollbar-track-transparent";
    const justify =
      align === "left"
        ? "justify-start"
        : align === "center"
        ? "justify-center"
        : align === "right"
        ? "justify-end"
        : "justify-between";
    return `${base} ${justify} ${gap}`;
  }, [wrap, align]);

  // Ensure active chip is scrolled into view
  useEffect(() => {
    if (!containerRef.current || !activeId) return;
    const el = containerRef.current.querySelector<HTMLButtonElement>(
      `button[data-id="${CSS.escape(activeId)}"]`
    );
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
    }
  }, [activeId, items]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (items.length === 0) return;
    const LEFT = ["ArrowLeft"];
    const RIGHT = ["ArrowRight"];
    const ACTIVATE = ["Enter", " "];
    const REMOVE = ["Backspace", "Delete"];

    // If nothing is focused, set to active chip or first
    const ensureIndex = () => {
      if (focusIndex >= 0 && focusIndex < items.length) return focusIndex;
      const idx = Math.max(
        0,
        activeId ? items.findIndex((i) => i.id === activeId) : 0
      );
      setFocusIndex(idx);
      return idx;
    };

    if (LEFT.includes(e.key)) {
      e.preventDefault();
      const idx = ensureIndex();
      const next = Math.max(0, idx - 1);
      setFocusIndex(next);
      focusChip(next);
    } else if (RIGHT.includes(e.key)) {
      e.preventDefault();
      const idx = ensureIndex();
      const next = Math.min(items.length - 1, idx + 1);
      setFocusIndex(next);
      focusChip(next);
    } else if (ACTIVATE.includes(e.key) && selectable) {
      e.preventDefault();
      const idx = ensureIndex();
      const it = items[idx];
      if (it) onActivate(it.id);
    } else if (REMOVE.includes(e.key) && removable && onRemove) {
      e.preventDefault();
      const idx = ensureIndex();
      const it = items[idx];
      if (it) onRemove(it.id);
      // move focus to previous chip if exists
      const next = Math.max(0, Math.min(idx, items.length - 2));
      setFocusIndex(next);
      requestAnimationFrame(() => focusChip(next));
    }
  };

  const focusChip = (idx: number) => {
    if (!containerRef.current) return;
    const btns = containerRef.current.querySelectorAll<HTMLButtonElement>(
      "button[data-chip]"
    );
    const el = btns[idx];
    if (el) el.focus();
  };

  return (
    <div
      ref={containerRef}
      role="listbox"
      aria-label={ariaLabel}
      aria-orientation="horizontal"
      className={clsx(layoutCls, className)}
      onKeyDown={handleKeyDown}
    >
      {items.map((item) => {
        const isActive = activeId === item.id;

        const chipLabel =
          chipAriaLabel?.(item, isActive) ??
          `${item.label}${isActive ? " (active)" : ""}`;

        return (
          <div key={item.id} role="option" aria-selected={isActive}>
            {/* Whole-chip button (activates/selects) */}
            <button
              type="button"
              data-chip
              data-id={item.id}
              className={clsx(
                "group inline-flex items-center rounded-full border border-border-neutral transition cursor-pointer",
                sizeClasses.chip,
                isActive
                  ? "bg-border-neutral font-medium text-white border-border-neutral"
                  : " border-border-neutral bg-neutral-90 font-medium"
              )}
              aria-label={chipLabel}
              onClick={() => selectable && onActivate(item.id)}
            >
                 
             
              {isActive && (
                <span
                  className={clsx(
                    "material-symbols-rounded mb-2 leading-none",
                    sizeClasses.icon
                  )}
                  aria-hidden="true"
                >
                  check
                </span>
              )}
              
              <span className={clsx("truncate max-w-48", isActive && "ml-2")}>
                {item.label}
              </span>


            
             
            </button>
          </div>
        );
      })}
    </div>
  );
};

export default ChipsRow;