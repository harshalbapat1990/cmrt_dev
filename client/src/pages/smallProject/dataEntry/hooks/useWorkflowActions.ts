import { useState, useCallback, type Dispatch, type SetStateAction } from "react";
import ActivityDataService from "@/services/ActivityData.service";
import ProjectOptionsService, { type ProjectOption } from "@/services/ProjectOptions.service";
import { ConstructionPeriodsService, type ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { StageInstance, StageLabel } from "../dataEntryTypes";

export type PeriodWorkflowAction = "submit" | "approve" | "reject" | "requestReopen" | "approveReopen" | "rejectReopen";
export type AdminDecisionAction = "approve" | "reject" | "approveReopen" | "denyReopen";

interface UseWorkflowActionsParams {
    activeStage: StageLabel;
    activeStageInstance: StageInstance | null;
    activeOptionId: string | null;
    activeOption: ProjectOption | null;
    activePeriod: ConstructionPeriod | null;
    constructionPeriods: ConstructionPeriod[];
    designSeedOptionId: string | null;
    success: (msg: string) => void;
    setProjectOptions: Dispatch<SetStateAction<ProjectOption[]>>;
    setConstructionPeriods: Dispatch<SetStateAction<ConstructionPeriod[]>>;
    setSelectedConstructionMonth: Dispatch<SetStateAction<string | null>>;
}

export function useWorkflowActions({
    activeStage,
    activeStageInstance,
    activeOptionId,
    activeOption,
    activePeriod,
    constructionPeriods,
    designSeedOptionId,
    success,
    setProjectOptions,
    setConstructionPeriods,
    setSelectedConstructionMonth,
}: UseWorkflowActionsParams) {
    const [adminDecisionOpen, setAdminDecisionOpen] = useState<AdminDecisionAction | null>(null);
    const [decisionComments, setDecisionComments] = useState("");
    const [reopenModalOpen, setReopenModalOpen] = useState(false);
    const [reopenJustification, setReopenJustification] = useState("");
    const [submitModalOpen, setSubmitModalOpen] = useState(false);
    const [periodWorkflowOpen, setPeriodWorkflowOpen] = useState<PeriodWorkflowAction | null>(null);

    const refreshOptionTotals = useCallback(async () => {
        if (!activeStageInstance) return;

        try {
            const refreshed = await ProjectOptionsService.ensureOptions(activeStageInstance.id);
            setProjectOptions((prev) => {
                const map = new Map(refreshed.map((o) => [o.id, o]));
                return prev.map((o) => map.get(o.id) ?? o);
            });
        } catch (e) {
            console.warn("Failed to refresh option totals", e);
        }

        if (activeStage === "Construction") {
            try {
                const periods = await ConstructionPeriodsService.listPeriods(activeStageInstance.id);
                setConstructionPeriods(Array.isArray(periods) ? periods : []);
            } catch (e) {
                console.warn("Failed to refresh construction periods", e);
            }
        }
    }, [activeStageInstance, activeStage, setProjectOptions, setConstructionPeriods]);

    const refreshConstructionPeriods = useCallback(async (): Promise<ConstructionPeriod[]> => {
        if (!activeStageInstance) return [];
        try {
            const periods = await ConstructionPeriodsService.listPeriods(activeStageInstance.id);
            const list = Array.isArray(periods) ? periods : [];
            setConstructionPeriods(list);
            return list;
        } catch (e) {
            console.error("Failed to refresh construction periods", e);
            return [];
        }
    }, [activeStageInstance, setConstructionPeriods]);

    const handleReportSubmission = async () => {
        if (!activeOptionId) return;
        const updatedOpts = await ProjectOptionsService.submitReport(activeOptionId);
        setSubmitModalOpen(false);
        success(`${activeStage} report was successfully submitted for approval`);
        setProjectOptions((prev) => {
            const map = new Map(updatedOpts.map((o: ProjectOption) => [o.id, o]));
            return prev.map((o) => map.get(o.id) ?? o);
        });
    };

    const triggerAdminDecision = async () => {
        if (!activeOptionId) return;
        const status = activeOption?.approval_status ?? "draft";
        const isReopenRequested =
            activePeriod?.status === "reopen_requested" || status === "pending_reopen";

        let updatedOpts: ProjectOption[] = [];
        try {
            if (adminDecisionOpen === "approve" && status === "submitted") {
                updatedOpts = await ProjectOptionsService.approveReport(activeOptionId, decisionComments);
                success(`${activeStage} stage is approved by the administrator`);
            } else if (status === "submitted" && adminDecisionOpen === "reject") {
                updatedOpts = await ProjectOptionsService.rejectReport(activeOptionId, decisionComments);
                success(`${activeStage} stage is rejected by the administrator`);
            } else if (adminDecisionOpen === "approveReopen" && isReopenRequested) {
                updatedOpts = await ProjectOptionsService.approveReopen(activeOptionId, decisionComments);
                success(`${activeStage} stage reopen request approved`);
            } else if (adminDecisionOpen === "denyReopen" && isReopenRequested) {
                updatedOpts = await ProjectOptionsService.rejectReopen(activeOptionId, decisionComments);
                success(`${activeStage} stage reopen request rejected`);
            }
            if (!updatedOpts.length) return;
            setAdminDecisionOpen(null);
            setDecisionComments("");
            setProjectOptions((prev) => {
                const map = new Map(updatedOpts.map((o) => [o.id, o]));
                return prev.map((o) => map.get(o.id) ?? o);
            });
        } catch (e) {
            console.error("Admin decision failed", e);
        }
    };

    const submitReopenRequest = async () => {
        if (!activeOptionId) return;
        try {
            const updatedOpts = await ProjectOptionsService.requestReopen(
                activeOptionId,
                reopenJustification.trim()
            );
            setProjectOptions((prev) => {
                const map = new Map(updatedOpts.map((o: ProjectOption) => [o.id, o]));
                return prev.map((o) => map.get(o.id) ?? o);
            });
            success("Reopen request sent to admin");
            setReopenModalOpen(false);
            setReopenJustification("");
        } catch (e) {
            console.error("Reopen request failed", e);
        }
    };

    const handlePeriodWorkflowConfirm = async (reason?: string) => {
        if (!activePeriod || !periodWorkflowOpen) return;
        const action = periodWorkflowOpen;
        const requiresReason = action === "reject" || action === "requestReopen" || action === "rejectReopen";
        const trimmedReason = reason?.trim();
        // The modal validates this too, but keep the hook safe if called directly.
        if (requiresReason && !trimmedReason) return;
        const confirmationReason = trimmedReason ?? "";

        const id = activePeriod.id;
        switch (action) {
            case "submit":
                await ConstructionPeriodsService.submit(id);
                success("Period submitted for approval");
                break;
            case "approve":
                await ConstructionPeriodsService.approve(id);
                success("Period approved — next period created automatically");
                break;
            case "reject":
                await ConstructionPeriodsService.reject(id, confirmationReason);
                success("Period rejected");
                break;
            case "requestReopen":
                await ConstructionPeriodsService.requestReopen(id, confirmationReason);
                success("Reopen request sent to admin");
                break;
            case "approveReopen":
                await ConstructionPeriodsService.approveReopen(id);
                success("Reopen request approved — period is now editable");
                break;
            case "rejectReopen":
                await ConstructionPeriodsService.rejectReopen(id, confirmationReason);
                success("Reopen request rejected");
                break;
        }
        setPeriodWorkflowOpen(null);
        const refreshed = await refreshConstructionPeriods();
        await refreshOptionTotals();
        if (action === "approve") {
            const next = refreshed.find((p) => p.status === "in_progress");
            if (next) setSelectedConstructionMonth(next.id);
        }
    };

    const seedPeriodsFromDesign = useCallback(
        async (periodIds: string[]) => {
            if (!designSeedOptionId || !activeStageInstance) return;
            const eligible = constructionPeriods
                .filter((p) => p.status === "in_progress" || p.status === "rejected")
                .map((p) => p.id);
            const toSeed = periodIds.filter((id) => eligible.includes(id));
            if (toSeed.length === 0) return;
            await ActivityDataService.seedFromDesign(
                designSeedOptionId,
                activeStageInstance.id,
                toSeed
            );
        },
        [designSeedOptionId, activeStageInstance, constructionPeriods]
    );

    return {
        adminDecisionOpen,
        setAdminDecisionOpen,
        decisionComments,
        setDecisionComments,
        reopenModalOpen,
        setReopenModalOpen,
        reopenJustification,
        setReopenJustification,
        submitModalOpen,
        setSubmitModalOpen,
        periodWorkflowOpen,
        setPeriodWorkflowOpen,
        refreshOptionTotals,
        refreshConstructionPeriods,
        handleReportSubmission,
        triggerAdminDecision,
        submitReopenRequest,
        handlePeriodWorkflowConfirm,
        seedPeriodsFromDesign,
    };
}
