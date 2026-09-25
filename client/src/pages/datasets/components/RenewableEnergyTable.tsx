import type { RenewableEnergyRow, RenewableEnergyEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: RenewableEnergyRow[];
  editCtx?: RenewableEnergyEditCtx;
}

export default function RenewableEnergyTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: RenewableEnergyRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      classification: r.classification ?? '',
      notes: r.notes ?? '',
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Emissions Source</TH>
          <TH>Classification</TH>
          <TH>Notes</TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          const isEditing = ec?.editingId === r.id;
          if (isEditing && ec) {
            return (
              <tr
                key={i}
                className="bg-amber-50"
                tabIndex={-1}
                onBlur={(e) => {
                  if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveEdit();
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelEdit(); }
                  else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveEdit(); }
                }}
              >
                <TD muted>{r.emissions_source}</TD>
                <TD>
                  <InlineInput
                    value={ec.editDraft.classification ?? ''}
                    onChange={v => ec.onEditField('classification', v)}
                    placeholder="Classification"
                  />
                </TD>
                <TD>
                  <InlineInput
                    value={ec.editDraft.notes ?? ''}
                    onChange={v => ec.onEditField('notes', v)}
                    placeholder="Notes"
                  />
                </TD>
                <TD>
                  <SaveCancelButtons
                    onSave={ec.onSaveEdit}
                    onCancel={ec.onCancelEdit}
                    saving={ec.saving}
                    error={ec.saveError}
                  />
                </TD>
              </tr>
            );
          }
          return (
            <tr
              key={i}
              className={`border-b border-neutral-80 ${isSA ? 'cursor-pointer hover:bg-neutral-95' : ''}`}
              onClick={() => startEdit(r)}
            >
              <TD>{r.emissions_source}</TD>
              <TD>{r.classification}</TD>
              <TD muted>{r.notes ?? '—'}</TD>
              {isSA && (
                <TD>
                  <button
                    type="button"
                    className="text-red-500 cursor-pointer hover:text-red-700 text-xs px-1"
                    onClick={(e) => { e.stopPropagation(); ec?.onDelete?.(r.id); }}
                  >
                    Delete
                  </button>
                </TD>
              )}
            </tr>
          );
        })}
        {rows.length === 0 && (
          <tr>
            <td colSpan={isSA ? 4 : 3} className="py-6 text-center text-text-muted text-xs">
              No renewable energy classifications found
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
