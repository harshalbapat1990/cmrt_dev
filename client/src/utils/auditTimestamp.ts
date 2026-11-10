const HAS_TIME_ZONE = /(Z|[+-]\d{2}:?\d{2})$/i;

/** Audit timestamps are stored as UTC-naive PostgreSQL timestamps. */
export function parseAuditTimestamp(value: string | null | undefined): Date | null {
  if (!value) return null;
  const normalized = HAS_TIME_ZONE.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatAuditTimestamp(value: string | null | undefined): string {
  const date = parseAuditTimestamp(value);
  if (!date) return value ?? "—";
  return new Intl.DateTimeFormat("en-AU", {
    timeZone: "Australia/Sydney",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(date);
}
