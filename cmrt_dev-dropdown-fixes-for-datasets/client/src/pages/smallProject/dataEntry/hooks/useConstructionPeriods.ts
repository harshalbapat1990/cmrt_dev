import { useEffect, type Dispatch, type SetStateAction } from "react";
import { ConstructionPeriodsService, type ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { StageInstance, StageLabel } from "../dataEntryTypes";

interface Params {
    enabled: boolean;
    activeStage: StageLabel;
    activeStageInstance: StageInstance | null;
    setPeriods: (periods: ConstructionPeriod[]) => void;
    setSelectedPeriodId: Dispatch<SetStateAction<string | null>>;
}

/** Loads the periods used by Construction and Recurring stage workflows. */
export function useConstructionPeriods({
    enabled,
    activeStage,
    activeStageInstance,
    setPeriods,
    setSelectedPeriodId,
}: Params): void {
    useEffect(() => {
        if (!enabled || (activeStage !== "Construction" && activeStage !== "Recurring") || !activeStageInstance) return;
        let cancelled = false;
        void ConstructionPeriodsService.listPeriods(activeStageInstance.id)
            .then((response) => {
                if (cancelled) return;
                const periods = Array.isArray(response) ? response : [];
                setPeriods(periods);
                if (periods.length === 0) return;
                const current = periods.find((period) => period.status !== "approved") ?? periods[periods.length - 1];
                setSelectedPeriodId((selectedId) => periods.some((period) => period.id === selectedId) ? selectedId : current.id);
            })
            .catch((error: unknown) => {
                console.error("Failed to fetch construction periods", error);
            });
        return () => { cancelled = true; };
    }, [enabled, activeStage, activeStageInstance, setPeriods, setSelectedPeriodId]);
}
