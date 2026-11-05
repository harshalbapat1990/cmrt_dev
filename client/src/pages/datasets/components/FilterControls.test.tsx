import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MultiSelect } from './FilterControls';

describe('dataset filter option ordering', () => {
  it('shows named filter choices alphabetically while returning the original value', () => {
    const onChange = vi.fn();
    render(<MultiSelect label="Category" options={['Zinc', 'asphalt', 'Concrete']} selected={[]} onChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: 'Category' }));

    const choices = screen.getAllByRole('checkbox').map((checkbox) =>
      checkbox.parentElement?.textContent?.trim(),
    );
    expect(choices).toEqual(['asphalt', 'Concrete', 'Zinc']);
    fireEvent.click(screen.getByRole('checkbox', { name: 'asphalt' }));
    expect(onChange).toHaveBeenCalledWith(['asphalt']);
  });
});
