import EmissionCalculationsService from "@/services/EmissionCalculations.service";
import LookupsService, { type UnitOption } from "@/services/Lookups.service";

const GRADE1_IDS = [1];

const SENSITIVITY_OPTIONS = [
    { label: "Low", value: "Low" },
    { label: "Mid", value: "Mid" },
    { label: "High", value: "High" },
];


const mapToOptions = (list: any[], labelField = "name", valueField = "id") =>
    (list ?? []).map((x) => ({ label: x[labelField], value: x[valueField] }));

const pickLabel = (v: any) => {
    if (v == null) return "";
    if (typeof v === "string" || typeof v === "number") return String(v);
    return v.label ?? v.name ?? v.value ?? "";
};

export const assetTableConfig = (projectId: string) => ({
    tableName: "Asset level",
    calculation: {
        grade: 1,
        requiredKeys: [
            "mastertype_id",
            "typecast_id",
            "band_code",
            "quantity",
            "unit_id",
        ],
        triggerKeys: [
            "mastertype_name",
            "mastertype_id",
            "typecast_name",
            "typecast_id",
            "band_code",
            "quantity",
            "unit_code",
            "unit_id",
        ],
        buildPayload: (row: any, ctx: { jurisdiction: string }) => {
            const mastertype = pickLabel(row.mastertype_name);
            const typecast = pickLabel(row.typecast_name);
            const sensitivity = pickLabel(row.band_code);
            const functional_unit = pickLabel(row.canonical_unit_code || row.unit_code);
            const convFactor = row.unit_conversion_factor != null ? Number(row.unit_conversion_factor) : 1;
            const quantity = row.quantity != null ? Number(row.quantity) * convFactor : NaN;

            if (!mastertype || !typecast || !sensitivity || Number.isNaN(quantity) || !functional_unit) {
                return null;
            }
            return {
                mastertype,
                typecast,
                sensitivity,
                quantity,
                functional_unit,
                jurisdiction: ctx.jurisdiction,
            };
        },
        // table-specific API call
        calculate: async (payload: any) => {
            // For asset table, use grade1 endpoint OR your table endpoint
            return EmissionCalculationsService.grade1EmissionValues(payload);
        },

        // map API response -> row changes
        mapResultToRow: (apiRes: any, row?: any) => {
            const val =
                apiRes?.total_emissions_tco2e != null && !Number.isNaN(Number(apiRes.total_emissions_tco2e))
                    ? Number(apiRes.total_emissions_tco2e)
                    : (row?.total_emissions_tco2e != null ? Number(row.total_emissions_tco2e) : null);
            return {
                emissions_tco2e: val,
            };
        }
    },
    fileHeaders: [
        { 
            key: "mastertype_name", 
            label: "Mastertype" 
        },
        { 
            key: "typecast_name", 
            label: "Typecast" 
        },
        { 
            key: "band_code", 
            label: "Sensitivity" 
        },
        { 
            key: "unit_code", 
            label: "Unit" 
        },
        { 
            key: "quantity", 
            label: "Quantity" 
        },
        // { key: "emissions_tco2e", label: "Emissions" },
        { 
            key: "notes", 
            label: "Notes/Comments (optional)" 
        }
    ],
    rules: [
        {
            label: "Mastertype",
            keySource: "mastertype_name",
            key: "mastertype_id",
            required: true,
            lookup: {
                fetch: async (_ctx?: { row?: any }) => {
                    const list = await LookupsService.fetchMasterTypesbyProjectId(projectId);
                    return mapToOptions(list);
                },
                labelField: "label",
                idField: "value",

            }
        },
        {
            label: "Typecast",
            keySource: "typecast_name",
            key: "typecast_id",
            required: true,
            lookup: {
                fetch: async (ctx?: { row?: any }) => {
                    const masterTypeId = ctx?.row?.mastertype_id;
                    if (!masterTypeId) return [];
                    const list = await LookupsService.fetchTypecasts(masterTypeId, projectId);
                    return mapToOptions(list);
                },
                labelField: "label",
                idField: "value",

            }
        },
        {
            label: "Sensitivity",
            keySource: "band_code",
            key: "band_code",
            required: true,
            options: SENSITIVITY_OPTIONS.map(x => x.value)
        },
        {
            label: "Unit",
            keySource: "unit_code",
            key: "unit_id",
            required: true,
            lookup: {
                fetch: async (ctx?: { row?: any }) => {
                    const typecastId = ctx?.row?.typecast_id;
                    if (typecastId) {
                        return mapToOptions(await LookupsService.fetchUnitsByTypecast(typecastId, GRADE1_IDS));
                    }
                    return mapToOptions(await LookupsService.fetchUnits());
                },
                labelField: "label",
                idField: "value",
            }
        },
        {
            label: "Quantity",
            keySource: "quantity",
            key: "quantity",
            number: true,
            required: true
        },
        { 
            label: "Notes/Comments (optional)", 
            keySource: "notes", 
            key: "notes" 
        }
    ],
    columns: () => [
        {
            header: "Mastertype",
            width: "20%",
            key: "mastertype_name",
            editable: true,
            // editableWhen: (row: any) => row?.id === "__NEW__",
            editorType: "select",
            idKey: "mastertype_id",
            getOptions: async () => {
                if (!projectId) return [];
                const list = await LookupsService.fetchMasterTypesbyProjectId(projectId); // [{id,name}]
                return mapToOptions(list);
            },
            clearsOnChange: ["typecast_name", "typecast_id", "unit_code", "unit_id"],
        },
        {
            header: "Typecast",
            width: "20%",
            key: "typecast_name",
            editable: true,
            // editableWhen: (row: any) => row?.id === "__NEW__",
            editorType: "select",
            idKey: "typecast_id",
            dependsOnKeys: ["mastertype_id"],
            getOptions: async (ctx?: { row?: any }) => {
                const masterTypeId = ctx?.row?.mastertype_id;
                if (!masterTypeId) return [];
                const list = await LookupsService.fetchTypecasts(masterTypeId, projectId);
                return mapToOptions(list);
            },
            clearsOnChange: ["unit_code", "unit_id"],
            noCache: true,
            refreshOnDepsChange: true,
        },
        {
            header: "Sensitivity",
            width: "10%",
            key: "band_code",
            editable: true,
            // editableWhen: (row: any) => row?.id === "__NEW__",
            editorType: "select",
            getOptions: () => SENSITIVITY_OPTIONS,
        },
        {
            header: "Unit",
            width: "8%",
            key: "unit_code",
            editable: true,
            // editableWhen: (row: any) => row?.id === "__NEW__",
            editorType: "select",
            idKey: "unit_id",
            dependsOnKeys: ["typecast_id"],
            getOptions: async (ctx?: { row?: any }) => {
                const typecastId = ctx?.row?.typecast_id;
                const list: UnitOption[] = typecastId
                    ? await LookupsService.fetchUnitsByTypecast(typecastId, GRADE1_IDS)
                    : await LookupsService.fetchUnits();
                return list.map(u => ({
                    label: u.name,
                    value: u.id,
                    is_canonical: u.is_canonical,
                    canonical_unit_id: u.canonical_unit_id ?? null,
                    canonical_unit_code: u.canonical_unit_code ?? u.name,
                    to_canonical_factor: u.to_canonical_factor ?? null,
                }));
            },
            onSelect: (selected: any) => ({
                canonical_unit_id: selected?.canonical_unit_id ?? null,
                unit_conversion_factor: selected?.to_canonical_factor ?? null,
                canonical_unit_code: selected?.canonical_unit_code ?? selected?.label ?? null,
            }),
            noCache: true,
            refreshOnDepsChange: true,
        },
        {
            header: "Quantity",
            width: "10%",
            key: "quantity",
            editable: true,
            editorType: "number",
        },
        { 
            header: "Emissions (tCO2e)", 
            width: "12%", 
            key: "emissions_tco2e", 
            editable: false 
        },
        {
            header: "Notes / Comments (optional)",
            width: "30%",
            key: "notes",
            editable: true,
            editorType: "text",
        },
    ],

});