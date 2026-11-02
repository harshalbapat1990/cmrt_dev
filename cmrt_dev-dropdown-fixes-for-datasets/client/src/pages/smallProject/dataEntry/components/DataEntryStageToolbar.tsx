import { useCallback, useRef, useState } from "react";
import { SelectListbox } from "@/components/common/Select";
import { formatEmissionsOrQuantity } from "@/utils/utils";
import { useOutsideClick } from "../useOutsideClick";

interface Props {
  isConstructionStage: boolean;
  isRecurringStage: boolean;
  isLargeProject: boolean;
  isBusinessCaseStage: boolean;
  isReadOnly: boolean;
  totalEmissions: number;
  operationalLifeYears: number | null;
  designReportNumbers: number[];
  designReportNumber: number;
  onRequestDesignReportChange: (reportNumber: number) => void;
  activeOptionId: string | null;
  options: { label: string; value: string }[];
  onOptionChange: (optionId: string) => void;
  onOpenCopyData: () => void;
  onOpenManageOptions: () => void;
}

/** Toolbar for stage totals, design report selection, and Business Case options. */
export function DataEntryStageToolbar({
  isConstructionStage,
  isRecurringStage,
  isLargeProject,
  isBusinessCaseStage,
  isReadOnly,
  totalEmissions,
  operationalLifeYears,
  designReportNumbers,
  designReportNumber,
  onRequestDesignReportChange,
  activeOptionId,
  options,
  onOptionChange,
  onOpenCopyData,
  onOpenManageOptions,
}: Props) {
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const moreMenuRef = useRef<HTMLDivElement>(null);
  const closeMenu = useCallback(() => setMoreMenuOpen(false), []);
  useOutsideClick(moreMenuRef, closeMenu, moreMenuOpen);

  return (
    <>
      <div className="flex px-12 pt-10 pb-6 items-center justify-between">
        {!isConstructionStage && (
          <div className="flex flex-col gap-0.5">
            {totalEmissions > 0 && <div className="text-sm text-text-faint">Total Emissions</div>}
            {totalEmissions > 0 && (
              <div className="text-[28px] font-bold text-text-dark leading-tight">
                {formatEmissionsOrQuantity(totalEmissions, "en-US")} {" "}
                <span className="font-light">tCO<sub>2</sub>e</span>
              </div>
            )}
          </div>
        )}
        <div className="flex items-center gap-4">
          {isConstructionStage && isLargeProject && designReportNumbers.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-text-base">Design Report</span>
              <select
                className="h-9 border border-border-input rounded px-2 text-sm bg-white"
                value={designReportNumber}
                disabled={isReadOnly}
                onChange={(event) => {
                  if (isReadOnly) return;
                  const nextReport = Number(event.target.value);
                  if (nextReport !== designReportNumber) onRequestDesignReportChange(nextReport);
                }}
              >
                {designReportNumbers.map((number) => (
                  <option key={number} value={number}>Design Report {number}</option>
                ))}
              </select>
            </div>
          )}
          {isBusinessCaseStage && (
            <>
              <span className="text-sm text-text-base">Currently editing</span>
              <SelectListbox
                value={activeOptionId ?? ""}
                onChange={onOptionChange}
                options={options}
              />
              <div className="relative" ref={moreMenuRef}>
                {!isReadOnly && (
                  <button
                    className="p-2 rounded hover:bg-neutral-200 cursor-pointer transition-colors"
                    onClick={() => setMoreMenuOpen((open) => !open)}
                    aria-label="More options"
                    type="button"
                  >
                    <span className="material-symbols-rounded">more_vert</span>
                  </button>
                )}
                {moreMenuOpen && (
                  <div className="absolute cursor-pointer right-0 mt-1 w-44 rounded-lg border border-neutral-200 bg-white shadow-lg z-30 py-1">
                    <button
                      className="w-full text-left px-4 py-2 text-sm text-text-base hover:bg-neutral-50 transition-colors"
                      onClick={() => { closeMenu(); onOpenCopyData(); }}
                      type="button"
                    >
                      Copy data
                    </button>
                    <button
                      className="w-full text-left px-4 py-2 text-sm text-text-base hover:bg-neutral-50 transition-colors"
                      onClick={() => { closeMenu(); onOpenManageOptions(); }}
                      type="button"
                    >
                      Manage options
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
      {!isConstructionStage && !isRecurringStage && (
        <div className="text-text-base text-sm px-12 mb-4">Operational life of project: {operationalLifeYears} years</div>
      )}
    </>
  );
}
