import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { InlineSelect } from './TablePrimitives';

describe('InlineSelect option ordering', () => {
  it('sorts named dataset options alphabetically without changing values', () => {
    render(<InlineSelect value="z" onChange={() => undefined} options={[
      { id: 'z', name: 'Zinc' }, { id: 'a', name: 'asphalt' },
    ]} />);
    const select = screen.getByRole('combobox');
    expect(Array.from(select.querySelectorAll('option')).map(option => option.textContent))
      .toEqual(['asphalt', 'Zinc']);
    expect((select as HTMLSelectElement).value).toBe('z');
  });
});
