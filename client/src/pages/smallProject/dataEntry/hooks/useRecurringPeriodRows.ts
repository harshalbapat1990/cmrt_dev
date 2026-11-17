import { useEffect } from "react";
import ActivityDataService, { type ActivityDataOut } from "@/services/ActivityData.service";
import LookupsService from "@/services/Lookups.service";
import type { DataEntryRow, LookupChoice, ReportingBoundary, StageInstance } from "../dataEntryTypes";
import { GRADE34_IDS } from "../rowTransforms";

interface Params {
    activeStageInstance: StageInstance | null;
    periodId: string | null;
    projectId: string;
    reportingBoundaries: ReportingBoundary[];
    apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
    updateRows: (key: "recurringG3", rows: DataEntryRow[]) => void;
    updateElectricityRows?: (rows: DataEntryRow[]) => void;
}

/** Loads recurring emissions rows and creates blank rows for uncovered boundaries. */
export function useRecurringPeriodRows({
    activeStageInstance,
    periodId,
    projectId,
    reportingBoundaries,
    apiRowToUiRow,
    updateRows,
    updateElectricityRows,
}: Params): void {
    useEffect(() => {
        if (!activeStageInstance || !periodId) return;
        updateRows("recurringG3", []);
        updateElectricityRows?.([]);
        let cancelled = false;
        void (async () => {
            try {
                const rawRows = await ActivityDataService.fetchRows(
                    activeStageInstance.id,
                    "recurringG3",
                    undefined,
                    periodId,
                );
                if (cancelled) return;
                const rows = (Array.isArray(rawRows) ? rawRows : []).map(apiRowToUiRow);
                const existingBoundaryIds = new Set(rows.map((row) =>
                    row.reporting_boundary_id ?? row.extra_fields?.reporting_boundary_id,
                ).filter((id): id is string => Boolean(id)));
                const placeholders = await Promise.all(reportingBoundaries
                    .filter((boundary) => boundary.category.trim().toLowerCase() !== "electricity" && !existingBoundaryIds.has(boundary.id))
                    .map((boundary) => createBoundaryPlaceholder(boundary, projectId)));
                if (!cancelled) updateRows("recurringG3", [...rows, ...placeholders]);
                const electricityRaw = await ActivityDataService.fetchRows(
                    activeStageInstance.id,
                    "electricity",
                    undefined,
                    periodId,
                );
                if (cancelled) return;
                const electricityRows = (Array.isArray(electricityRaw) ? electricityRaw : []).map(apiRowToUiRow);
                const existingElectricityBoundaryIds = new Set(electricityRows.map((row) =>
                    row.reporting_boundary_id ?? row.extra_fields?.reporting_boundary_id,
                ).filter((id): id is string => Boolean(id)));
                const electricityPlaceholders = reportingBoundaries
                    .filter((boundary) => boundary.category.trim().toLowerCase() === "electricity" && !existingElectricityBoundaryIds.has(boundary.id))
                    .map((boundary) => electricityBoundaryRow(boundary));
                if (!cancelled) updateElectricityRows?.([...electricityRows, ...electricityPlaceholders]);
            } catch (error) {
                console.error("Failed to load recurringG3 rows:", error);
            }
        })();
        return () => { cancelled = true; };
    }, [activeStageInstance, periodId, projectId, reportingBoundaries, apiRowToUiRow, updateRows, updateElectricityRows]);
}

function electricityBoundaryRow(boundary: ReportingBoundary): DataEntryRow {
    return {
        id: `__BOUNDARY_${boundary.id}__`,
        _fromBoundary: true,
        reporting_boundary_id: boundary.id,
        stage_or_activity: boundary.stage_or_activity,
        emissions_category: "Electricity",
        emissions_subcategory: "Electricity",
        emission_source: boundary.source ?? "",
        quantity_mwh: null,
        unit_display: "MWh",
        unit_code: "MWh",
        emissions_tco2e: null,
        total_emissions_tco2e: null,
    };
}

async function createBoundaryPlaceholder(boundary: ReportingBoundary, projectId: string): Promise<DataEntryRow> {
    const normalize = (value: string) => value.trim().toLowerCase();
    const matchByName = (raw: string, list: LookupChoice[]) =>
        list.find((choice) => normalize(choice.name ?? choice.label ?? "") === normalize(raw));
    try {
        const categories = await LookupsService.fetchBgmCategories(GRADE34_IDS, projectId);
        const category = matchByName(boundary.category, categories);
        const categoryId = category?.id ?? category?.value ?? null;
        let subcategoryId: string | null = null;
        if (categoryId) {
            const subcategories = await LookupsService.fetchBgmSubcategories(GRADE34_IDS, categoryId, projectId);
            const subcategory = matchByName(boundary.sub_category, subcategories);
            subcategoryId = subcategory?.id ?? subcategory?.value ?? null;
        }
        let sourceId: string | null = null;
        if (subcategoryId && boundary.source) {
            const sources = await LookupsService.fetchBgmSources(GRADE34_IDS, subcategoryId, projectId);
            const source = matchByName(boundary.source, sources);
            sourceId = source?.id ?? source?.value ?? null;
        }
        return boundaryRow(boundary, categoryId, subcategoryId, sourceId);
    } catch {
        return boundaryRow(boundary, null, null, null);
    }
}

function boundaryRow(
    boundary: ReportingBoundary,
    categoryId: string | null,
    subcategoryId: string | null,
    sourceId: string | null,
): DataEntryRow {
    return {
        id: `__BOUNDARY_${boundary.id}__`,
        _fromBoundary: true,
        reporting_boundary_id: boundary.id,
        emissions_category: boundary.category,
        emissions_subcategory: boundary.sub_category,
        emissions_source_name: boundary.source ?? "",
        emissions_category_id: categoryId,
        emissions_subcategory_id: subcategoryId,
        emissions_source: sourceId,
        unit_code: null,
        unit_id: null,
        quantity: null,
        emissions_tco2e: null,
        total_emissions_tco2e: null,
    };
}
