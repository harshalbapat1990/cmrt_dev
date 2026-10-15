import type { EpdRow, MaterialRow, MixRow } from "./concreteRegisterTypes";

/** Returns the weighted material carbon intensity, or null until at least one
 * material has both required values. This mirrors the register's current rules.
 */
export function getCarbonIntensity(materials: MaterialRow[] | undefined): number | null {
  if (!materials?.length) return null;
  return materials.reduce<number | null>((total, material) => {
    if (material.quantityKgM3 === null || material.carbonFactor === null) return total;
    return (total ?? 0) + material.quantityKgM3 * material.carbonFactor;
  }, null);
}

export function getMixEmissions(row: MixRow, materials: MaterialRow[] | undefined): number | null {
  const intensity = getCarbonIntensity(materials);
  if (intensity === null || row.volumeM3 === null) return null;
  return (row.volumeM3 * intensity) / 1000;
}

export function getEpdEmissions(row: Pick<EpdRow, "gwpA1A3" | "volumeM3">): number | null {
  if (row.gwpA1A3 === null || row.volumeM3 === null) return null;
  return (row.volumeM3 * row.gwpA1A3) / 1000;
}
