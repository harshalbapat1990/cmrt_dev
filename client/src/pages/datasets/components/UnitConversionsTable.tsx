import type { UnitConversionRow, UnitConversionEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: UnitConversionRow[];
  editCtx?: UnitConversionEditCtx;
}

export default function UnitConversionsTable({ rows, editCtx }: Props) {
  const ec = editCtx;

  const startEdit = (r: UnitConversionRow) => {
    if (!ec) return;
    ec.onStartEdit(r.id, {
      factor: r.factor ?? '',
    });
  };

  const formatNumber = (value: string | number | null) => {
    if (!value) return '—';
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return '—';
    // Format without scientific notation
    return num.toLocaleString('en-US', { useGrouping: true, maximumFractionDigits: 20 });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>From Unit</TH>
          <TH>To Unit</TH>
          <TH right>Conversion Factor</TH>
          {ec && <TH>Actions</TH>}
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
                <TD muted>{r.from_unit ? (r.from_unit.label ?? r.from_unit.code) : '—'}</TD>
                <TD muted>{r.to_unit ? (r.to_unit.label ?? r.to_unit.code) : '—'}</TD>
                <TD right>
                  <InlineInput
                    type="number"
                    value={ec.editDraft.factor ?? ''}
                    onChange={v => ec.onEditField('factor', v)}
                    placeholder="Factor"
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
              className={`even:bg-neutral-98 hover:bg-blue-50 ${ec && !ec.editingId ? 'cursor-pointer' : ''}`}
              onDoubleClick={ec && !ec.editingId ? () => startEdit(r) : undefined}
            >
              <TD>{r.from_unit ? (r.from_unit.label ?? r.from_unit.code) : '—'}</TD>
              <TD>{r.to_unit ? (r.to_unit.label ?? r.to_unit.code) : '—'}</TD>
              <TD right muted={!r.factor}>{formatNumber(r.factor)}</TD>
              {ec && (
                <TD>
                  {!ec.editingId && ec.onDelete && (
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
