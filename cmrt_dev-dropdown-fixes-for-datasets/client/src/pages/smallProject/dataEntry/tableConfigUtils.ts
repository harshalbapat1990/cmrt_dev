export interface TableLookupOption {
  label: string;
  value: string | number;
}

export function asTableConfigRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null
    ? value as Record<string, unknown>
    : {};
}

export function mapTableLookupOptions(
  values: unknown[],
  labelField = "name",
  valueField = "id",
): TableLookupOption[] {
  return values.flatMap((value) => {
    const record = asTableConfigRecord(value);
    const label = record[labelField];
    const optionValue = record[valueField];
    if ((typeof label !== "string" && typeof label !== "number") ||
      (typeof optionValue !== "string" && typeof optionValue !== "number")) {
      return [];
    }
    return [{ label: String(label), value: optionValue }];
  });
}

export function pickTableLabel(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string" || typeof value === "number") return String(value);
  const record = asTableConfigRecord(value);
  return pickTableLabel(record.label ?? record.name ?? record.value);
}
