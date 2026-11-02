import CheckCircleGreen from "@/assets/icons/check-circle-green.svg";
import Info from "@/assets/icons/info.svg";

interface Props {
  showMitigations: boolean;
  isProjectAdmin: boolean;
  isReopenRequested: boolean;
  isApproved: boolean;
  isStageLocked: boolean;
  isPeriodWorkflowStage: boolean;
  constructionPeriodCount: number;
  isSubmitted: boolean;
  isRejected: boolean;
  rejectionComment?: string | null;
  reopenReason: string;
  adminViewOnly: boolean;
  statusBasedReadOnly: boolean;
}

/** Status and access notices shown above the active stage tables. */
export function DataEntryStatusNotices({
  showMitigations,
  isProjectAdmin,
  isReopenRequested,
  isApproved,
  isStageLocked,
  isPeriodWorkflowStage,
  constructionPeriodCount,
  isSubmitted,
  isRejected,
  rejectionComment,
  reopenReason,
  adminViewOnly,
  statusBasedReadOnly,
}: Props) {
  const showApprovedNotice = !showMitigations && !isProjectAdmin && !isReopenRequested && (isApproved || isStageLocked);
  const showReopenNotice = !showMitigations && !isProjectAdmin && isReopenRequested &&
    !(isPeriodWorkflowStage && constructionPeriodCount > 0);
  const showRejectedNotice = !showMitigations && !isProjectAdmin && isRejected;
  const showAdminReopenReason = !showMitigations && isProjectAdmin && isReopenRequested;
  const showAdminViewNotice = !showMitigations && adminViewOnly && !statusBasedReadOnly;

  return (
    <>
      {showApprovedNotice && (
        <div className="flex flex-col gap-2 mx-12 mt-4 px-4 py-3 rounded bg-light-green border border-success/35 text-success text-sm">
          <div className="flex items-center gap-2">
            <img src={CheckCircleGreen} alt="Approved" className="w-5 h-5" />
            <div className="font-bold">This report has been approved</div>
          </div>
          <div className="px-7">This report is read-only and can no longer be edited. You can submit a request to reopen it if you need to update it.</div>
        </div>
      )}

      {showReopenNotice && (
        <div className="flex flex-col gap-2 mx-12 mt-4 px-4 py-3 rounded bg-info-bg border border-in-progress/35 text-in-progress text-sm">
          <div className="flex items-center gap-2">
            <img src={Info} alt="Approved" className="w-5 h-5 text-in-progress" />
            <div className="font-bold">Reopen requested</div>
          </div>
          <div className="px-7">Awaiting administrator approval to reopen</div>
        </div>
      )}

      {!showMitigations && !isProjectAdmin && isSubmitted && (
        <div className="m-6 p-4 bg-info-bg border border-in-progress/35 rounded text-in-progress font-medium">
          This report is submitted and currently under review.
        </div>
      )}

      {showRejectedNotice && (
        <div className="flex flex-col gap-2 mx-12 mt-4 px-4 py-3 bg-red-50 border border-red-200 rounded">
          <p className="font-bold text-danger">Submission Rejected</p>
          <p className="text-sm text-danger">Admin Comment: {rejectionComment}</p>
        </div>
      )}

      {showAdminReopenReason && (
        <div className="mx-12 mt-6 p-6 bg-info-bg border border-info-border/35 rounded">
          <h3 className="text-sm font-bold text-info-border uppercase mb-2">Request to Reopen Justification</h3>
          <p className="text-text-base">{reopenReason || "—"}</p>
        </div>
      )}

      {showAdminViewNotice && (
        <div className="flex flex-col gap-2 mx-12 mt-4 px-4 py-3 rounded bg-info-bg border border-in-progress/35 text-in-progress text-sm">
          <div className="flex items-center gap-2">
            <img src={Info} alt="Info" className="w-5 h-5" />
            <div className="font-bold">View-only access</div>
          </div>
          <div className="px-7">A submission is currently in progress. You have view-only access as a project admin. To make edits, contact your organisation admin to be assigned the Editor role.</div>
        </div>
      )}
    </>
  );
}
