export const CONCRETE_STRENGTHS = [5, 10, 15, 20, 25, 32, 40, 50, 65, 80, 100];

export const MIX_TYPE_OPTIONS = [
  { label: "Ready-mix", value: "READY_MIX" },
  { label: "Precast", value: "PRECAST" },
];

export interface SimplifiedRow {
  id: string;
  mixType: string;
  strengthMpa: string;
  scmPct: number | null;
  volumeM3: number | null;
  notes: string;
  emissions_tco2e: number;
}

export interface MixRow {
  id: string;
  mixId: string;
  mixType: string;
  strengthMpa: string;
  volumeM3: number | null;
  notes: string;
  expanded: boolean;
}

export interface MaterialRow {
  id: string;
  materialName: string;
  quantityKgM3: number | null;
  carbonFactor: number | null;
}

export interface EpdRow {
  id: string;
  mixId: string;
  gwpA1A3: number | null;
  volumeM3: number | null;
  notes: string;
  emissions_tco2e: number;
}

export interface ConcreteRegisterSnapshot {
  simplifiedRows: SimplifiedRow[];
  mixRows: MixRow[];
  materialsMap: Record<string, MaterialRow[]>;
  epdRows: EpdRow[];
}
