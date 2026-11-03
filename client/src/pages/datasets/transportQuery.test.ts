import { describe, expect, it } from 'vitest';
import { buildTransportQueryParams } from './transportQuery';

describe('buildTransportQueryParams', () => {
  it('loads the selected revision without an effective-date filter', () => {
    const params = buildTransportQueryParams('revision-123');

    expect(params.get('dataset_revision_id')).toBe('revision-123');
    expect(params.get('limit')).toBe('5000');
    expect(params.get('skip')).toBe('0');
    expect(params.has('as_of_date')).toBe(false);
  });
});
