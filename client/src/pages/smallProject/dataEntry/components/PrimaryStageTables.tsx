import type { ComponentProps } from "react";
import TableWrapper from "@/components/common/TableWrapper";
import type { DataEntryRow } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";

type WrapperProps = ComponentProps<typeof TableWrapper>;
type PrimaryTableKey =
  | "asset" | "component" | "bcDetailedLevel" | "electricity"
  | "componentRepl" | "refurbishment" | "replDetailed"
  | "opEnergy" | "opEnergyDetailed" | "opEnergyElectricity";
type RowsUpdater = DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[]);

interface Props extends Pick<WrapperProps,
  "renderEditor" | "onRequestUpload" | "onNewRowSave" | "accordionState" |
  "setAccordionState" | "readOnly"
> {
  visible: Partial<Record<PrimaryTableKey, boolean>>;
  rowsFor: (key: UploadKey) => DataEntryRow[];
  updateRows: (key: UploadKey, updater: RowsUpdater) => void;
  errors: Partial<Record<UploadKey, string | null>>;
  columns: Record<PrimaryTableKey, WrapperProps["columns"]>;
  onCellChange: (key: UploadKey) => NonNullable<WrapperProps["onCellChange"]>;
  onRowPatch: (key: UploadKey) => NonNullable<WrapperProps["onRowPatch"]>;
  onCancel: (key: UploadKey) => () => void;
  onDelete: (key: UploadKey) => WrapperProps["onDeleteRow"];
}

const TABLES: readonly {
  key: PrimaryTableKey;
  title: string;
  exportFileName: string;
  tooltip?: string;
  stringifyDeleteId?: boolean;
}[] = [
  { key: "asset", title: "Asset level", tooltip: "Asset level data should only be used when Component level data is not available.", exportFileName: "AssetLevel.csv" },
  { key: "component", title: "Component level", exportFileName: "ComponentLevel.csv" },
  { key: "bcDetailedLevel", title: "Detailed level (Grade 3)", exportFileName: "DetailedLevel.csv" },
  { key: "electricity", title: "Electricity", exportFileName: "Electricity.csv" },
  { key: "componentRepl", title: "Component level replacement", tooltip: "Component level data will be visible when component level data under construction is available.", exportFileName: "ComponentLevel.csv" },
  { key: "refurbishment", title: "Other partial replacement or refurbishment activities", exportFileName: "Replacement and Refurbishment.csv" },
  { key: "replDetailed", title: "Detailed Level (Grade 3)", exportFileName: "DetailedLevel-replacement.csv", stringifyDeleteId: true },
  { key: "opEnergy", title: "Component level (grade 2)", exportFileName: "OperationalEnergy.csv" },
  { key: "opEnergyDetailed", title: "Detailed Level (Grade 3)", exportFileName: "OperationalEnergy_DetailedLevel.csv" },
  { key: "opEnergyElectricity", title: "Electricity", exportFileName: "OperationalEnergy_Electricity.csv" },
];

/** Business Case and Design tables for construction, replacement and operational energy. */
export function PrimaryStageTables({
  visible,
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
    {TABLES.filter(({ key }) => visible[key]).map(({ key, title, exportFileName, tooltip, stringifyDeleteId }) => {
      const baseDelete = onDelete(key);
      const onDeleteRow = baseDelete && stringifyDeleteId
        ? (id: string | number) => baseDelete(String(id))
        : baseDelete;

      return (
        <TableWrapper
          key={key}
          title={title}
          tooltip={tooltip}
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
          onDeleteRow={onDeleteRow}
          {...sharedProps}
        />
      );
    })}
  </>;
}
