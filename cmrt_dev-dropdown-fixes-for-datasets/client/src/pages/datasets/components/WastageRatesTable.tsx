import type { WastageRateRow, WastageRateEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: WastageRateRow[];
  editCtx?: WastageRateEditCtx;
}

export default function WastageRatesTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: WastageRateRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      construction_wastage_rate: r.construction_wastage_rate?.toString() ?? '',
      recycling_rate: r.recycling_rate?.toString() ?? '',
      landfill_rate: r.landfill_rate?.toString() ?? '',
      source: r.source ?? '',
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Material</TH>
          <TH right>Construction Wastage Rate (%)</TH>
          <TH right>Recycling Rate (%)</TH>
          <TH right>Landfill Rate (%)</TH>
          <TH>Source</TH>
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
                <TD muted>{r.material?.name ?? '—'}</TD>
                <TD right>
                  <InlineInput
                    type="number"
                    value={ec.editDraft.construction_wastage_rate ?? ''}
                    onChange={v => ec.onEditField('construction_wastage_rate', v)}
                    placeholder="Value"
                  />
                </TD>
                <TD right>
                  <InlineInput
                    type="number"
                    value={ec.editDraft.recycling_rate ?? ''}
                    onChange={v => ec.onEditField('recycling_rate', v)}
                    placeholder="Value"
                  />
                </TD>
                <TD right>
                  <InlineInput
                    type="number"
                    value={ec.editDraft.landfill_rate ?? ''}
                    onChange={v => ec.onEditField('landfill_rate', v)}
                    placeholder="Value"
                  />
                </TD>
                <TD>
                  <InlineInput
                    value={ec.editDraft.source ?? ''}
                    onChange={v => ec.onEditField('source', v)}
                    placeholder="Source"
                  />
                </TD>
                <TD>
                  <SaveCancelButtons onSave={ec.onSaveEdit} onCancel={ec.onCancelEdit} saving={ec.saving} error={ec.saveError} />
                </TD>
              </tr>
            );
          }
          return (
            <tr
              key={i}
              className={`even:bg-neutral-98 hover:bg-blue-50 ${isSA && !ec?.editingId ? 'cursor-pointer' : ''}`}
              onDoubleClick={isSA && !ec?.editingId ? () => startEdit(r) : undefined}
            >
              <TD>{r.material?.name ?? '—'}</TD>
              <TD right muted={r.construction_wastage_rate == null}>{r.construction_wastage_rate ?? '—'}</TD>
              <TD right muted={r.recycling_rate == null}>{r.recycling_rate ?? '—'}</TD>
              <TD right muted={r.landfill_rate == null}>{r.landfill_rate ?? '—'}</TD>
              <TD muted>{r.source ?? '—'}</TD>
              {isSA && (
                <TD>
                  {!ec?.editingId && ec?.onDelete && (
                    <button
                      type="button"
                      onClick={() => ec.onDelete!(r.id)}
                      title="Delete row"
                      className="rounded p-0.5 cursor-pointer text-red-400 hover:text-red-600 hover:bg-red-50"
                    >
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
