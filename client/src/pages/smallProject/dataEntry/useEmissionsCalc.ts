import { useCallback, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { DataEntryRow } from "./dataEntryTypes";
import type { UploadKey } from "./stageConstants";
import { isElectricityTable } from "./stageConstants";
import { resolveTableConfig } from "./tableConfigRegistry";
import { hasAllRequired, isValidEmission, getApiErrorMessage } from "./dataEntryValidation";
import ActivityDataService from "@/services/ActivityData.service";
import http from "@/http";

export type CalcCtx = {
    jurisdiction: string;
    region?: string;
    reference_period?: number;
    project_id?: string;
    project_option_id: string | null,
    project_stage_instance_id: string | null,
    ops_start_year?: number;
    tableKey: string;
    construction_start_year: string;
    construction_end_year: string;
};

export type CalcConfig = {
    grade: 1 | 2 | 3;
    requiredKeys: string[];
    triggerKeys: string[];
    buildPayload: (row: DataEntryRow, ctx: CalcCtx) => Record<string, unknown> | null;
    calculate: (payload: Record<string, unknown>, ctx: CalcCtx, tableKey: UploadKey) => Promise<unknown>;
    mapResultToRow: (apiRes: unknown, row?: DataEntryRow) => Partial<DataEntryRow>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isCalcConfig(value: unknown): value is CalcConfig {
    if (!isRecord(value)) return false;
    const grade = value.grade;
    return (grade === 1 || grade === 2 || grade === 3)
        && Array.isArray(value.requiredKeys)
        && value.requiredKeys.every((key) => typeof key === "string")
        && Array.isArray(value.triggerKeys)
        && value.triggerKeys.every((key) => typeof key === "string")
        && typeof value.buildPayload === "function"
        && typeof value.calculate === "function"
        && typeof value.mapResultToRow === "function";
}

async function runWithConcurrency<T>(
    items: T[],
    limit: number,
    worker: (item: T) => Promise<void>
) {
    let idx = 0;
    const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
        while (idx < items.length) {
            const current = items[idx++];
            await worker(current);
        }
    });
    await Promise.all(runners);
}

interface EmissionsCalcParams {
    projectId: string;
    projectGridCtx: { jurisdiction: string; region: string } | null;
    operationalLifeYears: number | null;
    opsStartYear: number | null;
    constructionStartDate: string | null;
    constructionEndDate: string | null;
    refreshOptionTotals: () => Promise<void>;
    projectOptionId?: string | null;
    projectStageInstanceId?: string | null;
}

export function useEmissionsCalc({
    projectId,
    projectGridCtx,
    operationalLifeYears,
    opsStartYear,
    constructionStartDate,
    constructionEndDate,
    refreshOptionTotals,
    projectOptionId,
    projectStageInstanceId
}: EmissionsCalcParams) {
    const datasetRevisionRef = useRef<{ projectId: string | null; loaded: boolean; value: string | null }>({
        projectId: null,
        loaded: false,
        value: null,
    });

    const resolveDatasetRevisionId = useCallback(async (): Promise<string | null> => {
        if (!projectId) return null;
        if (datasetRevisionRef.current.projectId !== projectId) {
            datasetRevisionRef.current = { projectId, loaded: false, value: null };
        }
        if (datasetRevisionRef.current.loaded) {
            return datasetRevisionRef.current.value;
        }

        try {
            const response = await http.get(`/api/project-dataset-revisions/by-project/${projectId}`);
            const bindings = Array.isArray(response.data) ? response.data : [];
            const revisionId = bindings[0]?.dataset_revision_id ?? null;
            datasetRevisionRef.current = { projectId, loaded: true, value: revisionId };
            return revisionId;
        } catch {
            datasetRevisionRef.current = { projectId, loaded: true, value: null };
            return null;
        }
    }, [projectId]);

    const getCalcConfig = (tableKey: UploadKey): CalcConfig | null => {
        const cfg = resolveTableConfig(tableKey, projectId);
        return isCalcConfig(cfg?.calculation) ? cfg.calculation : null;
    };

    const computeEmissionsForRow = useCallback(
        async (tableKey: UploadKey, row: DataEntryRow): Promise<Partial<DataEntryRow> | null> => {
            if ((tableKey === "asset" || tableKey === "component") && !projectId) {
                return null;
            }
            if (isElectricityTable(tableKey) && !projectGridCtx?.jurisdiction) {
                return null;
            }
            const calcCfg = getCalcConfig(tableKey);
            if (!calcCfg) return null;

            const ctx: CalcCtx = {
                jurisdiction: projectGridCtx?.jurisdiction ?? "",
                region: projectGridCtx?.region,
                reference_period: operationalLifeYears ?? undefined,
                project_id: projectId,
                project_option_id: projectOptionId || null,
                project_stage_instance_id: projectStageInstanceId ?? null,
                ops_start_year: opsStartYear ?? undefined,
                tableKey,
                construction_start_year: constructionStartDate ?? "",
                construction_end_year: constructionEndDate ?? "",
            };

            if (!hasAllRequired(row, calcCfg.requiredKeys)) {
                return { total_emissions_tco2e: "-", emissions_tco2e: "-" };
            }

            if (tableKey === "componentRepl") {
                const rawLife = row?.life;
                if (rawLife !== undefined && rawLife !== null && rawLife !== "") {
                    const life = Number(rawLife);
                    const opLife = Number(operationalLifeYears);
                    if (!Number.isFinite(life) || life <= 0) {
                        return {
                            total_emissions_tco2e: "-",
                            emissions_tco2e: "-",
                            _calculation_error: "Life (years) must be a valid positive number.",
                        };
                    }
                    if (life >= opLife) {
                        return {
                            total_emissions_tco2e: "-",
                            emissions_tco2e: "-",
                            _calculation_error: `Life (years) must be less than or equal to the operational life of project (${opLife} years).`,
                        };
                    }
                }
            }

            const payload = calcCfg.buildPayload(row, ctx);
            if (!payload) {
                return { total_emissions_tco2e: "-", emissions_tco2e: "-" };
            }

            const resolvedDatasetRevisionId = await resolveDatasetRevisionId();
            const payloadWithDatasetRevision = {
                ...payload,
                dataset_revision_id: row?.dataset_revision_id ?? resolvedDatasetRevisionId ?? null,
            };

            try {
                const res = await calcCfg.calculate(payloadWithDatasetRevision, ctx, tableKey);
                const mappedRow = calcCfg.mapResultToRow(res, row) ?? {};
                const v =
                    mappedRow.total_emissions_tco2e ??
                    mappedRow.emissions_tco2e ??
                    mappedRow.location_based_tco2e ??
                    mappedRow.market_based_tco2e;

                return {
                    ...mappedRow,
                    total_emissions_tco2e: v,
                    emissions_tco2e: v,
                };
            } catch (e) {
                const message = getApiErrorMessage(e);
                console.warn("Emission calc failed:", tableKey, message, e);
                return {
                    total_emissions_tco2e: "-",
                    emissions_tco2e: "-",
                    _calculation_error: message,
                };
            }
        },
        [
            projectGridCtx,
            operationalLifeYears,
            projectId,
            opsStartYear,
            constructionStartDate,
            constructionEndDate,
            projectOptionId,
            projectStageInstanceId,
            resolveDatasetRevisionId,
        ]
    );

    const recalcAndPersistRows = useCallback(
        async (
            tableKey: UploadKey,
            rows: DataEntryRow[],
            setRows: Dispatch<SetStateAction<DataEntryRow[]>>
        ) => {
            const calcCfg = getCalcConfig(tableKey);
            if (!calcCfg) return;
            if (!rows?.length) return;

            const targets = rows.filter((r) => r?._fromApi && r.id != null);

            await runWithConcurrency(targets, 6, async (r) => {
                const patch = await computeEmissionsForRow(tableKey, r);
                if (!patch) return;

                const requiredPresent = calcCfg ? hasAllRequired(r, calcCfg.requiredKeys) : false;
                const nextVal = patch.total_emissions_tco2e ?? patch.emissions_tco2e;

                if (requiredPresent && !isValidEmission(nextVal)) {
                    return;
                }

                setRows((prev) => prev.map((x) => (x.id === r.id ? { ...x, ...patch } : x)));

                try {
                    const emissionsNum =
                        (patch.total_emissions_tco2e ?? patch.emissions_tco2e) === "-"
                            ? null
                            : Number(patch.total_emissions_tco2e ?? patch.emissions_tco2e);

                    if (isElectricityTable(tableKey)) {
                        const updatedRow = { ...r, ...patch };
                        const extraFields = {
                            ...updatedRow,
                            location_based_tco2e: patch.location_based_tco2e ?? null,
                            market_based_tco2e: patch.market_based_tco2e ?? null,
                        };
                        delete extraFields._fromApi;

                        await ActivityDataService.updateRow(String(r.id), {
                            quantity: Number(updatedRow.quantity_mwh ?? r.quantity ?? 0),
                            emissions_tco2e: emissionsNum,
                            extra_fields: extraFields,
                        });
                    } else {
                        await ActivityDataService.updateRow(String(r.id), {
                            emissions_tco2e: emissionsNum,
                        });
                    }
                    await refreshOptionTotals();
                } catch (e) {
                    console.warn("Failed to persist recalculated emissions:", tableKey, r.id, e);
                }
            });
        },
        [computeEmissionsForRow, refreshOptionTotals]
    );

    const recalcElectricitySiblings = useCallback(
        async (
            tableKey: UploadKey,
            excludeId: string | null,
            rows: DataEntryRow[],
            setRows: Dispatch<SetStateAction<DataEntryRow[]>>,
        ) => {
            const targets = rows.filter(
                (r) => r?._fromApi && r.id != null && (excludeId == null || r.id !== excludeId),
            );
            if (!targets.length) return;

            await runWithConcurrency(targets, 6, async (r) => {
                const patch = await computeEmissionsForRow(tableKey, r);
                if (!patch) return;

                setRows((prev) => prev.map((x) => (x.id === r.id ? { ...x, ...patch } : x)));

                try {
                    const raw = patch.total_emissions_tco2e ?? patch.emissions_tco2e;
                    const emissionsNum =
                        raw === "-" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);
                    const updatedRow = { ...r, ...patch };
                    const extraFields = {
                        ...updatedRow,
                        location_based_tco2e: patch.location_based_tco2e ?? null,
                        market_based_tco2e: patch.market_based_tco2e ?? null,
                    };
                    delete extraFields._fromApi;
                    await ActivityDataService.updateRow(String(r.id), {
                        quantity: Number(updatedRow.quantity_mwh ?? r.quantity ?? 0),
                        emissions_tco2e: emissionsNum,
                        extra_fields: extraFields,
                    });
                } catch (e) {
                    console.warn("recalcElectricitySiblings: failed to persist", tableKey, r.id, e);
                }
            });

            try {
                await refreshOptionTotals();
            } catch (e) {
                console.warn("recalcElectricitySiblings: refreshOptionTotals failed", e);
            }
        },
        [computeEmissionsForRow, refreshOptionTotals],
    );

    return {
        getCalcConfig,
        computeEmissionsForRow,
        recalcAndPersistRows,
        recalcElectricitySiblings,
    };
}
