import { useEffect, useState } from "react";
import { fetchStageResubmissionAudit } from "@/services/AuditLog.service";

interface UseStageResubmissionAuditParams {
  enabled: boolean;
  isProjectAdmin: boolean;
  stageInstanceId: string | null | undefined;
  projectOptionId: string | null | undefined;
  approvalStatus: string | null | undefined;
}

/** Loads the prior-rejection indicator only for an admin viewing a submitted option. */
export function useStageResubmissionAudit({
  enabled,
  isProjectAdmin,
  stageInstanceId,
  projectOptionId,
  approvalStatus,
}: UseStageResubmissionAuditParams) {
  const [hasResubmission, setHasResubmission] = useState(false);

  useEffect(() => {
    if (!enabled || !isProjectAdmin || !stageInstanceId || approvalStatus !== "submitted") {
      setHasResubmission(false);
      return;
    }

    let cancelled = false;
    fetchStageResubmissionAudit(stageInstanceId, projectOptionId ?? undefined)
      .then((result) => {
        if (!cancelled) setHasResubmission(result.has_prior_rejection);
      })
      .catch(() => {
        if (!cancelled) setHasResubmission(false);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, isProjectAdmin, stageInstanceId, projectOptionId, approvalStatus]);

  return hasResubmission;
}
