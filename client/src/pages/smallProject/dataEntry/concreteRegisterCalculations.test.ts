import { describe, expect, it } from "vitest";
import { getCarbonIntensity, getEpdEmissions, getMixEmissions } from "./concreteRegisterCalculations";
import type { MaterialRow, MixRow } from "./concreteRegisterTypes";

const material = (quantityKgM3: number | null, carbonFactor: number | null): MaterialRow => ({
  id: crypto.randomUUID(), materialName: "cement", quantityKgM3, carbonFactor,
});

describe("concrete register calculations", () => {
  it("returns no intensity when materials are absent or incomplete", () => {
    expect(getCarbonIntensity(undefined)).toBeNull();
    expect(getCarbonIntensity([material(100, null)])).toBeNull();
    expect(getCarbonIntensity([material(100, 0.5), material(null, 0.2)])).toBe(50);
  });

  it("calculates mix emissions from material intensity and volume", () => {
    const mix: MixRow = { id: "mix", mixId: "M1", mixType: "READY_MIX", strengthMpa: "32", volumeM3: 2, notes: "", expanded: false };
    expect(getMixEmissions(mix, [material(100, 0.5)])).toBe(0.1);
    expect(getMixEmissions({ ...mix, volumeM3: null }, [material(100, 0.5)])).toBeNull();
  });

  it("calculates EPD emissions only when both inputs exist", () => {
    expect(getEpdEmissions({ gwpA1A3: 400, volumeM3: 2 })).toBe(0.8);
    expect(getEpdEmissions({ gwpA1A3: null, volumeM3: 2 })).toBeNull();
  });
});
