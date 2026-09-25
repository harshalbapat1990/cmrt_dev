import type { DirectSubstitutionRow } from '../types';
import { TH, TD } from './TablePrimitives';

interface Props {
  rows: DirectSubstitutionRow[];
}

function formatQty(v: string | number): string {
  if (v === '' || v == null) return '—';
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (!Number.isFinite(n)) return String(v);
  return String(n);
}

export default function DirectSubstitutionsTable({ rows }: Props) {
  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>User emissions source</TH>
          <TH>User unit</TH>
          <TH>BAU equivalent emission source</TH>
          <TH>BAU equivalent unit</TH>
          <TH right>BAU quantity per user unit</TH>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="even:bg-neutral-98 hover:bg-blue-50">
            <TD muted>{r.user_emissions_source || '—'}</TD>
            <TD>{r.user_unit || '—'}</TD>
            <TD muted>{r.bau_equivalent_emission_source || '—'}</TD>
            <TD>{r.bau_equivalent_unit || '—'}</TD>
            <TD right>{formatQty(r.bau_quantity_per_user_unit)}</TD>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
