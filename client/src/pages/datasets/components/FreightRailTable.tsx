import type { FreightRailRow, FreightRailEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: FreightRailRow[];
  editCtx?: FreightRailEditCtx;
}

export default function FreightRailTable({ rows, editCtx }: Props) {
  const ec = editCtx;

  return (
    <div className="overflow-x-auto overflow-y-auto h-full">
      <table className="border-collapse text-xs w-full">
        <thead className="sticky top-0 z-10 bg-neutral-90">
          <tr>
            <TH>Train Type</TH>
            <TH>Terrain</TH>
            <TH right>Fuel Consumption (L/000 GTK)</TH>
            <TH>Source Note</TH>
            {ec && <TH>Actions</TH>}
          </tr>
        </thead>
        <tbody>
          {rows.map(r => {
            const isEditing = ec?.editingId === r.id;
            return (
              <tr
                key={r.id}
                className={`${isEditing ? 'bg-amber-50' : 'even:bg-neutral-98 hover:bg-primary/5'} ${ec && !isEditing ? 'cursor-pointer' : ''}`}
                onDoubleClick={ec && !isEditing ? () => ec.onStartEdit(r.id, {
                  fuel_consumption: r.fuel_consumption_l_per_000_gtk != null
                    ? String(r.fuel_consumption_l_per_000_gtk)
                    : '',
                  source_note: r.source_note ?? '',
                }) : undefined}
                tabIndex={isEditing ? -1 : undefined}
                onBlur={isEditing && ec ? (e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveEdit(); } : undefined}
                onKeyDown={isEditing && ec ? (e) => { if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelEdit(); } else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveEdit(); } } : undefined}
              >
                <TD>{r.train_type}</TD>
                <TD>{r.terrain}</TD>
                {isEditing && ec ? (
                  <>
                    <td className="px-2 py-1.5 border-r border-b border-neutral-90 min-w-[140px]">
                      <InlineInput
                        type="number"
                        value={ec.editDraft.fuel_consumption ?? ''}
                        onChange={v => ec.onEditField('fuel_consumption', v)}
                        placeholder="L/000 GTK"
                      />
                    </td>
                    <td className="px-2 py-1.5 border-r border-b border-neutral-90 min-w-[200px]">
                      <InlineInput
                        value={ec.editDraft.source_note ?? ''}
                        onChange={v => ec.onEditField('source_note', v)}
                        placeholder="source note"
                      />
                    </td>
                    <td className="px-3 py-1.5 border-b border-neutral-90">
                      <SaveCancelButtons
                        onSave={ec.onSaveEdit}
                        onCancel={ec.onCancelEdit}
                        saving={ec.saving}
                        error={ec.saveError}
                      />
                    </td>
                  </>
                ) : (
                  <>
                    <TD right muted={r.fuel_consumption_l_per_000_gtk == null}>
                      {r.fuel_consumption_l_per_000_gtk ?? '—'}
                    </TD>
                    <TD muted={!r.source_note}>{r.source_note ?? '—'}</TD>
                    {ec && (
                      <td className="px-3 py-2 border-b border-neutral-90">
                        {ec.onDelete && (
                          <button
                            type="button"
                            onClick={() => ec.onDelete!(r.id)}
                            title="Delete row"
                            className="rounded cursor-pointer p-0.5 text-red-400 hover:text-red-600 hover:bg-red-50"
                          >
                            <span className="material-symbols-rounded text-[14px] leading-none">delete</span>
                          </button>
                        )}
                      </td>
                    )}
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
