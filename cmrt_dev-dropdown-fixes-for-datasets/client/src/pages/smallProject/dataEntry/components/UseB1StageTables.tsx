import type { ComponentProps } from "react";
import TableWrapper from "@/components/common/TableWrapper";
import type { DataEntryRow } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";

type TableProps = ComponentProps<typeof TableWrapper>;
type RowsUpdater = DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[]);

interface Props extends Pick<TableProps,
  "renderEditor" | "onRequestUpload" | "onNewRowSave" | "accordionState" |
  "setAccordionState" | "readOnly"
> {
  rowsFor: (key: UploadKey) => DataEntryRow[];
  updateRows: (key: UploadKey, updater: RowsUpdater) => void;
  errors: Partial<Record<UploadKey, string | null>>;
  columns: Record<"useB1G2" | "useB1G3", TableProps["columns"]>;
  onCellChange: (key: UploadKey) => NonNullable<TableProps["onCellChange"]>;
  onRowPatch: (key: UploadKey) => NonNullable<TableProps["onRowPatch"]>;
  onCancel: (key: UploadKey) => () => void;
  onDelete: (key: UploadKey) => TableProps["onDeleteRow"];
  isConstructionStage: boolean;
}

const TABLES = [
  { key: "useB1G2", title: "Component Level (Grade 2)", exportFileName: "UseB1_ComponentLevel.csv" },
  { key: "useB1G3", title: "Detailed Level (Grade 3)", exportFileName: "UseB1_DetailedLevel.csv" },
] as const;

/** Shared Business Case, Design and Construction rendering for the Use B1 tables. */
export function UseB1StageTables({
  rowsFor,
  updateRows,
  errors,
  columns,
  onCellChange,
  onRowPatch,
  onCancel,
  onDelete,
  isConstructionStage,
  ...sharedProps
}: Props) {
  return <>
    {TABLES.map(({ key, title, exportFileName }) => (
      <TableWrapper
        key={key}
        title={title}
        rows={rowsFor(key)}
        setRows={(updater) => updateRows(key, updater as RowsUpdater)}
        columns={columns[key]}
        exportFileName={exportFileName}
        uploadKey={key}
        accordionKey={key}
        error={errors[key]}
        onCellChange={onCellChange(key)}
        onRowPatch={onRowPatch(key)}
        onCancel={onCancel(key)}
        onDeleteRow={onDelete(key)}
        isConstructionStage={isConstructionStage}
        {...sharedProps}
      />
    ))}
  </>;
}
