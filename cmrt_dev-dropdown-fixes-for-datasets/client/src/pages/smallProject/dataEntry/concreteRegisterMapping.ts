import type { ConcreteMixOut } from "@/services/ConcreteRegister.service";
import { CONCRETE_STRENGTHS, MIX_TYPE_OPTIONS, type ConcreteRegisterSnapshot } from "./concreteRegisterTypes";

export function mapConcreteMixes(mixes: ConcreteMixOut[]): ConcreteRegisterSnapshot {
  const snapshot: ConcreteRegisterSnapshot = {
    simplifiedRows: [],
    mixRows: [],
    materialsMap: {},
    epdRows: [],
  };

  for (const mix of mixes) {
    if (mix.method === "simplified") {
      snapshot.simplifiedRows.push({
        id: mix.id,
        mixType: mix.mix_type ?? MIX_TYPE_OPTIONS[0].value,
        strengthMpa: mix.strength_mpa !== null ? String(mix.strength_mpa) : String(CONCRETE_STRENGTHS[0]),
        scmPct: mix.scm_pct !== null ? Number(mix.scm_pct) : null,
        volumeM3: mix.volume_m3 !== null ? Number(mix.volume_m3) : null,
        notes: mix.notes ?? "",
        emissions_tco2e: Number(mix.emissions_tco2e),
      });
    } else if (mix.method === "mix_design") {
      snapshot.mixRows.push({
        id: mix.id,
        mixId: mix.mix_id_label ?? "",
        mixType: mix.mix_type ?? MIX_TYPE_OPTIONS[0].value,
        strengthMpa: mix.strength_mpa !== null ? String(mix.strength_mpa) : String(CONCRETE_STRENGTHS[0]),
        volumeM3: mix.volume_m3 !== null ? Number(mix.volume_m3) : null,
        notes: mix.notes ?? "",
        expanded: false,
      });
      snapshot.materialsMap[mix.id] = mix.materials.map((material) => ({
        id: material.id,
        materialName: material.material_name,
        quantityKgM3: material.quantity_kg_m3 !== null ? Number(material.quantity_kg_m3) : null,
        carbonFactor: material.carbon_factor !== null ? Number(material.carbon_factor) : null,
      }));
    } else if (mix.method === "epd_pcf") {
      snapshot.epdRows.push({
        id: mix.id,
        mixId: mix.mix_id_label ?? "",
        gwpA1A3: mix.gwp_a1a3 !== null ? Number(mix.gwp_a1a3) : null,
        volumeM3: mix.volume_m3 !== null ? Number(mix.volume_m3) : null,
        notes: mix.notes ?? "",
        emissions_tco2e: Number(mix.emissions_tco2e),
      });
    }
  }
  return snapshot;
}
