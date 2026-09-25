import React from "react";
import { formatDisplayNumber } from "@/utils/utils";

/* ================= TYPES ================= */

export type ColumnConfig<T> = {
  key: keyof T;
  label: string;
  align?: "left" | "right" | "center";
  render?: (value: T[keyof T], row: T) => React.ReactNode;
};

interface DataTableProps<T> {
  title?: string;
  columns: ColumnConfig<T>[];
  rows: T[];
  onExport?: () => void;
}

/* ================= COMPONENT ================= */

function DataTable<T>({
  title,
  columns,
  rows,
  onExport,
}: DataTableProps<T>) {
  return (
    <div className="bg-white border border-[#E8E8E8] rounded-[var(--radius-3)]">

      {/* ================= HEADER ================= */}
      {(title || onExport) && (
        <div className="flex items-center justify-between px-6 py-4">
          {title && (
            <h2 className="text-base font-medium text-[#3F3A38]">
              {title}
            </h2>
          )}

          {onExport && (
            <button
              onClick={onExport}
              className="inline-flex items-center gap-2 rounded-[var(--radius-3)]  cursor-pointer bg-[#D35400] px-4 py-2 text-sm text-white hover:brightness-95"
            >
              <span className="material-symbols-rounded text-[18px]">
                description
              </span>
              Export to Excel
            </button>
          )}
        </div>
      )}

      {/* ================= TABLE ================= */}
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-sm">

          {/* ===== HEAD ===== */}
          <thead className="bg-[#F2F2F2] text-[#6C6C6C]">
            <tr>
              <th className="sticky left-0 z-10 w-12 border-r border-b border-[#E8E8E8] bg-[#F2F2F2] px-3 py-2 text-left font-medium">
                #
              </th>

              {columns.map((col) => (
                <th
                  key={String(col.key)}
                  className="border-r border-b border-[#E8E8E8] px-4 py-2 text-left whitespace-nowrap font-medium"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>

          {/* ===== BODY ===== */}
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={columns.length + 1}
                  className="px-6 py-10 text-center text-[#6C6C6C]"
                >
                  No data available
                </td>
              </tr>
            )}

            {rows.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={rowIndex % 2 === 0 ? "bg-white" : "bg-[#FAFAFA]"}
              >
                {/* Row index */}
                <td className="sticky left-0 z-10 border-r border-b border-[#E8E8E8] bg-[#F2F2F2] px-3 py-2 font-medium text-[#3F3A38]">
                  {rowIndex + 1}
                </td>

                {columns.map((col) => (
                  <td
                    key={String(col.key)}
                    className={`border-r border-b border-[#EFEFEF] px-4 py-2 whitespace-nowrap ${
                      col.align === "right"
                        ? "text-right tabular-nums"
                        : col.align === "center"
                        ? "text-center"
                        : "text-left"
                    }`}
                  >
                    {col.render
                      ? col.render(row[col.key], row)
                      : col.align === "right"
                      ? formatDisplayNumber(row[col.key])
                      : String(row[col.key] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default DataTable;