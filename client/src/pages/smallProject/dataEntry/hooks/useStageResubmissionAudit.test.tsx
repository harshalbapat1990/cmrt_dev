import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchStageResubmissionAudit } from "@/services/AuditLog.service";
import { useStageResubmissionAudit } from "./useStageResubmissionAudit";

vi.mock("@/services/AuditLog.service", () => ({
  fetchStageResubmissionAudit: vi.fn(),
}));

describe("useStageResubmissionAudit", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads the prior rejection state for an admin's submitted option", async () => {
    vi.mocked(fetchStageResubmissionAudit).mockResolvedValue({ has_prior_rejection: true } as Awaited<ReturnType<typeof fetchStageResubmissionAudit>>);
    const { result } = renderHook(() => useStageResubmissionAudit({
      enabled: true,
      isProjectAdmin: true,
      stageInstanceId: "stage-1",
      projectOptionId: "option-1",
      approvalStatus: "submitted",
    }));

    await waitFor(() => expect(result.current).toBe(true));
    expect(fetchStageResubmissionAudit).toHaveBeenCalledWith("stage-1", "option-1");
  });

  it("does not request audit details for other users or unsubmitted options", () => {
    renderHook(() => useStageResubmissionAudit({
      enabled: true,
      isProjectAdmin: false,
      stageInstanceId: "stage-1",
      projectOptionId: "option-1",
      approvalStatus: "submitted",
    }));
    expect(fetchStageResubmissionAudit).not.toHaveBeenCalled();
  });
});
