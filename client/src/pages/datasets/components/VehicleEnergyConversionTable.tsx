import type { VehicleEnergyConversionRow, VehicleEnergyEditCtx } from '../types';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: VehicleEnergyConversionRow[];
  editCtx?: VehicleEnergyEditCtx;
}

export default function VehicleEnergyConversionTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: VehicleEnergyConversionRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      ev_projection_category: r.ev_projection_category,
      primary_ice_fuel: r.primary_ice_fuel,
      hybrid_fuel_savings_pct: r.hybrid_fuel_savings_pct ?? '',
      phev_fuel_savings_pct: r.phev_fuel_savings_pct ?? '',
      bev_energy_shift_kwh_per_l: r.bev_energy_shift_kwh_per_l ?? '',
      fcev_hydrogen_consumption_kwh_per_l: r.fcev_hydrogen_consumption_kwh_per_l ?? '',
      source_comments: r.source_comments ?? '',
    });
  };

  return (
    <div>
      <p className="mb-2 text-xs text-text-base italic px-4">
        * EV Category values are used to map EV uptake rates to relevant vehicle classes from Australian Transport Assessment and Planning 
        (ATAP) Road Parameter Values (PV2).
        </p>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-xs">
            <thead className="sticky top-0 z-10 bg-neutral-90">
              <tr>
                <TH>Vehicle Class</TH>
                <TH>EV Category</TH>
                <TH>Primary ICE Fuel</TH>
                <TH right normalCase>Hybrid fuel savings (%)</TH>
                <TH right normalCase>PHEV fuel savings (%)</TH>
                <TH right normalCase>BEV energy shift (kWh/L)</TH>
                <TH right normalCase>FCEV hydrogen consumptions (kWh/L)</TH>
                <TH>Source</TH>
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
                  <TD>
                    <InlineInput value={ec.addDraft.ev_projection_category ?? ''} onChange={v => ec.onAddField('ev_projection_category', v)} placeholder="EV category" />
                  </TD>
                  <TD>
                    <InlineInput value={ec.addDraft.primary_ice_fuel ?? ''} onChange={v => ec.onAddField('primary_ice_fuel', v)} placeholder="ICE fuel" />
                  </TD>
                  <TD right>
                    <InlineInput type="number" value={ec.addDraft.hybrid_fuel_savings_pct ?? ''} onChange={v => ec.onAddField('hybrid_fuel_savings_pct', v)} placeholder="0.00" />
                  </TD>
                  <TD right>
                    <InlineInput type="number" value={ec.addDraft.phev_fuel_savings_pct ?? ''} onChange={v => ec.onAddField('phev_fuel_savings_pct', v)} placeholder="0.00" />
                  </TD>
                  <TD right>
                    <InlineInput type="number" value={ec.addDraft.bev_energy_shift_kwh_per_l ?? ''} onChange={v => ec.onAddField('bev_energy_shift_kwh_per_l', v)} placeholder="0.0000" />
                  </TD>
                  <TD right>
                    <InlineInput type="number" value={ec.addDraft.fcev_hydrogen_consumption_kwh_per_l ?? ''} onChange={v => ec.onAddField('fcev_hydrogen_consumption_kwh_per_l', v)} placeholder="0.0000" />
                  </TD>
                  <TD>
                    <InlineInput value={ec.addDraft.source_comments ?? ''} onChange={v => ec.onAddField('source_comments', v)} placeholder="Source" />
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
                      <TD>
                        <InlineInput value={ec.editDraft.ev_projection_category ?? ''} onChange={v => ec.onEditField('ev_projection_category', v)} placeholder="EV category" />
                      </TD>
                      <TD>
                        <InlineInput value={ec.editDraft.primary_ice_fuel ?? ''} onChange={v => ec.onEditField('primary_ice_fuel', v)} placeholder="ICE fuel" />
                      </TD>
                      <TD right>
                        <InlineInput type="number" value={ec.editDraft.hybrid_fuel_savings_pct ?? ''} onChange={v => ec.onEditField('hybrid_fuel_savings_pct', v)} placeholder="0.00" />
                      </TD>
                      <TD right>
                        <InlineInput type="number" value={ec.editDraft.phev_fuel_savings_pct ?? ''} onChange={v => ec.onEditField('phev_fuel_savings_pct', v)} placeholder="0.00" />
                      </TD>
                      <TD right>
                        <InlineInput type="number" value={ec.editDraft.bev_energy_shift_kwh_per_l ?? ''} onChange={v => ec.onEditField('bev_energy_shift_kwh_per_l', v)} placeholder="0.0000" />
                      </TD>
                      <TD right>
                        <InlineInput type="number" value={ec.editDraft.fcev_hydrogen_consumption_kwh_per_l ?? ''} onChange={v => ec.onEditField('fcev_hydrogen_consumption_kwh_per_l', v)} placeholder="0.0000" />
                      </TD>
                      <TD>
                        <InlineInput value={ec.editDraft.source_comments ?? ''} onChange={v => ec.onEditField('source_comments', v)} placeholder="Source" />
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
                    <TD>{r.ev_projection_category}</TD>
                    <TD>{r.primary_ice_fuel}</TD>
                    <TD right muted={r.hybrid_fuel_savings_pct == null}>{r.hybrid_fuel_savings_pct ?? '—'}</TD>
                    <TD right muted={r.phev_fuel_savings_pct == null}>{r.phev_fuel_savings_pct ?? '—'}</TD>
                    <TD right muted={r.bev_energy_shift_kwh_per_l == null}>{r.bev_energy_shift_kwh_per_l ?? '—'}</TD>
                    <TD right muted={r.fcev_hydrogen_consumption_kwh_per_l == null}>{r.fcev_hydrogen_consumption_kwh_per_l ?? '—'}</TD>
                    <TD muted>{r.source_comments ?? '—'}</TD>
                    {isSA && (
                      <TD>
                        {!ec?.editingId && ec?.onDelete && (
                          <button
                            type="button"
                            onClick={() => ec.onDelete!(r.id)}
                            title="Delete row"
                            className="rounded cursor-pointer p-0.5 text-red-400 hover:text-red-600 hover:bg-red-50"
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
