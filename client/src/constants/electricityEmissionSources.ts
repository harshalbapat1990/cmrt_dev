export const ELECTRICITY_EMISSION_SOURCES = [
  "Grid Electricity",
  "Onsite Renewable Electricity",
  "Offsite Renewable Electricity",
] as const;

export type ElectricityEmissionSource = (typeof ELECTRICITY_EMISSION_SOURCES)[number];
