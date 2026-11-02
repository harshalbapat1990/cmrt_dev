import { formatDisplayNumber } from "@/utils/utils";
import { NumericInput } from "@/components/common/NumericInput";
import AddIcon from "@/assets/icons/add.svg";
import Download from "@/assets/icons/download.svg";
import UploadFile from "@/assets/icons/upload_file.svg";
import type { EpdRow } from "../concreteRegisterTypes";
import type { useConcreteRegisterActions } from "../hooks/useConcreteRegisterActions";

export type ConcreteEpdPcfTableActions = Pick<
  ReturnType<typeof useConcreteRegisterActions>,
  "addEpdRow" | "updateEpdRow" | "syncEpdRow" | "deleteEpdRow" | "getEpdEmissions"
>;

export interface ConcreteEpdPcfTableProps {
  rows: EpdRow[];
  readOnly: boolean;
  actions: ConcreteEpdPcfTableActions;
}

const cellClass = "px-3 py-2 border-b border-neutral-90 align-top";
const headerClass = "bg-neutral-95 text-text-faint text-xs uppercase px-3 py-2 text-left whitespace-nowrap";

function formatEmissions(value: number | null): string {
  return formatDisplayNumber(value, { decimalsBelowThreshold: 4, threshold: Number.MAX_SAFE_INTEGER });
}

/** EPD / PCF rows have an independent schema and edit/save lifecycle. */
export function ConcreteEpdPcfTable({ rows, readOnly, actions }: ConcreteEpdPcfTableProps) {
  const { addEpdRow, updateEpdRow, syncEpdRow, deleteEpdRow, getEpdEmissions } = actions;

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mt-4 mb-5 gap-4">
        {!readOnly && (
          <div className="flex flex-wrap gap-6 text-primary text-sm">
            <button type="button" className="flex items-center gap-1 hover:bg-neutral-90 px-0.5">
              <img src={Download} alt="" className="h-5 w-5" />
              <span className="font-medium">{rows.length ? "Export to Excel" : "Download blank template"}</span>
            </button>
            <button type="button" className="flex items-center gap-1 hover:bg-neutral-90 px-0.5">
              <img src={UploadFile} alt="" className="h-5 w-5" />
              <span className="font-medium">Upload file</span>
            </button>
            <button type="button" onClick={() => void addEpdRow()} className="flex items-center gap-1 cursor-pointer hover:bg-neutral-90 px-0.5">
              <img src={AddIcon} alt="" className="h-5 w-5" />
              <span className="font-medium">Add row</span>
            </button>
          </div>
        )}
      </div>
      <table className="border border-neutral-90 w-full text-sm">
        <thead>
          <tr>
            <th className={headerClass}>Mix ID</th>
            <th className={headerClass}>GWP Total A1-A3 (kgCO&#8322;e/m&#179;)</th>
            <th className={headerClass}>Volume (m&#179;)</th>
            <th className={headerClass}>Emissions (tCO&#8322;e)</th>
            <th className={headerClass}>Notes</th>
            {!readOnly && <th className={`${headerClass} w-12`} />}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={readOnly ? 5 : 6} className="px-4 py-10 text-center text-neutral-90">
                <div className="text-base font-medium">No data yet</div>
                <div className="text-sm">Get started by adding data manually or uploading a file</div>
              </td>
            </tr>
          )}
          {rows.map((row) => {
            const emissions = getEpdEmissions(row);
            return (
              <tr key={row.id}>
                <td className={cellClass}>
                  {readOnly ? <span>{row.mixId || "-"}</span> : (
                    <input
                      type="text"
                      value={row.mixId}
                      onChange={(event) => updateEpdRow(row.id, "mixId", event.target.value)}
                      onBlur={() => syncEpdRow(row)}
                      className="w-full border border-neutral-90 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                      aria-label="Mix ID"
                    />
                  )}
                </td>
                <td className={cellClass}>
                  {readOnly ? <span>{formatDisplayNumber(row.gwpA1A3, { decimalsBelowThreshold: 4, threshold: Number.MAX_SAFE_INTEGER })}</span> : (
                    <NumericInput
                      value={row.gwpA1A3}
                      allowDecimal
                      onChange={(value) => updateEpdRow(row.id, "gwpA1A3", typeof value === "number" ? value : null)}
                      onBlur={() => syncEpdRow(row)}
                      ariaLabel="GWP A1-A3"
                    />
                  )}
                </td>
                <td className={cellClass}>
                  {readOnly ? <span>{formatDisplayNumber(row.volumeM3)}</span> : (
                    <NumericInput
                      value={row.volumeM3}
                      allowDecimal
                      onChange={(value) => updateEpdRow(row.id, "volumeM3", typeof value === "number" ? value : null)}
                      onBlur={() => syncEpdRow(row)}
                      ariaLabel="Volume m3"
                    />
                  )}
                </td>
                <td className={cellClass}><span className="text-text-faint">{formatEmissions(emissions)}</span></td>
                <td className={cellClass}>
                  {readOnly ? <span>{row.notes || "-"}</span> : (
                    <input
                      type="text"
                      value={row.notes}
                      onChange={(event) => updateEpdRow(row.id, "notes", event.target.value)}
                      onBlur={() => syncEpdRow(row)}
                      className="w-full border border-neutral-90 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                      aria-label="Notes"
                    />
                  )}
                </td>
                {!readOnly && (
                  <td className="whitespace-nowrap px-2 py-3 w-12">
                    <button
                      type="button"
                      title="Delete row"
                      onClick={() => void deleteEpdRow(row.id)}
                      className="inline-flex items-center justify-center cursor-pointer h-8 w-8 rounded hover:bg-neutral-95 text-text-faint hover:text-red-600"
                    >
                      <span className="material-symbols-rounded text-[20px]">delete</span>
                    </button>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
