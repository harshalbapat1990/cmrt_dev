import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SelectListbox } from './Select';

describe('SelectListbox option ordering', () => {
  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', class {
      observe() {}
      disconnect() {}
      unobserve() {}
    });
  });

  it('shows named choices alphabetically by default', () => {
    const onChange = vi.fn();
    render(<SelectListbox value="" onChange={onChange} options={[
      { label: 'Zulu', value: 'z' }, { label: 'alpha', value: 'a' }, { label: 'Item 10', value: '10' }, { label: 'Item 2', value: '2' },
    ]} />);

    fireEvent.focus(screen.getByRole('combobox'));
    const options = within(screen.getByRole('listbox')).getAllByRole('option');
    expect(options.map(option => option.textContent?.trim())).toEqual(['alpha', 'Item 2', 'Item 10', 'Zulu']);
    fireEvent.click(within(screen.getByRole('listbox')).getByText('Item 2'));
    expect(onChange).toHaveBeenCalledWith('2');
  });

  it('retains a configured semantic order', () => {
    render(<SelectListbox value="" onChange={vi.fn()} optionOrder="provided" options={[
      { label: 'Construction', value: 'construction' }, { label: 'Design', value: 'design' },
    ]} />);

    fireEvent.focus(screen.getByRole('combobox'));
    const options = within(screen.getByRole('listbox')).getAllByRole('option');
    expect(options.map(option => option.textContent?.trim())).toEqual(['Construction', 'Design']);
  });
});
