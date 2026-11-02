import type { OperationalEquipmentRow, OperationalEquipmentEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: OperationalEquipmentRow[];
  editCtx?: OperationalEquipmentEditCtx;
}

export default function OperationalEquipmentTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const startEdit = (r: OperationalEquipmentRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      group_name:  r.group_name,
      item:        r.item,
      power_kw:    r.power_kw,
      hours_per_day: r.hours_per_day,
      days_per_year: r.days_per_year,
      source:      r.source ?? '',
    });
  };

  const previewMwh = (ec: OperationalEquipmentEditCtx): string => {
    const p = parseFloat(ec.editDraft.power_kw ?? '');
    const h = parseFloat(ec.editDraft.hours_per_day ?? '');
    const d = parseFloat(ec.editDraft.days_per_year ?? '');
    if (isNaN(p) || isNaN(h) || isNaN(d)) return '—';
    return ((p * h * d) / 1000).toFixed(4);
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Group</TH>
          <TH>Item</TH>
          <TH right normalCase>Power (kW)</TH>
          <TH right normalCase>Hours/day</TH>
          <TH right normalCase>Days/year</TH>
          <TH right normalCase>
            <span title="Calculated: Power × Hours × Days ÷ 1000">
              Annual MWh/yr *
            </span>
          </TH>
          <TH normalCase>Source</TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          const isEditing = ec?.editingId === r.id;
          if (isEditing && ec) {
            return (
              <tr key={r.id} className="bg-amber-50" tabIndex={-1}
                onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveEdit(); }}
                onKeyDown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelEdit(); } else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveEdit(); } }}
              >
                <TD>
                  <InlineInput
                    value={ec.editDraft.group_name ?? ''}
                    onChange={v => ec.onEditField('group_name', v)}
                    placeholder="Group"
                  />
                </TD>
                <TD>
                  <InlineInput
                    value={ec.editDraft.item ?? ''}
                    onChange={v => ec.onEditField('item', v)}
                    placeholder="Item"
                  />
                </TD>
                <TD right>
                  <InlineInput
                    type="number"
                    value={ec.editDraft.power_kw ?? ''}
                    onChange={v => ec.onEditField('power_kw', v)}
                    placeholder="kW"
                  />
                </TD>
                <TD right>
                  <InlineInput
                    type="number"
                    value={ec.editDraft.hours_per_day ?? ''}
                    onChange={v => ec.onEditField('hours_per_day', v)}
                    placeholder="hrs"
                  />
                </TD>
                <TD right>
                  <InlineInput
                    type="number"
                    value={ec.editDraft.days_per_year ?? ''}
                    onChange={v => ec.onEditField('days_per_year', v)}
                    placeholder="days"
                  />
                </TD>
                <TD right muted>
                  <span className="italic text-neutral-400">{previewMwh(ec)}</span>
                </TD>
                <TD>
                  <InlineInput
                    value={ec.editDraft.source ?? ''}
                    onChange={v => ec.onEditField('source', v)}
                    placeholder="Source"
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
              key={r.id ?? i}
              className={`even:bg-neutral-98 hover:bg-blue-50 ${isSA && !ec?.editingId ? 'cursor-pointer' : ''}`}
              onDoubleClick={isSA && !ec?.editingId ? () => startEdit(r) : undefined}
            >
              <TD>{r.group_name}</TD>
              <TD>{r.item}</TD>
              <TD right muted>{r.power_kw}</TD>
              <TD right muted>{r.hours_per_day}</TD>
              <TD right muted>{r.days_per_year}</TD>
              <TD right muted>
                <span className="italic">{r.annual_electricity_consumption_mwh}</span>
              </TD>
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
      {rows.length > 0 && (
        <tfoot>
          <tr>
            <td colSpan={isSA ? 8 : 7} className="px-2 py-1 text-neutral-400 text-[10px] italic">
              * Annual MWh/yr = Power (kW) × Hours/day × Days/year ÷ 1000 — calculated, not stored
            </td>
          </tr>
        </tfoot>
      )}
    </table>
  );
}
