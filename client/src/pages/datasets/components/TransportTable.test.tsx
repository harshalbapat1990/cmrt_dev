import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TransportTable from './TransportTable';
import { TRANSPORT_COLS } from '../csvColumns';
import type { TransportRow } from '../types';

const row: TransportRow = {
  id: 'transport-1',
  material_id: 'material-1',
  material_name: 'Concrete',
  emissions_category_id: null,
  emissions_category_name: null,
  jurisdiction_id: 'jurisdiction-1',
  jurisdiction_name: 'New South Wales',
  truck_distance: '10',
  truck_transport_mode: 'Truck',
  rail_distance: null,
  rail_transport_mode: null,
  sea_distance: null,
  sea_transport_mode: null,
  source: 'Dataset',
  grade_applicability: '3',
  effective_from: '2026-01-01',
  effective_to: null,
};

describe('TransportTable', () => {
  it('does not display effective date columns', () => {
    render(<TransportTable rows={[row]} />);

    expect(screen.getByText('Material / Category')).toBeTruthy();
    expect(screen.queryByText('Effective From')).toBeNull();
    expect(screen.queryByText('Effective To')).toBeNull();
  });

  it('omits effective date columns from transport exports', () => {
    expect(TRANSPORT_COLS.map(({ key }) => key)).not.toContain('effective_from');
    expect(TRANSPORT_COLS.map(({ key }) => key)).not.toContain('effective_to');
  });
});
