// src/constants/stages.ts

/** Canonical stage approval status values (all lowercase). */
export const StageApprovalStatus = {
  DRAFT: "draft",
  AWAITING: "awaiting_approval",
  APPROVED: "approved",
  REJECTED: "rejected",
  REOPEN_REQUESTED: "reopen_requested",
  FINAL_APPROVED: "final_approved",
} as const;

export type StageApprovalStatusKey =
  (typeof StageApprovalStatus)[keyof typeof StageApprovalStatus];

/** Contributors should not be able to edit when submission is under review or approved/final. */
export const isReadOnlyForContributor = (status?: string) => {
  const s = (status || "").toLowerCase();
  return ([
    StageApprovalStatus.AWAITING,
    StageApprovalStatus.APPROVED,
    StageApprovalStatus.REOPEN_REQUESTED,
    StageApprovalStatus.FINAL_APPROVED,
  ] as readonly string[]).includes(s);
};

/** Admins never edit the user’s tables inline; their view is always read-only. */
export const isReadOnlyForAdmin = (_status?: string) => true;