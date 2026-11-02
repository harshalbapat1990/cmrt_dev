import { useMemo } from 'react';
import type { DecarbRow, DecarbEditCtx, NamedOption } from '../types';
import { InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: DecarbRow[];
  yearFrom: number;
  yearTo: number;
  editCtx?: DecarbEditCtx;
}

export default function ElectricDecarbTable({ rows, yearFrom, yearTo, editCtx }: Props) {
  const ec = editCtx;
  const isPct = rows[0]?.unit?.code === '%';
  const unit = rows[0]?.unit ? (rows[0].unit.label ?? rows[0].unit.code) : '';

  const hasRegion = rows.some(r => r.region_id != null) || (ec?.activeFtHasRegion ?? false);

  const cellMap = useMemo(() => {
    const m = new Map<string, DecarbRow>();
    for (const r of rows) {
      m.set(`${r.jurisdiction_id}__${r.region_id ?? ''}__${r.year}`, r);
    }
    return m;
  }, [rows]);

  const series = useMemo(() => {
    const seen = new Set<string>();
    const result: Array<{ jurId: string; jurName: string; regionId: string | null; regionName: string | null }> = [];
    for (const r of rows) {
      const key = `${r.jurisdiction_id}__${r.region_id ?? ''}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push({
          jurId: r.jurisdiction_id,
          jurName: r.jurisdiction_name ?? r.jurisdiction_id,
          regionId: r.region_id,
          regionName: r.region_name,
        });
      }
    }
    return result.sort(
      (a, b) =>
        a.jurName.localeCompare(b.jurName) ||
        (a.regionName ?? '').localeCompare(b.regionName ?? ''),
    );
  }, [rows]);

  const years = useMemo(() => {
    const allYears = new Set(rows.map(r => r.year));
    const out: number[] = [];
    for (let y = yearFrom; y <= yearTo; y++) {
      if (allYears.has(y)) out.push(y);
    }
    return out;
  }, [rows, yearFrom, yearTo]);

  const displayVal = (r: DecarbRow | undefined): string => {
    if (!r) return '—';
    if (r.value_qualifier === 'D') return 'D';
    if (r.value == null) return '—';
    return isPct ? (r.value * 100).toFixed(2) : String(r.value);
  };

  const addRegionOpts: NamedOption[] = useMemo(() => {
    if (!ec?.addDraft.jurisdictionId) return [];
    return ec.allRegions
      .filter(r => r.jurisdictionId === ec.addDraft.jurisdictionId)
      .map(r => ({ id: r.id, name: r.name }));
  }, [ec?.allRegions, ec?.addDraft.jurisdictionId]);

  const stickyTd = 'sticky bg-white z-[1] border-r border-b border-neutral-90';
  const stickyTh = 'sticky bg-neutral-90 z-[2] border-r border-b border-neutral-90 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-base whitespace-nowrap text-left';

  return (
    <div>
      <p className="mb-2 text-xs text-text-base italic px-4">
        * These values represent mandatory renewable electricity requirements for liable entities as used in the market-based emissions
        calculations. This is determined by the Clean Energy Regulator in Australia and not relevant to New Zealand.
      </p>
      <div className="overflow-x-auto overflow-y-auto h-full">
        <table className="border-collapse text-xs">
          <thead className="sticky top-0 z-10">
            <tr>
              {hasRegion && (
                <th className={`${stickyTh} left-0 min-w-[150px]`}>Region</th>
              )}
              {years.map(y => (
                <th
                  key={y}
                  className="px-2 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-base whitespace-nowrap border-r border-b border-neutral-90 text-right min-w-[58px] bg-neutral-90"
                >
                  {y}
                </th>
              ))}
              <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-base whitespace-nowrap border-b border-neutral-90 text-left bg-neutral-90 min-w-[80px]">
                Unit
              </th>
            </tr>
          </thead>
          <tbody>
            {ec?.adding && (
              <tr className="bg-blue-50">
                <td className={`${stickyTd} left-0 px-2 py-1.5 min-w-[150px]`}>
                  <div className="flex flex-col gap-0.5">
                    <InlineSelect
                      value={ec.addDraft.jurisdictionId}
                      options={ec.jurOpts}
                      onChange={v => ec.onAddField('jurisdictionId', v)}
                      placeholder="— jurisdiction —"
                    />
                    {hasRegion && (
                      <InlineSelect
                        value={ec.addDraft.regionId}
                        options={addRegionOpts}
                        onChange={v => ec.onAddField('regionId', v)}
                        placeholder={
                          ec.addDraft.jurisdictionId ? '— region —' : '— pick jurisdiction first —'
                        }
                      />
                    )}
                  </div>
                </td>
                {years.map(y => (
                  <td key={y} className="px-2 py-1.5 border-r border-b border-neutral-90 text-center text-text-base tabular-nums">
                    —
                  </td>
                ))}
                <td className="px-3 py-1.5 border-b border-neutral-90">
                  <SaveCancelButtons
                    onSave={ec.onSaveAdd}
                    onCancel={ec.onCancelAdd}
                    saving={ec.saving}
                    error={ec.saveError}
                  />
                </td>
              </tr>
            )}

            {series.map(s => (
              <tr
                key={`${s.jurId}__${s.regionId ?? ''}`}
                className="even:bg-neutral-98 hover:bg-primary/5"
              >
                {hasRegion && (
                  <td className={`${stickyTd} left-0 px-3 py-2 text-xs text-text-base whitespace-nowrap min-w-[150px]`}>
                    {s.regionName ?? '—'}
                  </td>
                )}
                {years.map(y => {
                  const cell = cellMap.get(`${s.jurId}__${s.regionId ?? ''}__${y}`);
                  const isEditing = !!cell && ec?.editCellId === cell.id;

                  if (isEditing && ec) {
                    return (
                      <td key={y} className="px-1 py-1 border-r border-b border-neutral-90 min-w-[100px]">
                        <div className="flex items-center gap-0.5">
                          <InlineInput
                            value={ec.cellDraft}
                            onChange={ec.onCellChange}
                            placeholder="value or D"
                          />
                          <button
                            type="button"
                            onClick={ec.onSaveCell}
                            disabled={ec.saving}
                            title="Save"
                            className="shrink-0 cursor-pointer rounded bg-primary p-0.5 text-white disabled:opacity-40 hover:bg-primary/90"
                          >
                            <span className="material-symbols-rounded text-[12px] leading-none">check</span>
                          </button>
                          <button
                            type="button"
                            onClick={ec.onCancelCell}
                            title="Cancel"
                            className="shrink-0 cursor-pointer rounded border border-neutral-80 bg-white p-0.5 text-text-base hover:bg-neutral-98"
                          >
                            <span className="material-symbols-rounded text-[12px] leading-none">close</span>
                          </button>
                        </div>
                        {ec.saveError && (
                          <p className="text-[10px] text-red-600 mt-0.5 max-w-[96px]">{ec.saveError}</p>
                        )}
                      </td>
                    );
                  }

                  const val = displayVal(cell);
                  const isD = cell?.value_qualifier === 'D';
                  const isBlank = val === '—';
                  const canClick =
                    !!ec && !ec.editCellId && !ec.adding && !!cell;

                  return (
                    <td
                      key={y}
                      className={[
                        'px-2 cursor-pointer py-2 text-xs text-right tabular-nums border-r border-b border-neutral-90',
                        isD ? 'text-amber-600 font-medium' : '',
                        isBlank && !isD ? 'text-text-base' : 'text-text-dark',
                        canClick ? 'cursor-pointer hover:bg-amber-50' : '',
                      ].join(' ')}
                      title={
                        isD ? 'Disclosed but withheld — click to edit'
                          : canClick ? 'Click to edit'
                            : ''
                      }
                      onClick={canClick ? () => ec.onEditCell(cell!.id) : undefined}
                    >
                      {val}
                    </td>
                  );
                })}
                <td className="px-3 py-2 text-xs text-text-base border-b border-neutral-90 whitespace-nowrap">
                  {unit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

