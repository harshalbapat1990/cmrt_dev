import type { ElectricityRecyclingAssumptionRow, ElectricityRecyclingEditCtx } from '../types';
import { TH, TD, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: ElectricityRecyclingAssumptionRow[];
  editCtx?: ElectricityRecyclingEditCtx;
}

const toNumber = (v: unknown): number | null => {
  if (v === null || v === undefined || v === '') return null;
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : null;
};

const fmtPctDisplay = (v: unknown): string => {
  const n = toNumber(v);
  if (n === null) return '—';
  const pct = n * 100;
  return Number.isInteger(pct) ? `${pct}%` : `${pct.toFixed(2).replace(/\.?0+$/, '')}%`;
};

const fmtPctInput = (v: unknown): string => {
  const n = toNumber(v);
  if (n === null) return '';
  return (n * 100).toString();
};

export default function ElectricityRecyclingAssumptionsTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Metric</TH>
          <TH right>Default BAU(%)</TH>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const isEditing = ec?.editRowId === r.id;
          const editable = !r.is_calculated;

          return (
            <tr key={r.id} className="even:bg-neutral-98 hover:bg-blue-50">
              <TD muted>{r.metric_label || '—'}</TD>
              <TD right>
                {isSA && editable && isEditing && ec ? (
                  <div
                    className="inline-flex items-center gap-1 justify-end"
                    tabIndex={-1}
                    onBlur={(e) => {
                      if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveCell();
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelCell(); }
                      else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveCell(); }
                    }}
                  >
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step="any"
                      value={ec.cellDraft}
                      onChange={(e) => ec.onCellChange(e.target.value)}
                      className="w-24 rounded border border-neutral-80 px-2 py-0.5 text-right text-xs focus:outline-none focus:border-primary"
                      autoFocus
                    />
                    <span className="text-text-base">%</span>
                    <SaveCancelButtons onSave={ec.onSaveCell} onCancel={ec.onCancelCell} saving={ec.saving} />
                  </div>
                ) : isSA && editable ? (
                  <button
                    type="button"
                    className="rounded cursor-pointer px-1 py-0.5 hover:bg-neutral-90"
                    onClick={() => ec!.onEditCell(r.id, fmtPctInput(r.default_bau_pct))}
                    title="Click to edit"
                  >
                    {fmtPctDisplay(r.default_bau_pct)}
                  </button>
                ) : (
                  <span className={r.is_calculated ? 'text-text-base italic' : undefined}>
                    {fmtPctDisplay(r.default_bau_pct)}
                  </span>
                )}
              </TD>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
