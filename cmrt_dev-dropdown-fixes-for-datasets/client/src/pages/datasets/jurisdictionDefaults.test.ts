import { describe, expect, it } from 'vitest';
import { withDefaultJurisdiction, withJurisdictionBackfill } from './jurisdictionDefaults';

describe('withDefaultJurisdiction', () => {
  it('fills an omitted jurisdiction on a new scoped row', () => {
    expect(withDefaultJurisdiction({ name: 'factor' }, 'jurisdiction-1')).toEqual({
      name: 'factor',
      jurisdiction_id: 'jurisdiction-1',
    });
  });

  it('preserves an explicitly supplied jurisdiction', () => {
    const payload = { jurisdiction_id: 'chosen-jurisdiction' };
    expect(withDefaultJurisdiction(payload, 'scope-jurisdiction')).toBe(payload);
  });

  it('leaves the jurisdiction empty when the scope has no default', () => {
    expect(withDefaultJurisdiction({ jurisdiction_id: null }, null)).toEqual({ jurisdiction_id: null });
  });
});

describe('withJurisdictionBackfill', () => {
  it('fills legacy rows from the scope only when the stored jurisdiction is missing', () => {
    expect(withJurisdictionBackfill({ value: 3, jurisdiction_id: null }, null, 'scope-jurisdiction')).toEqual({
      value: 3,
      jurisdiction_id: 'scope-jurisdiction',
    });
  });

  it('preserves the row jurisdiction if an edit omits it', () => {
    expect(withJurisdictionBackfill({ value: 3, jurisdiction_id: null }, 'existing-jurisdiction', 'scope-jurisdiction'))
      .toEqual({ value: 3, jurisdiction_id: 'existing-jurisdiction' });
  });

  it('preserves a jurisdiction explicitly chosen during the edit', () => {
    expect(withJurisdictionBackfill({ jurisdiction_id: 'chosen-jurisdiction' }, 'existing-jurisdiction', 'scope-jurisdiction'))
      .toEqual({ jurisdiction_id: 'chosen-jurisdiction' });
  });

  it('does not change unscoped rows when no default exists', () => {
    expect(withJurisdictionBackfill({ jurisdiction_id: null }, null, null)).toEqual({ jurisdiction_id: null });
  });
});
