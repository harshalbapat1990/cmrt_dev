import { useMemo } from 'react';
import type { CarbonValueRow, CarbonValueEditCtx, NamedOption } from '../types';
import { InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: CarbonValueRow[];
  yearFrom: number;
  yearTo: number;
  editCtx?: CarbonValueEditCtx;
}

export default function CarbonValuesTable({ rows, yearFrom, yearTo, editCtx }: Props) {
  const ec = editCtx;

  const cellMap = useMemo(() => {
    const m = new Map<string, CarbonValueRow>();
    for (const r of rows) {
      m.set(`${r.jurisdiction_id}__${r.range_code}__${r.year}`, r);
    }
    return m;
  }, [rows]);

  const series = useMemo(() => {
    const seen = new Set<string>();
    const result: Array<{ jurId: string; jurName: string; rangeCode: string; rangeName: string | null }> = [];
    for (const r of rows) {
      const key = `${r.jurisdiction_id}__${r.range_code}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push({
          jurId: r.jurisdiction_id,
          jurName: r.jurisdiction_name ?? r.jurisdiction_id,
          rangeCode: r.range_code,
          rangeName: r.range_name,
        });
      }
    }
    return result.sort(
      (a, b) =>
        a.jurName.localeCompare(b.jurName) ||
        (a.rangeName ?? '').localeCompare(b.rangeName ?? ''),
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

  const displayVal = (r: CarbonValueRow | undefined): string => {
    if (!r) return '—';
    if (r.value == null) return '—';
    return `$${r.value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
  };

  const addRangeOpts: NamedOption[] = ec?.rangeOpts ?? [];

  const stickyTd = 'sticky bg-white z-[1] border-r border-b border-neutral-90';
  const stickyTh = 'sticky bg-neutral-90 z-[2] border-r border-b border-neutral-90 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-base whitespace-nowrap text-left';

  return (
    <div className="overflow-x-auto overflow-y-auto h-full">
      <table className="border-collapse text-xs">
        <thead className="sticky top-0 z-10">
          <tr>
            <th className={`${stickyTh} left-0 min-w-[100px]`}>Range</th>
            {years.map(y => (
              <th
                key={y}
                className="px-2 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-base whitespace-nowrap border-r border-b border-neutral-90 text-right min-w-[70px] bg-neutral-90"
              >
                {y}
              </th>
            ))}
            <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-base whitespace-nowrap border-b border-neutral-90 text-left bg-neutral-90 min-w-[80px]">
              Currency
            </th>
          </tr>
        </thead>
        <tbody>
          {ec?.adding && (
            <tr className="bg-blue-50">
              <td className={`${stickyTd} left-0 px-2 py-1.5 min-w-[100px]`}>
                <div className="flex flex-col gap-0.5">
                  <InlineSelect
                    value={ec.addDraft.jurisdictionId}
                    options={ec.jurOpts}
                    onChange={v => ec.onAddField('jurisdictionId', v)}
                    placeholder="— jurisdiction —"
                  />
                  <InlineSelect
                    value={ec.addDraft.rangeCode}
                    options={addRangeOpts}
                    onChange={v => ec.onAddField('rangeCode', v)}
                    placeholder="— range —"
                  />
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
              key={`${s.jurId}__${s.rangeCode}`}
              className="even:bg-neutral-98 hover:bg-primary/5"
            >
              <td className={`${stickyTd} left-0 px-3 py-2 text-xs text-text-base whitespace-nowrap min-w-[100px]`}>
                {s.rangeName ?? s.rangeCode}
              </td>
              {years.map(y => {
                const cell = cellMap.get(`${s.jurId}__${s.rangeCode}__${y}`);
                const isEditing = !!cell && ec?.editCellId === cell.id;

                if (isEditing && ec) {
                  return (
                    <td key={y} className="px-1 py-1 border-r border-b border-neutral-90 min-w-[120px]">
                      <div className="flex items-center gap-0.5">
                        <InlineInput
                          value={ec.cellDraft}
                          onChange={ec.onCellChange}
                          placeholder="value"
                        />
                        <button
                          type="button"
                          onClick={ec.onSaveCell}
                          disabled={ec.saving}
                          title="Save"
                          className="shrink-0 rounded cursor-pointer bg-primary p-0.5 text-white disabled:opacity-40 hover:bg-primary/90"
                        >
                          <span className="material-symbols-rounded text-[12px] leading-none">check</span>
                        </button>
                        <button
                          type="button"
                          onClick={ec.onCancelCell}
                          title="Cancel"
                          className="shrink-0 rounded cursor-pointer border border-neutral-80 bg-white p-0.5 text-text-base hover:bg-neutral-98"
                        >
                          <span className="material-symbols-rounded text-[12px] leading-none">close</span>
                        </button>
                      </div>
                      {ec.saveError && (
                        <p className="text-[10px] text-red-600 mt-0.5 max-w-[110px]">{ec.saveError}</p>
                      )}
                    </td>
                  );
                }

                const val = displayVal(cell);
                const isBlank = val === '—';
                const canClick =
                  !!ec && !ec.editCellId && !!cell;

                return (
                  <td
                    key={y}
                    className={[
                      'px-2 py-2 text-xs text-right tabular-nums cursor-pointer border-r border-b border-neutral-90',
                      isBlank ? 'text-text-base' : 'text-text-dark font-medium',
                      canClick ? 'cursor-pointer hover:bg-amber-50' : '',
                    ].join(' ')}
                    onClick={canClick ? () => ec.onEditCell(cell!.id) : undefined}
                  >
                    {val}
                  </td>
                );
              })}
              <td className="px-2 py-2 text-xs text-text-base border-b border-neutral-90">
                {rows.find(r => r.jurisdiction_id === s.jurId && r.range_code === s.rangeCode)?.currency || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
