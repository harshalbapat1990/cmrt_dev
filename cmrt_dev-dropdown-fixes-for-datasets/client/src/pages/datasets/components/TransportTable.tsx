import type { TransportRow, InlineEditContext } from '../types';
import { TODAY, DEFAULT_EFFECTIVE_TO } from '../constants';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

export default function TransportTable({ rows, editCtx }: { rows: TransportRow[]; editCtx?: InlineEditContext }) {
  const ec = editCtx;
  const isSA = !!ec;

  const modeCell = (mode: string | null, dist: string | null) => {
    if (!dist && !mode) return '—';
    const d = dist != null ? `${dist} km` : null;
    if (mode && d) return `${mode} (${d})`;
    return mode ?? d ?? '—';
  };

  const startEdit = (row: TransportRow) => {
    if (!ec) return;
    ec.onStartEdit(row.id, {
      material_id: row.material_id ?? '',
      emissions_category_id: row.emissions_category_id ?? '',
      jurisdiction_id: row.jurisdiction_id,
      truck_distance: row.truck_distance ?? '',
      rail_distance: row.rail_distance ?? '',
      sea_distance: row.sea_distance ?? '',
      truck_transport_mode: row.truck_transport_mode ?? '',
      rail_transport_mode: row.rail_transport_mode ?? '',
      sea_transport_mode: row.sea_transport_mode ?? '',
      source: row.source ?? '',
      grade_applicability: row.grade_applicability ?? '',
      effective_from: row.effective_from ?? '',
      effective_to: row.effective_to ?? '',
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Material / Category</TH>
          <TH>Jurisdiction</TH>
          <TH>Truck</TH>
          <TH>Rail</TH>
          <TH>Sea</TH>
          <TH>Grade</TH>
          <TH>Source</TH>
          <TH>Effective From</TH>
          <TH>Effective To</TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {ec?.adding && (
          <tr className="bg-blue-50">
            <TD>
              <div className="flex flex-col gap-0.5">
                <select
                  value={ec.addDraft.__tr_key_type ?? 'material'}
                  onChange={e => ec.onAddField('__tr_key_type', e.target.value)}
                  className="w-full rounded border border-primary px-1 py-0.5 text-xs bg-white focus:outline-none"
                >
                  <option value="material">Material</option>
                  <option value="category">Category</option>
                </select>
                {(ec.addDraft.__tr_key_type ?? 'material') === 'material'
                  ? <InlineSelect value={ec.addDraft.material_id ?? ''} options={ec.matOpts} onChange={v => ec.onAddField('material_id', v)} placeholder="— material —" />
                  : <InlineSelect value={ec.addDraft.emissions_category_id ?? ''} options={ec.ecOpts} onChange={v => ec.onAddField('emissions_category_id', v)} placeholder="— category —" />
                }
              </div>
            </TD>
            <TD><InlineSelect value={ec.addDraft.jurisdiction_id ?? ''} options={ec.jurOpts} onChange={v => ec.onAddField('jurisdiction_id', v)} placeholder="— jurisdiction —" /></TD>
            <TD>
              <div className="flex flex-col gap-0.5">
                <InlineInput value={ec.addDraft.truck_transport_mode ?? ''} onChange={v => ec.onAddField('truck_transport_mode', v)} placeholder="Mode" />
                <InlineInput value={ec.addDraft.truck_distance ?? ''} onChange={v => ec.onAddField('truck_distance', v)} type="number" placeholder="km" />
              </div>
            </TD>
            <TD>
              <div className="flex flex-col gap-0.5">
                <InlineInput value={ec.addDraft.rail_transport_mode ?? ''} onChange={v => ec.onAddField('rail_transport_mode', v)} placeholder="Mode" />
                <InlineInput value={ec.addDraft.rail_distance ?? ''} onChange={v => ec.onAddField('rail_distance', v)} type="number" placeholder="km" />
              </div>
            </TD>
            <TD>
              <div className="flex flex-col gap-0.5">
                <InlineInput value={ec.addDraft.sea_transport_mode ?? ''} onChange={v => ec.onAddField('sea_transport_mode', v)} placeholder="Mode" />
                <InlineInput value={ec.addDraft.sea_distance ?? ''} onChange={v => ec.onAddField('sea_distance', v)} type="number" placeholder="km" />
              </div>
            </TD>
            <TD><InlineInput value={ec.addDraft.grade_applicability ?? ''} onChange={v => ec.onAddField('grade_applicability', v)} /></TD>
            <TD><InlineInput value={ec.addDraft.source ?? ''} onChange={v => ec.onAddField('source', v)} /></TD>
            <TD><InlineInput value={ec.addDraft.effective_from ?? ''} onChange={v => ec.onAddField('effective_from', v)} type="date" /></TD>
            <TD><InlineInput value={ec.addDraft.effective_to ?? ''} onChange={v => ec.onAddField('effective_to', v)} type="date" /></TD>
            <TD><SaveCancelButtons onSave={ec.onSaveAdd} onCancel={ec.onCancelAdd} saving={ec.saving} error={ec.saveError} /></TD>
          </tr>
        )}
        {rows.map(r => {
          const isEditing = ec?.editingId === r.id;
          if (isEditing && ec) {
            const matOrCat = r.material_id
              ? (r.material_name ?? r.material_id)
              : (r.emissions_category_name ?? r.emissions_category_id ?? '—');
            return (
              <tr key={r.id} className="bg-amber-50" tabIndex={-1}
                onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveEdit(); }}
                onKeyDown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelEdit(); } else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveEdit(); } }}
              >
                <TD><span className="text-xs text-text-base italic">{matOrCat}</span></TD>
                <TD><InlineSelect value={ec.editDraft.jurisdiction_id ?? ''} options={ec.jurOpts} onChange={v => ec.onEditField('jurisdiction_id', v)} /></TD>
                <TD>
                  <div className="flex flex-col gap-0.5">
                    <InlineInput value={ec.editDraft.truck_transport_mode ?? ''} onChange={v => ec.onEditField('truck_transport_mode', v)} placeholder="Mode" />
                    <InlineInput value={ec.editDraft.truck_distance ?? ''} onChange={v => ec.onEditField('truck_distance', v)} type="number" placeholder="km" />
                  </div>
                </TD>
                <TD>
                  <div className="flex flex-col gap-0.5">
                    <InlineInput value={ec.editDraft.rail_transport_mode ?? ''} onChange={v => ec.onEditField('rail_transport_mode', v)} placeholder="Mode" />
                    <InlineInput value={ec.editDraft.rail_distance ?? ''} onChange={v => ec.onEditField('rail_distance', v)} type="number" placeholder="km" />
                  </div>
                </TD>
                <TD>
                  <div className="flex flex-col gap-0.5">
                    <InlineInput value={ec.editDraft.sea_transport_mode ?? ''} onChange={v => ec.onEditField('sea_transport_mode', v)} placeholder="Mode" />
                    <InlineInput value={ec.editDraft.sea_distance ?? ''} onChange={v => ec.onEditField('sea_distance', v)} type="number" placeholder="km" />
                  </div>
                </TD>
                <TD><InlineInput value={ec.editDraft.grade_applicability ?? ''} onChange={v => ec.onEditField('grade_applicability', v)} /></TD>
                <TD><InlineInput value={ec.editDraft.source ?? ''} onChange={v => ec.onEditField('source', v)} /></TD>
                <TD><InlineInput value={ec.editDraft.effective_from ?? ''} onChange={v => ec.onEditField('effective_from', v)} type="date" /></TD>
                <TD><InlineInput value={ec.editDraft.effective_to ?? ''} onChange={v => ec.onEditField('effective_to', v)} type="date" /></TD>
                <TD><SaveCancelButtons onSave={ec.onSaveEdit} onCancel={ec.onCancelEdit} saving={ec.saving} error={ec.saveError} /></TD>
              </tr>
            );
          }
          return (
            <tr
              key={r.id}
              className={`even:bg-neutral-98 hover:bg-blue-50 ${isSA && !ec?.editingId && !ec?.adding ? 'cursor-pointer' : ''}`}
              onDoubleClick={isSA && !ec?.editingId && !ec?.adding ? () => startEdit(r) : undefined}
            >
              <TD>{r.material_name ?? r.emissions_category_name ?? r.material_id ?? r.emissions_category_id ?? '—'}</TD>
              <TD>{r.jurisdiction_name ?? r.jurisdiction_id}</TD>
              <TD muted>{modeCell(r.truck_transport_mode, r.truck_distance)}</TD>
              <TD muted>{modeCell(r.rail_transport_mode, r.rail_distance)}</TD>
              <TD muted>{modeCell(r.sea_transport_mode, r.sea_distance)}</TD>
              <TD muted>{r.grade_applicability ?? '—'}</TD>
              <TD muted>{r.source ?? '—'}</TD>
              <TD>{r.effective_from ?? TODAY}</TD>
              <TD>{r.effective_to ?? DEFAULT_EFFECTIVE_TO}</TD>
              {isSA && (
                <TD>
                  {!ec?.editingId && !ec?.adding && ec?.onDelete && (
                    <button type="button" onClick={() => ec.onDelete!(r.id)} title="Delete row"
                      className="rounded cursor-pointer p-0.5 text-red-400 hover:text-red-600 hover:bg-red-50">
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
