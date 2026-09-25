// components/PaginationBar.tsx
import React from "react";

type Props = {
  page: number;                 // current page (1-based)
  totalItems: number;           // total number of items (after filtering)
  pageSize: number;             // current page size (rows per page)
  onChangePage: (page: number) => void;
  onChangePageSize: (size: number) => void;
  className?: string;
};

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 200];

const PaginationBar: React.FC<Props> = ({
  page,
  totalItems,
  pageSize,
  onChangePage,
  onChangePageSize,
  className,
}) => {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const canGoPrev = page > 1;
  const canGoNext = page < totalPages;

  const goFirst = () => canGoPrev && onChangePage(1);
  const goPrev = () => canGoPrev && onChangePage(page - 1);
  const goNext = () => canGoNext && onChangePage(page + 1);
  const goLast = () => canGoNext && onChangePage(totalPages);

  const numbers = getCompactPageNumbers(page, totalPages);

  return (
    <div
      className={[
        "w-full border-t border-gray-200 bg-white",
        "px-3 py-2",
        "flex items-center justify-between gap-3",
        className ?? "",
      ].join(" ")}
    >
      {/* Left controls */}
      <div className="flex items-center gap-1 cursor-pointer select-none">
        <IconButton
          title="First page"
          disabled={!canGoPrev}
          onClick={goFirst}
          iconName="first_page"
        />
        <IconButton
          title="Previous page"
          disabled={!canGoPrev}
          onClick={goPrev}
          iconName="chevron_left"
        />

        {numbers.map((n, idx) =>
          n === "..." ? (
            <span key={`e-${idx}`} className="px-2 text-text-base select-none">
              …
            </span>
          ) : (
            <button
              key={n}
              onClick={() => onChangePage(n)}
              className={[
                "min-w-8 h-8 px-2 rounded border text-sm text-text-base cursor-pointer",
                "transition-colors",
                n === page
                  ? "bg-neutral-95 border-light-grey text-text-base"
                  : "bg-white border-light-grey hover:bg-gray-50",
              ].join(" ")}
              type="button"
              aria-current={n === page ? "page" : undefined}
            >
              {n}
            </button>
          )
        )}

        <IconButton
          title="Next page"
          disabled={!canGoNext}
          onClick={goNext}
          iconName="chevron_right"
        />
        <IconButton
          title="Last page"
          disabled={!canGoNext}
          onClick={goLast}
          iconName="last_page"
        />
      </div>

      {/* Right controls: page size select */}
      <label className="flex items-center gap-2">
        <span className="text-sm text-text-base">Items per page</span>
        <div className="relative">
          <select
            className="appearance-none border border-gray-300 rounded px-3 py-1.5 pr-8 text-sm bg-white text-text-base"
            value={pageSize}
            onChange={(e) => onChangePageSize(Number(e.target.value))}
            aria-label="Rows per page"
          >
            {PAGE_SIZE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          {/* Rounded caret */}
          <span className="pointer-events-none absolute right-1.5 top-5.5 -translate-y-1/2 text-gray-600">
            <span className="material-symbols-rounded text-[18px] leading-none">
              expand_more
            </span>
          </span>
        </div>
      </label>
    </div>
  );
};

export default PaginationBar;

/** Compact page numbers like: 1 2 3 4 … 10, or 1 … 4 5 6 … 10 */
function getCompactPageNumbers(
  current: number,
  total: number
): (number | "...")[] {
  const out: (number | "...")[] = [];
  const add = (x: number | "...") => out.push(x);
  const range = (a: number, b: number) => {
    for (let i = a; i <= b; i++) add(i);
  };

  if (total <= 7) {
    range(1, total);
    return out;
  }
  add(1);
  if (current <= 4) {
    range(2, 5);
    add("...");
    add(total);
  } else if (current >= total - 3) {
    add("...");
    range(total - 4, total);
  } else {
    add("...");
    range(current - 1, current + 1);
    add("...");
    add(total);
  }
  return out;
}

/** Small icon button that uses Material Symbols Rounded */
const IconButton: React.FC<{
  title: string;
  disabled: boolean;
  onClick: () => void;
  iconName: string; // Material Symbols icon name
}> = ({ title, disabled, onClick, iconName }) => (
  <button
    title={title}
    disabled={disabled}
    onClick={onClick}
    type="button"
    className={[
      "w-8 h-8 rounded border text-sm",
      "flex items-center justify-center",
      "transition-colors select-none cursor-pointer",
      disabled
        ? "bg-gray-50 border-gray-200 text-gray-300 cursor-not-allowed"
        : "bg-white border-gray-200 hover:bg-gray-50",
    ].join(" ")}
    aria-label={title}
  >
    <span
      className={[
        "material-symbols-rounded",
        disabled ? "text-gray-300" : "text-gray-700",
      ].join(" ")}
      aria-hidden="true"
      style={{ fontSize: 18, lineHeight: 1 }}
    >
      {iconName}
    </span>
    <span className="sr-only">{title}</span>
  </button>
);