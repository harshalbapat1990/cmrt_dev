import { useEffect, type Dispatch, type SetStateAction } from "react";
import ActivityDataService, { type ActivityDataOut } from "@/services/ActivityData.service";
import type { DataEntryRow, ProjectClass, ReportingBoundary, StageInstance, StageLabel } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";
import { REPLACEMENT_LABEL, REPLACEMENT_LABEL_LARGE } from "../stageConstants";

interface Params {
    enabled: boolean;
    activeStage: StageLabel;
    activeSubStage: string;
    activeStageInstance: StageInstance | null;
    periodId: string | null;
    projectClass: ProjectClass | null;
    reportingBoundaries: ReportingBoundary[];
    updateRows: (key: UploadKey, rows: DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[])) => void;
    apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
    resolveBoundaryComponentIds: (boundary: ReportingBoundary) => Promise<{
        emissions_category_id: string | null;
        emissions_subcategory_id: string | null;
        emissions_source: string | null;
    }>;
    recalcAndPersistRows: (
        key: UploadKey,
        rows: DataEntryRow[],
        setRows: Dispatch<SetStateAction<DataEntryRow[]>>,
    ) => Promise<void>;
}

const mapApiRows = (rows: ActivityDataOut[], mapper: Params["apiRowToUiRow"]): DataEntryRow[] =>
    (Array.isArray(rows) ? rows : []).map(mapper);

/** Loads table rows for construction periods, including large-project sub-stages. */
export function useConstructionPeriodRows({
    enabled,
    activeStage,
    activeSubStage,
    activeStageInstance,
    periodId,
    projectClass,
    reportingBoundaries,
    updateRows,
    apiRowToUiRow,
    resolveBoundaryComponentIds,
    recalcAndPersistRows,
}: Params): void {
    useEffect(() => {
        if (!enabled || activeStage !== "Construction" || !activeStageInstance || !periodId) return;
        const stageInstance = activeStageInstance;
        let cancelled = false;
        void (async () => {
            try {
                if (projectClass === "LARGE" && activeSubStage !== "Construction") {
                    await loadLargeProjectSubstageRows();
                    return;
                }
                updateRows("constructionG2", []);
                updateRows("constructionG3", []);
                updateRows("electricity", []);
                const [rawG2, rawG3, rawElectricity] = await Promise.all([
                    ActivityDataService.fetchRows(stageInstance.id, "constructionG2", undefined, periodId),
                    ActivityDataService.fetchRows(stageInstance.id, "constructionG3", undefined, periodId),
                    ActivityDataService.fetchRows(stageInstance.id, "electricity", undefined, periodId),
                ]);
                if (cancelled) return;
                const g2Rows = mapApiRows(rawG2, apiRowToUiRow);
                const constructionBoundaries = reportingBoundaries.filter((boundary) => boundary.stage_or_activity === "Construction");
                const missingBoundaries = constructionBoundaries.filter((boundary) =>
                    !g2Rows.some((row) => row.extra_fields?.reporting_boundary_id === boundary.id),
                );
                const placeholders = await Promise.all(missingBoundaries.map(async (boundary): Promise<DataEntryRow> => ({
                    id: `__BOUNDARY_${boundary.id}__`,
                    _fromBoundary: true,
                    emissions_category: boundary.category,
                    emissions_subcategory: boundary.sub_category,
                    emissions_source_name: boundary.source ?? "",
                    ...await resolveBoundaryComponentIds(boundary),
                    unit_code: null,
                    unit_id: null,
                    quantity: null,
                    emissions_tco2e: null,
                })));
                if (cancelled) return;
                updateRows("constructionG2", [...g2Rows, ...placeholders]);
                updateRows("constructionG3", mapApiRows(rawG3, apiRowToUiRow));
                const electricityRows = mapApiRows(rawElectricity, apiRowToUiRow);
                updateRows("electricity", electricityRows);
                const invalidElectricityRows = electricityRows.filter((row) =>
                    !row.location_based_tco2e || row.location_based_tco2e === "-" || Number.isNaN(Number(row.location_based_tco2e)),
                );
                if (invalidElectricityRows.length) {
                    void recalcAndPersistRows("electricity", invalidElectricityRows, (rows) => updateRows("electricity", rows));
                }
            } catch (error) {
                console.error("Failed to fetch construction data for period", error);
            }
        })();

        async function loadLargeProjectSubstageRows(): Promise<void> {
            try {
                if (activeSubStage === "Use (B1)") {
                    updateRows("useB1G2", []);
                    updateRows("useB1G3", []);
                    const [rawG2, rawG3] = await Promise.all([
                        ActivityDataService.fetchRows(stageInstance.id, "useB1G2", undefined, periodId),
                        ActivityDataService.fetchRows(stageInstance.id, "useB1G3", undefined, periodId),
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
                    updateRows("componentRepl", []);
                    updateRows("refurbishment", []);
                    updateRows("replDetailed", []);
                    const [rawComponent, rawRefurbishment, rawDetailed] = await Promise.all([
                        ActivityDataService.fetchRows(stageInstance.id, "componentRepl", undefined, periodId),
                        ActivityDataService.fetchRows(stageInstance.id, "refurbishment", undefined, periodId),
                        ActivityDataService.fetchRows(stageInstance.id, "replDetailed", undefined, periodId),
                    ]);
                    if (cancelled) return;
                    updateRows("componentRepl", mapApiRows(rawComponent, apiRowToUiRow));
                    updateRows("refurbishment", mapApiRows(rawRefurbishment, apiRowToUiRow));
                    updateRows("replDetailed", mapApiRows(rawDetailed, apiRowToUiRow));
                    return;
                }

                if (activeSubStage === "Operational energy (B6) and Water (B7)") {
                    updateRows("opEnergy", []);
                    updateRows("opEnergyDetailed", []);
                    updateRows("opEnergyElectricity", []);
                    const [rawOperational, rawDetailed, rawElectricity] = await Promise.all([
                        ActivityDataService.fetchRows(stageInstance.id, "opEnergy", undefined, periodId),
                        ActivityDataService.fetchRows(stageInstance.id, "opEnergyDetailed", undefined, periodId),
                        ActivityDataService.fetchRows(stageInstance.id, "opEnergyElectricity", undefined, periodId),
                    ]);
                    if (cancelled) return;
                    updateRows("opEnergy", mapApiRows(rawOperational, apiRowToUiRow));
                    updateRows("opEnergyDetailed", mapApiRows(rawDetailed, apiRowToUiRow));
                    const electricityRows = mapApiRows(rawElectricity, apiRowToUiRow);
                    updateRows("opEnergyElectricity", electricityRows);
                    if (electricityRows.some((row) => row.emissions_tco2e == null)) {
                        void recalcAndPersistRows("opEnergyElectricity", electricityRows, (rows) => updateRows("opEnergyElectricity", rows));
                    }
                }
            } catch (error) {
                console.error("Failed to fetch construction operations data for period", error);
            }
        }

        return () => { cancelled = true; };
    }, [enabled, activeStage, activeSubStage, activeStageInstance, periodId, projectClass, reportingBoundaries,
        updateRows, apiRowToUiRow, resolveBoundaryComponentIds, recalcAndPersistRows]);
}
