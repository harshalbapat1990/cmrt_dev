import type { ComponentProps } from "react";
import TableWrapper from "@/components/common/TableWrapper";
import type { DataEntryRow } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";

type WrapperProps = ComponentProps<typeof TableWrapper>;
type TableKey = "componentRepl" | "refurbishment" | "replDetailed" | "opEnergy" | "opEnergyDetailed" | "opEnergyElectricity";
type RowsUpdater = DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[]);

interface Props extends Pick<WrapperProps,
  "renderEditor" | "onRequestUpload" | "onNewRowSave" | "accordionState" |
  "setAccordionState" | "readOnly"
> {
  section: "replacement" | "operationalEnergyWater";
  rowsFor: (key: UploadKey) => DataEntryRow[];
  updateRows: (key: UploadKey, updater: RowsUpdater) => void;
  errors: Partial<Record<UploadKey, string | null>>;
  columns: Record<TableKey, WrapperProps["columns"]>;
  onCellChange: (key: UploadKey) => NonNullable<WrapperProps["onCellChange"]>;
  onRowPatch: (key: UploadKey) => NonNullable<WrapperProps["onRowPatch"]>;
  onCancel: (key: UploadKey) => () => void;
  onDelete: (key: UploadKey) => WrapperProps["onDeleteRow"];
}

const TABLES_BY_SECTION: Record<Props["section"], readonly { key: TableKey; title: string; exportFileName: string }[]> = {
  replacement: [
    { key: "componentRepl", title: "Component level replacement", exportFileName: "ComponentLevel.csv" },
    { key: "refurbishment", title: "Other partial replacement or refurbishment activities", exportFileName: "Replacement and Refurbishment.csv" },
    { key: "replDetailed", title: "Detailed Level (Grade 3)", exportFileName: "DetailedLevel-replacement.csv" },
  ],
  operationalEnergyWater: [
    { key: "opEnergy", title: "Component Level (Grade 2)", exportFileName: "OperationalEnergy_ComponentLevel.csv" },
    { key: "opEnergyDetailed", title: "Detailed Level (Grade 3)", exportFileName: "OperationalEnergy_DetailedLevel.csv" },
    { key: "opEnergyElectricity", title: "Electricity", exportFileName: "OperationalEnergy_Electricity.csv" },
  ],
};

/** Tables used by the large-project Construction Replacement and Operational Energy sub-stages. */
export function ConstructionLargeProjectTables({
  section,
  rowsFor,
  updateRows,
  errors,
  columns,
  onCellChange,
  onRowPatch,
  onCancel,
  onDelete,
  ...sharedProps
}: Props) {
  return <>
    {TABLES_BY_SECTION[section].map(({ key, title, exportFileName }) => (
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
        isConstructionStage
        {...sharedProps}
      />
    ))}
  </>;
}
