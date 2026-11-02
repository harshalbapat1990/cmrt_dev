import type { EnergyDensityConversionRow, EnergyDensityConversionEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: EnergyDensityConversionRow[];
  editCtx?: EnergyDensityConversionEditCtx;
}

export default function EnergyDensityConversionsTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: EnergyDensityConversionRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      category: r.category ?? '',
      name: r.name ?? '',
      energy_density: r.energy_density?.toString() ?? '',
      source_comments: r.source_comments ?? '',
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Category</TH>
          <TH>Name</TH>
          <TH>Unit</TH>
          <TH right normalCase>Energy Density (GJ/unit)</TH>
          <TH>Source/Comments</TH>
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
                <TD><InlineInput value={ec.editDraft.category ?? ''} onChange={v => ec.onEditField('category', v)} placeholder="Category" /></TD>
                <TD><InlineInput value={ec.editDraft.name ?? ''} onChange={v => ec.onEditField('name', v)} placeholder="Name" /></TD>
                <TD muted>{r.unit ? (r.unit.label ?? r.unit.code) : '—'}</TD>
                <TD right><InlineInput type="number" value={ec.editDraft.energy_density ?? ''} onChange={v => ec.onEditField('energy_density', v)} placeholder="Energy Density" /></TD>
                <TD><InlineInput value={ec.editDraft.source_comments ?? ''} onChange={v => ec.onEditField('source_comments', v)} placeholder="Source/Comments" /></TD>
                <TD><SaveCancelButtons onSave={ec.onSaveEdit} onCancel={ec.onCancelEdit} saving={ec.saving} error={ec.saveError} /></TD>
              </tr>
            );
          }
          return (
            <tr key={i}
              className={`even:bg-neutral-98 hover:bg-blue-50 ${isSA && !ec?.editingId ? 'cursor-pointer' : ''}`}
              onDoubleClick={isSA && !ec?.editingId ? () => startEdit(r) : undefined}
            >
              <TD>{r.category ?? '—'}</TD>
              <TD>{r.name ?? '—'}</TD>
              <TD muted>{r.unit ? (r.unit.label ?? r.unit.code) : '—'}</TD>
              <TD right muted={r.energy_density == null}>{r.energy_density ?? '—'}</TD>
              <TD muted>{r.source_comments ?? '—'}</TD>
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
