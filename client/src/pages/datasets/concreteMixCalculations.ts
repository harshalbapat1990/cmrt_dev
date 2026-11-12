import {
  CONCRETE_MIX_STRENGTHS,
  type ConcreteMixAssumption,
  type ConcreteMixDesignRow,
  type ConcreteMixStrengthField,
} from "./types";

export const CALCULATED_CONCRETE_COMPONENT_CODES = [
  "general_purpose_cement",
  "fly_ash",
  "ggbf_slag",
] as const;

export type CalculatedConcreteComponentCode = typeof CALCULATED_CONCRETE_COMPONENT_CODES[number];

/** Canonical component rows and order shared by the editor and its CSV export. */
export const CONCRETE_MIX_COMPONENTS = [
  { code: "total_cementitious_content", label: "Total cementitious content", kind: "input" },
  { code: "general_purpose_cement", label: "General purpose cement", kind: "calc", calc: "general_purpose_cement" },
  { code: "fly_ash", label: "Fly ash", kind: "calc", calc: "fly_ash" },
  { code: "ggbf_slag", label: "GGBF slag", kind: "calc", calc: "ggbf_slag" },
  { code: "silica_fume", label: "Silica Fume", kind: "input" },
  { code: "fine_aggregates", label: "Fine Aggregates", kind: "input" },
  { code: "coarse_aggregates", label: "Coarse Aggregates", kind: "input" },
  { code: "recycled_aggregates", label: "Recycled Aggregates", kind: "input" },
  { code: "manufactured_sand", label: "Manufactured sand", kind: "input" },
  { code: "mains_water", label: "Mains Water", kind: "input" },
  { code: "onsite_recycled_water", label: "Onsite Recycled / Captured Water", kind: "input" },
  { code: "admixture", label: "Admixture", kind: "input" },
] as const;

export const normalizeConcreteMixComponentCode = (code: string): string => code.trim().toLowerCase();

/** Select one stable row per logical component, preferring its canonical code. */
export function deduplicateConcreteMixRows(rows: ConcreteMixDesignRow[]): ConcreteMixDesignRow[] {
  const byCode = new Map<string, ConcreteMixDesignRow>();
  for (const row of rows) {
    const code = normalizeConcreteMixComponentCode(row.component_code);
    const current = byCode.get(code);
    if (!current || row.component_code === code && current.component_code !== code) {
      byCode.set(code, row);
    }
  }
  return [...byCode.values()];
}
export type CalculatedConcreteValues = Record<
  CalculatedConcreteComponentCode,
  Partial<Record<ConcreteMixStrengthField, number | null>>
>;

const STRENGTH_FIELDS: ReadonlyArray<{
  strength: typeof CONCRETE_MIX_STRENGTHS[number];
  field: ConcreteMixStrengthField;
}> = [
  { strength: 20, field: "strength_20_kg_m3" },
  { strength: 25, field: "strength_25_kg_m3" },
  { strength: 32, field: "strength_32_kg_m3" },
  { strength: 40, field: "strength_40_kg_m3" },
  { strength: 50, field: "strength_50_kg_m3" },
  { strength: 65, field: "strength_65_kg_m3" },
  { strength: 80, field: "strength_80_kg_m3" },
  { strength: 100, field: "strength_100_kg_m3" },
];

const toNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number.parseFloat(String(value));
  return Number.isFinite(parsed) ? parsed : null;
};

/** Calculate the three mix components using the same assumptions shown in the editor. */
export function calculateConcreteMixComponents(
  assumptions: ConcreteMixAssumption | null,
  totalRow: ConcreteMixDesignRow | undefined,
): CalculatedConcreteValues {
  const values: CalculatedConcreteValues = {
    general_purpose_cement: {},
    fly_ash: {},
    ggbf_slag: {},
  };
  const bauScm = toNumber(assumptions?.bau_scm_content_pct);
  const maxFlyAsh = toNumber(assumptions?.default_max_fly_ash_pct);

  for (const { field } of STRENGTH_FIELDS) {
    const total = toNumber(totalRow?.[field]);
    if (bauScm === null || maxFlyAsh === null || total === null) {
      values.general_purpose_cement[field] = null;
      values.fly_ash[field] = null;
      values.ggbf_slag[field] = null;
      continue;
    }

    values.general_purpose_cement[field] = (1 - bauScm) * total;
    values.fly_ash[field] = Math.min(bauScm, maxFlyAsh) * total;
    values.ggbf_slag[field] = Math.max(bauScm - maxFlyAsh, 0) * total;
  }

  return values;
}

/** Prepare export rows, overriding stale stored calculated cells with live values. */
export function prepareConcreteMixCsvRows(
  rows: ConcreteMixDesignRow[],
  assumptions: ConcreteMixAssumption | null,
): Array<Pick<ConcreteMixDesignRow, "component_label" | ConcreteMixStrengthField>> {
  const uniqueRows = deduplicateConcreteMixRows(rows);
  const byCode = new Map(
    uniqueRows.map(row => [normalizeConcreteMixComponentCode(row.component_code), row]),
  );
  const totalRow = byCode.get("total_cementitious_content");
  const calculated = calculateConcreteMixComponents(assumptions, totalRow);

  return CONCRETE_MIX_COMPONENTS.map(component => {
    const row = byCode.get(component.code);
    const strengths = Object.fromEntries(STRENGTH_FIELDS.map(({ field }) => {
      if (component.kind === "calc" && component.calc) {
        return [field, calculated[component.calc][field] ?? null];
      }
      return [field, row?.[field] ?? null];
    })) as Record<ConcreteMixStrengthField, string | number | null>;

    return {
      component_label: component.label,
      ...strengths,
    };
  });
}

export function concreteMixStrengthFields(): readonly ConcreteMixStrengthField[] {
  return STRENGTH_FIELDS.map(({ field }) => field);
}
