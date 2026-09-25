import type { VepmRow, VepmEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: VepmRow[];
  editCtx?: VepmEditCtx;
}

const EDIT_FIELDS: Array<{ key: string; label: string }> = [
  { key: 'fleet_average_co2e_g_km', label: 'Fleet Avg CO2e (g/km)' },
  { key: 'light_vehicle_co2e_g_km', label: 'Light Vehicle (g/km)' },
  { key: 'heavy_vehicle_co2e_g_km', label: 'Heavy Vehicle (g/km)' },
  { key: 'bus_co2e_g_km', label: 'Bus (g/km)' },
];

export default function VepmTable({ rows, editCtx }: Props) {
  const ec = editCtx;

  return (
      <div className="overflow-x-auto overflow-y-auto h-full">
        <table className="border-collapse text-xs w-full">
          <thead className="sticky top-0 z-10 bg-neutral-90">
            <tr>
              <TH>Year</TH>
              <TH right normalCase>Speed (km/h)</TH>
              <TH right normalCase>Fleet Avg gCO₂e/km</TH>
              <TH right normalCase>Light Vehicle gCO₂e/km</TH>
              <TH right normalCase>Heavy Vehicle gCO₂e/km</TH>
              <TH right normalCase>Bus gCO₂e/km</TH>
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
                    fleet_average_co2e_g_km: r.fleet_average_co2e_g_km != null ? String(r.fleet_average_co2e_g_km) : '',
                    light_vehicle_co2e_g_km: r.light_vehicle_co2e_g_km != null ? String(r.light_vehicle_co2e_g_km) : '',
                    heavy_vehicle_co2e_g_km: r.heavy_vehicle_co2e_g_km != null ? String(r.heavy_vehicle_co2e_g_km) : '',
                    bus_co2e_g_km: r.bus_co2e_g_km != null ? String(r.bus_co2e_g_km) : '',
                  }) : undefined}
                  tabIndex={isEditing ? -1 : undefined}
                  onBlur={isEditing && ec ? (e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveEdit(); } : undefined}
                  onKeyDown={isEditing && ec ? (e) => { if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelEdit(); } else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveEdit(); } } : undefined}
                >
                  <TD>{r.year}</TD>
                  <TD right>{r.speed_kmh}</TD>
                  {isEditing && ec ? (
                    <>
                      {EDIT_FIELDS.map(f => (
                        <td key={f.key} className="px-2 py-1.5 border-r border-b border-neutral-90 min-w-[120px]">
                          <InlineInput
                            type="number"
                            value={ec.editDraft[f.key] ?? ''}
                            onChange={v => ec.onEditField(f.key, v)}
                            placeholder={f.label}
                          />
                        </td>
                      ))}
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
                      <TD right muted={r.fleet_average_co2e_g_km == null}>{r.fleet_average_co2e_g_km ?? '—'}</TD>
                      <TD right muted={r.light_vehicle_co2e_g_km == null}>{r.light_vehicle_co2e_g_km ?? '—'}</TD>
                      <TD right muted={r.heavy_vehicle_co2e_g_km == null}>{r.heavy_vehicle_co2e_g_km ?? '—'}</TD>
                      <TD right muted={r.bus_co2e_g_km == null}>{r.bus_co2e_g_km ?? '—'}</TD>
                      {ec && (
                        <td className="px-3 py-2 border-b border-neutral-90">
                          {ec.onDelete && (
                            <button
                              type="button"
                              onClick={() => ec.onDelete!(r.id)}
                              title="Delete row"
                              className="rounded p-0.5 cursor-pointer text-red-400 hover:text-red-600 hover:bg-red-50"
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
