export type DatasetCreatePayload = Record<string, unknown>;

/** Applies a scope default only when a new jurisdiction-aware row has no value. */
export function withDefaultJurisdiction<T extends DatasetCreatePayload>(
  payload: T,
  defaultJurisdictionId: string | null,
): T {
  const existing = payload.jurisdiction_id;
  if (existing != null && existing !== '') return payload;
  if (!defaultJurisdictionId) return payload;
  return { ...payload, jurisdiction_id: defaultJurisdictionId };
}

/**
 * Preserve a row's current jurisdiction on edits and backfill only legacy rows
 * whose jurisdiction is missing. An explicit jurisdiction in the edit payload
 * still takes precedence.
 */
export function withJurisdictionBackfill<T extends DatasetCreatePayload>(
  payload: T,
  existingJurisdictionId: string | null | undefined,
  defaultJurisdictionId: string | null,
): T {
  const requested = payload.jurisdiction_id;
  if (requested != null && requested !== '') return payload;
  const jurisdictionId = existingJurisdictionId || defaultJurisdictionId;
  if (!jurisdictionId) return payload;
  return { ...payload, jurisdiction_id: jurisdictionId };
}
