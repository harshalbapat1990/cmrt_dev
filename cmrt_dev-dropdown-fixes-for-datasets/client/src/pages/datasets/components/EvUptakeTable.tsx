import { useMemo } from 'react';
import type { EvUptakeRow, EvUptakeEditCtx } from '../types';
import { InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: EvUptakeRow[];
  yearFrom: number;
  yearTo: number;
  editCtx?: EvUptakeEditCtx;
}

export default function EvUptakeTable({ rows, yearFrom, yearTo, editCtx }: Props) {
  const ec = editCtx;

  const cellMap = useMemo(() => {
    const m = new Map<string, EvUptakeRow>();
    for (const r of rows) {
      m.set(`${r.scenario_code}__${r.jurisdiction_id}__${r.vehicle_category_code}__${r.energy_type_code}__${r.year}`, r);
    }
    return m;
  }, [rows]);

  const series = useMemo(() => {
    const seen = new Set<string>();
    const result: Array<{
      scenarioCode: string; scenarioName: string | null;
      jurId: string; jurName: string | null;
      vehicleCategoryCode: string; vehicleCategoryName: string | null;
      energyTypeCode: string; energyTypeName: string | null;
    }> = [];
    for (const r of rows) {
      const key = `${r.scenario_code}__${r.jurisdiction_id}__${r.vehicle_category_code}__${r.energy_type_code}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push({
          scenarioCode: r.scenario_code,
          scenarioName: r.scenario_name,
          jurId: r.jurisdiction_id,
          jurName: r.jurisdiction_name,
          vehicleCategoryCode: r.vehicle_category_code,
          vehicleCategoryName: r.vehicle_category_name,
          energyTypeCode: r.energy_type_code,
          energyTypeName: r.energy_type_name,
        });
      }
    }
    return result.sort(
      (a, b) =>
        a.scenarioCode.localeCompare(b.scenarioCode) ||
        (a.jurName ?? a.jurId).localeCompare(b.jurName ?? b.jurId) ||
        a.vehicleCategoryCode.localeCompare(b.vehicleCategoryCode) ||
        a.energyTypeCode.localeCompare(b.energyTypeCode),
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

  const displayVal = (r: EvUptakeRow | undefined): string => {
    if (!r || r.uptake_pct == null) return '—';
    return (r.uptake_pct * 100).toFixed(2) + '%';
  };

  const stickyTd = 'sticky bg-white z-[1] border-r border-b border-neutral-90';
  const stickyTh = 'sticky bg-neutral-90 z-[2] border-r border-b border-neutral-90 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-base whitespace-nowrap text-left';

  return (
    <div className="overflow-x-auto overflow-y-auto h-full">
      <table className="border-collapse text-xs">
        <thead className="sticky top-0 z-10">
          <tr>
            <th className={`${stickyTh} left-0 min-w-[120px]`}>Scenario</th>
            <th className={`${stickyTh} left-[120px] min-w-[140px]`}>Vehicle Category</th>
            <th className={`${stickyTh} left-[260px] min-w-[110px]`}>Energy Type</th>
            {years.map(y => (
              <th
                key={y}
                className="px-2 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-base whitespace-nowrap border-r border-b border-neutral-90 text-right min-w-[64px] bg-neutral-90"
              >
                {y}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ec?.adding && (
            <tr className="bg-blue-50">
              <td className={`${stickyTd} left-0 px-2 py-1.5 min-w-[120px]`}>
                <div className="flex flex-col gap-0.5">
                  <InlineSelect
                    value={ec.addDraft.scenarioCode}
                    options={ec.scenarioOpts}
                    onChange={v => ec.onAddField('scenarioCode', v)}
                    placeholder="— scenario —"
                  />
                  <InlineSelect
                    value={ec.addDraft.jurisdictionId}
                    options={ec.jurOpts}
                    onChange={v => ec.onAddField('jurisdictionId', v)}
                    placeholder="— jurisdiction —"
                  />
                </div>
              </td>
              <td className={`${stickyTd} left-[120px] px-2 py-1.5 min-w-[140px]`}>
                <InlineSelect
                  value={ec.addDraft.vehicleCategoryCode}
                  options={ec.vehicleCategoryOpts}
                  onChange={v => ec.onAddField('vehicleCategoryCode', v)}
                  placeholder="— vehicle category —"
                />
              </td>
              <td className={`${stickyTd} left-[260px] px-2 py-1.5 min-w-[110px]`}>
                <InlineSelect
                  value={ec.addDraft.energyTypeCode}
                  options={ec.energyTypeOpts}
                  onChange={v => ec.onAddField('energyTypeCode', v)}
                  placeholder="— energy type —"
                />
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
              key={`${s.scenarioCode}__${s.jurId}__${s.vehicleCategoryCode}__${s.energyTypeCode}`}
              className="even:bg-neutral-98 hover:bg-primary/5"
            >
              <td className={`${stickyTd} left-0 px-3 py-2 text-xs font-medium text-text-dark whitespace-nowrap min-w-[120px]`}>
                {s.scenarioName ?? s.scenarioCode}
              </td>
              <td className={`${stickyTd} left-[120px] px-3 py-2 text-xs text-text-base whitespace-nowrap min-w-[140px]`}>
                {s.vehicleCategoryName ?? s.vehicleCategoryCode}
              </td>
              <td className={`${stickyTd} left-[260px] px-3 py-2 text-xs text-text-base whitespace-nowrap min-w-[110px]`}>
                {s.energyTypeName ?? s.energyTypeCode}
              </td>
              {years.map(y => {
                const cell = cellMap.get(`${s.scenarioCode}__${s.jurId}__${s.vehicleCategoryCode}__${s.energyTypeCode}__${y}`);
                const isEditing = !!cell && ec?.editCellId === cell.id;

                if (isEditing && ec) {
                  return (
                    <td key={y} className="px-1 py-1 border-r border-b border-neutral-90 min-w-[100px]">
                      <div className="flex items-center gap-0.5">
                        <InlineInput
                          value={ec.cellDraft}
                          onChange={ec.onCellChange}
                          placeholder="% value"
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
                const isBlank = val === '—';
                const canClick = !!ec && !ec.editCellId && !ec.adding && !!cell;

                return (
                  <td
                    key={y}
                    className={[
                      'px-2 py-2 text-xs text-right tabular-nums border-r border-b border-neutral-90',
                      isBlank ? 'text-text-base' : 'text-text-dark',
                      canClick ? 'cursor-pointer hover:bg-amber-50' : '',
                    ].join(' ')}
                    title={canClick ? 'Click to edit' : ''}
                    onClick={canClick ? () => ec.onEditCell(cell!.id) : undefined}
                  >
                    {val}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
