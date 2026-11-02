/** Shared editable road user row used by small and multi-year large projects. */
export interface RoadUserRow {
  id: string;
  vehicleType: string;
  vkt: string;
  vht: string;
  avgSpeed: string;
  lastEdited: "vht" | "avgSpeed" | null;
  notes: string;
}

export interface RoadParams {
  ev_uptake_scenario: string;
  roughness: string;
  gradient: string;
  curvature: string;
}

export interface RoadUserYearData {
  params: RoadParams;
  rows: RoadUserRow[];
}
