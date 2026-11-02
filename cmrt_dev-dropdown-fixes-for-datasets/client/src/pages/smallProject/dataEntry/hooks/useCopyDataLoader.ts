import { useCallback } from "react";
import ActivityDataService, { type ActivityDataOut } from "@/services/ActivityData.service";
import type { DataEntryRow, ProjectClass, ReportingBoundary, StageInstance } from "../dataEntryTypes";
import { REPLACEMENT_LABEL, REPLACEMENT_LABEL_LARGE, type UploadKey } from "../stageConstants";

interface Params {
    activeSubStage: string;
    activeStageInstance: StageInstance | null;
    activeOptionId: string | null;
    projectClass: ProjectClass | null;
    reportingBoundaries: ReportingBoundary[];
    updateRows: (key: UploadKey, rows: DataEntryRow[]) => void;
    apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
    resolveBoundaryComponentIds: (boundary: ReportingBoundary) => Promise<{
        emissions_category_id: string | null;
        emissions_subcategory_id: string | null;
        emissions_source: string | null;
    }>;
    closeCopyDialog: () => void;
    refreshUsers: () => void;
}

export function useCopyDataLoader({
    activeSubStage,
    activeStageInstance,
    activeOptionId,
    projectClass,
    reportingBoundaries,
    updateRows,
    apiRowToUiRow,
    resolveBoundaryComponentIds,
    closeCopyDialog,
    refreshUsers,
}: Params): () => Promise<void> {
    return useCallback(async () => {
        closeCopyDialog();
        if (!activeStageInstance || !activeOptionId) return;

        if (activeSubStage === "Construction") {
            const requests: Promise<ActivityDataOut[]>[] = [
                ActivityDataService.fetchRows(activeStageInstance.id, "asset", activeOptionId),
                ActivityDataService.fetchRows(activeStageInstance.id, "component", activeOptionId),
            ];
            if (projectClass === "LARGE") {
                requests.push(
                    ActivityDataService.fetchRows(activeStageInstance.id, "bcDetailedLevel", activeOptionId),
                    ActivityDataService.fetchRows(activeStageInstance.id, "electricity", activeOptionId),
                );
            }
            const results = await Promise.all(requests);
            updateRows("asset", mapApiRows(results[0], apiRowToUiRow));
            const componentRows = mapApiRows(results[1], apiRowToUiRow);
            const constructionBoundaries = reportingBoundaries.filter((boundary) => boundary.stage_or_activity === "Construction");
            const missingBoundaries = constructionBoundaries.filter((boundary) =>
                !componentRows.some((row) => row.extra_fields?.reporting_boundary_id === boundary.id),
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
            updateRows("component", [...componentRows, ...placeholders]);
            if (projectClass === "LARGE") {
                updateRows("bcDetailedLevel", mapApiRows(results[2], apiRowToUiRow));
                updateRows("electricity", results[3].map((row) => ({
                    _fromApi: true,
                    ...(row.extra_fields ?? {}),
                    id: row.id,
                    metric_id: row.metric_id,
                    quantity: row.quantity,
                    unit_id: row.unit_id,
                    emissions_tco2e: row.emissions_tco2e,
                    location_based_tco2e: row.extra_fields?.location_based_tco2e ?? null,
                    market_based_tco2e: row.extra_fields?.market_based_tco2e ?? null,
                })));
            }
            return;
        }

        if (activeSubStage === "Use (B1)" && projectClass === "LARGE") {
            const [rawG2, rawG3] = await Promise.all([
                ActivityDataService.fetchRows(activeStageInstance.id, "useB1G2", activeOptionId),
                ActivityDataService.fetchRows(activeStageInstance.id, "useB1G3", activeOptionId),
            ]);
            updateRows("useB1G2", mapApiRows(rawG2, apiRowToUiRow));
            updateRows("useB1G3", mapApiRows(rawG3, apiRowToUiRow));
            return;
        }

        if (activeSubStage === REPLACEMENT_LABEL || activeSubStage === REPLACEMENT_LABEL_LARGE) {
            const [rawComponent, rawRefurbishment] = await Promise.all([
                ActivityDataService.fetchRows(activeStageInstance.id, "componentRepl", activeOptionId),
                ActivityDataService.fetchRows(activeStageInstance.id, "refurbishment", activeOptionId),
            ]);
            updateRows("componentRepl", mapApiRows(rawComponent, apiRowToUiRow));
            updateRows("refurbishment", mapApiRows(rawRefurbishment, apiRowToUiRow));
            return;
        }

        if (activeSubStage === "Operational energy (B6)") {
            const rawOperational = await ActivityDataService.fetchRows(activeStageInstance.id, "opEnergy", activeOptionId);
            updateRows("opEnergy", mapApiRows(rawOperational, apiRowToUiRow));
            return;
        }

        if (activeSubStage === "Users (B8)") refreshUsers();
    }, [activeSubStage, activeStageInstance, activeOptionId, projectClass, reportingBoundaries,
        updateRows, apiRowToUiRow, resolveBoundaryComponentIds, closeCopyDialog, refreshUsers]);
}

function mapApiRows(
    rows: ActivityDataOut[] | null | undefined,
    mapper: (row: ActivityDataOut) => DataEntryRow,
): DataEntryRow[] {
    return (Array.isArray(rows) ? rows : []).map(mapper);
}
