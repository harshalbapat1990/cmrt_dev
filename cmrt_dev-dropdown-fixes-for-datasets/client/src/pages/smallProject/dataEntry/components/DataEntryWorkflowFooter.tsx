import { useRef, useState } from "react";
import { useOutsideClick } from "../useOutsideClick";

type PeriodDecision = "submit" | "approve" | "reject";
type AdminDecision = "approveReopen" | "approve" | "denyReopen" | "reject";

interface Props {
  isConstructionStage: boolean;
  isRecurringStage: boolean;
  isProjectAdmin: boolean;
  periodStatus: string | null;
  isSubmitted: boolean;
  isApproved: boolean;
  isReopenRequested: boolean;
  adminViewOnly: boolean;
  showMitigationsNext: boolean;
  showCompletenessNext: boolean;
  shouldShowSubmit: boolean;
  isLastSubStage: boolean;
  isFirstSubStage: boolean;
  onExitToProject: () => void;
  onExitLater: () => void;
  onBack: () => void;
  onPeriodWorkflow: (decision: PeriodDecision) => void;
  onAdminDecision: (decision: AdminDecision) => void;
  onShowMitigations: () => void;
  onShowCompleteness: () => void;
  onSubmit: () => void;
  onNextSubStage: () => void;
}

export function DataEntryWorkflowFooter({
  isConstructionStage,
  isRecurringStage,
  isProjectAdmin,
  periodStatus,
  isSubmitted,
  isApproved,
  isReopenRequested,
  adminViewOnly,
  showMitigationsNext,
  showCompletenessNext,
  shouldShowSubmit,
  isLastSubStage,
  isFirstSubStage,
  onExitToProject,
  onExitLater,
  onBack,
  onPeriodWorkflow,
  onAdminDecision,
  onShowMitigations,
  onShowCompleteness,
  onSubmit,
  onNextSubStage,
}: Props) {
  const [reviewMenuOpen, setReviewMenuOpen] = useState(false);
  const reviewMenuRef = useRef<HTMLDivElement>(null);
  useOutsideClick(reviewMenuRef, () => setReviewMenuOpen(false), reviewMenuOpen);

  const periodReview = (isConstructionStage || isRecurringStage) &&
    isProjectAdmin && periodStatus === "awaiting_approval";
  const stageReview = isProjectAdmin && (isSubmitted || isReopenRequested);
  const showExitOnly = !adminViewOnly && (isSubmitted || isApproved);

  return (
    <div className="bg-white p-5 px-12 flex justify-end gap-3 border-t border-neutral-90 sticky bottom-0 z-20">
      {periodReview ? (
        <>
          <button className="border border-border-input text-text-dark px-6 cursor-pointer py-3 rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors" type="button" onClick={onExitToProject}>Exit</button>
          <button className="px-6 py-3 rounded-[var(--radius-3)] text-sm font-medium cursor-pointer bg-red-600 text-white hover:bg-red-700 transition-colors" type="button" onClick={() => onPeriodWorkflow("reject")}>Reject Period</button>
          <button className="px-6 py-3 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium bg-green-600 text-white hover:bg-green-700 transition-colors" type="button" onClick={() => onPeriodWorkflow("approve")}>Approve Period</button>
        </>
      ) : stageReview ? (
        <>
          <button className="border border-border-input text-text-dark px-6 py-3 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors" type="button" onClick={onExitToProject}>Exit</button>
          <button className="border border-primary text-primary px-6 py-3 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors" type="button" onClick={onBack} disabled={isFirstSubStage}>Back</button>
          <div className="relative" ref={reviewMenuRef}>
            <button className="bg-primary text-white px-6 py-3 cursor-pointer rounded-[var(--radius-3)] flex items-center gap-2" type="button" onClick={() => setReviewMenuOpen((open) => !open)}>
              Review and respond
              <span className="material-symbols-rounded text-base">{reviewMenuOpen ? "keyboard_arrow_up" : "keyboard_arrow_down"}</span>
            </button>
            {reviewMenuOpen && (
              <div className="absolute right-0 bottom-full mb-2 rounded-lg border border-neutral-200 bg-white shadow-lg z-30 overflow-hidden">
                <div className="p-3 text-xs text-info-border bg-info-bg leading-4"><span className="font-medium">Note:</span>{" "}Selecting an option in this panel will make changes to confirm before submission.</div>
                <div className="flex flex-col">
                  <button className="w-full text-text-base text-left px-4 py-2 text-sm cursor-pointer hover:bg-neutral-50 border-b border-neutral-95" onClick={() => { setReviewMenuOpen(false); onAdminDecision(isReopenRequested ? "approveReopen" : "approve"); }}>Approve</button>
                  <button className="w-full text-left px-4 py-2 text-sm cursor-pointer hover:bg-neutral-50 text-red-700" onClick={() => { setReviewMenuOpen(false); onAdminDecision(isReopenRequested ? "denyReopen" : "reject"); }}>Reject</button>
                </div>
              </div>
            )}
          </div>
        </>
      ) : (
        <>
          {showExitOnly ? (
            <button className="border border-primary text-primary px-6 py-3 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors" type="button" onClick={onExitToProject}>Exit</button>
          ) : (
            <button className="border border-primary text-primary px-6 py-3 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors" type="button" onClick={onExitLater}>Exit and continue later</button>
          )}
          {showMitigationsNext ? (
            <button onClick={onShowMitigations} className="bg-primary text-white px-6 py-3 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium hover:bg-opacity-90 transition-colors" type="button">Next</button>
          ) : showCompletenessNext ? (
            <button onClick={onShowCompleteness} className="bg-primary text-white px-6 py-3 rounded-[var(--radius-3)] text-sm font-medium hover:bg-opacity-90 transition-colors" type="button">Next</button>
          ) : shouldShowSubmit ? (
            <button onClick={onSubmit} className="bg-primary text-white px-6 py-3 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium hover:bg-opacity-90 transition-colors" type="button">Submit</button>
          ) : !(isConstructionStage || isRecurringStage) ? (
            <button className={`px-6 py-3 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium transition-colors ${isLastSubStage ? "bg-neutral-300 text-neutral-600 cursor-not-allowed" : "bg-primary text-white hover:bg-opacity-90"}`} type="button" disabled={isLastSubStage} onClick={onNextSubStage}>Next</button>
          ) : null}
        </>
      )}
    </div>
  );
}
