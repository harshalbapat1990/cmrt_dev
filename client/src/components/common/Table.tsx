import React, { useMemo, useState, useEffect } from "react";
import { SelectListbox } from "./Select";
import Download from "../../assets/icons/download.svg";
import UploadFile from "../../assets/icons/upload_file.svg";
import Add from "../../assets/icons/add.svg";
import { downloadCsv, type CsvColumn } from "../../utils/downloadCsv";
import { formatDisplayNumber } from "@/utils/utils";

const formatNoteDate = (iso: string): string => {
  try {
    return new Date(iso).toLocaleDateString("en-AU", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
};

interface Column<T> {
  header: string;
  key: keyof T | "actions";
  render?: (item: T) => React.ReactNode;
  editable?: boolean; // if true, table should be editable for that cell
  editableWhen?: (row: any) => boolean;
  renderEditor?: (args: {
    value: any;
    onChange: (next: any) => void;
    onCommit: (next?: any) => void;
    item: any;
  }) => React.ReactNode;
  renderAddRow?: (args: {
    value: any;
    onChange: (next: any) => void;
    item: any;
  }) => React.ReactNode;
  editorType?: any;
  getOptions?: (ctx: { row: any; isNew: boolean }) => Promise<any> | null;
  idKey?: keyof T;
  dependsOnKeys?: (keyof T)[];
  clearsOnChange?: (keyof T)[];
  onSelect?: (selected: any | undefined) => Record<string, any>;
  noCache?: boolean;
  refreshOnDepsChange?: boolean;
  width?: string;
}

interface TableProps<T> {
  data: T[];
  columns: any;
  onRowClick?: (item: T) => void;
  /** Prefer batch patch if cascading requires multiple field updates at once */
  onRowPatch?: (args: {
    id: T extends { id: infer I } ? I : string | number;
    patch: Partial<T>;
    item: T;
  }) => void;
  onCellChange?: (args: {
    id: T extends { id: infer I } ? I : string | number;
    key: keyof T;
    value: any;
    item: T;
  }) => void; // to change cell value
  getRowKey?: (item: any, index: any) => any;
  enableInlineNewRow?: boolean;
  newRowInitial?: () => Partial<T>;
  onNewRowInit?: () => Promise<void> | void;
  onNewRowSave?: (draft: Partial<T>) => Promise<boolean | void> | void;
  onNewRowCancel?: () => void;
  exportFileName?: string;
  onRequestUpload?: () => void;
  readOnly?: boolean;
  hideToolbarActions?: boolean;
  hideAddRow?: boolean;
  onDeleteRow?: (id: string | number) => void;
  onEditRow?: (item: any) => void;
  actionsBtn?: boolean;
  onActionSelect?: (value: string)=> void;
  onCellDoubleClick?: (key: string, row: any) => void;
}

const NUMERIC_KEYS_TO_FORMAT = new Set([
  // emissions
  "emissions_tco2e",
  "total_emissions_tco2e",
  "location_based_tco2e",
  "market_based_tco2e",
  // quantities
  "quantity",
  "quantity_mwh",
]);

const NEW_ROW_MIX_OPTIONS = [
  { label: "New mix with mix design", value: "New mix with mix design" },
  { label: "New mix with EPD/PCF", value: "New mix with EPD/PCF" },
]

const isNumber = (v: any) => {
  if (v === "" || v == null || v === "-") return false;
  const cleaned = typeof v === "string" ? v.replace(/,/g, "").trim() : v;
  return Number.isFinite(Number(cleaned));
};

const shouldFormatCell = (col: any, value: any) => {
  const key = String(col.key);
  return (
    (col.editorType === "number" || NUMERIC_KEYS_TO_FORMAT.has(key)) &&
    isNumber(value)
  );
};

const NEW_ROW_ID = "__NEW__";

const DefaultEditor: React.FC<{
  value: any;
  onChange: (v: any) => void;
  onCommit: (next?: any) => void;
  autoFocus?: boolean,
  editorType?: any;
}> = ({ value, onChange, onCommit, autoFocus = true, editorType }) => {
  const ref = React.useRef<HTMLInputElement>(null);
  const isNumber = editorType === "number" || (typeof value === "number" && Number.isFinite(value));
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (isNumber) {
      // Allow only numbers and a single optional decimal point 
      if (val === "" || /^-?\d*\.?\d*$/.test(val)) {
        onChange(val);
      }
    } else {
      onChange(val);
    }
  };

  const handleCommit = (e: React.SyntheticEvent<HTMLInputElement>) => {
    let val: string | number = e.currentTarget.value;
    if (isNumber && val !== "") {
      const parsed = Number(val);
      val = isNaN(parsed) ? val : parsed;
    }
    onCommit(val);
  };
  return (
    <input
      ref={ref}
      type="text"
      inputMode={isNumber ? "decimal" : "text"}
      className={[
        "w-full border rounded px-2 py-1 text-sm",
        isNumber ? "text-right tabular-nums" : "text-left",
      ].join(" ")}
      value={value ?? ""}
      onChange={handleChange}
      onBlur={handleCommit}
      onKeyDown={(e: any) => {
        if (e.key === "Enter" || e.key === "Escape") { handleCommit(e); }
      }}
      autoFocus={autoFocus}
    />
  );
};

/** Determine current select value for a row/column */
const getSelectCurrentValue = (row: any, col: Column<any>, options: any[]) => {
  const arr = Array.isArray(options) ? options : [];
  const idVal = col.idKey ? row[col.idKey as string] : undefined;
  if (idVal != null && idVal !== "") return String(idVal);
  const label = row[col.key as string];
  const matched = arr.find((o: any) => o.label === label);
  return matched ? matched.value : "";
};

const SelectEditor = ({
  row,
  col,
  isNew,
  onCommit,
  onApplyCascadeNewRow,
  onApplyCascadeExistingRow,
}: {
  row: any;
  col: Column<any>;
  isNew: boolean;
  onCommit?: () => void;
  onApplyCascadeNewRow?: (col: Column<any>, selected: any) => Promise<void>;
  onApplyCascadeExistingRow?: (item: any, col: Column<any>, selected: any) => Promise<void>;
}) => {
  const [options, setOptions] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const depValues = (col.dependsOnKeys || []).map((k) => String(row[k as string] ?? ""));

  useEffect(() => {
    let cancelled = false;

    (async () => {
      if (col.editorType !== "select" || !col.getOptions) {
        setOptions([]);
        return;
      }
      // If there are dependencies, ensure they have values before calling
      const hasDeps = (col.dependsOnKeys && col.dependsOnKeys.length > 0) || false;
      if (hasDeps) {
        const ready = (col.dependsOnKeys || []).every((d) => {
          const v = row[d as string];
          return v != null && String(v) !== "";
        });
        if (!ready) {
          setOptions([]);
          return;
        }
      }
      try {
        setLoading(true);
        const res = await col.getOptions({ row, isNew });
        if (cancelled) return;
        setOptions(Array.isArray(res) ? res : []);
      } catch (e) {
        if (!cancelled) setOptions([]);
        console.error("Failed to fetch options", e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    isNew,
    String(col.key),
    row?.id,
    ...depValues,
  ]);

  const currentValue = getSelectCurrentValue(row, col, options);

  return (
    <SelectListbox
      value={currentValue}
      onChange={async (val: string) => {
        const selected = options.find((o: any) => o.value === val);
        if (isNew) {
          await onApplyCascadeNewRow?.(col, selected);
        } else {
          await onApplyCascadeExistingRow?.(row, col, selected);
        }
        onCommit?.();
      }}
      options={options}
      loading={loading as any}
      autoFocus={!isNew}
      minMenuWidth={240}
    />
  );
};

const Table = <T extends { id: string | number }>({
  data,
  columns,
  onRowClick,
  onCellChange,
  // getRowKey,
  onRowPatch,
  enableInlineNewRow = false,
  newRowInitial,
  onNewRowInit,
  onNewRowSave,
  onNewRowCancel,
  exportFileName,
  onRequestUpload,
  readOnly,
  hideToolbarActions,
  onDeleteRow,
  onEditRow,
  hideAddRow,
  actionsBtn,
  onActionSelect,
  onCellDoubleClick,
}: TableProps<T>) => {
  const [editing, setEditing] = useState<{
    id: string | number;
    key: keyof T;
  } | null>(null);
  const [draft, setDraft] = useState<any>("");

  const [newRowDraft, setNewRowDraft] = useState<any | null>(null);
  const [savingNew, setSavingNew] = useState(false);
  const [newRowMix, setNewRowMix] = useState("");


  const csvColumns: CsvColumn[] = useMemo(
    () =>
      (columns || [])
        .filter((c: any) => c.key !== "actions")
        .map((c: any) => ({
          key: String(c.key),
          label: c.header,
        })),
    [columns],
  );

  const handleDownloadOrExport = () => {
    const fname = exportFileName || (data.length ? "export.csv" : "template.csv");
    if (!data.length) {
      downloadCsv(csvColumns, [], fname, true, true);
    } else {
      downloadCsv(csvColumns, data as any[], fname, false, true);
    }
  };

  const effectiveColumns: Column<T>[] = useMemo(() => {
    if (!enableInlineNewRow) return columns;
    const hasActions = columns.some((c: any) => c.key === "actions");
    if (hasActions) return columns;
    return [
      ...columns,
      {
        header: "",
        key: "actions",
        width: "7%",
      } as Column<T>,
    ];
  }, [columns, enableInlineNewRow]);

  const startEditing = (item: any, key: any) => {
    if (readOnly) return;
    setEditing({ id: item.id, key });

    const val = item[key];
    setDraft(val === undefined || val === null ? "" : val);

  };

  const stopEditing = () => {
    setEditing(null);
    setDraft("");
  };

  const commit = (item: any, key: any, next?: any) => {
    if (!onCellChange) {
      stopEditing();
      return;
    }
    if (!editing || editing.id !== item.id || editing.key !== key) {
      return;
    }
    let valueToCommit = next !== undefined ? next : draft;

    if (columns.find((c: any) => c.key === key)?.editorType === "number") {
      valueToCommit = Number(valueToCommit);
      if (isNaN(valueToCommit)) valueToCommit = null;
    }

    const currentValue = item[key];

    if (currentValue !== valueToCommit) {
      onCellChange({ id: item.id, key, value: valueToCommit, item });
    }

    stopEditing();
  };



  const defaultEditor = (
    value: any,
    onChange: (v: any) => void,
    onCommit: (next?: any) => void,
    autoFocus: boolean = true,
    editorType?: any
  ) => <DefaultEditor value={value} onChange={onChange} onCommit={onCommit} autoFocus={autoFocus} editorType={editorType} />;


  /** Apply cascading changes for NEW row (local draft) */
  const applyCascadeNewRow = async (col: Column<T>, selected: any | undefined) => {
    if (!newRowDraft) return;
    const patch: any = {};
    // Set current field id + label
    if (selected) {
      patch[col.key as string] = selected.label;
      if (col.idKey) patch[col.idKey as string] = selected.value;
    } else {
      patch[col.key as string] = "";
      if (col.idKey) patch[col.idKey as string] = "";
    }
    (col.clearsOnChange || []).forEach((k) => {
      patch[k as string] = "";
    });
    const extraFromSelect = col.onSelect ? col.onSelect(selected) : {};

    const nextDraft = { ...newRowDraft, ...patch, ...extraFromSelect };
    setNewRowDraft(nextDraft);
  };

  /** Apply cascading for EXISTING row */
  const applyCascadeExistingRow = async (
    item: T,
    col: Column<T>,
    selected: any | undefined,
  ) => {
    const basePatch: Partial<T> = {} as any;
    (basePatch as any)[col.key as string] = selected ? selected.label : "";
    if (col.idKey)
      (basePatch as any)[col.idKey as string] = selected ? selected.value : "";

    (col.clearsOnChange || []).forEach((k) => {
      (basePatch as any)[k as string] = "";
    });
    // Allow the column to inject extra auto-fill fields (e.g. default frequency)
    const extraFromSelect = col.onSelect ? col.onSelect(selected) : {};
    Object.assign(basePatch, extraFromSelect);

    if (onRowPatch) {
      onRowPatch({ id: item.id as any, patch: basePatch, item });
    } else if (onCellChange) {
      Object.entries(basePatch).forEach(([k, v]) => {
        onCellChange({ id: item.id as any, key: k as keyof T, value: v, item });
      });
    }
  };



  const startNewRow = async () => {
    if (!enableInlineNewRow) return;
    if (readOnly) return;
    if (newRowDraft) return;
    try {
      if (onNewRowInit) await onNewRowInit();
    } catch { }
    const base = (newRowInitial ? newRowInitial() : {}) as any;
    setNewRowDraft({ id: NEW_ROW_ID, ...base });
  };

  const cancelNewRow = () => {
    setNewRowDraft(null);
    onNewRowCancel?.();
  };

  const saveNewRow = async (e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    if (!onNewRowSave || !newRowDraft) return;
    try {
      setSavingNew(true);

      const ok = await onNewRowSave(newRowDraft);

      if (ok === false) {
        setSavingNew(false);
        return;
      }
      setNewRowDraft(null);
    } catch (err) {
      console.error("Failed to save new row:", err);
    } finally {
      setSavingNew(false);
    }
  };

  const setNewDraftField = (key: any, val: any) => {
    setNewRowDraft((prev: any) => ({ ...(prev || {}), [key]: val }));
  };

  const renderNewRowCell = (col: Column<T>) => {
    if (!newRowDraft) return null;

    if (col.key === "actions") {
      return (
        <td className="whitespace-nowrap px-2 py-3 w-10">
          <div className="flex items-center gap-1 justify-end">
            <button
              type="button"
              className="inline-flex items-center justify-center h-8 w-8 rounded text-primary hover:bg-neutral-95 cursor-pointer"
              title="Save"
              onClick={(e: any) => saveNewRow(e)}
              disabled={savingNew}
            >
              <span className="material-symbols-rounded text-success">
                check
              </span>
            </button>
            <button
              type="button"
              className="inline-flex items-center justify-center h-8 w-8 rounded text-primary hover:bg-neutral-95 cursor-pointer"
              title="Cancel"
              onClick={cancelNewRow}
              disabled={savingNew}
            >
              <span className="material-symbols-rounded text-[20px]">
                close
              </span>
            </button>
          </div>
        </td>
      );
    }

    const key = col.key as keyof T;
    const value = newRowDraft[key as any];
    const isEditable = col.editable ?? true;

    if (!isEditable) {
      const isNumericNewCell = col.editorType === "number" || String(col.key) === "emissions_tco2e";
      return (
        <td className={["whitespace-normal break-words overflow-hidden px-2 py-3 text-text-table-cell", isNumericNewCell ? "text-right tabular-nums" : ""].join(" ").trim()}>
          {col.renderAddRow
            ? col.renderAddRow({ value, onChange: () => {}, item: newRowDraft })
            : col.render
            ? col.render(newRowDraft as T)
            : (value ?? "")}
        </td>
      );
    }
    if (col.editorType === "select" && col.getOptions) {
      return (
        <td className="whitespace-nowrap px-2 py-3 text-text-table-cell">
          <SelectEditor row={newRowDraft} col={col} isNew={true}
            onApplyCascadeNewRow={applyCascadeNewRow} />
        </td>
      );
    }

    return (
      <td className="px-2 py-3 text-text-table-cell">
        {col.renderAddRow
          ? col.renderAddRow({
            value,
            onChange: (next: any) => setNewDraftField(key, next),
            item: newRowDraft,
          })
          : col.renderEditor
            ?
            col.renderEditor({
              value,
              onChange: (next: any) => setNewDraftField(key, next),
              onCommit: (next: any) => setNewDraftField(key, next),
              item: newRowDraft,
            })
            : defaultEditor(value ?? "", (next) => setNewDraftField(key, next), () => { }, false, col.editorType)}
      </td>
    );
  };

  return (
    <>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mt-4 mb-5 gap-4">
        <div className="flex flex-wrap text-primary text-sm">
          {!hideToolbarActions && (
            <button
              type="button"
              onClick={handleDownloadOrExport}
              className="flex items-center gap-1 hover:bg-neutral-90 px-4 py-2 cursor-pointer"
            >
              <img src={Download} alt="" className="h-5 w-5" />
              <span className="font-medium">
                {data.length ? "Export to Excel" : "Download blank template"}
              </span>
            </button>
          )}

          {!readOnly && (
            <>
              {!hideToolbarActions && (
                <button
                  type="button"
                  onClick={onRequestUpload}
                  className="flex items-center gap-1 hover:bg-neutral-90 px-4 py-2 cursor-pointer"
                >
                  <img src={UploadFile} alt="" className="h-5 w-5" />
                  <span className="font-medium">Upload file</span>
                </button>
              )}

              {!hideAddRow && !actionsBtn && (
                <button
                  type="button"
                  onClick={startNewRow}
                  className="flex items-center gap-1 hover:bg-neutral-90 px-4 py-2 cursor-pointer"
                >
                  <img src={Add} alt="" className="h-5 w-5" />
                  <span className="font-medium">Add row</span>
                </button>
              )}
                {actionsBtn && (
                <SelectListbox
                  className="w-40!"
                  placeholder="New row or mix"
                  value={newRowMix ?? ""}
                  onChange={(value: any) => {
                    setNewRowMix("");
                    onActionSelect?.(value);
                  }}
                  options={NEW_ROW_MIX_OPTIONS}
                />
              )}
            </>
          )}
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg">
        <table className={`w-full table-fixed divide-y divide-gray-200 bg-white text-sm ${readOnly ? "opacity-70" : ""}`}>
          <thead className="text-left">
            <tr>
              {effectiveColumns.map((col, idx) => {
                const isNumericHeader =
                  col.editorType === "number" || String(col.key) === "emissions_tco2e";

                // Hide actions column header in readOnly
                if (readOnly && col.key === "actions") return null;
                return (
                  <th key={idx}
                    className={[
                      "px-2 py-3 text-xs text-text-base font-medium",
                      isNumericHeader ? "text-right" : "text-left",
                    ].join(" ")}
                    style={col.width ? { width: col.width } : undefined}
                  >
                    {col.header}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y-2 divide-gray-100">

            {/* If no data and not adding a new row */}
            {data.length === 0 && !newRowDraft && (
              <tr>
                <td
                  colSpan={effectiveColumns.length}
                  className="px-4 py-10 text-center text-text-base"
                >
                  <div className=" font-medium leading-relaxed">No data yet</div>
                  <div className="text-sm">
                    Get started by adding data manually or uploading a file
                  </div>
                </td>
              </tr>
            )}
            {enableInlineNewRow && !readOnly && newRowDraft && (
              <tr key={NEW_ROW_ID} className="bg-new-row">
                {effectiveColumns.map((col, idx) => (
                  <React.Fragment key={`new-${String(col.key)}-${idx}`}>
                    {renderNewRowCell(col)}
                  </React.Fragment>
                ))}
              </tr>
            )}
            {data.map((item, rowIdx) => {
              return (
                <tr
                  key={rowIdx}
                  onClick={() => onRowClick?.(item)}
                  className={
                    onRowClick
                      ? "cursor-pointer hover:bg-gray-50 transition-colors"
                      : ""
                  }
                >
                  {effectiveColumns.map((col, idx) => {
                    const isNumericCol =
                      col.editorType === "number" || String(col.key) === "emissions_tco2e";
                    const isRowEditing = editing?.id === item.id;
                    if (readOnly && col.key === "actions") return null;
                    if (col.key === "actions") {
                      return (
                        <td
                          key={idx}
                          className="whitespace-nowrap px-2 py-3 text-text-table-cell w-10"
                        >
                          {onDeleteRow && !isRowEditing && !(item as any)?._fromBoundary && (
                            <button
                              type="button"
                              onClick={() => onDeleteRow(item.id)}
                              title="Delete row"
                              className="inline-flex items-center justify-center cursor-pointer h-8 w-8 rounded text-red-400 hover:text-red-600 hover:bg-red-50"
                            >
                              <span className="material-symbols-rounded text-[18px]">delete</span>
                            </button>
                          )}
                          {onEditRow && !isRowEditing && (
                            <button
                              type="button"
                              onClick={() => onEditRow(item)}
                              title="Edit row"
                              className="inline-flex cursor-pointer items-center justify-center h-8 w-8 rounded text-text-faint hover:text-primary hover:bg-neutral-95"
                            >
                              <span className="material-symbols-rounded text-[18px]">edit</span>
                            </button>
                          )}
                        </td>
                      );
                    }
                    const isEditing =
                      editing &&
                      editing.id === item.id &&
                      editing.key === col.key;
                    const value =
                      col.key === "actions" ? null : (item[col.key] as any);

                    if (
                      isEditing &&
                      col.editorType === "select" &&
                      col.getOptions
                    ) {
                      return (
                        <td
                          key={idx}
                          className="px-2 py-3 text-text-table-cell"
                        >
                          <SelectEditor
                            key={`editor-${item.id}-${String(col.key)}`}
                            row={item}
                            col={col}
                            isNew={false}
                            onCommit={() => setTimeout(stopEditing, 0)}
                            onApplyCascadeExistingRow={applyCascadeExistingRow}
                          />
                        </td>
                      );
                    }

                    return (
                      <td
                        key={idx}
                        className={[
                          isNumericCol ? "whitespace-nowrap" : "whitespace-normal break-words overflow-hidden",
                          "px-2 py-3 text-text-table-cell",
                          isNumericCol ? "text-right tabular-nums" : "text-left",
                        ].join(" ")}
                        onDoubleClick={() => {
                          if (readOnly) return;
                          const baseEditable =
                            (col.editable ?? true);
                          const checkToEditCell = col.editableWhen ? col.editableWhen(item) : true;
                          const isEditable = baseEditable && checkToEditCell;

                          if (!isEditing && isEditable) startEditing(item, col.key);
                          else if (!isEditing && !isEditable) onCellDoubleClick?.(String(col.key), item);
                        }}
                      >
                        {isEditing ? (
                          <div key={`edit-${item.id}-${String(col.key)}`}>
                            {col.renderEditor ? (
                              col.renderEditor({
                                value: draft,
                                onChange: setDraft,
                                onCommit: (next?: any) => commit(item, col.key, next),
                                item,
                              })
                            ) : (
                              defaultEditor(
                                draft,
                                setDraft,
                                (next?: any) => commit(item, col.key, next),
                                true,
                                col.editorType
                              )
                            )}
                          </div>
                        ) : col.render ? (
                          col.render(item)
                        ) : col.key === "notes" && value ? (
                          <div>
                            <span>{value}</span>
                            {((item as any).notes_author || (item as any).notes_date) && (
                              <div className="text-xs text-neutral-400 mt-0.5">
                                {[
                                  (item as any).notes_author,
                                  (item as any).notes_date
                                    ? formatNoteDate((item as any).notes_date)
                                    : null,
                                ]
                                  .filter(Boolean)
                                  .join(" • ")}
                              </div>
                            )}
                          </div>
                        ) : shouldFormatCell(col, value) ? (
                          formatDisplayNumber(value, { locale: "en-US" })
                        ) : (
                          (value ?? "-") as React.ReactNode
                        )}

                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
};

export default Table;
