import type { RecycledContentRow, InlineEditContext } from '../types';
import { TODAY, DEFAULT_EFFECTIVE_TO } from '../constants';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

export default function RecycledContentTable({ rows, editCtx }: { rows: RecycledContentRow[]; editCtx?: InlineEditContext }) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (row: RecycledContentRow) => {
    if (!ec) return;
    ec.onStartEdit(row.id, {
      material_id: row.material_id ?? '',
      recycled_from_material_id: row.recycled_from_material_id ?? '',
      percent: row.percent != null ? String(Math.round(parseFloat(row.percent) * 100)) : '',
      jurisdiction_id: row.jurisdiction_id ?? '',
      effective_from: row.effective_from ?? '',
      effective_to: row.effective_to ?? '',
      notes: row.notes ?? '',
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Material</TH>
          <TH right>Percent (%)</TH>
          <TH>Effective From</TH>
          <TH>Effective To</TH>
          <TH>Notes</TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {ec?.adding && (
          <tr className="bg-blue-50">
            <TD><InlineSelect value={ec.addDraft.material_id ?? ''} options={ec.matOpts} onChange={v => ec.onAddField('material_id', v)} placeholder="— material —" /></TD>
            <TD right><InlineInput value={ec.addDraft.percent ?? ''} onChange={v => ec.onAddField('percent', v)} type="number" placeholder="0–100" /></TD>
            <TD><InlineInput value={ec.addDraft.effective_from ?? ''} onChange={v => ec.onAddField('effective_from', v)} type="date" /></TD>
            <TD><InlineInput value={ec.addDraft.effective_to ?? ''} onChange={v => ec.onAddField('effective_to', v)} type="date" /></TD>
            <TD><InlineInput value={ec.addDraft.notes ?? ''} onChange={v => ec.onAddField('notes', v)} /></TD>
            <TD><SaveCancelButtons onSave={ec.onSaveAdd} onCancel={ec.onCancelAdd} saving={ec.saving} error={ec.saveError} /></TD>
          </tr>
        )}
        {rows.map(r => {
          const isEditing = ec?.editingId === r.id;
          if (isEditing && ec) {
            return (
              <tr key={r.id} className="bg-amber-50" tabIndex={-1}
                onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveEdit(); }}
                onKeyDown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelEdit(); } else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveEdit(); } }}
              >
                <TD><InlineSelect value={ec.editDraft.material_id ?? ''} options={ec.matOpts} onChange={v => ec.onEditField('material_id', v)} /></TD>
                <TD right><InlineInput value={ec.editDraft.percent ?? ''} onChange={v => ec.onEditField('percent', v)} type="number" /></TD>
                <TD><InlineInput value={ec.editDraft.effective_from ?? ''} onChange={v => ec.onEditField('effective_from', v)} type="date" /></TD>
                <TD><InlineInput value={ec.editDraft.effective_to ?? ''} onChange={v => ec.onEditField('effective_to', v)} type="date" /></TD>
                <TD><InlineInput value={ec.editDraft.notes ?? ''} onChange={v => ec.onEditField('notes', v)} /></TD>
                <TD><SaveCancelButtons onSave={ec.onSaveEdit} onCancel={ec.onCancelEdit} saving={ec.saving} error={ec.saveError} /></TD>
              </tr>
            );
          }
          return (
            <tr
              key={r.id}
              className={`even:bg-neutral-98 hover:bg-blue-50 ${isSA && !ec?.editingId && !ec?.adding ? 'cursor-pointer' : ''}`}
              onDoubleClick={isSA && !ec?.editingId && !ec?.adding ? () => startEdit(r) : undefined}
            >
              <TD>{r.material_name ?? r.material_id ?? '—'}</TD>
              <TD right>{r.percent != null ? `${(parseFloat(r.percent) * 100).toFixed(1)}` : '—'}</TD>
              <TD>{r.effective_from ?? TODAY}</TD>
              <TD>{r.effective_to ?? DEFAULT_EFFECTIVE_TO}</TD>
              <TD muted>{r.notes ?? ''}</TD>
              {isSA && (
                <TD>
                  {!ec?.editingId && !ec?.adding && ec?.onDelete && (
                    <button type="button" onClick={() => ec.onDelete!(r.id)} title="Delete row"
                      className="rounded p-0.5 text-red-400 cursor-pointer hover:text-red-600 hover:bg-red-50">
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
