import { useCallback, useRef, useState } from "react";
import { SelectListbox } from "@/components/common/Select";
import { useOutsideClick } from "../useOutsideClick";

interface Props {
  years: number[];
  activeYear: number | null;
  readOnly: boolean;
  onYearChange?: (year: number) => void;
  onAddYear?: () => void;
  onCopyYear?: () => void;
  onDeleteYear?: () => void;
}

/** Year selection and its add/copy/delete menu for large road-user data. */
export function LargeRoadUsersYearSelector({
  years,
  activeYear,
  readOnly,
  onYearChange,
  onAddYear,
  onCopyYear,
  onDeleteYear,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const closeMenu = useCallback(() => setMenuOpen(false), []);
  useOutsideClick(menuRef, closeMenu, menuOpen);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-sm text-text-base font-medium mr-12">Modelled year:</span>
      {years.length > 0 ? (
        <SelectListbox
          value={String(activeYear ?? "")}
          options={years.map((year) => ({ label: String(year), value: String(year) }))}
          onChange={(value: string) => onYearChange?.(Number(value))}
          disabled={readOnly}
          className="h-9 w-48"
        />
      ) : (
        <span className="text-sm text-text-faint italic">No years</span>
      )}

      {!readOnly && (
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            className="p-2 rounded hover:bg-neutral-200 cursor-pointer transition-colors"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="More modelled year options"
          >
            <span className="material-symbols-rounded">more_vert</span>
          </button>

          {menuOpen && (
            <div className="absolute left-0 mt-1 w-48 rounded-lg border border-neutral-200 bg-white shadow-lg z-30 py-1">
              <button
                type="button"
                className="w-full text-left px-4 cursor-pointer py-2 text-sm hover:bg-neutral-50"
                onClick={() => { setMenuOpen(false); onAddYear?.(); }}
              >
                Add year
              </button>
              {years.length > 1 && (
                <button
                  type="button"
                  className="w-full text-left px-4 py-2 cursor-pointer text-sm hover:bg-neutral-50"
                  onClick={() => { setMenuOpen(false); onCopyYear?.(); }}
                >
                  Copy from…
                </button>
              )}
              {activeYear !== null && (
                <button
                  type="button"
                  className="w-full text-left px-4 py-2 text-sm cursor-pointer text-danger hover:bg-red-50"
                  onClick={() => { setMenuOpen(false); onDeleteYear?.(); }}
                >
                  Delete year {activeYear}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
