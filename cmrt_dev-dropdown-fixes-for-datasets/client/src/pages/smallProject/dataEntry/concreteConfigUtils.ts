import { asTableConfigRecord, pickTableLabel } from "./tableConfigUtils";

export function normalizeConcreteMixType(value: unknown): string {
  const label = pickTableLabel(value);
  if (label === "READY_MIX") return "Ready-mix";
  if (label === "PRECAST") return "Precast";
  return label;
}

export function parseConcreteStrengthMpa(value: unknown): number | null {
  const raw = pickTableLabel(value);
  const number = Number(raw.replace(/[^0-9.]/g, ""));
  return Number.isFinite(number) ? number : null;
}

export function extractConcreteEmissions(response: unknown): number | null {
  const result = asTableConfigRecord(response);
  const nested = asTableConfigRecord(result.data);
  const value = result.total_emissions_tco2e
    ?? result.emissions_tco2e
    ?? nested.total_emissions_tco2e
    ?? nested.emissions_tco2e
    ?? null;
  if (value === "-" || value === "" || value == null || !Number.isFinite(Number(value))) return null;
  return Number(value);
}
