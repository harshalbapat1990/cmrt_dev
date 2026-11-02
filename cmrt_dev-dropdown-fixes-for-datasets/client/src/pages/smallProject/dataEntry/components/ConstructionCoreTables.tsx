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
  columns: Record<"constructionG2" | "constructionG3" | "electricity", TableProps["columns"]>;
  onCellChange: (key: UploadKey) => NonNullable<TableProps["onCellChange"]>;
  onRowPatch: (key: UploadKey) => NonNullable<TableProps["onRowPatch"]>;
  onDelete: (key: UploadKey) => TableProps["onDeleteRow"];
}

const TABLES = [
  { key: "constructionG2", title: "Component level", exportFileName: "ConstructionG2Data.csv" },
  { key: "constructionG3", title: "Detailed level - construction stage", exportFileName: "ConstructionG3Data.csv" },
  { key: "electricity", title: "Electricity", exportFileName: "Electricity.csv" },
] as const;

/** Construction-stage tables whose edits are locked to the active construction period. */
export function ConstructionCoreTables({
  rowsFor,
  updateRows,
  errors,
  columns,
  onCellChange,
  onRowPatch,
  onDelete,
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
        onDeleteRow={onDelete(key)}
        isConstructionStage
        {...sharedProps}
      />
    ))}
  </>;
}
