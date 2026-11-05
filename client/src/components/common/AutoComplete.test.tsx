import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import AsyncAutocomplete from './AutoComplete';

describe('AsyncAutocomplete option ordering', () => {
  it('shows loaded named suggestions alphabetically by default', async () => {
    const loadOptions = vi.fn().mockResolvedValue([
      { id: 'z', label: 'Zulu Area' }, { id: 'b', label: 'Beta' }, { id: 'a', label: 'Alpha' },
    ]);
    render(<AsyncAutocomplete value="a" onChange={vi.fn()} loadOptions={loadOptions} minLength={1} />);

    fireEvent.focus(screen.getByRole('combobox'));
    const listbox = await screen.findByRole('listbox');
    await waitFor(() => expect(within(listbox).getAllByRole('option')).toHaveLength(3));
    expect(within(listbox).getAllByRole('option').map(option => option.textContent?.trim()))
      .toEqual(['Alpha', 'Beta', 'Zulu Area']);
  });

  it('retains provider order when requested', async () => {
    const loadOptions = vi.fn().mockResolvedValue([
      { id: 'z', label: 'Zulu Area' }, { id: 'a', label: 'Alpha' },
    ]);
    render(<AsyncAutocomplete value="a" onChange={vi.fn()} loadOptions={loadOptions} minLength={1} optionOrder="provided" />);

    fireEvent.focus(screen.getByRole('combobox'));
    const listbox = await screen.findByRole('listbox');
    await waitFor(() => expect(within(listbox).getAllByRole('option')).toHaveLength(2));
    expect(within(listbox).getAllByRole('option').map(option => option.textContent?.trim()))
      .toEqual(['Zulu Area', 'Alpha']);
  });
});
