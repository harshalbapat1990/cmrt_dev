import LookupsService from "@/services/Lookups.service";
import { isElectricityTable } from "./stageConstants";
import type { UploadKey } from "./stageConstants";

export const GRADE2_IDS = [2];
export const GRADE34_IDS = [3, 4];

export const apiRowToUiRow = (apiRow: any): any => {
    const extra = apiRow.extra_fields ?? {};
    const emRaw =
        extra.total_emissions_tco2e ??
        extra.emissions_tco2e ??
        apiRow.total_emissions_tco2e ??
        apiRow.emissions_tco2e ??
        null;
    const em =
        emRaw !== null && emRaw !== "" && emRaw !== "-" ? Number(emRaw) : null;
    return {
        _fromApi: true,
        extra_fields: extra,
        ...extra,
        _fromBoundary: !!(extra.fromBoundary || extra.reporting_boundary_id),
        id: apiRow.id,
        metric_id: apiRow.metric_id,
        dataset_revision_id: apiRow.dataset_revision_id ?? null,
        quantity: apiRow.quantity,
        unit_id: apiRow.unit_id,
        emissions_tco2e: em,
        total_emissions_tco2e: em,
        location_based_tco2e: extra.location_based_tco2e ?? null,
        market_based_tco2e: extra.market_based_tco2e ?? null,
    };
};

export const buildExtraFields = (
    row: any,
    opts?: { keepEmissions?: boolean; tableKey?: UploadKey }
): any => {
    const keepEmissions = !!opts?.keepEmissions;
    const tableKey = opts?.tableKey;
    const ef = { ...row };
    delete ef._fromApi;
    delete ef.id;
    delete ef.metric_id;
    delete ef.quantity;
    delete ef.unit_id;
    if (!isElectricityTable(tableKey ?? "")) {
        delete ef.location_based_tco2e;
        delete ef.market_based_tco2e;
    }
    delete ef.emissions_tco2e;
    if (!keepEmissions) {
        delete ef.total_emissions_tco2e;
    }
    return ef;
};

export const resolveBoundaryComponentIds = async (
    b: { category: string; sub_category: string; source?: string | null },
    projectId: string
): Promise<{
    emissions_category_id: string | null;
    emissions_subcategory_id: string | null;
    emissions_source: string | null;
}> => {
    const normalize = (s: string) => s?.trim().toLowerCase() ?? "";
    const matchByName = (raw: string, list: any[]) =>
        list.find((x) => normalize(x.name ?? x.label ?? "") === normalize(raw));

    try {
        const cats = await LookupsService.fetchBgmCategories(GRADE2_IDS, projectId);
        const catObj = matchByName(b.category, cats);
        const catId = catObj?.id ?? catObj?.value ?? null;

        let subId: string | null = null;
        if (catId) {
            const subs = await LookupsService.fetchBgmSubcategories(GRADE2_IDS, catId);
            const subObj = matchByName(b.sub_category, subs);
            subId = subObj?.id ?? subObj?.value ?? null;
        }

        let sourceId: string | null = null;
        if (subId && b.source) {
            const srcs = await LookupsService.fetchBgmSources(GRADE2_IDS, subId);
            const srcObj = matchByName(b.source, srcs);
            sourceId = srcObj?.id ?? srcObj?.value ?? null;
        }

        return {
            emissions_category_id: catId,
            emissions_subcategory_id: subId,
            emissions_source: sourceId,
        };
    } catch {
        return {
            emissions_category_id: null,
            emissions_subcategory_id: null,
            emissions_source: null,
        };
    }
};
