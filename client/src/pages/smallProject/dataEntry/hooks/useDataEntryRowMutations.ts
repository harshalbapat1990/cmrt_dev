import React, { useCallback } from "react";
import ActivityDataService from "@/services/ActivityData.service";
import { fetchAllActiveMrFactors } from "../refurbishmentTableConfig";
import { buildExtraFields } from "../rowTransforms";
import { hasAllRequired, isValidEmission } from "../dataEntryValidation";
import { isElectricityTable, type UploadKey } from "../stageConstants";
import type { MeProfile } from "@/context/UserContext";
import type { DataEntryCellChange, DataEntryRow, DataEntryRowPatch, FugitiveOption } from "../dataEntryTypes";
import type { CalcConfig } from "../useEmissionsCalc";

interface UseDataEntryRowMutationsParams {
    projectId: string;
    user: MeProfile | null;
    fugitiveList: FugitiveOption[];
    getRows: (key: UploadKey) => DataEntryRow[];
    updateRows: (key: UploadKey, updater: DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[])) => void;
    setErrorForKey: (key: UploadKey, error: string | null) => void;
    getCalcConfig: (key: UploadKey) => CalcConfig | null;
    computeEmissionsForRow: (key: UploadKey, row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
    refreshOptionTotals: () => Promise<void>;
    recalcElectricitySiblings: (key: UploadKey, excludeId: string | null, rows: DataEntryRow[], setRows: React.Dispatch<React.SetStateAction<DataEntryRow[]>>) => Promise<void>;
    validateElectricityYear: (key: UploadKey, row: DataEntryRow) => string | null;
    validateComponentReplLife: (key: UploadKey, row: DataEntryRow) => string | null;
    handleSaveBoundaryRow: (id: string, key: UploadKey, row: DataEntryRow, setRows: React.Dispatch<React.SetStateAction<DataEntryRow[]>>) => Promise<void>;
    syncComponentQtyToReplacement: (
        sourceId: string,
        quantity: DataEntryRow["quantity"],
    ) => Promise<void>;
    deleteTarget: { id: string; tableKey: UploadKey } | null;
    setDeleteTarget: React.Dispatch<React.SetStateAction<{ id: string; tableKey: UploadKey } | null>>;
}

function readServerEmission(value: string | null | undefined): number | null {
    if (value == null || value === "" || value === "-") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

export function useDataEntryRowMutations({
    projectId,
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
}: UseDataEntryRowMutationsParams) {
    const onCellChange =
        (tableKey: UploadKey, setRows: React.Dispatch<React.SetStateAction<DataEntryRow[]>>) =>
        async ({ id, key, value, item }: DataEntryCellChange) => {
            let finalRow = { ...item, [key]: value };
            const cfg = getCalcConfig(tableKey);

            if (isElectricityTable(tableKey)) {
                const electricityTriggerKeys = new Set(["emission_source", "year", "quantity_mwh"]);
                if (electricityTriggerKeys.has(String(key))) {
                    const updatedRow = { ...item, [key]: value };
                    const yearError = validateElectricityYear(tableKey, updatedRow);
                    if (yearError) {
                        setErrorForKey(tableKey, yearError);
                        setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...updatedRow } : r)));
                        return;
                    }
                    setErrorForKey(tableKey, null);
                    if (updatedRow.emission_source && updatedRow.year && updatedRow.quantity_mwh) {
                        const calc = await computeEmissionsForRow(tableKey, updatedRow);
                        if (!calc) return;
                        const nextRow = {
                            ...updatedRow,
                            ...calc,
                            location_based_tco2e: calc.location_based_tco2e ?? null,
                            market_based_tco2e: calc.market_based_tco2e ?? null,
                            unit_display: String(updatedRow.unit_display ?? "MWh"),
                        };
                        setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...nextRow } : r)));
                        if (item?._fromApi) {
                            const raw = nextRow.total_emissions_tco2e ?? nextRow.emissions_tco2e;
                            const emissionsNum =
                                raw === "-" || raw === "" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);
                            const extra_fields = {
                                ...nextRow,
                                location_based_tco2e: nextRow.location_based_tco2e,
                                market_based_tco2e: nextRow.market_based_tco2e,
                                unit_display: String(updatedRow.unit_display ?? "MWh"),
                            };
                            delete extra_fields._fromApi;
                            await ActivityDataService.updateRow(String(id), {
                                quantity: Number(updatedRow["quantity_mwh"]),
                                emissions_tco2e: emissionsNum,
                                extra_fields,
                            });
                            void recalcElectricitySiblings(
                                tableKey,
                                String(id),
                                getRows(tableKey),
                                (updater) => updateRows(tableKey, updater),
                            );
                        }
                    }
                } else {
                    setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                    if (item?._fromApi) {
                        const extra_fields = { ...item, [key]: value };
                        delete extra_fields._fromApi;
                        await ActivityDataService.updateRow(String(id), { extra_fields });
                        await refreshOptionTotals();
                    }
                }
                return;
            }

            if (tableKey === "useB1G2" && String(key) === "application_type_id") {
                const eq = fugitiveList.find((e) => e.id === value);
                setRows((prev) =>
                    prev.map((row) =>
                        row.id === id
                            ? {
                                  ...row,
                                  application_type_id: value,
                                  application_type: eq?.equipment_type ?? "",
                                  annual_leakage_rate_percent: eq
                                      ? Number.parseFloat(String(eq.default_annual_leakage_rate))
                                      : null,
                              }
                            : row
                    )
                );
                if (item?._fromApi) {
                    const extra_fields = {
                        ...item,
                        application_type_id: value,
                        application_type: eq?.equipment_type ?? "",
                        annual_leakage_rate_percent: eq ? Number.parseFloat(String(eq.default_annual_leakage_rate)) : null,
                    };
                    delete extra_fields._fromApi;
                    await ActivityDataService.updateRow(String(id), { extra_fields });
                }
                return;
            }

            if (tableKey === "componentRepl") {
                const isComponentReplTrigger = cfg?.triggerKeys?.includes(String(key));
                if (isComponentReplTrigger) {
                    const lifeError = validateComponentReplLife(tableKey, finalRow);
                    if (lifeError) {
                        setErrorForKey("componentRepl", lifeError);
                        setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                        return;
                    }
                    setErrorForKey("componentRepl", null);
                }
            }

            const isTrigger = !!cfg && cfg.triggerKeys.includes(String(key));

            if (isTrigger) {
                if (tableKey === "refurbishment") await fetchAllActiveMrFactors(undefined, projectId);

                const calcPatch = await computeEmissionsForRow(tableKey, finalRow);

                if (calcPatch) {
                    const requiredPresent = cfg ? hasAllRequired(finalRow, cfg.requiredKeys) : false;
                    const nextVal = calcPatch.total_emissions_tco2e ?? calcPatch.emissions_tco2e;
                    const calcFailedButShouldHaveWorked = requiredPresent && !isValidEmission(nextVal);
                    if (!calcFailedButShouldHaveWorked) {
                        finalRow = { ...finalRow, ...calcPatch };
                    }
                }

                setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));

                if (item?._fromApi) {
                    const apiPatch: Record<string, unknown> = {
                        ...(finalRow.quantity != null ? { quantity: Number(finalRow.quantity) } : {}),
                        ...(finalRow.unit_id != null ? { unit_id: finalRow.unit_id } : {}),
                        extra_fields: buildExtraFields(finalRow, { keepEmissions: true, tableKey }),
                    };
                    const saved = await ActivityDataService.updateRow(String(id), apiPatch);
                    if (saved && Object.prototype.hasOwnProperty.call(saved, "emissions_tco2e")) {
                        const serverEmissions = readServerEmission(saved.emissions_tco2e);
                        setRows((prev) => prev.map((row) => row.id === id
                            ? { ...row, emissions_tco2e: serverEmissions, total_emissions_tco2e: serverEmissions }
                            : row));
                    }
                    await refreshOptionTotals();
                }

                if (tableKey === "component" && String(key) === "quantity" && item?._fromApi) {
                    if (typeof value === "string" || typeof value === "number" || value == null) {
                        await syncComponentQtyToReplacement(String(id), value);
                    }
                }

                if (item?._fromBoundary && String(id).startsWith("__BOUNDARY_") && finalRow.quantity != null) {
                    await handleSaveBoundaryRow(String(id), tableKey, finalRow, setRows);
                }

                return;
            }

            if (String(key) === "notes") {
                const authorName =
                    [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
                    user?.email ||
                    "";
                if (value) {
                    finalRow = { ...finalRow, notes_author: authorName, notes_date: new Date().toISOString() };
                } else {
                    finalRow = { ...finalRow, notes_author: null, notes_date: null };
                }
            }

            setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));

            if (item?._fromApi) {
                const topLevelKeys = new Set(["quantity", "unit_id", "metric_id"]);
                const shouldSave = topLevelKeys.has(String(key)) || key === "life" || key === "notes";
                if (shouldSave) {
                    const patch: Record<string, unknown> = {};
                    if (topLevelKeys.has(String(key))) {
                        patch[key] = value;
                    } else {
                        const extra_fields = { ...finalRow };
                        delete extra_fields._fromApi;
                        patch.extra_fields = extra_fields;
                    }
                    await ActivityDataService.updateRow(String(id), patch);
                }
            }
        };

    const onRowPatch =
        (_tableKey: UploadKey, setRows: React.Dispatch<React.SetStateAction<DataEntryRow[]>>) =>
        async ({ id, patch, item }: DataEntryRowPatch) => {
            if (_tableKey === "concreteRegSimplified" || _tableKey === "concreteRegDetailed") {
                let finalRow = { ...item, ...patch };
                try {
                    const calcPatch = await computeEmissionsForRow(_tableKey, finalRow);
                    if (calcPatch) finalRow = { ...finalRow, ...calcPatch };
                    setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                    const rawEmissions = finalRow.total_emissions_tco2e ?? finalRow.emissions_tco2e;
                    const emissionsNum =
                        rawEmissions === "-" || rawEmissions === "" || rawEmissions == null || Number.isNaN(Number(rawEmissions))
                            ? null
                            : Number(rawEmissions);
                    const extraFields = { ...finalRow };
                    delete extraFields._fromApi;
                    delete extraFields.id;
                    delete extraFields.metric_id;
                    delete extraFields.unit_id;
                    extraFields.emissions_tco2e = emissionsNum;
                    extraFields.total_emissions_tco2e = emissionsNum;
                    const quantity = _tableKey === "concreteRegSimplified"
                        ? (finalRow.volume != null ? Number(finalRow.volume) : 0)
                        : (finalRow.quantity != null ? Number(finalRow.quantity) : 0);
                    await ActivityDataService.updateRow(String(id), {
                        quantity,
                        emissions_tco2e: emissionsNum,
                        extra_fields: extraFields,
                    });
                    await refreshOptionTotals();
                } catch (e) {
                    console.error("Failed to patch concrete register row:", e);
                }
                return;
            }

            let finalRow = { ...item, ...patch };
            setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));

            if (isElectricityTable(_tableKey)) {
                const yearError = validateElectricityYear(_tableKey, finalRow);
                if (yearError) { setErrorForKey(_tableKey, yearError); return; }
                setErrorForKey(_tableKey, null);
            }

            const cfg = getCalcConfig(_tableKey);
            const touchedTrigger = cfg?.triggerKeys?.some((k: string) =>
                Object.prototype.hasOwnProperty.call(patch, k)
            );

            if (_tableKey === "componentRepl" && touchedTrigger) {
                const lifeError = validateComponentReplLife(_tableKey, finalRow);
                if (lifeError) { setErrorForKey("componentRepl", lifeError); return; }
                setErrorForKey("componentRepl", null);
            }

            let didUpdate = false;

            if (cfg && touchedTrigger) {
                const calcPatch = await computeEmissionsForRow(_tableKey, finalRow);

                if (calcPatch) {
                    finalRow = { ...finalRow, ...calcPatch };
                    setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));

                    if (isElectricityTable(_tableKey) && item?._fromApi && calcPatch) {
                        const raw = calcPatch.total_emissions_tco2e ?? calcPatch.emissions_tco2e;
                        const emissionsNum =
                            raw === "-" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);
                        const extraFields = {
                            ...(item.extra_fields ?? item),
                            ...finalRow,
                            ...calcPatch,
                            unit_display: finalRow.unit_display ?? "MWh",
                        };
                        delete extraFields._fromApi;
                        await ActivityDataService.updateRow(String(id), {
                            quantity: Number(finalRow.quantity_mwh),
                            emissions_tco2e: emissionsNum,
                            extra_fields: extraFields,
                        });
                        didUpdate = true;
                        void recalcElectricitySiblings(
                            _tableKey,
                            String(id),
                            getRows(_tableKey),
                            (updater) => updateRows(_tableKey, updater),
                        );
                    }
                }

                const topLevelKeys = new Set(["quantity", "unit_id"]);
                const hasSaveable = Object.keys(patch).some(
                    (k) => topLevelKeys.has(k) || k === "life" || k === "notes"
                );

                if (hasSaveable && item?._fromApi) {
                    try {
                        const apiPatch: Record<string, unknown> = {};
                        for (const [k, v] of Object.entries(patch)) {
                            if (topLevelKeys.has(k)) apiPatch[k] = v;
                        }
                        apiPatch.extra_fields = buildExtraFields(finalRow, { keepEmissions: true, tableKey: _tableKey });
                        const saved = await ActivityDataService.updateRow(String(id), apiPatch);
                        if (saved && Object.prototype.hasOwnProperty.call(saved, "emissions_tco2e")) {
                            const serverEmissions = readServerEmission(saved.emissions_tco2e);
                            setRows((prev) => prev.map((row) => row.id === id
                                ? { ...row, emissions_tco2e: serverEmissions, total_emissions_tco2e: serverEmissions }
                                : row));
                        }
                        didUpdate = true;
                    } catch (e) {
                        console.warn("Failed to patch row:", e);
                    }
                }

                if (!didUpdate && item?._fromApi) {
                    try {
                        const apiPatch: Record<string, unknown> = {
                            ...(finalRow.quantity != null ? { quantity: Number(finalRow.quantity) } : {}),
                            extra_fields: buildExtraFields(finalRow, { keepEmissions: true, tableKey: _tableKey }),
                        };
                        const saved = await ActivityDataService.updateRow(String(id), apiPatch);
                        if (saved && Object.prototype.hasOwnProperty.call(saved, "emissions_tco2e")) {
                            const serverEmissions = readServerEmission(saved.emissions_tco2e);
                            setRows((prev) => prev.map((row) => row.id === id
                                ? { ...row, emissions_tco2e: serverEmissions, total_emissions_tco2e: serverEmissions }
                                : row));
                        }
                        didUpdate = true;
                    } catch (e) {
                        console.warn("Failed to persist select-triggered emission update:", e);
                    }
                }

                if (didUpdate) await refreshOptionTotals();

                if (_tableKey === "component" && "quantity" in patch && item?._fromApi) {
                    const replRow = getRows("componentRepl").find((row) => row._syncedSourceId === id);
                    if (replRow?._fromApi) {
                        try {
                            const replDraft = { ...replRow, quantity: patch.quantity };
                            const replPatch = await computeEmissionsForRow("componentRepl", replDraft);
                            const finalReplRow = { ...replDraft, ...(replPatch || {}) };
                            const raw = finalReplRow.total_emissions_tco2e ?? finalReplRow.emissions_tco2e;
                            const replEmissionsNum =
                                raw === "-" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);
                            if (replRow.id == null) return;
                            await ActivityDataService.updateRow(String(replRow.id), {
                                quantity: Number(patch.quantity ?? 0),
                                emissions_tco2e: replEmissionsNum,
                                extra_fields: (() => {
                                    const ef = { ...finalReplRow };
                                    delete ef._fromApi;
                                    delete ef.id;
                                    delete ef.metric_id;
                                    delete ef.quantity;
                                    delete ef.unit_id;
                                    delete ef.emissions_tco2e;
                                    delete ef.total_emissions_tco2e;
                                    return ef;
                                })(),
                            });
                            updateRows("componentRepl", (prev) =>
                                prev.map((row) => (row.id === replRow.id ? finalReplRow : row))
                            );
                        } catch (e) {
                            console.warn("Failed to sync quantity to componentRepl:", e);
                        }
                    }
                }
            }
        };

    const doDeleteRow = useCallback(async () => {
        if (!deleteTarget) return;
        if (deleteTarget.tableKey === "concreteRegSimplified" || deleteTarget.tableKey === "concreteRegDetailed") {
            await ActivityDataService.deleteRow(deleteTarget.id);
            updateRows(deleteTarget.tableKey, (prev) => prev.filter((row) => row.id !== deleteTarget.id));
            setDeleteTarget(null);
            return;
        }
        if (deleteTarget.tableKey === "component") {
            const replRow = getRows("componentRepl").find((row) => row._syncedSourceId === deleteTarget.id);
            if (replRow?._fromApi) {
                if (replRow.id == null) throw new Error("The linked replacement row has no saved ID.");
                await ActivityDataService.deleteRow(String(replRow.id));
                updateRows("componentRepl", (prev) => prev.filter((row) => row.id !== replRow.id));
            }
        }
        const electricitySiblings = isElectricityTable(deleteTarget.tableKey)
            ? getRows(deleteTarget.tableKey).filter(
                  (row) => row.id !== deleteTarget.id && row._fromApi,
              )
            : [];
        await ActivityDataService.deleteRow(deleteTarget.id);
        updateRows(deleteTarget.tableKey, (prev) => prev.filter((row) => row.id !== deleteTarget.id));
        setDeleteTarget(null);
        try {
            await refreshOptionTotals();
        } catch (error) {
            console.warn("Failed to refresh totals after deleting a row:", error);
        }
        if (electricitySiblings.length > 0) {
            void recalcElectricitySiblings(
                deleteTarget.tableKey,
                null,
                electricitySiblings,
                (updater) => updateRows(deleteTarget.tableKey, updater),
            );
        }
    }, [deleteTarget, setDeleteTarget, updateRows, getRows, refreshOptionTotals, recalcElectricitySiblings]);


    return { onCellChange, onRowPatch, doDeleteRow };
}
