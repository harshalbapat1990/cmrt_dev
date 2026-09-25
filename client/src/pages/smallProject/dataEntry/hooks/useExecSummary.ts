import { useState, useEffect } from "react";
import ProjectOptionsService, { type ProjectOption } from "@/services/ProjectOptions.service";
import { ConstructionPeriodsService, type ConstructionPeriod } from "@/services/ConstructionPeriods.service";

interface UseExecSummaryParams {
    activeStage: string;
    activeOption: ProjectOption | null;
    activePeriod: ConstructionPeriod | null;
    activeOptionId: string | null;
    user: any;
    success: (msg: string) => void;
    setConstructionPeriods: React.Dispatch<React.SetStateAction<ConstructionPeriod[]>>;
    setProjectOptions: React.Dispatch<React.SetStateAction<ProjectOption[]>>;
}

export function useExecSummary({
    activeStage,
    activeOption,
    activePeriod,
    activeOptionId,
    user,
    success,
    setConstructionPeriods,
    setProjectOptions,
}: UseExecSummaryParams) {
    const [execSummary, setExecSummary] = useState<string>("");
    const [execSummaryDirty, setExecSummaryDirty] = useState<boolean>(false);
    const [execSummaryAuthor, setExecSummaryAuthor] = useState<string | null>(null);
    const [execSummaryDate, setExecSummaryDate] = useState<string | null>(null);

    useEffect(() => {
        const isConstructionStage = activeStage === "Construction";
        if (isConstructionStage) {
            setExecSummary(activePeriod?.exec_summary ?? "");
            setExecSummaryAuthor(activePeriod?.exec_summary_author ?? null);
            setExecSummaryDate(activePeriod?.exec_summary_date ?? null);
        } else {
            setExecSummary(activeOption?.exec_summary ?? "");
            setExecSummaryAuthor(activeOption?.exec_summary_author ?? null);
            setExecSummaryDate(activeOption?.exec_summary_date ?? null);
        }
        setExecSummaryDirty(false);
    }, [activeOption?.id, activePeriod?.id, activeStage]);

    const saveExecSummary = async () => {
        const isConstructionStage = activeStage === "Construction";
        const isRecurringStage = activeStage === "Recurring";
        try {
            const authorName =
                [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
                user?.email ||
                "";
            const nowIso = new Date().toISOString();

            if (isConstructionStage || isRecurringStage) {
                if (!activePeriod) return;
                const updated = await ConstructionPeriodsService.saveExecSummary(
                    activePeriod.id,
                    execSummary || null,
                    execSummary ? authorName : undefined,
                    execSummary ? nowIso : undefined,
                );
                setConstructionPeriods((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
                setExecSummaryAuthor(updated.exec_summary_author ?? null);
                setExecSummaryDate(updated.exec_summary_date ?? null);
            } else {
                if (!activeOptionId) return;
                const updated = await ProjectOptionsService.saveExecSummary(
                    activeOptionId,
                    execSummary || null,
                    execSummary ? authorName : undefined,
                    execSummary ? nowIso : undefined,
                );
                setProjectOptions((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
                setExecSummaryAuthor(updated.exec_summary_author ?? null);
                setExecSummaryDate(updated.exec_summary_date ?? null);
            }
            setExecSummaryDirty(false);
            success("Executive summary saved");
        } catch (e) {
            console.error("Failed to save executive summary", e);
        }
    };

    return {
        execSummary,
        setExecSummary,
        execSummaryDirty,
        setExecSummaryDirty,
        execSummaryAuthor,
        execSummaryDate,
        saveExecSummary,
    };
}
