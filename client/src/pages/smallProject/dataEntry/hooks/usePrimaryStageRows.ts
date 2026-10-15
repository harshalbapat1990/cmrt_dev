import { useEffect, type Dispatch, type SetStateAction } from "react";
import ActivityDataService, { type ActivityDataOut } from "@/services/ActivityData.service";
import type { DataEntryRow, ProjectClass, ReportingBoundary, StageInstance, StageLabel } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";
import { REPLACEMENT_LABEL, REPLACEMENT_LABEL_LARGE } from "../stageConstants";
import { fetchAllActiveMrFactors } from "../refurbishmentTableConfig";
import { keepTableRows } from "../useTableRows";

type BoundaryComponentIds = {
    emissions_category_id: string | null;
    emissions_subcategory_id: string | null;
    emissions_source: string | null;
};

const mapApiRows = (
    rows: ActivityDataOut[] | null | undefined,
    mapper: (row: ActivityDataOut) => DataEntryRow,
): DataEntryRow[] => (Array.isArray(rows) ? rows : []).map(mapper);

interface Params {
    enabled: boolean;
    activeStage: StageLabel;
    activeSubStage: string;
    activeStageInstance: StageInstance | null;
    activeOptionId: string | null;
    projectClass: ProjectClass | null;
    reportingBoundaries: ReportingBoundary[];
    updateRows: (key: UploadKey, rows: DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[])) => void;
    setTableRows: (updater: (previous: ReturnType<typeof keepTableRows>) => ReturnType<typeof keepTableRows>) => void;
    apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
    resolveBoundaryComponentIds: (boundary: ReportingBoundary) => Promise<BoundaryComponentIds>;
    recalcAndPersistRows: (
        key: UploadKey,
        rows: DataEntryRow[],
    setRows: Dispatch<SetStateAction<DataEntryRow[]>>,
    ) => Promise<void>;
}

/** Loads option scoped rows for the Business Case and Design stages. */
export function usePrimaryStageRows({
    enabled,
    activeStage,
    activeSubStage,
    activeStageInstance,
    activeOptionId,
    projectClass,
    reportingBoundaries,
    updateRows,
    setTableRows,
    apiRowToUiRow,
    resolveBoundaryComponentIds,
    recalcAndPersistRows,
}: Params): void {
    useEffect(() => {
        let cancelled = false;
        void (async () => {
            try {
                setTableRows((previous) => keepTableRows(previous, ["concreteRegSimplified", "concreteRegDetailed"]));
                if (!enabled) return;
                if (activeStage !== "Business case" && activeStage !== "Design") return;
                if (!activeStageInstance || activeOptionId === null) return;

                if (activeSubStage === "Construction") {
                    const requests: Promise<ActivityDataOut[]>[] = [
                        activeStage === "Business case"
                            ? ActivityDataService.fetchRows(activeStageInstance.id, "asset", activeOptionId)
                            : Promise.resolve([]),
                        ActivityDataService.fetchRows(activeStageInstance.id, "component", activeOptionId),
                    ];
                    if (projectClass === "LARGE") {
                        requests.push(
                            ActivityDataService.fetchRows(activeStageInstance.id, "bcDetailedLevel", activeOptionId ?? undefined),
                            ActivityDataService.fetchRows(activeStageInstance.id, "electricity", activeOptionId ?? undefined),
                        );
                    }
                    const results = await Promise.all(requests);
                    if (cancelled) return;
                    const assetRows = mapApiRows(results[0], apiRowToUiRow);
                    updateRows("asset", assetRows);
                    if (assetRows.some((row) => row.emissions_tco2e == null)) {
                        void recalcAndPersistRows("asset", assetRows, (rows) => updateRows("asset", rows));
                    }

                    const componentRows = mapApiRows(results[1], apiRowToUiRow);
                    const constructionBoundaries = reportingBoundaries.filter((boundary) => boundary.stage_or_activity === "Construction");
                    const missingComponentBoundaries = constructionBoundaries.filter((boundary) =>
                        !componentRows.some((row) => row.reporting_boundary_id === boundary.id || row.extra_fields?.reporting_boundary_id === boundary.id),
                    );
                    const placeholders = await Promise.all(missingComponentBoundaries.map(async (boundary): Promise<DataEntryRow> => {
                        const ids = await resolveBoundaryComponentIds(boundary);
                        return {
                            id: `__BOUNDARY_${boundary.id}__`, _fromBoundary: true,
                            emissions_category: boundary.category,
                            emissions_subcategory: boundary.sub_category,
                            emissions_source_name: boundary.source ?? "",
                            ...ids,
                            unit_code: null, unit_id: null, quantity: null, emissions_tco2e: null,
                        };
                    }));
                    if (cancelled) return;
                    updateRows("component", [...componentRows, ...placeholders]);
                    if (componentRows.some((row) => row.emissions_tco2e == null)) {
                        void recalcAndPersistRows("component", componentRows, (rows) => updateRows("component", rows));
                    }
                    if (projectClass === "LARGE") {
                        updateRows("bcDetailedLevel", mapApiRows(results[2], apiRowToUiRow));
                        const electricityRows = mapApiRows(results[3], apiRowToUiRow);
                        updateRows("electricity", electricityRows);
                        if (electricityRows.some((row) => row.emissions_tco2e == null)) {
                            void recalcAndPersistRows("electricity", electricityRows, (rows) => updateRows("electricity", rows));
                        }
                    }
                    return;
                }

                if (activeSubStage === "Use (B1)" && projectClass === "LARGE") {
                    const [rawG2, rawG3] = await Promise.all([
                        ActivityDataService.fetchRows(activeStageInstance.id, "useB1G2", activeOptionId ?? undefined),
                        ActivityDataService.fetchRows(activeStageInstance.id, "useB1G3", activeOptionId ?? undefined),
                    ]);
                    if (cancelled) return;
                    for (const [key, rawRows] of [["useB1G2", rawG2], ["useB1G3", rawG3]] as const) {
                        const rows = mapApiRows(rawRows, apiRowToUiRow);
                        updateRows(key, rows);
                        if (rows.some((row) => row.emissions_tco2e == null)) {
                            void recalcAndPersistRows(key, rows, (nextRows) => updateRows(key, nextRows));
                        }
                    }
                    return;
                }

                if (activeSubStage === REPLACEMENT_LABEL || activeSubStage === REPLACEMENT_LABEL_LARGE) {
                    const [rawComponent, rawRefurbishment, rawDetailed] = await Promise.all([
                        ActivityDataService.fetchRows(activeStageInstance.id, "componentRepl", activeOptionId ?? undefined),
                        ActivityDataService.fetchRows(activeStageInstance.id, "refurbishment", activeOptionId ?? undefined),
                        ActivityDataService.fetchRows(activeStageInstance.id, "replDetailed", activeOptionId ?? undefined),
                    ]);
                    if (cancelled) return;
                    const componentRows = mapApiRows(rawComponent, apiRowToUiRow);
                    const refurbishmentRows = mapApiRows(rawRefurbishment, apiRowToUiRow);
                    updateRows("componentRepl", componentRows);
                    updateRows("replDetailed", mapApiRows(rawDetailed, apiRowToUiRow));
                    if (!reportingBoundaries.length) {
                        updateRows("refurbishment", refurbishmentRows);
                        return;
                    }
                    const maintenanceBoundaries = reportingBoundaries.filter((boundary) => boundary.stage_or_activity === "Maintenance");
                    const factors = await fetchAllActiveMrFactors();
                    const placeholders: DataEntryRow[] = maintenanceBoundaries
                        .filter((boundary) => !refurbishmentRows.some((row) => row.extra_fields?.reporting_boundary_id === boundary.id))
                        .map((boundary) => {
                            const factor = factors.find((item) => item.activity_type === boundary.category && item.item === boundary.sub_category);
                            return {
                                id: `__BOUNDARY_${boundary.id}__`, _fromBoundary: true,
                                activityType: boundary.category, item: boundary.sub_category,
                                mr_factor_id: factor?.id ?? null, unit_code: factor?.unit?.code ?? "m2",
                                frequency: factor?.default_frequency_years ?? null,
                                quantity: null, emissions_tco2e: null,
                            };
                        });
                    if (cancelled) return;
                    updateRows("refurbishment", [...refurbishmentRows, ...placeholders]);
                    if (componentRows.some((row) => row.emissions_tco2e == null)) {
                        void recalcAndPersistRows("componentRepl", componentRows, (rows) => updateRows("componentRepl", rows));
                    }
                    if (refurbishmentRows.some((row) => row.emissions_tco2e == null)) {
                        void recalcAndPersistRows("refurbishment", refurbishmentRows, (rows) => updateRows("refurbishment", rows));
                    }
                    return;
                }

                if (activeSubStage === "Operational energy (B6)") {
                    const [rawOperational, rawDetailed, rawElectricity] = await Promise.all([
                        ActivityDataService.fetchRows(activeStageInstance.id, "opEnergy", activeOptionId ?? undefined),
                        projectClass === "LARGE" ? ActivityDataService.fetchRows(activeStageInstance.id, "opEnergyDetailed", activeOptionId ?? undefined) : Promise.resolve([]),
                        projectClass === "LARGE" ? ActivityDataService.fetchRows(activeStageInstance.id, "opEnergyElectricity", activeOptionId ?? undefined) : Promise.resolve([]),
                    ]);
                    if (cancelled) return;
                    const operationalRows = mapApiRows(rawOperational, apiRowToUiRow);
                    const operationsBoundaries = reportingBoundaries.filter((boundary) => boundary.stage_or_activity === "Operations");
                    const operationalPlaceholders: DataEntryRow[] = operationsBoundaries
                        .filter((boundary) => !operationalRows.some((row) => row.extra_fields?.reporting_boundary_id === boundary.id))
                        .map((boundary) => ({
                            id: `__BOUNDARY_${boundary.id}__`, _fromBoundary: true,
                            emissions_category: "Electricity", group_name: boundary.category,
                            item: boundary.sub_category, unit_code: "Each", quantity: null,
                            location_based_total_tco2e: null, market_based_total_tco2e: null, emissions_tco2e: null,
                        }));
                    updateRows("opEnergy", reportingBoundaries.length ? [...operationalRows, ...operationalPlaceholders] : operationalRows);
                    if (projectClass === "LARGE") {
                        updateRows("opEnergyDetailed", mapApiRows(rawDetailed, apiRowToUiRow));
                        const electricityRows = mapApiRows(rawElectricity, apiRowToUiRow);
                        updateRows("opEnergyElectricity", electricityRows);
                        if (electricityRows.some((row) => row.emissions_tco2e == null)) {
                            void recalcAndPersistRows("opEnergyElectricity", electricityRows, (rows) => updateRows("opEnergyElectricity", rows));
                        }
                    }
                }
            } catch (error) {
                console.error("Error fetching data:", error);
            }
        })();
        return () => { cancelled = true; };
    }, [enabled, activeStage, activeSubStage, activeStageInstance, activeOptionId, projectClass, reportingBoundaries, updateRows, setTableRows, apiRowToUiRow, resolveBoundaryComponentIds, recalcAndPersistRows]);
}
