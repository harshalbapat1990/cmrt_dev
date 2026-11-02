import type { ComponentProps } from "react";
import TableWrapper from "@/components/common/TableWrapper";
import ShortcutTools from "../ShortcutTools";
import type { DataEntryRow } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";

type WrapperProps = ComponentProps<typeof TableWrapper>;
type ConcreteKey = "concreteRegSimplified" | "concreteRegDetailed";
type RowsUpdater = DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[]);

interface Props extends Pick<WrapperProps,
  "renderEditor" | "onRequestUpload" | "onNewRowSave" | "accordionState" |
  "setAccordionState" | "readOnly"
> {
  rowsFor: (key: UploadKey) => DataEntryRow[];
  updateRows: (key: UploadKey, updater: RowsUpdater) => void;
  errors: Partial<Record<UploadKey, string | null>>;
  columns: Record<ConcreteKey, WrapperProps["columns"]>;
  onCellChange: (key: UploadKey) => NonNullable<WrapperProps["onCellChange"]>;
  onRowPatch: (key: UploadKey) => NonNullable<WrapperProps["onRowPatch"]>;
  onCancel: (key: UploadKey) => () => void;
  onDelete: (key: UploadKey) => WrapperProps["onDeleteRow"];
  onEditDetailedRow: (row: DataEntryRow) => void;
  onActionSelect: (action: string) => void;
  stageInstanceId: string;
  projectId: string;
  projectOptionId: string | null;
  onSaved: () => void;
}

const TABLES = [
  { key: "concreteRegSimplified", title: "Concrete register (grade 3) - simplified", exportFileName: "Concrete_Register_simplified.csv" },
  { key: "concreteRegDetailed", title: "Concrete register (grade 3) - detailed", exportFileName: "Concrete_Register_detailed.csv" },
] as const;

/** Concrete register tables and their related construction shortcut tools. */
export function ConcreteStageTables({
  rowsFor,
  updateRows,
  errors,
  columns,
  onCellChange,
  onRowPatch,
  onCancel,
  onDelete,
  onEditDetailedRow,
  onActionSelect,
  stageInstanceId,
  projectId,
  projectOptionId,
  onSaved,
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
        {...sharedProps}
        {...(key === "concreteRegDetailed" ? {
          onEditRow: !sharedProps.readOnly ? onEditDetailedRow : undefined,
          onActionSelect,
          onCellDoubleClick: (columnKey: string, row: DataEntryRow) => {
            if (!sharedProps.readOnly && columnKey === "mixId") onEditDetailedRow(row);
          },
        } : {})}
      />
    ))}
    <ShortcutTools
      stageInstanceId={stageInstanceId}
      projectId={projectId}
      projectOptionId={projectOptionId}
      readOnly={sharedProps.readOnly}
      onSaved={onSaved}
    />
  </>;
}
