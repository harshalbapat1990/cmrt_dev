import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import MultiSelectDropdown from './MultiSelectDropDown';

describe('MultiSelectDropdown option ordering', () => {
  it('sorts named choices by default and allows semantic supplied order', () => {
    const options = [{ label: 'Zulu', value: 'z' }, { label: 'Alpha', value: 'a' }];
    const { rerender } = render(
      <MultiSelectDropdown options={options} selected={[]} onChange={vi.fn()} label="Choices" />,
    );
    fireEvent.click(screen.getByRole('combobox', { name: 'Choices' }));
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent?.trim()))
      .toEqual(['Alpha', 'Zulu']);

    rerender(
      <MultiSelectDropdown options={options} selected={[]} onChange={vi.fn()} label="Choices" optionOrder="provided" />,
    );
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent?.trim()))
      .toEqual(['Zulu', 'Alpha']);
  });
});
