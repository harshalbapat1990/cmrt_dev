import EmissionCalculationsService from "@/services/EmissionCalculations.service";

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

export const concreteRegDetailedConfig = () => ({
    tableName: "Concrete register (grade 3) - detailed",
    calculation: {
        grade: 3,
        requiredKeys: [
            "method",
            "mixId",
            "volume",
        ],
        triggerKeys: [
            "method",
            "mixId",
            "volume",
            "strength",
            "gwp_a1a3",
            "materials",
            "mixType",
        ],
        buildPayload: (row: any, ctx: any) => {
            const method = row.method;
            const project_id = ctx.project_id;
            const mix_id_label = row.mixId;
            const mix_type = normalizeMixType(row.mixType ?? row.mix_type);
            const strength_mpa = parseStrengthMpa(row.strength ?? row.strength_mpa);
            const volume_m3 = Number(row.volume ?? row.volume_m3);

            if (!project_id || !method || !mix_id_label || Number.isNaN(volume_m3)) {
                return null;
            }

            if (method === "mix_design") {
                const materials = (row.materials ?? [])
                    .filter((m: any) => m.quantityKgM3 != null || m.quantity_kg_m3 != null)
                    .map((m: any) => ({
                        material_name: m.materialName ?? m.material_name,
                        quantity_kg_m3: Number(m.quantityKgM3 ?? m.quantity_kg_m3),
                    }));
                if (!mix_type || strength_mpa == null || !materials.length) {
                    return null;
                }
                return {
                    method,
                    request: {
                        project_id,
                        mix_id_label,
                        mix_type,
                        strength_mpa,
                        volume_m3,
                        materials,
                    },
                };
            }
            if (method === "epd_pcf") {
                const gwp_a1a3_kgco2e_m3 = Number(
                    row.gwpA1A3 ?? row.gwp_a1a3 ?? row.gwp_a1a3_kgco2e_m3
                );
                if (
                    !mix_type ||
                    strength_mpa == null ||
                    Number.isNaN(gwp_a1a3_kgco2e_m3)
                ) {
                    return null;
                }
                return {
                    method,
                    request: {
                        project_id,
                        mix_id_label,
                        mix_type,
                        strength_mpa,
                        volume_m3,
                        gwp_a1a3_kgco2e_m3,
                    },
                };
            }
            return null;
        },
        calculate: async (payload: any) => {
            if (payload.method === "mix_design") {
                return EmissionCalculationsService.concreteRegNewMixCalculations(payload.request);
            }
            if (payload.method === "epd_pcf") {
                return EmissionCalculationsService.concreteRegNewMixEPDCalculations(payload.request);
            }
            return null;
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
            key: "mixId", 
            label: "Mix ID" 
        },
        { 
            key: "volume (m3)", 
            label: "Volume (m3)" 
        },
        { 
            key: "notes", 
            label: "Notes/Comments (optional)" 
        }
    ],
    rules: [
        {
            label: "Mix ID",
            keySource: "mixId",
            key: "mixId",
            required: true,
        },
        {
            label: "Volume (m3)",
            keySource: "volume (m3)",
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
            header: "Mix ID",
            width: "20%",
            key: "mixId",
            editable: false,
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
            width: "48%",
            key: "notes",
            editable: true,
            editorType: "text",
        },
        {
            header: "",
            width: "6%",
            key: "actions",
        }

    ],
});