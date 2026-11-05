import { describe, expect, it } from "vitest";
import { CONCRETE_MIX_DESIGN_COLS } from "./csvColumns";
import type { ConcreteMixAssumption, ConcreteMixDesignRow, ConcreteMixStrengthField } from "./types";
import {
  calculateConcreteMixComponents,
  concreteMixStrengthFields,
  deduplicateConcreteMixRows,
  prepareConcreteMixCsvRows,
} from "./concreteMixCalculations";

const assumptions = (bau: string, maxFlyAsh: string): ConcreteMixAssumption => ({
  id: "assumption-1",
  dataset_revision_id: "revision-1",
  bau_scm_content_pct: bau,
  default_max_fly_ash_pct: maxFlyAsh,
  is_active: true,
});

const mixRow = (
  component_code: string,
  component_label: string,
  values: Partial<Record<ConcreteMixStrengthField, string | number | null>> = {},
): ConcreteMixDesignRow => ({
  id: component_code,
  dataset_revision_id: "revision-1",
  component_code,
  component_label,
  display_order: 1,
  strength_20_kg_m3: null,
  strength_25_kg_m3: null,
  strength_32_kg_m3: null,
  strength_40_kg_m3: null,
  strength_50_kg_m3: null,
  strength_65_kg_m3: null,
  strength_80_kg_m3: null,
  strength_100_kg_m3: null,
  is_active: true,
  ...values,
});

describe("concrete mix calculation and CSV preparation", () => {
  it("calculates every strength column for the reported 30% SCM assumption", () => {
    const total = mixRow("total_cementitious_content", "Total cementitious content", {
      strength_20_kg_m3: 300,
      strength_25_kg_m3: 350,
      strength_32_kg_m3: 400,
      strength_40_kg_m3: 450,
      strength_50_kg_m3: 500,
      strength_65_kg_m3: 550,
      strength_80_kg_m3: 600,
      strength_100_kg_m3: 650,
    });
    const values = calculateConcreteMixComponents(assumptions("0.30", "0.30"), total);

    for (const field of concreteMixStrengthFields()) {
      const cementitious = Number(total[field]);
      expect(values.general_purpose_cement[field]).toBeCloseTo(cementitious * 0.7);
      expect(values.fly_ash[field]).toBeCloseTo(cementitious * 0.3);
      expect(values.ggbf_slag[field]).toBe(0);
    }
  });

  it("caps fly ash and assigns the remaining SCM share to slag", () => {
    const total = mixRow("total_cementitious_content", "Total cementitious content", {
      strength_20_kg_m3: 400,
    });
    const values = calculateConcreteMixComponents(assumptions("0.30", "0.20"), total);

    expect(values.general_purpose_cement.strength_20_kg_m3).toBeCloseTo(280);
    expect(values.fly_ash.strength_20_kg_m3).toBeCloseTo(80);
    expect(values.ggbf_slag.strength_20_kg_m3).toBeCloseTo(40);
  });

  it("handles zero assumptions and missing total values distinctly", () => {
    const total = mixRow("total_cementitious_content", "Total cementitious content", {
      strength_20_kg_m3: 250,
      strength_25_kg_m3: null,
    });
    const values = calculateConcreteMixComponents(assumptions("0", "0"), total);

    expect(values.general_purpose_cement.strength_20_kg_m3).toBe(250);
    expect(values.fly_ash.strength_20_kg_m3).toBe(0);
    expect(values.ggbf_slag.strength_20_kg_m3).toBe(0);
    expect(values.general_purpose_cement.strength_25_kg_m3).toBeNull();
    expect(values.fly_ash.strength_25_kg_m3).toBeNull();
    expect(values.ggbf_slag.strength_25_kg_m3).toBeNull();
    expect(calculateConcreteMixComponents(assumptions("0.3", "0.2"), undefined).fly_ash.strength_20_kg_m3).toBeNull();
  });

  it("overrides stale calculated values in CSV rows and leaves input rows/order intact", () => {
    const total = mixRow("total_cementitious_content", "Total cementitious content", {
      strength_20_kg_m3: "500",
    });
    const cement = mixRow("general_purpose_cement", "General purpose cement", {
      strength_20_kg_m3: 0,
    });
    const flyAsh = mixRow("fly_ash", "Fly ash", { strength_20_kg_m3: 0 });
    const slag = mixRow("ggbf_slag", "GGBF slag", { strength_20_kg_m3: 0 });
    const input = mixRow("fine_aggregates", "Fine Aggregates", { strength_20_kg_m3: 123 });
    const rows = [total, cement, flyAsh, slag, input];

    const exported = prepareConcreteMixCsvRows(rows, assumptions("0.30", "0.20"));

    expect(exported.map(row => row.component_code)).toEqual(rows.map(row => row.component_code));
    expect(exported[0]).toBe(total);
    expect(exported[1].strength_20_kg_m3).toBeCloseTo(350);
    expect(exported[2].strength_20_kg_m3).toBeCloseTo(100);
    expect(exported[3].strength_20_kg_m3).toBeCloseTo(50);
    expect(exported[4]).toBe(input);
  });

  it("exports one canonical row when active data contains case or whitespace variants", () => {
    const total = mixRow("total_cementitious_content", "Total cementitious content", {
      strength_20_kg_m3: 500,
    });
    const canonicalFlyAsh = mixRow("fly_ash", "Fly ash", { strength_20_kg_m3: 0 });
    const variants = [
      total,
      mixRow(" FLY_ASH ", "Legacy Fly ash", { strength_20_kg_m3: 84 }),
      canonicalFlyAsh,
      mixRow("fine_aggregates", "Fine Aggregates", { strength_20_kg_m3: 900 }),
    ];

    const exported = prepareConcreteMixCsvRows(variants, assumptions("0.30", "0.20"));

    expect(exported.map(row => row.component_code)).toEqual([
      "total_cementitious_content",
      "fly_ash",
      "fine_aggregates",
    ]);
    expect(exported[1].strength_20_kg_m3).toBeCloseTo(100);
    expect(deduplicateConcreteMixRows(variants)).toHaveLength(3);
  });

  it("recalculates the next export when assumptions or total cementitious values change", () => {
    const total = mixRow("total_cementitious_content", "Total cementitious content", {
      strength_20_kg_m3: 500,
    });
    const staleCalculatedRows = [
      total,
      mixRow("general_purpose_cement", "General purpose cement", { strength_20_kg_m3: 0 }),
      mixRow("fly_ash", "Fly ash", { strength_20_kg_m3: 0 }),
      mixRow("ggbf_slag", "GGBF slag", { strength_20_kg_m3: 0 }),
    ];

    const firstExport = prepareConcreteMixCsvRows(staleCalculatedRows, assumptions("0.30", "0.20"));
    const afterAssumptionEdit = prepareConcreteMixCsvRows(staleCalculatedRows, assumptions("0.40", "0.20"));
    const afterTotalEdit = prepareConcreteMixCsvRows([
      { ...total, strength_20_kg_m3: 600 },
      ...staleCalculatedRows.slice(1),
    ], assumptions("0.40", "0.20"));

    expect(firstExport[2].strength_20_kg_m3).toBeCloseTo(100);
    expect(afterAssumptionEdit[2].strength_20_kg_m3).toBeCloseTo(100);
    expect(afterAssumptionEdit[3].strength_20_kg_m3).toBeCloseTo(100);
    expect(afterTotalEdit[1].strength_20_kg_m3).toBeCloseTo(360);
    expect(afterTotalEdit[2].strength_20_kg_m3).toBeCloseTo(120);
    expect(afterTotalEdit[3].strength_20_kg_m3).toBeCloseTo(120);
  });

  it("keeps the established CSV headers and strength-column order", () => {
    expect(CONCRETE_MIX_DESIGN_COLS.map(column => column.label)).toEqual([
      "Component",
      "20 MPa (kg/m3)",
      "25 MPa (kg/m3)",
      "32 MPa (kg/m3)",
      "40 MPa (kg/m3)",
      "50 MPa (kg/m3)",
      "65 MPa (kg/m3)",
      "80 MPa (kg/m3)",
      "100 MPa (kg/m3)",
    ]);
  });
});
