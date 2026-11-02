import { useMemo } from "react";
import { formatDisplayNumber } from "@/utils/utils";
import { MITIGATION_TYPE_LABEL, type Mitigation } from "../mitigationTypes";

interface MitigationSummaryViewProps {
  mitigations: Mitigation[];
  embedded?: boolean;
}

export function MitigationSummaryView({ mitigations, embedded = false }: MitigationSummaryViewProps) {
  const maxSaving = mitigations.length > 0
    ? Math.max(...mitigations.map((mitigation) => mitigation.estimatedSavingTco2e || 0), 1)
    : 1;

  return (
    <div className={embedded ? "flex flex-col flex-1 min-h-0 w-full" : "px-12 py-6 flex flex-col flex-1 min-h-0"}>
      {!embedded && <h2 className="text-2xl text-text-dark mb-6">Mitigations summary</h2>}
      <div className="bg-white border border-neutral-90 rounded-[var(--radius-3)] p-6 flex-1 min-h-0 flex flex-col">
        <div className="flex text-sm font-medium text-text-base border-b border-neutral-90 pb-3 mb-4 shrink-0">
          <div className="flex-1">Mitigation name</div>
          <div className="w-52 text-right shrink-0">Total savings (tCO<sub>2</sub>e)</div>
        </div>
        <div className="flex flex-col gap-4 overflow-y-auto flex-1 min-h-0 pr-1">
          {mitigations.length === 0 ? (
            <div className="text-sm text-text-faint py-8 text-center">No mitigations to summarize yet.</div>
          ) : mitigations.map((mitigation) => {
            const saving = mitigation.estimatedSavingTco2e || 0;
            const percentage = maxSaving > 0 ? Math.min(100, (saving / maxSaving) * 100) : 0;
            return (
              <div key={mitigation.id} className="flex items-center gap-4">
                <div className="flex-1 text-sm text-text-dark truncate">{mitigation.name}</div>
                <div className="w-52 flex items-center gap-2 justify-end shrink-0">
                  <div className="flex-1 min-w-[72px] h-2 bg-neutral-95 rounded overflow-hidden">
                    <div className="h-full bg-success/70 rounded" style={{ width: `${percentage}%` }} />
                  </div>
                  <span className="tabular-nums text-sm text-text-dark w-[110px] text-right">
                    {formatDisplayNumber(saving)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

interface MitigationsListProps {
  mitigations: Mitigation[];
  onAdd?: () => void;
  onDelete?: (id: string) => void;
  onEdit?: (mitigation: Mitigation) => void;
  allowMutations?: boolean;
  viewOnlyInteraction?: boolean;
  onOpenRow?: (mitigation: Mitigation) => void;
  embedded?: boolean;
}

export function MitigationsList({
  mitigations,
  onAdd,
  onDelete,
  onEdit,
  allowMutations = true,
  viewOnlyInteraction = false,
  onOpenRow,
  embedded = false,
}: MitigationsListProps) {
  const totalSaving = mitigations.reduce((sum, mitigation) => sum + (mitigation.estimatedSavingTco2e || 0), 0);
  const grouped = useMemo(() => {
    const groups = new Map<string, Mitigation[]>();
    for (const mitigation of mitigations) {
      const group = mitigation.group?.trim() ? mitigation.group.trim() : "Ungrouped";
      const items = groups.get(group) ?? [];
      items.push(mitigation);
      groups.set(group, items);
    }
    return Array.from(groups.entries());
  }, [mitigations]);

  return (
    <div className={embedded ? "" : "px-12 py-6"}>
      <div className="flex items-center justify-between mb-4">
        <div>{!embedded && <h2 className="text-2xl text-text-dark">Mitigations</h2>}</div>
        {allowMutations && onAdd && (
          <button type="button" onClick={onAdd} className="inline-flex items-center gap-2 px-4 py-2 text-sm cursor-pointer rounded-[var(--radius-3)] bg-primary text-white hover:bg-primary/90">
            <span className="material-symbols-rounded text-base leading-none">add</span>
            Add mitigation
          </button>
        )}
      </div>

      {mitigations.length > 0 && (
        <div className="bg-white border border-neutral-90 rounded-[var(--radius-3)] p-5 mb-6 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide text-text-faint">Total estimated saving</div>
            <div className="text-[28px] font-bold text-text-dark leading-tight">
              {formatDisplayNumber(totalSaving)} <span className="font-light">tCO<sub>2</sub>e</span>
            </div>
          </div>
          <div className="text-sm text-text-faint">{mitigations.length} mitigation{mitigations.length === 1 ? "" : "s"}</div>
        </div>
      )}

      <div className="bg-white border border-neutral-90 rounded-[var(--radius-3)]">
        <table className="w-full text-sm">
          <thead className="bg-neutral-95 text-text-base uppercase text-xs tracking-wide">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Mitigation name</th>
              <th className="text-left px-4 py-3 font-medium">Project stage</th>
              <th className="text-left px-4 py-3 font-medium">Mitigation category</th>
              <th className="text-right px-4 py-3 font-medium">Emissions savings (tCO<sub>2</sub>e)</th>
              <th className="text-left px-4 py-3 font-medium">Notes / Comments (optional)</th>
              {(allowMutations || viewOnlyInteraction) && <th className="px-4 py-3 text-right font-medium">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {mitigations.length === 0 ? (
              <tr className="border-t border-neutral-90">
                <td colSpan={allowMutations || viewOnlyInteraction ? 7 : 6} className="px-4 py-10 text-center">
                  <div className="text-text-dark font-medium">No mitigations yet</div>
                  <div className="text-sm text-text-faint mt-1">Get started by adding data manually.</div>
                </td>
              </tr>
            ) : grouped.flatMap(([, items]) => items.map((mitigation) => (
              <tr
                key={mitigation.id}
                className={`border-t border-neutral-90 hover:bg-neutral-98 ${viewOnlyInteraction ? "cursor-pointer" : ""}`}
                onClick={() => viewOnlyInteraction && onOpenRow?.(mitigation)}
                role={viewOnlyInteraction ? "button" : undefined}
              >
                <td className="px-4 py-3 text-text-dark">{mitigation.name}</td>
                <td className="px-4 py-3 text-text-base">{mitigation.lifecyclePhaseLabel}</td>
                <td className="px-4 py-3 text-text-base">{MITIGATION_TYPE_LABEL[mitigation.type]}</td>
                <td className="px-4 py-3 text-right tabular-nums text-text-dark">{formatDisplayNumber(mitigation.estimatedSavingTco2e || 0)}</td>
                <td className="px-4 py-3 text-text-base">{mitigation.notes || "—"}</td>
                {(allowMutations || viewOnlyInteraction) && (
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-1 justify-end">
                      {allowMutations && <>
                        <button type="button" aria-label={`Edit ${mitigation.name}`} onClick={(event) => { event.stopPropagation(); onEdit?.(mitigation); }} className="p-1 rounded hover:bg-neutral-95 text-text-base cursor-pointer">
                          <span className="material-symbols-rounded text-[18px]">edit</span>
                        </button>
                        <button type="button" aria-label={`Delete ${mitigation.name}`} onClick={(event) => { event.stopPropagation(); onDelete?.(mitigation.id); }} className="p-1 rounded hover:bg-neutral-95 text-text-base cursor-pointer">
                          <span className="material-symbols-rounded text-[18px]">delete</span>
                        </button>
                      </>}
                      {viewOnlyInteraction && !allowMutations && <span className="material-symbols-rounded text-[18px] text-text-faint">visibility</span>}
                    </div>
                  </td>
                )}
              </tr>
            )))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
