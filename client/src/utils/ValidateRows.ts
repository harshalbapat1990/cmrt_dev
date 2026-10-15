export type ValidationRow = Record<string, unknown>;
export type LookupResult = object;

type LookupFetch = {
  bivarianceHack(context?: { row?: ValidationRow }): Promise<LookupResult[]>;
}["bivarianceHack"];

export function normalizeValidationRules(rules: FieldRule[]): FieldRule[] {
  return rules.map((rule) => {
    const lookup = rule.lookup;
    if (!lookup?.fetch) return rule;
    return {
      ...rule,
      lookup: {
        ...lookup,
        fetch: async (ctx?: { row?: ValidationRow }) => {
          const result = await lookup.fetch(ctx);
          return Array.isArray(result) ? result : [];
        },
      },
    };
  });
}

export type FieldRule = {
  label: string;
  key: string;
  required?: boolean;
  lookup?: {
    fetch: LookupFetch;
    labelField?: string;
    idField?: string;
  };
  number?: boolean;
  options?: Array<string | { label: string; value: string }>;
  keySource?: string;
};

export async function validateRows(
  parsedRows: ValidationRow[],
  rules: FieldRule[]
) {
  const errors: string[] = [];
  const validRows: ValidationRow[] = [];

  for (let rowIndex = 0; rowIndex < parsedRows.length; rowIndex++) {
    const row = parsedRows[rowIndex];
    const out: ValidationRow = {};
    const rowNum = rowIndex + 2;

    for (const rule of rules) {
      const sourceKey = rule.keySource || rule.key.replace(/_id$/, "");
      const rawVal = String(row[sourceKey] ?? "").trim();

      // Required validation
      if (rule.required && !rawVal) {
        errors.push(`Row ${rowNum}: Missing "${rule.label}"`);
        continue;
      }

      // Skip empty optional fields
      if (!rawVal) {
        continue;
      }

      // Options check
      if (rule.options && !rule.options.some((option) =>
        (typeof option === "string" ? option : option.value) === rawVal
      )) {
        errors.push(`Row ${rowNum}: Invalid "${rule.label}" → "${rawVal}"`);
        continue;
      }

      // Numeric check
      if (rule.number) {
        const n = Number(rawVal.replace(/,/g, ""));
        if (!Number.isFinite(n)) {
          errors.push(`Row ${rowNum}: "${rule.label}" must be numeric`);
          continue;
        }
        out[rule.key] = n;
        continue;
      }

      // Lookup validation with row context for dependencies
      if (rule.lookup) {
        try {
          const list = await rule.lookup.fetch({ row: out }); // Pass current row progress
          const map = new Map<string, LookupResult>();
          
          
for (const item of list) {
      const labelField = rule.lookup.labelField ?? "label";

      const record = item as Record<string, unknown>;
      const label = String(record[labelField] ?? "").toLowerCase();
      if (label) {
        map.set(label, record);
      }
    }

    const hit = map.get(rawVal.toLowerCase());

    if (!hit) {
      errors.push(`Row ${rowNum}: Unknown "${rule.label}" → "${rawVal}"`);
      continue;
    }

    const labelField = rule.lookup.labelField ?? "label";
    const idField = rule.lookup.idField ?? "value";

    const hitRecord = hit as Record<string, unknown>;
    out[rule.key] = hitRecord[idField];
    out[sourceKey] = hitRecord[labelField];

          out[`${rule.key}Name`] = hitRecord[labelField];
        } catch (error) {
          errors.push(`Row ${rowNum}: Error validating "${rule.label}"`);
        }
        continue;
      }

      // Assign normal text
      out[rule.key] = rawVal;
    }

    validRows.push(out);
  }

  return { errors, validRows };
}
