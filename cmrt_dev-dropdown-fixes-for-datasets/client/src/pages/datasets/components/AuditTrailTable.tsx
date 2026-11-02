import type { AuditLogRow } from '../types';
import { TH, TD } from './TablePrimitives';

export default function AuditTrailTable({ rows }: { rows: AuditLogRow[] }) {
  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Timestamp</TH>
          <TH>Entity Type</TH>
          <TH>Action</TH>
          <TH>Field</TH>
          <TH>Old Value</TH>
          <TH>New Value</TH>
          <TH>Performed By</TH>
        </tr>
      </thead>
      <tbody>
        {rows.map(r => (
          <tr key={r.id} className="even:bg-neutral-98 hover:bg-blue-50">
            <TD>{r.performed_at ? new Date(r.performed_at).toLocaleString() : '—'}</TD>
            <TD muted>{r.entity_name ?? r.entity_type}</TD>
            <TD>
              <span className="rounded bg-neutral-200 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide">
                {r.action}
              </span>
            </TD>
            <TD muted>{r.field_name ?? '—'}</TD>
            <TD muted>{r.old_value ?? '—'}</TD>
            <TD muted>{r.new_value ?? '—'}</TD>
            <TD muted>{r.performed_by_email ?? r.performed_by ?? '—'}</TD>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
