import type { ComponentProps, SetStateAction } from "react";
import TableWrapper from "@/components/common/TableWrapper";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { DataEntryRow } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";
import { PeriodEmissionSummary } from "./PeriodEmissionSummary";

type TableProps = ComponentProps<typeof TableWrapper>;

interface Props extends Pick<TableProps,
    "renderEditor" | "accordionState" | "setAccordionState" | "error" | "onCancel" |
    "readOnly" | "onDeleteRow" | "onCellChange" | "onRowPatch"
> {
    period: ConstructionPeriod;
    activities: string[];
    rowsByActivity: Record<string, DataEntryRow[]>;
    electricityRowsByActivity: Record<string, DataEntryRow[]>;
    columnsForActivity: (activity: string) => TableProps["columns"];
    electricityColumns: TableProps["columns"];
    electricityError?: string | null;
    onActivityRowsChange: (activity: string, updater: SetStateAction<DataEntryRow[]>) => void;
    onElectricityRowsChange: (activity: string, updater: SetStateAction<DataEntryRow[]>) => void;
    onRequestUpload: (key: UploadKey, activity: string) => void;
    onDeleteElectricityRow?: (id: string | number) => void;
    onElectricityCellChange?: (activity: string) => TableProps["onCellChange"];
    onElectricityRowPatch?: (activity: string) => TableProps["onRowPatch"];
    onElectricityCancel?: TableProps["onCancel"];
    saveNewRow: (draft: DataEntryRow, tableKey: UploadKey, activity: string) => Promise<boolean>;
}

export function RecurringStageContent({
    period,
    activities,
    rowsByActivity,
    electricityRowsByActivity,
    columnsForActivity,
    electricityColumns,
    electricityError,
    onActivityRowsChange,
    onElectricityRowsChange,
    onRequestUpload,
    onDeleteElectricityRow,
    onElectricityCellChange,
    onElectricityRowPatch,
    onElectricityCancel,
    saveNewRow,
    renderEditor,
    accordionState,
    setAccordionState,
    error,
    onCancel,
    readOnly,
    onDeleteRow,
    onCellChange,
    onRowPatch,
}: Props) {
    return (
        <>
            <PeriodEmissionSummary period={period} />
            {activities.length === 0 ? (
                <div className="rounded-[var(--radius-3)] border border-border-input bg-white p-5 text-sm text-text-dark">
                    <p className="font-medium">No recurring emissions tables are configured for this project.</p>
                    <p className="mt-1 text-text-faint">
                        Recurring tables are created from the project’s reporting boundaries. Add at least one
                        recurring emissions source in project setup, then return here.
                    </p>
                </div>
            ) : null}
            {activities.map((activity) => {
                const activityRows = rowsByActivity[activity] ?? [];
                const electricityRows = electricityRowsByActivity[activity] ?? [];
                return (
                    <TableWrapper
                        key={activity}
                        title={activity}
                        rows={activityRows}
                        setRows={(updater: SetStateAction<DataEntryRow[]>) => onActivityRowsChange(activity, updater)}
                        columns={columnsForActivity(activity)}
                        exportFileName={`Recurring_${activity}.csv`}
                        uploadKey="recurringG3"
                        renderEditor={renderEditor}
                        onRequestUpload={() => onRequestUpload("recurringG3", activity)}
                        onNewRowSave={(draft, key) => saveNewRow(draft, key, activity)}
                        accordionKey={activity}
                        accordionState={accordionState}
                        setAccordionState={setAccordionState}
                        error={error}
                        onCancel={onCancel}
                        readOnly={readOnly}
                        onDeleteRow={onDeleteRow}
                        onCellChange={onCellChange}
                        onRowPatch={onRowPatch}
                    >
                        <TableWrapper
                            title="Electricity"
                            rows={electricityRows}
                            setRows={(updater: SetStateAction<DataEntryRow[]>) => onElectricityRowsChange(activity, updater)}
                            columns={electricityColumns}
                            exportFileName={`Recurring_${activity}_Electricity.csv`}
                            uploadKey="electricity"
                            renderEditor={renderEditor}
                            onRequestUpload={() => onRequestUpload("electricity", activity)}
                            onNewRowSave={(draft, key) => saveNewRow(draft, key, activity)}
                            accordionKey={`${activity}-electricity`}
                            accordionState={accordionState}
                            setAccordionState={setAccordionState}
                            collapsible={false}
                            error={electricityError ?? error}
                            onCancel={onElectricityCancel ?? onCancel}
                            readOnly={readOnly}
                            onDeleteRow={onDeleteElectricityRow}
                            onCellChange={onElectricityCellChange?.(activity) ?? onCellChange}
                            onRowPatch={onElectricityRowPatch?.(activity) ?? onRowPatch}
                        />
                        <h3 className="mb-3 text-lg font-medium text-text-dark">All other sources</h3>
                    </TableWrapper>
                );
            })}
        </>
    );
}
