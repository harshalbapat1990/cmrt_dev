import type { Dispatch, SetStateAction } from "react";
import type { ComponentProps } from "react";
import TableWrapper from "@/components/common/TableWrapper";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { DataEntryRow } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";
import type { useRowOperations } from "./useRowOperations";

type TableInteractionCallback = NonNullable<ComponentProps<typeof TableWrapper>["onCellChange"]>;
type RowPatchCallback = NonNullable<ComponentProps<typeof TableWrapper>["onRowPatch"]>;
type DeleteCallback = NonNullable<ComponentProps<typeof TableWrapper>["onDeleteRow"]>;
type RowOperations = ReturnType<typeof useRowOperations>;

interface UseDataEntryTableHandlersParams {
    updateRows: (key: UploadKey, updater: DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[])) => void;
    setErrorForKey: (key: UploadKey, error: string | null) => void;
    onCellChange: RowOperations["onCellChange"];
    onRowPatch: RowOperations["onRowPatch"];
    setDeleteTarget: Dispatch<SetStateAction<{ id: string; tableKey: UploadKey } | null>>;
    isReadOnly: boolean;
    activePeriod: ConstructionPeriod | null;
}

/** Shared edit, validation, and deletion handlers used by all data-entry table groups. */
export function createDataEntryTableHandlers({
    updateRows,
    setErrorForKey,
    onCellChange,
    onRowPatch,
    setDeleteTarget,
    isReadOnly,
    activePeriod,
}: UseDataEntryTableHandlersParams) {
    const onCellChangeFor = (key: UploadKey): TableInteractionCallback =>
        onCellChange(key, (rows) => updateRows(key, rows));

    const onRowPatchFor = (key: UploadKey): RowPatchCallback =>
        onRowPatch(key, (rows) => updateRows(key, rows));

    const onCancelFor = (key: UploadKey) => () => setErrorForKey(key, null);

    const onDeleteForEditableTable = (key: UploadKey): DeleteCallback | undefined =>
        isReadOnly ? undefined : (id) => setDeleteTarget({ id: String(id), tableKey: key });

    const onDeleteForConstructionPeriod = (key: UploadKey): DeleteCallback | undefined =>
        activePeriod?.status === "in_progress"
            ? (id) => setDeleteTarget({ id: String(id), tableKey: key })
            : undefined;

    return {
        onCellChangeFor,
        onRowPatchFor,
        onCancelFor,
        onDeleteForEditableTable,
        onDeleteForConstructionPeriod,
    };
}
