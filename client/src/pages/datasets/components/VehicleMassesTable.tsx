import type { VehicleMassRow, VehicleMassEditCtx } from '../types';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: VehicleMassRow[];
  editCtx?: VehicleMassEditCtx;
}

export default function VehicleMassesTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: VehicleMassRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      reference_gcm_tonnes: r.reference_gcm_tonnes ?? '',
      max_payload_tonnes: r.max_payload_tonnes ?? '',
      gvm_tonnes: r.gvm_tonnes ?? '',
      assumed_payload_pct: r.assumed_payload_pct ?? '',
    });
  };

  return (
      <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Vehicle Class</TH>
          <TH right normalCase>Reference GCM (tonnes)</TH>
          <TH right normalCase>Max Payload (tonnes)</TH>
          <TH right normalCase>GVM</TH>
          <TH right normalCase>Assumed Payload %</TH>
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
              <InlineInput type="number" value={ec.addDraft.reference_gcm_tonnes ?? ''} onChange={v => ec.onAddField('reference_gcm_tonnes', v)} placeholder="GCM" />
            </TD>
            <TD right>
              <InlineInput type="number" value={ec.addDraft.max_payload_tonnes ?? ''} onChange={v => ec.onAddField('max_payload_tonnes', v)} placeholder="Max payload" />
            </TD>
            <TD right>
              <InlineInput type="number" value={ec.addDraft.gvm_tonnes ?? ''} onChange={v => ec.onAddField('gvm_tonnes', v)} placeholder="GVM" />
            </TD>
            <TD right>
              <InlineInput type="number" value={ec.addDraft.assumed_payload_pct ?? ''} onChange={v => ec.onAddField('assumed_payload_pct', v)} placeholder="%" />
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
                  <InlineInput type="number" value={ec.editDraft.reference_gcm_tonnes ?? ''} onChange={v => ec.onEditField('reference_gcm_tonnes', v)} placeholder="GCM" />
                </TD>
                <TD right>
                  <InlineInput type="number" value={ec.editDraft.max_payload_tonnes ?? ''} onChange={v => ec.onEditField('max_payload_tonnes', v)} placeholder="Max payload" />
                </TD>
                <TD right>
                  <InlineInput type="number" value={ec.editDraft.gvm_tonnes ?? ''} onChange={v => ec.onEditField('gvm_tonnes', v)} placeholder="GVM" />
                </TD>
                <TD right>
                  <InlineInput type="number" value={ec.editDraft.assumed_payload_pct ?? ''} onChange={v => ec.onEditField('assumed_payload_pct', v)} placeholder="%" />
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
              <TD right muted={r.reference_gcm_tonnes == null}>{r.reference_gcm_tonnes ?? '—'}</TD>
              <TD right muted={r.max_payload_tonnes == null}>{r.max_payload_tonnes ?? '—'}</TD>
              <TD right muted={r.gvm_tonnes == null}>{r.gvm_tonnes ?? '—'}</TD>
              <TD right muted={r.assumed_payload_pct == null}>{r.assumed_payload_pct ?? '—'}</TD>
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
