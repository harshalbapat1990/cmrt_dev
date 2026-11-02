import type { InterruptedVehicleRow, InterruptedVehicleEditCtx } from '../types';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: InterruptedVehicleRow[];
  editCtx?: InterruptedVehicleEditCtx;
}

export default function InterruptedVehiclesTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: InterruptedVehicleRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      coefficient_a: r.coefficient_a,
      coefficient_b: r.coefficient_b,
    });
  };

  return (
    <div>
      <p className="mb-2 text-xs text-text-base italic px-4">
        * These variables are used in user emissions calculations for Australian projects consistent with the Australian Transport 
        Assessment and Planning (ATAP) Road Parameter Values (PV2). Values should only be changed to cater to methodology changes from ATAP.
      </p>
      <table className="w-full border-collapse text-xs">
        <thead className="sticky top-0 z-10 bg-neutral-90">
          <tr>
            <TH>Vehicle Class</TH>
            <TH right>Coefficient A</TH>
            <TH right>Coefficient B</TH>
            {isSA && <TH>&nbsp;</TH>}
          </tr>
        </thead>
        <tbody>
          {ec?.adding && (
            <tr className="bg-blue-50">
              <TD>
                <InlineSelect
                  value={ec.addDraft.vehicle_class_id ?? ''}
                  options={ec.vehicleClassOpts}
                  onChange={v => ec.onAddField('vehicle_class_id', v)}
                  placeholder="— vehicle class —"
                />
              </TD>
              <TD right>
                <InlineInput type="number" value={ec.addDraft.coefficient_a ?? ''} onChange={v => ec.onAddField('coefficient_a', v)} placeholder="A" />
              </TD>
              <TD right>
                <InlineInput type="number" value={ec.addDraft.coefficient_b ?? ''} onChange={v => ec.onAddField('coefficient_b', v)} placeholder="B" />
              </TD>
              <TD>
                <SaveCancelButtons onSave={ec.onSaveAdd} onCancel={ec.onCancelAdd} saving={ec.saving} error={ec.saveError} />
              </TD>
            </tr>
          )}
          {rows.map((r, i) => {
            const isEditing = ec?.editingId === r.id;
            if (isEditing && ec) {
              return (
                <tr key={r.id} className="bg-amber-50" tabIndex={-1}
                  onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveEdit(); }}
                  onKeyDown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelEdit(); } else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveEdit(); } }}
                >
                  <TD muted>{r.vehicle_class_name ?? '—'}</TD>
                  <TD right>
                    <InlineInput type="number" value={ec.editDraft.coefficient_a ?? ''} onChange={v => ec.onEditField('coefficient_a', v)} placeholder="A" />
                  </TD>
                  <TD right>
                    <InlineInput type="number" value={ec.editDraft.coefficient_b ?? ''} onChange={v => ec.onEditField('coefficient_b', v)} placeholder="B" />
                  </TD>
                  <TD>
                    <SaveCancelButtons onSave={ec.onSaveEdit} onCancel={ec.onCancelEdit} saving={ec.saving} error={ec.saveError} />
                  </TD>
                </tr>
              );
            }
            return (
              <tr
                key={r.id ?? i}
                className={`even:bg-neutral-98 hover:bg-blue-50 ${isSA && !ec?.editingId ? 'cursor-pointer' : ''}`}
                onDoubleClick={isSA && !ec?.editingId ? () => startEdit(r) : undefined}
              >
                <TD>{r.vehicle_class_name ?? '—'}</TD>
                <TD right>{r.coefficient_a}</TD>
                <TD right>{r.coefficient_b}</TD>
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
    </div>
  );
}
