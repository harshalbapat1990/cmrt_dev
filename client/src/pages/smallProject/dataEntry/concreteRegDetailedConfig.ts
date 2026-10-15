import EmissionCalculationsService from "@/services/EmissionCalculations.service";
import type { DataEntryRow } from "./dataEntryTypes";
import { asTableConfigRecord } from "./tableConfigUtils";
import { extractConcreteEmissions, normalizeConcreteMixType, parseConcreteStrengthMpa } from "./concreteConfigUtils";

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
        buildPayload: (row: DataEntryRow, ctx: { project_id?: string }) => {
            const method = row.method;
            const project_id = ctx.project_id;
            const mix_id_label = row.mixId;
            const mix_type = normalizeConcreteMixType(row.mixType ?? row.mix_type);
            const strength_mpa = parseConcreteStrengthMpa(row.strength ?? row.strength_mpa);
            const volume_m3 = Number(row.volume ?? row.volume_m3);

            if (!project_id || !method || !mix_id_label || Number.isNaN(volume_m3)) {
                return null;
            }

            if (method === "mix_design") {
                const materials = (Array.isArray(row.materials) ? row.materials : [])
                    .map(asTableConfigRecord)
                    .filter((material) => material.quantityKgM3 != null || material.quantity_kg_m3 != null)
                    .map((material) => ({
                        material_name: material.materialName ?? material.material_name,
                        quantity_kg_m3: Number(material.quantityKgM3 ?? material.quantity_kg_m3),
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
        calculate: async (payload: Record<string, unknown>) => {
            const request = asTableConfigRecord(payload.request);
            if (payload.method === "mix_design") {
                return EmissionCalculationsService.concreteRegNewMixCalculations(request);
            }
            if (payload.method === "epd_pcf") {
                return EmissionCalculationsService.concreteRegNewMixEPDCalculations(request);
            }
            return null;
        },

        mapResultToRow: (apiRes: unknown) => {
            const result = asTableConfigRecord(apiRes);
            const emissions = extractConcreteEmissions(apiRes);
            return {
                emissions_tco2e: emissions,
                gwp_a1a3_tco2e_m3: result.gwp_a1a3_tco2e_m3 ?? null,
                transport_a4_ef_tco2e_m3: result.transport_a4_ef_tco2e_m3 ?? null,
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
