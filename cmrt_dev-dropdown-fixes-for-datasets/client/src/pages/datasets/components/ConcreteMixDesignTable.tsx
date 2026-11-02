import { useMemo } from 'react';
import {
  CONCRETE_MIX_STRENGTHS,
  type ConcreteMixAssumption,
  type ConcreteMixDesignRow,
  type ConcreteMixEditCtx,
  type ConcreteMixStrengthField,
} from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

type RowKind = 'input' | 'calc';
const COMPONENT_ORDER: ReadonlyArray<{
  code: string;
  label: string;
  kind: RowKind;

  calc?: 'general_purpose_cement' | 'fly_ash' | 'ggbf_slag';
}> = [
  { code: 'total_cementitious_content', label: 'Total cementitious content', kind: 'input' },
  { code: 'general_purpose_cement',     label: 'General purpose cement',     kind: 'calc', calc: 'general_purpose_cement' },
  { code: 'fly_ash',                    label: 'Fly ash',                    kind: 'calc', calc: 'fly_ash' },
  { code: 'ggbf_slag',                  label: 'GGBF slag',                  kind: 'calc', calc: 'ggbf_slag' },
  { code: 'silica_fume',                label: 'Silica Fume',                kind: 'input' },
  { code: 'fine_aggregates',            label: 'Fine Aggregates',            kind: 'input' },
  { code: 'coarse_aggregates',          label: 'Coarse Aggregates',          kind: 'input' },
  { code: 'recycled_aggregates',        label: 'Recycled Aggregates',        kind: 'input' },
  { code: 'manufactured_sand',          label: 'Manufactured sand',          kind: 'input' },
  { code: 'mains_water',                label: 'Mains Water',                kind: 'input' },
  { code: 'onsite_recycled_water',      label: 'Onsite Recycled / Captured Water', kind: 'input' },
  { code: 'admixture',                  label: 'Admixture',                  kind: 'input' },
];

const STRENGTH_FIELDS: ReadonlyArray<{ strength: typeof CONCRETE_MIX_STRENGTHS[number]; field: ConcreteMixStrengthField }> = [
  { strength: 20,  field: 'strength_20_kg_m3'  },
  { strength: 25,  field: 'strength_25_kg_m3'  },
  { strength: 32,  field: 'strength_32_kg_m3'  },
  { strength: 40,  field: 'strength_40_kg_m3'  },
  { strength: 50,  field: 'strength_50_kg_m3'  },
  { strength: 65,  field: 'strength_65_kg_m3'  },
  { strength: 80,  field: 'strength_80_kg_m3'  },
  { strength: 100, field: 'strength_100_kg_m3' },
];

interface Props {
  assumptions: ConcreteMixAssumption | null;
  rows: ConcreteMixDesignRow[];
  editCtx?: ConcreteMixEditCtx;
}

const toNumber = (v: unknown): number | null => {
  if (v === null || v === undefined || v === '') return null;
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : null;
};

const fmtKgM3 = (v: number | null): string => {
  if (v === null) return '—';
  return Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/\.?0+$/, '');
};

const fmtPctInput = (v: unknown): string => {
  // values are stored as fractions in [0, 1]; display as percentage
  const n = toNumber(v);
  if (n === null) return '';
  return (n * 100).toString();
};

export default function ConcreteMixDesignTable({ assumptions, rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  // Build a lookup by component_code so we can render in the canonical order
  // regardless of API order, and recover the row-id needed to edit cells.
  const byCode = useMemo(() => {
    const m = new Map<string, ConcreteMixDesignRow>();
    for (const r of rows) m.set(r.component_code.toLowerCase(), r);
    return m;
  }, [rows]);

  const totalRow = byCode.get('total_cementitious_content');
  const bauScm = toNumber(assumptions?.bau_scm_content_pct);
  const maxFly = toNumber(assumptions?.default_max_fly_ash_pct);

  const calcCellValue = (
    calc: 'general_purpose_cement' | 'fly_ash' | 'ggbf_slag',
    field: ConcreteMixStrengthField,
  ): number | null => {
    if (!totalRow) return null;
    const total = toNumber((totalRow as unknown as Record<string, unknown>)[field]);
    if (total === null || bauScm === null || maxFly === null) return null;
    if (calc === 'general_purpose_cement') return (1 - bauScm) * total;
    if (calc === 'fly_ash')                return (bauScm < maxFly ? bauScm : maxFly) * total;
    /* ggbf_slag */                          return bauScm > maxFly ? (bauScm - maxFly) * total : 0;
  };


  const renderAssumptionInput = (
    field: 'bau_scm_content_pct' | 'default_max_fly_ash_pct',
    tooltip?: string,
  ) => {
    const isEditing = ec?.assumptionField === field;
    const current = field === 'bau_scm_content_pct'
      ? assumptions?.bau_scm_content_pct
      : assumptions?.default_max_fly_ash_pct;
    const display = fmtPctInput(current);

    return (
      <div className="flex items-center gap-2">
        {isSA && isEditing && ec ? (
          <div
            className="flex items-center gap-1"
            tabIndex={-1}
            onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveAssumption(); }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelAssumption(); }
              else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveAssumption(); }
            }}
          >
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              autoFocus
              value={ec.assumptionDraft}
              onChange={e => ec.onAssumptionChange(e.target.value)}
              className="w-24 rounded border border-primary px-2 py-1 text-xs focus:outline-none"
            />
            <span className="text-xs text-text-base">%</span>
            <SaveCancelButtons
              onSave={ec.onSaveAssumption}
              onCancel={ec.onCancelAssumption}
              saving={ec.saving}
              error={ec.saveError}
            />
          </div>
        ) : (
          <button
            type="button"
            disabled={!isSA}
            onClick={isSA ? () => ec!.onEditAssumption(field, display) : undefined}
            className={`min-w-[7rem] rounded cursor-pointer border px-3 py-1.5 text-left text-xs ${
              isSA
                ? 'border-neutral-80 bg-white hover:border-primary cursor-text'
                : 'border-neutral-90 bg-neutral-98 cursor-default'
            }`}
            title={isSA ? 'Click to edit' : undefined}
          >
            {display !== '' ? `${display}%` : '—'}
          </button>
        )}
        {tooltip && (
          <span
            className="material-symbols-rounded text-[16px] leading-none text-text-base cursor-help"
            title={tooltip}
            aria-label={tooltip}
          >
            info
          </span>
        )}
      </div>
    );
  };

  const renderCell = (
    row: ConcreteMixDesignRow | undefined,
    field: ConcreteMixStrengthField,
    kind: RowKind,
    calc?: 'general_purpose_cement' | 'fly_ash' | 'ggbf_slag',
    cellKeyPrefix?: string,
  ) => {
    const reactKey = `${cellKeyPrefix ?? ''}-${field}`;
    if (kind === 'calc') {
      const v = calc ? calcCellValue(calc, field) : null;
      return (
        <td
          key={reactKey}
          className="px-3 py-2 text-xs border-r border-b border-neutral-90 last:border-r-0 text-right tabular-nums text-text-base"
        >
          <span className="italic text-neutral-400">{fmtKgM3(v)}</span>
        </td>
      );
    }

    if (!row) {
      return (
        <td
          key={reactKey}
          className="px-3 py-2 text-xs border-r border-b border-neutral-90 last:border-r-0 text-right tabular-nums text-text-base"
        >
          —
        </td>
      );
    }

    const cellKey = `${row.id}::${field}`;
    const isEditing = ec?.editCellKey === cellKey;
    const v = toNumber((row as unknown as Record<string, unknown>)[field]);

    if (isEditing && ec) {
      return (
        <td
          key={reactKey}
          className="px-3 py-2 text-xs border-r border-b border-neutral-90 last:border-r-0 text-right tabular-nums text-text-dark bg-amber-50"
        >
          <div
            className="flex items-center justify-end gap-1"
            tabIndex={-1}
            onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveCell(); }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelCell(); }
              else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveCell(); }
            }}
          >
            <InlineInput
              type="number"
              value={ec.cellDraft}
              onChange={(val) => ec.onCellChange(val)}
              placeholder="kg/m3"
            />
            <SaveCancelButtons
              onSave={ec.onSaveCell}
              onCancel={ec.onCancelCell}
              saving={ec.saving}
              error={ec.saveError}
            />
          </div>
        </td>
      );
    }

    return (
      <td
        key={reactKey}
        className="px-3 py-2 text-xs border-r border-b border-neutral-90 last:border-r-0 text-right tabular-nums text-text-base"
      >
        <button
          type="button"
          disabled={!isSA}
          onClick={isSA ? () => ec!.onEditCell(row.id, field, v === null ? '' : String(v)) : undefined}
          className={`w-full text-right cursor-pointer tabular-nums ${isSA ? 'cursor-text hover:text-primary' : 'cursor-default'}`}
        >
          {fmtKgM3(v)}
        </button>
      </td>
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-3xl">
        <div className="rounded border border-neutral-90 bg-white px-3 py-2">
          <div className="text-[11px] font-medium uppercase tracking-wide text-text-base mb-1">
            BAU SCM Content (%)
          </div>
          {renderAssumptionInput('bau_scm_content_pct')}
          {/* <div className="text-[10px] text-text-faint mt-1">
            User input value, percentage (0-100%)
          </div> */}
        </div>
        <div className="rounded border border-neutral-90 bg-white px-3 py-2">
          <div className="text-[11px] font-medium uppercase tracking-wide text-text-base mb-1">
            Default max fly ash (%)
          </div>
          {renderAssumptionInput(
            'default_max_fly_ash_pct',
            'Fly ash content beyond which slag is assumed to be used for remaining SCM content',
          )}
         
        </div>
      </div>

      <table className="w-full border-collapse text-xs">
        <thead className="sticky top-0 z-10 bg-neutral-90">
          <tr>
            <TH>Strength (MPa)</TH>
            {STRENGTH_FIELDS.map(s => (
              <TH key={s.strength} right normalCase>{s.strength}</TH>
            ))}
          </tr>
          <tr>
            <TH normalCase>Component</TH>
            {STRENGTH_FIELDS.map(s => (
              <TH key={`${s.strength}-sub`} right normalCase>
                Default Mix Content (kg/m3)
              </TH>
            ))}
          </tr>
        </thead>
        <tbody>
          {COMPONENT_ORDER.map(comp => {
            const row = byCode.get(comp.code);
            return (
              <tr
                key={comp.code}
                className={`even:bg-neutral-98 ${comp.kind === 'calc' ? 'bg-neutral-95/50' : ''}`}
              >
                <TD>
                  <div className="flex items-center gap-1">
                    {comp.label}
                    {comp.kind === 'calc' && (
                      <span
                        //className="material-symbols-rounded text-[14px] leading-none text-text-faint"
                        //title="Calculated value (read-only)"
                        //aria-label="Calculated"
                      >
                        {/* calculate */}
                      </span>
                    )}
                  </div>
                </TD>
                {STRENGTH_FIELDS.map(s =>
                  renderCell(row, s.field, comp.kind, comp.calc, comp.code)
                )}
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={1 + STRENGTH_FIELDS.length} className="px-2 py-1 text-neutral-400 text-[10px] italic">
              * General purpose cement, Fly ash and GGBF slag are calculated from the
              BAU SCM content, Default max fly ash and Total cementitious content row.
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
