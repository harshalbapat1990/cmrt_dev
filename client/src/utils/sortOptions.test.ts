import { describe, expect, it } from 'vitest';
import { compareOptionLabels, sortNamedOptions, sortOptionsByLabel } from './sortOptions';

describe('dropdown option ordering', () => {
  it('compares case-insensitively with locale-aware numeric labels', () => {
    expect(['Type 10', 'alpha', 'Type 2', 'B. item'].sort(compareOptionLabels))
      .toEqual(['alpha', 'B. item', 'Type 2', 'Type 10']);
  });

  it('returns sorted copies and does not mutate caller options', () => {
    const options = [{ label: 'zebra', value: 'z' }, { label: 'Apple', value: 'a' }];
    expect(sortOptionsByLabel(options)).toEqual([
      { label: 'Apple', value: 'a' }, { label: 'zebra', value: 'z' },
    ]);
    expect(options[0].value).toBe('z');
  });

  it('sorts named options using their displayed names', () => {
    expect(sortNamedOptions([{ id: 'b', name: 'Beta' }, { id: 'a', name: 'alpha' }]))
      .toEqual([{ id: 'a', name: 'alpha' }, { id: 'b', name: 'Beta' }]);
  });
});
