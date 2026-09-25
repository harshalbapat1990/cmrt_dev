import React from "react";
import Table from "@/components/common/Table";
import InfoTooltip from "@/components/common/InfoTooltip";

type UploadKey = "asset" | "component" | "componentRepl" | "refurbishment" | "replDetailed" | "opEnergy" | "opEnergyDetailed" | "opEnergyElectricity" | "users" | "constructionG2" | "constructionG3" | "bcDetailedLevel" | "electricity" | "useB1G2" | "useB1G3" | "concreteRegSimplified" | "concreteRegDetailed" | "recurringG3";

type TableWrapperProps = {
  title: string;
  tooltip?: string;
  rows: any[];
  setRows: React.Dispatch<React.SetStateAction<any[]>>;
  columns: any[];
  exportFileName: string;
  uploadKey: UploadKey;
  renderEditor?: (col: any, props: any) => React.ReactNode;
  onRequestUpload: (key: UploadKey) => void;
  onNewRowSave: (draft: any, key: UploadKey) => Promise<boolean>;
  accordionKey: UploadKey;
  accordionState: Record<string, boolean>;
  setAccordionState: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  error?: string | null;
  onCellChange?: (args: { id: any; key: any; value: any; item: any }) => void;
  onRowPatch?: (args: { id: any; patch: any; item: any }) => void;
  readOnly?: boolean;
  onCancel?: () => void;
  onDeleteRow?: (id: string | number) => void;
  onEditRow?: (item: any) => void;
  onActionSelect?: (value: string) => void;
  onCellDoubleClick?: (key: string, row: any) => void;
  isConstructionStage?: boolean;
};

const TableWrapper: React.FC<TableWrapperProps> = ({
  title,
  tooltip,
  rows,
  setRows,
  columns,
  exportFileName,
  uploadKey,
  renderEditor,
  onRequestUpload,
  onNewRowSave,
  accordionKey,
  accordionState,
  setAccordionState,
  error,
  onCellChange,
  onRowPatch,
  readOnly = false,
  onCancel,
  onDeleteRow,
  onEditRow,
  onActionSelect,
  onCellDoubleClick,
  isConstructionStage = false,
}) => {

  const hideToolbarActions = isConstructionStage || uploadKey === "componentRepl" || uploadKey === "electricity" || uploadKey === "opEnergyElectricity";
  const hideAddRow = isConstructionStage || uploadKey === "componentRepl";
  const actionsBtn = uploadKey === "concreteRegDetailed";

  return (
    <div className="space-y-8 mx-12 mb-12 bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)]">
      <div className="flex items-center justify-between mb-4">
        <div className="text-2xl font-light text-text-dark">
          <span className="mr-1.5">{title}</span>
          {tooltip ? <InfoTooltip text={tooltip} iconSize={20} /> : null}
        </div>
        <button
          type="button"
          onClick={() =>
            setAccordionState((prev) => ({ ...prev, [accordionKey]: !prev[accordionKey] }))
          }
          className="w-5 h-5 inline-flex items-center cursor-pointer justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded"
        >
          <span className="material-symbols-rounded">
            {accordionState[accordionKey] ? "keyboard_arrow_up" : "keyboard_arrow_down"}
          </span>
        </button>
      </div>

      {accordionState[accordionKey] && (
        <>
          {error && (
            <div className="text-danger text-sm font-medium mb-2 px-1 flex items-center gap-1">
              <span className="material-symbols-rounded text-[18px]">error</span>
              {error}
            </div>
          )}

          <Table
            data={rows}
            columns={columns.map((col: any) => ({
              ...col,
              ...(renderEditor ? { renderEditor: (props: any) => renderEditor(col, props) } : {}),
            }))}
            exportFileName={exportFileName}
            enableInlineNewRow
            // Bind the upload key for this block
            onRequestUpload={() => onRequestUpload(uploadKey)}
            // Inline edits
            onCellChange={onCellChange ?? (({ id, key, value }: any) => {
              if (typeof id === "string" || typeof id === "number") {
                setRows((prev) => prev.map((r: any) => (r.id === id ? { ...r, [key]: value } : r)));
              }
            })}
            onRowPatch={onRowPatch ?? (({ id, patch }: any) =>
              setRows((prev) => prev.map((r: any) => (r.id === id ? { ...r, ...patch } : r))))
            }
            // Bind the save handler to this block’s key
            onNewRowSave={(draft: any) => onNewRowSave(draft, uploadKey)}
            readOnly={readOnly}
            onNewRowCancel={onCancel}
            hideToolbarActions={hideToolbarActions}
            hideAddRow={hideAddRow}
            onDeleteRow={onDeleteRow}
            onEditRow={onEditRow}
            actionsBtn={actionsBtn}
            onActionSelect={onActionSelect}
            onCellDoubleClick={onCellDoubleClick}
          />
        </>
      )}
    </div>
  );
};

export default TableWrapper;