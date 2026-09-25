import type { UninterruptedVehicleRow, UninterruptedVehicleEditCtx } from '../types';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: UninterruptedVehicleRow[];
  editCtx?: UninterruptedVehicleEditCtx;
}

function displayGradient(val: string): string {
  return val === '0' || val === '0.00' ? 'Flat' : val;
}

export default function UninterruptedVehiclesTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: UninterruptedVehicleRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      gradient_m_per_km: r.gradient_m_per_km,
      curvature_deg_per_km: r.curvature_deg_per_km,
      base_fuel_l_per_100km: r.base_fuel_l_per_100km,
      k1: r.k1,
      k2: r.k2,
      k3: r.k3,
      k4: r.k4,
      k5: r.k5,
    });
  };

  return (
        <div>
      <p className="mb-2 text-xs text-text-base italic px-4">
        * These variables are used in user emissions calculations for Australian projects consistent with the Australian
        Transport Assessment and Planning (ATAP) Road Parameter Values (PV2). Values should only be changed to cater to
        methodology changes from ATAP.
      </p>
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs">
        <thead className="sticky top-0 z-10 bg-neutral-90">
          <tr>
            <TH>Vehicle Class</TH>
            <TH right normalCase>Gradient (m/km)</TH>
            <TH right normalCase>Curvature (°/km)</TH>
            <TH right normalCase>Base Fuel (L/100km)</TH>
            <TH right normalCase>k1</TH>
            <TH right normalCase>k2</TH>
            <TH right normalCase>k3</TH>
            <TH right normalCase>k4</TH>
            <TH right normalCase>k5</TH>
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
                <InlineInput type="number" value={ec.addDraft.gradient_m_per_km ?? '0'} onChange={v => ec.onAddField('gradient_m_per_km', v)} placeholder="0" />
              </TD>
              <TD right>
                <InlineInput type="number" value={ec.addDraft.curvature_deg_per_km ?? ''} onChange={v => ec.onAddField('curvature_deg_per_km', v)} placeholder="curvature" />
              </TD>
              <TD right>
                <InlineInput type="number" value={ec.addDraft.base_fuel_l_per_100km ?? ''} onChange={v => ec.onAddField('base_fuel_l_per_100km', v)} placeholder="base fuel" />
              </TD>
              <TD right><InlineInput type="number" value={ec.addDraft.k1 ?? ''} onChange={v => ec.onAddField('k1', v)} placeholder="k1" /></TD>
              <TD right><InlineInput type="number" value={ec.addDraft.k2 ?? ''} onChange={v => ec.onAddField('k2', v)} placeholder="k2" /></TD>
              <TD right><InlineInput type="number" value={ec.addDraft.k3 ?? ''} onChange={v => ec.onAddField('k3', v)} placeholder="k3" /></TD>
              <TD right><InlineInput type="number" value={ec.addDraft.k4 ?? ''} onChange={v => ec.onAddField('k4', v)} placeholder="k4" /></TD>
              <TD right><InlineInput type="number" value={ec.addDraft.k5 ?? ''} onChange={v => ec.onAddField('k5', v)} placeholder="k5" /></TD>
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
                    <InlineInput type="number" value={ec.editDraft.gradient_m_per_km ?? ''} onChange={v => ec.onEditField('gradient_m_per_km', v)} placeholder="0" />
                  </TD>
                  <TD right>
                    <InlineInput type="number" value={ec.editDraft.curvature_deg_per_km ?? ''} onChange={v => ec.onEditField('curvature_deg_per_km', v)} placeholder="curvature" />
                  </TD>
                  <TD right>
                    <InlineInput type="number" value={ec.editDraft.base_fuel_l_per_100km ?? ''} onChange={v => ec.onEditField('base_fuel_l_per_100km', v)} placeholder="base fuel" />
                  </TD>
                  <TD right><InlineInput type="number" value={ec.editDraft.k1 ?? ''} onChange={v => ec.onEditField('k1', v)} /></TD>
                  <TD right><InlineInput type="number" value={ec.editDraft.k2 ?? ''} onChange={v => ec.onEditField('k2', v)} /></TD>
                  <TD right><InlineInput type="number" value={ec.editDraft.k3 ?? ''} onChange={v => ec.onEditField('k3', v)} /></TD>
                  <TD right><InlineInput type="number" value={ec.editDraft.k4 ?? ''} onChange={v => ec.onEditField('k4', v)} /></TD>
                  <TD right><InlineInput type="number" value={ec.editDraft.k5 ?? ''} onChange={v => ec.onEditField('k5', v)} /></TD>
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
                <TD right>{displayGradient(r.gradient_m_per_km)}</TD>
                <TD right>{r.curvature_deg_per_km}</TD>
                <TD right>{r.base_fuel_l_per_100km}</TD>
                <TD right>{r.k1}</TD>
                <TD right>{r.k2}</TD>
                <TD right>{r.k3}</TD>
                <TD right>{r.k4}</TD>
                <TD right>{r.k5}</TD>
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
    </div>
  );
}
