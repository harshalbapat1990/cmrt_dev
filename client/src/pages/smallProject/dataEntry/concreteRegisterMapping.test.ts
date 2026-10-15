import { describe, expect, it } from "vitest";
import type { ConcreteMixOut } from "@/services/ConcreteRegister.service";
import { mapConcreteMixes } from "./concreteRegisterMapping";

const mix = (overrides: Partial<ConcreteMixOut>): ConcreteMixOut => ({
  id: "mix-id",
  project_id: "project-id",
  method: "simplified",
  mix_type: null,
  strength_mpa: null,
  scm_pct: null,
  mix_id_label: null,
  gwp_a1a3: null,
  volume_m3: null,
  emissions_tco2e: 0,
  notes: null,
  sort_order: 0,
  materials: [],
  created_on: null,
  updated_on: null,
  ...overrides,
});

describe("mapConcreteMixes", () => {
  it("maps each API method to the matching register collection", () => {
    const result = mapConcreteMixes([
      mix({ id: "simple", method: "simplified", strength_mpa: 25, scm_pct: 10, volume_m3: 2 }),
      mix({
        id: "design", method: "mix_design", mix_id_label: "M1", materials: [{
          id: "material", concrete_mix_id: "design", material_name: "Cement",
          quantity_kg_m3: 300, carbon_factor: 0.4, sort_order: 0,
          created_on: null, updated_on: null,
        }],
      }),
      mix({ id: "epd", method: "epd_pcf", mix_id_label: "E1", gwp_a1a3: 400, volume_m3: 3 }),
    ]);

    expect(result.simplifiedRows).toHaveLength(1);
    expect(result.simplifiedRows[0]).toMatchObject({ id: "simple", strengthMpa: "25", scmPct: 10, volumeM3: 2 });
    expect(result.mixRows[0]).toMatchObject({ id: "design", mixId: "M1", expanded: false });
    expect(result.materialsMap.design[0]).toMatchObject({ materialName: "Cement", quantityKgM3: 300, carbonFactor: 0.4 });
    expect(result.epdRows[0]).toMatchObject({ id: "epd", mixId: "E1", gwpA1A3: 400, volumeM3: 3 });
  });

  it("applies the existing defaults for missing API values", () => {
    const result = mapConcreteMixes([mix({})]);
    expect(result.simplifiedRows[0]).toMatchObject({
      mixType: "READY_MIX",
      strengthMpa: "5",
      scmPct: null,
      volumeM3: null,
      notes: "",
    });
  });
});
