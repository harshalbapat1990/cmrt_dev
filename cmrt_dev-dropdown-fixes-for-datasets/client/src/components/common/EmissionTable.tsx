import React from "react";

/** One row in the Emissions table */
export type EmissionRow = {
  id: string;

  /** First column — for Small: lifecycle stage; for Contractor: activity type */
  stageOrActivity: string;

  /** Core taxonomy */
  category: string;
  subCategory: string;
  source: string;

  /** Optional numeric details (if you decide to show them) */
  quantity?: number | null;
  unit?: string | null;

  /** Meta */
  origin?: "uploaded" | "manual"; // for a small pill badge
  notes?: string | null;
};

export type EmissionTableProps = {
  /** Table rows (controlled by parent) */
  rows: EmissionRow[];

  /** Header label for the first column (e.g., "Project lifecycle stage" or "Activity type") */
  // leadingHeader: string;

  /** Callbacks (optional) */
  onRemove?: (id: string) => void;
  onRowClick?: (id: string) => void; // if you want to open a details panel

  col2Header?: string;
  col3Header?: string;
  showSource?: boolean;

  /** Columns toggles */
  showQuantity?: boolean; // show Quantity & Unit columns
  showOrigin?: boolean;   // show Uploaded/Manual badge column
  compact?: boolean;      // reduce paddings

  /** UI */
  className?: string;
  emptyMessage?: string;
};

const headerBaseCls =
  // removed `uppercase` to keep sentence case; kept small font + tracking for table look
  "px-3 py-3 text-left text-sm font-medium tracking-wide text-neutral-600";
const cellBaseCls = "px-3 py-2 text-sm text-[#48413F]";

const EmissionTable: React.FC<EmissionTableProps> = ({
  rows,
  // leadingHeader,
  col2Header = "Emissions category",
  col3Header = "Emissions sub-category",
  showSource = true,
  onRemove,
  onRowClick,
  showQuantity = false,
  showOrigin = true,
  compact = false,
  className,
  emptyMessage = "No emission sources added yet.",
}) => {
  // no sorting: render rows in the order provided
  const rowPad = compact ? "py-1.5" : "py-2";

  return (
    <div
      className={[
        "overflow-x-auto rounded-md border border-neutral-95 bg-white",
        className || "",
      ].join(" ")}
    >
      <table className="min-w-full border-collapse">
        <thead className="bg-neutral-90">
          <tr className="border-b  border-neutral-200">
            {/* <th scope="col" className={headerBaseCls}>
              {leadingHeader}
            </th> */}
            <th scope="col" className={headerBaseCls}>{col2Header}</th>
            <th scope="col" className={headerBaseCls}>{col3Header}</th>
            {showSource && <th scope="col" className={headerBaseCls}>Emissions source</th>}

          </tr>
        </thead>

        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={
                  (showSource ? 4 : 3) + (showQuantity ? 2 : 0) + (showOrigin ? 1 : 0) + ((onRemove || onRowClick) ? 1 : 0)
                }
                className="px-3 py-6 text-center text-sm text-neutral-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, idx) => (
              <tr
                key={row.id}
                className={[
                  "border-t border-neutral-100",
                  idx % 2 === 0 ? "bg-white" : "bg-neutral-50/30",
                  onRowClick ? "cursor-pointer hover:bg-neutral-50" : "",
                ].join(" ")}
                onClick={() => onRowClick?.(row.id)}
              >
                {/* <td className={`${cellBaseCls} ${rowPad}`}>
                  <span className="whitespace-nowrap">{row.stageOrActivity}</span>
                </td> */}
                <td className={`${cellBaseCls} ${rowPad}`}>
                  <span className="truncate">{row.category}</span>
                </td>
                <td className={`${cellBaseCls} ${rowPad}`}>
                  <span className="truncate">{row.subCategory}</span>
                </td>
                {showSource && (
                  <td className={`${cellBaseCls} ${rowPad}`}>
                    <span className="truncate">{row.source}</span>
                  </td>
                )}

                {/* Optional future columns:
                {showQuantity && (
                  <>
                    <td className={`${cellBaseCls} ${rowPad}`}>
                      {typeof row.quantity === "number" ? row.quantity : "—"}
                    </td>
                    <td className={`${cellBaseCls} ${rowPad}`}>
                      {row.unit ?? "—"}
                    </td>
                  </>
                )}

                {showOrigin && (
                  <td className={`${cellBaseCls} ${rowPad}`}>
                    {row.origin ? (
                      <span
                        className={[
                          "inline-flex items-center rounded-full px-2 py-0.5 text-xs",
                          row.origin === "uploaded"
                            ? "bg-blue-50 text-blue-700"
                            : "bg-emerald-50 text-emerald-700",
                        ].join(" ")}
                      >
                        {row.origin === "uploaded" ? "Uploaded file" : "Manual"}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                )}

                {(onRemove || onRowClick) && (
                  <td className={`${cellBaseCls} ${rowPad}`}>
                    <div className="flex justify-end gap-2">
                      {onRemove && (
                        <button
                          type="button"
                          className="rounded border border-neutral-300 px-2 py-1 text-xs text-neutral-700 hover:bg-neutral-100"
                          onClick={(e) => {
                            e.stopPropagation();
                            onRemove(row.id);
                          }}
                          aria-label={`Remove row for ${row.stageOrActivity}`}
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  </td>
                )} */}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default EmissionTable;