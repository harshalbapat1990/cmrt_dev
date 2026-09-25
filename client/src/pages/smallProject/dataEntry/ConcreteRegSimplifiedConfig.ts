import EmissionCalculationsService from "../../../services/EmissionCalculations.service";

const MIXTYPE_OPTIONS = [
    { label: "Ready-mix", value: "Ready-mix" },
    { label: "Precast", value: "Precast" },
];

const STRENGTH_OPTIONS = [
    { label: "5MPa", value: "5MPa" },
    { label: "10MPa", value: "10MPa" },
    { label: "15MPa", value: "15MPa" },
    { label: "20MPa", value: "20MPa" },
    { label: "25MPa", value: "25MPa" },
    { label: "32MPa", value: "32MPa" },
    { label: "40MPa", value: "40MPa" },
    { label: "50MPa", value: "50MPa" },
    { label: "65MPa", value: "65MPa" },
    { label: "80MPa", value: "80MPa" },
    { label: "100MPa", value: "100MPa" },];



const pickLabel = (v: any) => {
    if (v == null) return "";
    if (typeof v === "string" || typeof v === "number") return String(v);
    return v.label ?? v.name ?? v.value ?? "";
};

const normalizeMixType = (v: any) => {
    const raw = pickLabel(v);
    if (raw === "READY_MIX") return "Ready-mix";
    if (raw === "PRECAST") return "Precast";
    return raw;
};

const parseStrengthMpa = (v: any): number | null => {
    const raw = pickLabel(v);
    const n = Number(raw.replace(/[^0-9.]/g, ""));
    return Number.isFinite(n) ? n : null;
};

const extractConcreteEmissions = (apiRes: any): number | null => {
    const raw =
        apiRes?.total_emissions_tco2e ??
        apiRes?.emissions_tco2e ??
        apiRes?.data?.total_emissions_tco2e ??
        apiRes?.data?.emissions_tco2e ??
        null;
    if (raw === "-" || raw === "" || raw == null || Number.isNaN(Number(raw))) {
        return null;
    }
    return Number(raw);
};


export const concreteRegSimplifiedConfig = () => ({
    tableName: "Concrete register (grade 3) - simplified",
    calculation: {
        grade: 3,
        requiredKeys: [
            "mixType",
            "strength",
            "targetSCMContent",
            "volume",
        ],
        triggerKeys: [
            "mixType",
            "strength",
            "targetSCMContent",
            "volume",
        ],
        buildPayload: (row: any, ctx: any) => {
            const mix_type = normalizeMixType(row.mixType ?? row.mix_type);
            const strength_mpa = parseStrengthMpa(row.strength ?? row.strength_mpa);
            const scm_pct = Number(row.targetSCMContent ?? row.scm_pct);
            const volume_m3 = Number(row.volume ?? row.volume_m3);

            if (
                !ctx.project_id ||
                !mix_type ||
                Number.isNaN(strength_mpa) ||
                Number.isNaN(scm_pct) ||
                Number.isNaN(volume_m3)
            ) {
                return null;
            }
            return {
                project_id: ctx.project_id,
                mix_type,
                strength_mpa,
                scm_pct,
                volume_m3
            };
        },
        calculate: async (payload: any) => {
            return EmissionCalculationsService.concreteRegSimplifiedCalculations(payload);
        },

        mapResultToRow: (apiRes: any) => {
            const emissions = extractConcreteEmissions(apiRes);
            return {
                emissions_tco2e: emissions,
                gwp_a1a3_tco2e_m3: apiRes?.gwp_a1a3_tco2e_m3 ?? null,
                transport_a4_ef_tco2e_m3: apiRes?.transport_a4_ef_tco2e_m3 ?? null,
            };
        },
    },
    fileHeaders: [
        { 
            key: "mixType", 
            label: "Mix type" 
        },
        { 
            key: "strength", 
            label: "Strength" 
        },
        { 
            key: "targetSCMContent", 
            label: "Target SCM Content (%)" 
        },
        { 
            key: "volume", 
            label: "Volume (m3)" 
        },
        { 
            key: "notes", 
            label: "Notes/Comments (optional)" 
        }
    ],
    rules: [
        {
            label: "Mix type",
            keySource: "mixType",
            key: "mixType",
            required: true,
            options: MIXTYPE_OPTIONS,
        },
        {
            label: "Strength",
            keySource: "strength",
            key: "strength",
            required: true,
            options: STRENGTH_OPTIONS,
        },
        {
            label: "Target SCM Content (%)",
            keySource: "targetSCMContent",
            key: "targetSCMContent",
            required: true,
        },
        {
            label: "Volume (m3)",
            keySource: "volume",
            key: "volume",
            required: true,
        },
        { 
            label: "Notes/Comments (optional)", 
            keySource: "notes", 
            key: "notes" 
        }
    ],
    columns: () => [
        {
            header: "Mix type",
            width: "18%",
            key: "mixType",
            editable: true,
            editorType: "select",
            idKey: "mixType",
            getOptions: () => MIXTYPE_OPTIONS,
        },
        {
            header: "Strength",
            width: "18%",
            key: "strength",
            editable: true,
            editorType: "select",
            idKey: "strength",
            getOptions: () => STRENGTH_OPTIONS,
        },
        {
            header: "Target SCM Content (%)",
            width: "16%",
            key: "targetSCMContent",
            editable: true,
            editorType: "number",
        },
        {
            header: "Volume (m3)",
            width: "12%",
            key: "volume",
            editable: true,
            editorType: "number",
        },
        { 
            header: "Emissions (tCO₂e)", 
            width: "14%", 
            key: "emissions_tco2e", 
            editable: false 
        },
        {
            header: "Notes / Comments (optional)",
            width: "22%",
            key: "notes",
            editable: true,
            editorType: "text",
        },
    ],
});