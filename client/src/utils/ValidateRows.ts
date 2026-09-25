export function normalizeValidationRules(rules: any[]): any[] {
  return rules.map((r: any) =>
    r?.lookup?.fetch
      ? {
          ...r,
          lookup: {
            ...r.lookup,
            fetch: async (ctx?: { row?: any }) => {
              const res = await r.lookup.fetch(ctx);
              return Array.isArray(res) ? res : [];
            },
          },
        }
      : r,
  );
}

export type FieldRule = {
  label: string;
  key: string;
  required?: boolean;
  lookup?: {
    fetch: (ctx?: { row?: any }) => Promise<any[]>;
    labelField: string;
    idField: string;
  };
  number?: boolean;
  options?: string[];
  keySource?: string;
};

export async function validateRows(
  parsedRows: any[],
  rules: FieldRule[]
) {
  const errors: string[] = [];
  const validRows: any[] = [];

  for (let rowIndex = 0; rowIndex < parsedRows.length; rowIndex++) {
    const row = parsedRows[rowIndex];
    const out: any = {};
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
      if (rule.options && !rule.options.includes(rawVal)) {
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
          const map = new Map<string, any>();
          
          
for (const item of list) {
      const labelField = rule.lookup.labelField ?? "label";

      const label = String(item[labelField] ?? "").toLowerCase();
      if (label) {
        map.set(label, item);
      }
    }

    const hit = map.get(rawVal.toLowerCase());

    if (!hit) {
      errors.push(`Row ${rowNum}: Unknown "${rule.label}" → "${rawVal}"`);
      continue;
    }

    const labelField = rule.lookup.labelField ?? "label";
    const idField = rule.lookup.idField ?? "value";

    out[rule.key] = hit[idField];
    out[sourceKey] = hit[labelField];

          out[`${rule.key}Name`] = hit[rule.lookup.labelField];
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