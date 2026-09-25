import type { WasteRateRow, InlineEditContext } from '../types';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

export default function WasteRateTable({ rows, editCtx }: { rows: WasteRateRow[]; editCtx?: InlineEditContext }) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (row: WasteRateRow) => {
    if (!ec) return;
    ec.onStartEdit(row.id, {
      jurisdiction_id: row.jurisdiction_id,
      material_id: row.material_id,
      waste_treatment_id: row.waste_treatment_id,
      applicable_lifecycle_module_code: row.applicable_lifecycle_module_code ?? '',
      basis: row.basis,
      rate: row.rate,
      effective_from: row.effective_from ?? '',
      effective_to: row.effective_to ?? '',
      notes: row.notes ?? '',
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Jurisdiction</TH>
          <TH>Material</TH>
          <TH>Treatment</TH>
          <TH>Lifecycle Module</TH>
          <TH>Basis</TH>
          <TH right>Rate</TH>
          <TH>Effective From</TH>
          <TH>Effective To</TH>
          <TH>Notes</TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {ec?.adding && (
          <tr className="bg-blue-50">
            <TD><InlineSelect value={ec.addDraft.jurisdiction_id ?? ''} options={ec.jurOpts} onChange={v => ec.onAddField('jurisdiction_id', v)} placeholder="— jurisdiction —" /></TD>
            <TD><InlineSelect value={ec.addDraft.material_id ?? ''} options={ec.matOpts} onChange={v => ec.onAddField('material_id', v)} placeholder="— material —" /></TD>
            <TD><InlineSelect value={ec.addDraft.waste_treatment_id ?? ''} options={ec.wtOpts} onChange={v => ec.onAddField('waste_treatment_id', v)} placeholder="— treatment —" /></TD>
            <TD><InlineInput value={ec.addDraft.applicable_lifecycle_module_code ?? ''} onChange={v => ec.onAddField('applicable_lifecycle_module_code', v)} /></TD>
            <TD><InlineInput value={ec.addDraft.basis ?? ''} onChange={v => ec.onAddField('basis', v)} placeholder="Required" /></TD>
            <TD right><InlineInput value={ec.addDraft.rate ?? ''} onChange={v => ec.onAddField('rate', v)} type="number" placeholder="0.0" /></TD>
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
                <TD><InlineSelect value={ec.editDraft.jurisdiction_id ?? ''} options={ec.jurOpts} onChange={v => ec.onEditField('jurisdiction_id', v)} /></TD>
                <TD><InlineSelect value={ec.editDraft.material_id ?? ''} options={ec.matOpts} onChange={v => ec.onEditField('material_id', v)} /></TD>
                <TD><InlineSelect value={ec.editDraft.waste_treatment_id ?? ''} options={ec.wtOpts} onChange={v => ec.onEditField('waste_treatment_id', v)} /></TD>
                <TD><InlineInput value={ec.editDraft.applicable_lifecycle_module_code ?? ''} onChange={v => ec.onEditField('applicable_lifecycle_module_code', v)} /></TD>
                <TD><InlineInput value={ec.editDraft.basis ?? ''} onChange={v => ec.onEditField('basis', v)} /></TD>
                <TD right><InlineInput value={ec.editDraft.rate ?? ''} onChange={v => ec.onEditField('rate', v)} type="number" /></TD>
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
              <TD muted>{r.jurisdiction_name ?? r.jurisdiction_id}</TD>
              <TD muted>{r.material_name ?? r.material_id}</TD>
              <TD muted>{r.waste_treatment_name ?? r.waste_treatment_id}</TD>
              <TD muted>{r.applicable_lifecycle_module_code ?? '—'}</TD>
              <TD>{r.basis}</TD>
              <TD right>{r.rate}</TD>
              <TD>{r.effective_from ?? '—'}</TD>
              <TD>{r.effective_to ?? '—'}</TD>
              <TD muted>{r.notes ?? ''}</TD>
              {isSA && (
                <TD>
                  {!ec?.editingId && !ec?.adding && ec?.onDelete && (
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
