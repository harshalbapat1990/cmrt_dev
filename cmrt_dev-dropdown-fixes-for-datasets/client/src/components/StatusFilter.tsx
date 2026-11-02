import React, { useMemo, useRef, useState } from "react";
import {
  type RoleType,
  type StatusType,
  USER_STATUS_OPTIONS,
  ADMIN_STATUS_OPTIONS,
} from "../types/project";
import { useOutsideClick } from "../customHooks/useOutsideClick";

interface Props {
  role: RoleType;
  selected: StatusType[];
  onToggle: (status: StatusType) => void;
  onClearAll: () => void;
  className?: string;
}

const StatusFilter: React.FC<Props> = ({
  role,
  selected,
  onToggle,
  onClearAll,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useOutsideClick(ref as React.RefObject<HTMLElement>, () => setIsOpen(false));

  const options = role !== "user" ? ADMIN_STATUS_OPTIONS : USER_STATUS_OPTIONS;

  // Compute the label only for ARIA or fallback needs (not used visually now)
  const ariaLabelText = useMemo(() => {
    if (selected.length === 0) return "Status: All";
    if (selected.length === options.length) return "Status: All selected";
    if (selected.length === 1) return `Status: ${selected[0]}`;
    return `Status: ${selected.length} selected`;
  }, [selected, options.length]);

  // prevent the chip "x" from toggling the dropdown or blurring
  const stopAll = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  return (
    <div
      className={`relative inline-flex ${className ?? ""}`}
      ref={ref}
    >
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={ariaLabelText}
        className={`
          flex items-center gap-2
          cursor-pointer
          h-10 box-border
          rounded-[var(--radius-3)]
          border
          bg-white
          px-3
          text-sm
          transition-all duration-200
          hover:border-neutral-60
          ${
            isOpen
              ? "border-2 border-[#4F5459]"
              : "border border-border-input"
          }
        `}
      >
        {/* Label */}
        <span className="text-text-dark font-medium whitespace-nowrap">
          Status:
        </span>

        {/* Empty */}
        {selected.length === 0 && (
          <span className="text-text-base whitespace-nowrap">
            All
          </span>
        )}

        {/* Single */}
        {selected.length === 1 && (
          <div
            className="
              flex items-center gap-1
              cursor-pointer
              rounded-[var(--radius-3)]
              bg-text-table-cell
              text-xs text-white
            "
            style={{ paddingTop: 0.5, paddingBottom: 0.5, paddingLeft: 4, paddingRight: 4, height: 20 }}
            onClick={stopAll}
            onMouseDown={stopAll}
          >
            <span className="capitalize leading-none">
              {selected[0].toLowerCase()}
            </span>

            <button
              type="button"
              onClick={(e) => {
                stopAll(e);
                onToggle(selected[0]);
              }}
              className="
                flex items-center cursor-pointer justify-center
                rounded-full
                hover:bg-white/10
                transition-colors
              "
              style={{ padding: 3 }}
              aria-label={`Remove ${selected[0]}`}
            >
              <span
                className="material-symbols-rounded leading-none"
                style={{ fontSize: 8, width: 8, height: 8 }}
              >
                close
              </span>
            </button>
          </div>
        )}

        {/* Multiple */}
        {selected.length > 1 && (
          <div
            className="
              flex items-center gap-1 cursor-pointer
              rounded-[var(--radius-3)]
              bg-text-table-cell
              text-xs text-white
            "
            style={{ paddingTop: 0.5, paddingBottom: 0.5, paddingLeft: 4, paddingRight: 4, height: 20 }}
            onClick={stopAll}
            onMouseDown={stopAll}
          >
            <span>{selected.length} selected</span>

            <button
              type="button"
              onClick={(e) => {
                stopAll(e);
                onClearAll();
              }}
              className="
                flex items-center justify-center
                cursor-pointer
                rounded-full
                hover:bg-white/10
                transition-colors
              "
              style={{ padding: 3 }}
              aria-label="Clear selected statuses"
            >
              <span
                className="material-symbols-rounded leading-none"
                style={{ fontSize: 8, width: 8, height: 8 }}
              >
                close
              </span>
            </button>
          </div>
        )}

        {/* Chevron */}
        <span
          className={`
            material-symbols-rounded
            text-[20px]
            text-text-base
            transition-transform duration-200
            ${isOpen ? "rotate-180" : ""}
          `}
        >
          expand_more
        </span>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="
            absolute top-full left-0 z-30 mt-[1px]
            min-w-[220px]
            overflow-hidden
            rounded-[var(--radius-3)]
            border border-border
            bg-white
            shadow-lg
            animate-in fade-in zoom-in-95 duration-150
          "
          role="listbox"
        >
          <div className="py-1">
            {options.map((status) => {
              const checked = selected.includes(status);

              return (
                <label
                  key={status}
                  className="
                    flex cursor-pointer items-center gap-3
                    px-4 py-2.5
                    text-sm
                    transition-colors
                    hover:bg-neutral-95
                  "
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => onToggle(status)}
                    className="sr-only"
                  />

                  {/* Checkbox */}
                  {checked ? (
                    <span
                      className="inline-flex flex-shrink-0 items-center justify-center rounded-[var(--radius-3)]"
                      style={{ width: 13.5, height: 13.5, background: "var(--brand, #CC4C00)" }}
                    >
                      <span
                        className="material-symbols-rounded leading-none text-white"
                        style={{ fontSize: 10 }}
                      >
                        check
                      </span>
                    </span>
                  ) : (
                    <span
                      className="inline-flex flex-shrink-0 rounded-[var(--radius-3)]"
                      style={{
                        width: 13.5,
                        height: 13.5,
                        border: "1.35px solid var(--action-active, #0000008F)",
                      }}
                    />
                  )}

                  {/* Text */}
                  <span className="capitalize text-text-base leading-none">
                    {status.toLowerCase()}
                  </span>
                </label>
              );
            })}
          </div>

          {/* Footer */}
          {selected.length > 0 && (
            <>
              <div className="h-px bg-border" />

              <div className="p-2">
                <button
                  type="button"
                  onClick={onClearAll}
                  className="
                    w-full rounded-[var(--radius-3)]
                    px-3 py-2
                    cursor-pointer
                    text-left text-sm font-medium text-primary
                    transition-colors
                    hover:bg-primary-weak
                  "
                >
                  Clear all
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default StatusFilter;