import React, { useState, useCallback, useMemo } from "react";
import { NumericInput } from "@/components/common/NumericInput";
import ActivityDataService, { type ActivityDataOut } from "@/services/ActivityData.service";
import { fetchAllActiveMrFactors } from "../refurbishmentTableConfig";
import {
    type UploadKey,
} from "../stageConstants";
import { buildExtraFields } from "../rowTransforms";
import {
    getYearFromValue,
    getElectricityYearWindow as resolveElectricityYearWindow,
    validateElectricityYear as validateElectricityYearValue,
    validateComponentReplLife as validateComponentReplLifeValue,
} from "../rowOperationValidation";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { MeProfile } from "@/context/UserContext";
import type {
    DataEntryRow,
    FugitiveOption,
    StageInstance,
    TableRowMap,
} from "../dataEntryTypes";
import type { CalcConfig } from "../useEmissionsCalc";
import { useDataEntryRowMutations } from "./useDataEntryRowMutations";
import { createRowUploadOperations } from "./rowUploadOperations";
import { createNewRowSaveHandler } from "./newRowSaveHandler";

type EditorProps = {
    value: unknown;
    onChange: (value: unknown) => void;
    onCommit: (value?: unknown) => void;
};

type EditorColumn = {
    editorType?: string;
    key?: string;
    renderEditor?: (props: EditorProps) => React.ReactNode;
};

interface UseRowOperationsParams {
    activeStageInstance: StageInstance | null;
    projectId: string;
    activeOptionId: string | null;
    activePeriod: ConstructionPeriod | null;
    constructionStartDate: string | null;
    constructionEndDate: string | null;
    opsStartYear: number | null;
    operationalLifeYears: number | null;
    user: MeProfile | null;
    fugitiveList: FugitiveOption[];
    tableRows: TableRowMap;
    getRows: (key: UploadKey) => DataEntryRow[];
    updateRows: (key: UploadKey, updater: DataEntryRow[] | ((prev: DataEntryRow[]) => DataEntryRow[])) => void;
    setErrorForKey: (key: UploadKey, error: string | null) => void;
    resolveMetricId: (row: DataEntryRow, tableKey: UploadKey) => Promise<string | null>;
    apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
    computeEmissionsForRow: (tableKey: UploadKey, row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
    getCalcConfig: (tableKey: UploadKey) => CalcConfig | null;
    refreshOptionTotals: () => Promise<void>;
    recalcElectricitySiblings: (
        tableKey: UploadKey,
        excludeId: string | null,
        rows: DataEntryRow[],
        setRows: React.Dispatch<React.SetStateAction<DataEntryRow[]>>,
    ) => Promise<void>;
}

export function useRowOperations({
    activeStageInstance,
    projectId,
    activeOptionId,
    activePeriod,
    constructionStartDate,
    constructionEndDate,
    opsStartYear,
    operationalLifeYears,
    user,
    fugitiveList,
    tableRows,
    getRows,
    updateRows,
    setErrorForKey,
    resolveMetricId,
    apiRowToUiRow,
    computeEmissionsForRow,
    getCalcConfig,
    refreshOptionTotals,
    recalcElectricitySiblings,
}: UseRowOperationsParams) {
    const [deleteTarget, setDeleteTarget] = useState<{ id: string; tableKey: UploadKey } | null>(null);
    const [uploadTarget, setUploadTarget] = useState<UploadKey | null>(null);

    const getElectricityYearWindow = useCallback(
        (tableKey: UploadKey) => resolveElectricityYearWindow(tableKey, {
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
            operationalLifeYears,
        }),
        [constructionStartDate, constructionEndDate, opsStartYear, operationalLifeYears]
    );

    const validateElectricityYear = useCallback(
        (tableKey: UploadKey, row: DataEntryRow) => validateElectricityYearValue(tableKey, row, {
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
            operationalLifeYears,
        }),
        [constructionStartDate, constructionEndDate, opsStartYear, operationalLifeYears]
    );

    const validateComponentReplLife = useCallback(
        (tableKey: UploadKey, row: DataEntryRow) => validateComponentReplLifeValue(tableKey, row, operationalLifeYears),
        [operationalLifeYears]
    );

    const renderEditor = (col: EditorColumn, props: EditorProps) => {
        const value = typeof props.value === "string" || typeof props.value === "number"
            ? props.value
            : null;
        if (col.editorType === "year") {
            return (
                <input
                    type="number"
                    className="h-10 w-full bg-white border border-border-input rounded px-2 py-1 text-sm"
                    value={value ?? ""}
                    onChange={(e) => props.onChange(e.target.value)}
                    onBlur={() => props.onCommit(value)}
                    autoFocus
                    onKeyDown={(e) => {
                        if (e.key === "." || e.key === ",") e.preventDefault();
                    }}
                />
            );
        }
        if (col.editorType === "number") {
            return (
                <NumericInput
                    value={value ?? ""}
                    onChange={props.onChange}
                    onCommit={props.onCommit}
                    allowDecimal
                    autoFocus
                    uncontrolled
                />
            );
        }
        if (col.key === "notes") {
            return (
                <input
                    className="h-10 w-full bg-white border border-border-input rounded px-2 py-1 text-sm"
                    value={typeof props.value === "string" ? props.value : ""}
                    onChange={(e) => props.onChange(e.target.value)}
                    onBlur={() => props.onCommit(value)}
                    autoFocus
                />
            );
        }
        return col.renderEditor?.(props);
    };

    const handleSaveBoundaryRow = useCallback(
        async (
            rowId: string,
            tableKey: UploadKey,
            finalRow: DataEntryRow,
            setRows: React.Dispatch<React.SetStateAction<DataEntryRow[]>>
        ) => {
            if (!activeStageInstance || !projectId) return;
            const boundaryId = rowId.replace(/^__BOUNDARY_/, "").replace(/__$/, "");
            try {
                let metricId: string | null = null;
                let unit_id: string | null = finalRow.unit_id ?? null;
                const quantity = finalRow.quantity;

                if (tableKey === "refurbishment") {
                    unit_id = null;
                    await fetchAllActiveMrFactors();
                }

                try { metricId = await resolveMetricId(finalRow, tableKey); } catch { metricId = null; }

                let computedPatch: Partial<DataEntryRow> | null = null;
                try { computedPatch = await computeEmissionsForRow(tableKey, finalRow); } catch (e) { console.warn('[useRowOperations] computeEmissionsForRow failed, saving without computed values:', e); }

                const rowToSave = computedPatch ? { ...finalRow, ...computedPatch } : finalRow;
                const rawEmissions = rowToSave.total_emissions_tco2e ?? rowToSave.emissions_tco2e;
                const finalEmissionsNum =
                    rawEmissions == null || rawEmissions === "-" || Number.isNaN(Number(rawEmissions))
                        ? null
                        : Number(rawEmissions);

                const extra_fields: Record<string, unknown> = {
                    ...rowToSave,
                    reporting_boundary_id: boundaryId,
                    fromBoundary: true,
                    emissions_tco2e: finalEmissionsNum,
                    total_emissions_tco2e: finalEmissionsNum,
                };
                delete extra_fields._fromBoundary;
                delete extra_fields.id;

                const saved = await ActivityDataService.createRow({
                    project_id: projectId,
                    project_stage_instance_id: activeStageInstance.id,
                    project_option_id: activeOptionId ?? null,
                    metric_id: metricId ?? null,
                    quantity: quantity != null ? Number(quantity) : 0,
                    unit_id,
                    emissions_tco2e: finalEmissionsNum,
                    ui_table_key: tableKey,
                    extra_fields,
                    ...(["constructionG2", "constructionG3", "recurringG3"].includes(tableKey) && activePeriod
                        ? { submission_period_id: activePeriod.id }
                        : {}),
                });

                const savedUiRow = apiRowToUiRow(saved);
                setRows((prev) => prev.map((r) => (r.id === rowId ? savedUiRow : r)));

                if (tableKey === "component") {
                    try {
                        const replExtraFields: Record<string, unknown> = {
                            emissions_category: finalRow.emissions_category,
                            emissions_category_id: finalRow.emissions_category_id,
                            emissions_subcategory: finalRow.emissions_subcategory,
                            emissions_subcategory_id: finalRow.emissions_subcategory_id,
                            source: finalRow.source,
                            emissions_source: finalRow.emissions_source,
                            emissions_source_name: finalRow.emissions_source_name,
                            _syncedSourceId: saved.id,
                            _syncedFromConstruction: true,
                            reporting_boundary_id: boundaryId,
                            fromBoundary: true,
                            quantity: quantity != null ? Number(quantity) : null,
                        };
                        const replDraft = { ...replExtraFields, quantity: quantity ?? 0, unit_id, life: finalRow.life ?? null };
                        let replPatch: Partial<DataEntryRow> | null = null;
                        try { replPatch = await computeEmissionsForRow("componentRepl", replDraft); } catch (e) { console.warn('[useRowOperations] replacement emissions computation failed:', e); }
                        const replRaw = replPatch?.total_emissions_tco2e ?? replPatch?.emissions_tco2e;
                        const replEmissionsNum =
                            replRaw === "-" || replRaw === "" || replRaw == null || Number.isNaN(Number(replRaw))
                                ? null
                                : Number(replRaw);
                        const finalReplExtraFields: Record<string, unknown> = {
                            ...replExtraFields,
                            ...(replPatch || {}),
                            emissions_tco2e: replEmissionsNum,
                            total_emissions_tco2e: replEmissionsNum,
                        };
                        const replSaved = await ActivityDataService.createRow({
                            project_id: projectId,
                            project_stage_instance_id: activeStageInstance.id,
                            project_option_id: activeOptionId ?? null,
                            metric_id: metricId ?? null,
                            quantity: quantity != null ? Number(quantity) : 0,
                            unit_id,
                            emissions_tco2e: replEmissionsNum,
                            ui_table_key: "componentRepl",
                            extra_fields: finalReplExtraFields,
                        });
                        updateRows("componentRepl", (rows) => [apiRowToUiRow(replSaved), ...rows]);
                    } catch (e) {
                        console.warn("Failed to auto-create componentRepl for boundary component row:", e);
                    }
                }
            } catch (e) {
                console.warn("Failed to save boundary row:", tableKey, e);
            }
        },
        [activeStageInstance, projectId, activeOptionId, activePeriod, resolveMetricId, computeEmissionsForRow, apiRowToUiRow, updateRows]
    );

    const syncComponentQtyToReplacement = useCallback(
        async (sourceComponentRowId: string, newQty: DataEntryRow["quantity"]) => {
            const replRow = getRows("componentRepl").find((row) => row._syncedSourceId === sourceComponentRowId);
            if (!replRow?._fromApi) return;

            const draft = { ...replRow, quantity: newQty };
            const patch = await computeEmissionsForRow("componentRepl", draft);
            const final = patch ? { ...draft, ...patch } : draft;

            updateRows("componentRepl", (prev) => prev.map((row) => (row.id === replRow.id ? final : row)));

            const raw = final.total_emissions_tco2e ?? final.emissions_tco2e;
            const emissionsNum =
                raw === "-" || raw === "" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);

            if (replRow.id == null) return;
            await ActivityDataService.updateRow(String(replRow.id), {
                quantity: Number(newQty),
                emissions_tco2e: emissionsNum,
                extra_fields: buildExtraFields(final, { keepEmissions: true, tableKey: "componentRepl" }),
            });
            await refreshOptionTotals();
        },
        [tableRows, computeEmissionsForRow, getRows, updateRows, refreshOptionTotals]
    );

    const { onCellChange, onRowPatch, doDeleteRow } = useDataEntryRowMutations({
        user,
        fugitiveList,
        getRows,
        updateRows,
        setErrorForKey,
        getCalcConfig,
        computeEmissionsForRow,
        refreshOptionTotals,
        recalcElectricitySiblings,
        validateElectricityYear,
        validateComponentReplLife,
        handleSaveBoundaryRow,
        syncComponentQtyToReplacement,
        deleteTarget,
        setDeleteTarget,
    });
    const { parseFile, validateUpload, onUploadSuccess, syncComponentUploadToReplacement } = createRowUploadOperations({
        activeStageInstance,
        projectId,
        activeOptionId,
        activePeriod,
        getRows,
        updateRows,
        setErrorForKey,
        resolveMetricId,
        apiRowToUiRow,
        computeEmissionsForRow,
        refreshOptionTotals,
        validateComponentReplLife,
    });
    const handleSaveNewRow = useMemo(
        () => createNewRowSaveHandler({
            activeStageInstance,
            projectId,
            activeOptionId,
            activePeriod,
            user,
            getRows,
            updateRows,
            setErrorForKey,
            resolveMetricId,
            apiRowToUiRow,
            computeEmissionsForRow,
            refreshOptionTotals,
            validateComponentReplLife,
            validateElectricityYear,
            recalcElectricitySiblings,
        }),
        [activeStageInstance, projectId, activeOptionId, activePeriod, user, getRows, updateRows, setErrorForKey, resolveMetricId, apiRowToUiRow, computeEmissionsForRow, refreshOptionTotals, validateComponentReplLife, validateElectricityYear, recalcElectricitySiblings],
    );

    return {
        deleteTarget,
        setDeleteTarget,
        uploadTarget,
        setUploadTarget,
        getYearFromValue,
        getElectricityYearWindow,
        validateElectricityYear,
        validateComponentReplLife,
        handleSaveBoundaryRow,
        syncComponentQtyToReplacement,
        onCellChange,
        onRowPatch,
        doDeleteRow,
        renderEditor,
        handleSaveNewRow,
        parseFile,
        validateUpload,
        onUploadSuccess,
        syncComponentUploadToReplacement,
    };
}
