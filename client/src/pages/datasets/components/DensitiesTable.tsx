import type { DensityRow, DensityEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: DensityRow[];
  editCtx?: DensityEditCtx;
}

export default function DensitiesTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: DensityRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      density: r.density ?? '',
      source: r.source ?? '',
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Category</TH>
          <TH>Sub-Category</TH>
          <TH>Emissions Source</TH>
          <TH>Unit</TH>
          <TH right>Density</TH>
          <TH>Source Note</TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          const isEditing = ec?.editingId === r.id;
          if (isEditing && ec) {
            return (
              <tr key={i} className="bg-amber-50" tabIndex={-1}
                onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveEdit(); }}
                onKeyDown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelEdit(); } else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveEdit(); } }}
              >
                <TD muted>{r.emissions_category?.name ?? '—'}</TD>
                <TD muted>{r.emissions_sub_category?.name ?? '—'}</TD>
                <TD muted>{r.emissions_source ?? '—'}</TD>
                <TD muted>{r.unit ? (r.unit.label ?? r.unit.code) : '—'}</TD>
                <TD right><InlineInput type="number" value={ec.editDraft.density ?? ''} onChange={v => ec.onEditField('density', v)} placeholder="Value" /></TD>
                <TD><InlineInput value={ec.editDraft.source ?? ''} onChange={v => ec.onEditField('source', v)} placeholder="Source" /></TD>
                <TD><SaveCancelButtons onSave={ec.onSaveEdit} onCancel={ec.onCancelEdit} saving={ec.saving} error={ec.saveError} /></TD>
              </tr>
            );
          }
          return (
            <tr key={i}
              className={`even:bg-neutral-98 hover:bg-blue-50 ${isSA && !ec?.editingId ? 'cursor-pointer' : ''}`}
              onDoubleClick={isSA && !ec?.editingId ? () => startEdit(r) : undefined}
            >
              <TD>{r.emissions_category?.name ?? '—'}</TD>
              <TD>{r.emissions_sub_category?.name ?? '—'}</TD>
              <TD>{r.emissions_source ?? '—'}</TD>
              <TD muted>{r.unit ? (r.unit.label ?? r.unit.code) : '—'}</TD>
              <TD right muted={r.density == null}>{r.density ?? '—'}</TD>
              <TD muted>{r.source ?? '—'}</TD>
              {isSA && (
                <TD>
                  {!ec?.editingId && ec?.onDelete && (
                    <button type="button" onClick={() => ec.onDelete!(r.id)} title="Delete row"
                      className="rounded p-0.5 cursor-pointer text-red-400 hover:text-red-600 hover:bg-red-50">
                      <span className="material-symbols-rounded text-[14px] leading-none">delete</span>
                    </button>
                  )}
                </TD>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}