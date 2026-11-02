import { NumericInput } from "@/components/common/NumericInput";
import { useCallback, useEffect, useRef, useState } from "react";
import InfoTooltip from "@/components/common/InfoTooltip";
import ActivityDataService, { type ActivityDataCreate } from "@/services/ActivityData.service";
import CompletenessEmissionsService from "@/services/CompletenessEmissions.service";
import { formatDisplayNumber } from "@/utils/utils";
import {
    COMPLETENESS_MODULES,
    COMPLETENESS_RANGE_ERROR,
    COMPLETENESS_UI_TABLE_KEY,
    DEFAULT_COMPLETENESS_PCT,
    COMPLETENESS_MAX_PCT,
    COMPLETENESS_MIN_PCT,
    type CompletenessModuleKey,
} from "./completenessConstants";

export interface CompletenessProps {
    projectId: string;
    stageInstanceId: string;
    projectOptionId?: string | null;
    submissionPeriodId?: string | null;
    editorLocked?: boolean;
    onTotalsUpdated?: () => Promise<void>;
}

interface CompletenessRow {
    module: CompletenessModuleKey;
    label: string;
    completeness: string;
    upscalingAdjustment: number | null;
    error: string | null;
}

const formatTco2e = (val: number | null): string => {
    if (val == null || !Number.isFinite(val)) return "—";
    return formatDisplayNumber(val, {
        threshold: 100,
        decimalsBelowThreshold: 1,
        locale: "en-US",
        emptyText: "—",
    });
};

const isPctInRange = (val: number | null): boolean =>
    val != null && val >= COMPLETENESS_MIN_PCT && val <= COMPLETENESS_MAX_PCT;

const buildInitialRows = (): CompletenessRow[] =>
    COMPLETENESS_MODULES.map((m) => ({
        module: m.module,
        label: m.label,
        completeness: String(DEFAULT_COMPLETENESS_PCT),
        upscalingAdjustment: null,
        error: null,
    }));

const Completeness = ({
    projectId,
    stageInstanceId,
    projectOptionId = null,
    submissionPeriodId = null,
    editorLocked = false,
    onTotalsUpdated,
}: CompletenessProps) => {
    const [accordionExpanded, setAccordionExpanded] = useState<boolean>(true);
    const [rows, setRows] = useState<CompletenessRow[]>(buildInitialRows);
    const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
    const [loadError, setLoadError] = useState<string | null>(null);
    const calcTimers = useRef<Record<string, ReturnType<typeof setTimeout> | null>>({});
    const rowsRef = useRef(rows);
    rowsRef.current = rows;

    const scopedOptionId = submissionPeriodId ? null : (projectOptionId ?? null);
    const scopedPeriodId = submissionPeriodId ?? null;

 const runCalculateAndPersist = useCallback(
        async (nextRows: CompletenessRow[], persist: boolean) => {
            const modulesPayload = nextRows.map((row) => ({
                module: row.module,
                completeness_pct: Number(row.completeness),
            }));

     if (modulesPayload.some((m) => !isPctInRange(m.completeness_pct))) {
                return;
            }

             try {
                setLoadError(null);
                const result = await CompletenessEmissionsService.calculate({
                    project_id: projectId,
                    stage_instance_id: stageInstanceId,
                    project_option_id: scopedOptionId,
                    submission_period_id: scopedPeriodId,
                    elec_method: "location",
                    modules: modulesPayload,
                });

                const upliftByModule = new Map(
                    result.modules.map((m) => [m.module, Number(m.upscaling_adjustment_tco2e)])
                );

                setRows((prev) =>
                    prev.map((row) => ({
                        ...row,
                        upscalingAdjustment: upliftByModule.get(row.module) ?? null,
                    }))
                );

 if (persist && !editorLocked) {
                    setSaveState("saving");
                    const payload: ActivityDataCreate[] = nextRows.map((row) => ({
                        project_id: projectId,
                        project_stage_instance_id: stageInstanceId,
                        project_option_id: scopedOptionId,
                        submission_period_id: scopedPeriodId,
                        metric_id: null,
                        quantity: 0,
                        unit_id: null,
                        ui_table_key: COMPLETENESS_UI_TABLE_KEY,
                        extra_fields: {
                            module: row.module,
                            completeness_pct: Number(row.completeness),
                            upscaling_adjustment_tco2e: upliftByModule.get(row.module) ?? 0,
                        },
                    }));

                    await ActivityDataService.bulkUpsert(
                        stageInstanceId,
                        COMPLETENESS_UI_TABLE_KEY,
                        payload,
                        undefined,
                        scopedOptionId ?? undefined,
                        scopedPeriodId ?? undefined,
                    );

setSaveState("saved");
                    setTimeout(() => setSaveState("idle"), 2000);
                    await onTotalsUpdated?.();
                }
            } catch (error) {
                console.error("Error calculating/saving completeness data:", error);
                setLoadError("Failed to calculate completeness adjustments.");
                setSaveState("idle");
            }
        },
        [
            projectId,
            stageInstanceId,
            scopedOptionId,
            scopedPeriodId,
            editorLocked,
            onTotalsUpdated,
        ]   
    );
    
    useEffect(() => {
        let ignore = false;

        async function loadSaved() {
            if (!stageInstanceId) return;
            try {
                setLoadError(null);
                const saved = await ActivityDataService.fetchRows(
                    stageInstanceId,
                    COMPLETENESS_UI_TABLE_KEY,
                    scopedOptionId ?? undefined,
                    scopedPeriodId ?? undefined,
                );
                if (ignore) return;

                const savedByModule = new Map<string, number>();
                for (const row of saved) {
                    const mod = row.extra_fields?.module as string | undefined;
                    const pct = row.extra_fields?.completeness_pct;
                    if (mod && pct != null && pct !== "") {
                        savedByModule.set(mod, Number(pct));
                    }
                }

                const merged = COMPLETENESS_MODULES.map((m) => {
                    const pct = savedByModule.get(m.module) ?? DEFAULT_COMPLETENESS_PCT;
                    return {
                        module: m.module,
                        label: m.label,
                        completeness: String(pct),
                        upscalingAdjustment: null as number | null,
                        error: isPctInRange(pct) ? null : COMPLETENESS_RANGE_ERROR,
                    };
                });

                setRows(merged);
                await runCalculateAndPersist(merged, !editorLocked);
            } catch (error) {
                console.error("Failed to load completeness data:", error);
                if (!ignore) {
                    setLoadError("Failed to load completeness data.");
                    const defaults = buildInitialRows();
                    setRows(defaults);
                    await runCalculateAndPersist(defaults, false);
                }
            }
        }

         void loadSaved();

        return () => {
            ignore = true;
        };
    }, [
        stageInstanceId,
        scopedOptionId,
        scopedPeriodId,
        editorLocked,
        runCalculateAndPersist,
    ]);

    const scheduleRecalculate = useCallback(
        (moduleKey: CompletenessModuleKey, nextRows: CompletenessRow[]) => {
            if (calcTimers.current[moduleKey]) {
                clearTimeout(calcTimers.current[moduleKey]!);
            }
            calcTimers.current[moduleKey] = setTimeout(() => {
                void runCalculateAndPersist(nextRows, !editorLocked);
            }, 300);
        },
        [runCalculateAndPersist, editorLocked]
    );

    const handleCompletenessChange = (moduleKey: CompletenessModuleKey, val: number | null) => {
        if (editorLocked) return;

        const normalizedVal =
            val != null ? Math.round(val * 100) / 100 : null;
        const completenessValue =
            normalizedVal != null ? String(normalizedVal) : "";

        const error =
            normalizedVal == null || !isPctInRange(normalizedVal)
                ? COMPLETENESS_RANGE_ERROR
                : null;

        setRows((prev) => {
            const next = prev.map((row) =>
                row.module === moduleKey
                    ? {
                          ...row,
                          completeness: completenessValue,
                          error,
                      }
                    : row          
            );

            if (!error) {
                scheduleRecalculate(moduleKey, next);
            }

            return next;
        });      
    };

    const handleSave = async () => {
        if (editorLocked) return;
        const current = rowsRef.current;
        if (current.some((r) => r.error)) return;
        await runCalculateAndPersist(current, true);
    };

    useEffect(() => {
        return () => {
            Object.values(calcTimers.current).forEach((t) => t && clearTimeout(t));
        };
    }, []);

    return (
        <div className="m-12 bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)]">
            <div className="flex items-center justify-between mb-4">
                <div className="text-2xl font-light text-text-dark flex items-center gap-1">
                    Completeness
                    <InfoTooltip
                        text="This table is used to track completeness based on the approach in the ITMM Carbon Measurement for Infrastructure Technical Guidance. 
                Completeness values are set to 80% unless a higher value can be justified. The resulting emissions adjustment is added to the total emissions."
                        iconSize={16}
                        trigger="auto"
                        placement="right"
                        offset={60}
                        arrowOffset={5}
                    />
                </div>

                <div className="flex items-center gap-3">
                    {!editorLocked && (
                        <button
                            type="button"
                            className="px-3 py-2 text-sm bg-primary text-white rounded cursor-pointer disabled:opacity-50"
                            disabled={saveState === "saving" || rows.some((r) => r.error)}
                            onClick={() => void handleSave()}
                        >
                            Save
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={() => setAccordionExpanded((v) => !v)}
                        className="w-5 h-5 inline-flex items-center cursor-pointer justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded"
                    >
                        <span className="material-symbols-rounded">
                            {accordionExpanded ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                        </span>
                    </button>
                </div>
            </div>

             {loadError && (
                <div className="mb-4 text-sm text-danger">{loadError}</div>
            )}

            {accordionExpanded && (
<div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead>
                            <tr className="border-b border-neutral-200 font-medium text-text-base tet-xs">
                                <th className="px-4 py-3 text-left w-44">Module</th>
                                <th className="px-4 py-3 text-left">Completeness (%)</th>
                                <th className="px-4 py-3 text-right">
                                    Upscaling emissions adjustment (tCO<sub>2</sub>e)
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row) => (
                                <tr
                                    key={row.module}
                                    className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50 text-text-table-cell"
                                >
                                    <td className="px-4 py-3 bg-neutral-95">{row.label}</td>
                                    <td className="px-4 py-2">
                                        <NumericInput
                                            value={row.completeness}
                                            onChange={(val: string | number | null) =>
                                                handleCompletenessChange(
                                                    row.module,
                                                    val == null || val === ""
                                                        ? null
                                                        : Number(val)
                                                )
                                            }
                                            allowDecimal
                                            min={COMPLETENESS_MIN_PCT}
                                            max={COMPLETENESS_MAX_PCT}
                                            disabled={editorLocked}
                                        />
                                        {row.error && (
                                            <div className="text-xs text-danger mt-1">
                                                {row.error}
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 text-right">
                                        {formatTco2e(row.upscalingAdjustment)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default Completeness;