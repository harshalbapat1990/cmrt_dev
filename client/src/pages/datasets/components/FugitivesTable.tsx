import type { FugitiveRow, FugitiveEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: FugitiveRow[];
  editCtx?: FugitiveEditCtx;
}

export default function FugitivesTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: FugitiveRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      equipment_type: r.equipment_type ?? '',
      default_annual_leakage_rate: r.default_annual_leakage_rate?.toString() ?? '',
      source_comments: r.source_comments ?? '',
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Equipment Type</TH>
          <TH right>Leakage Rate (%)</TH>
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
                <TD><InlineInput value={ec.editDraft.equipment_type ?? ''} onChange={v => ec.onEditField('equipment_type', v)} placeholder="Equipment Type" /></TD>
                <TD right><InlineInput type="number" value={ec.editDraft.default_annual_leakage_rate ?? ''} onChange={v => ec.onEditField('default_annual_leakage_rate', v)} placeholder="Rate" /></TD>
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

              <TD>{r.equipment_type ?? '—'}</TD>
              <TD right muted={r.default_annual_leakage_rate == null}>{r.default_annual_leakage_rate ?? '—'}</TD>
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
