import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PeriodWorkflowModal from "./PeriodWorkflowModal";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";

const period: ConstructionPeriod = {
  id: "period-1",
  project_id: "project-1",
  stage_instance_id: "recurring-stage",
  frequency: "monthly",
  period_label: "Mar 2027",
  period_start_date: "2027-03-01",
  period_end_date: "2027-03-31",
  due_date: null,
  status: "approved",
  submitted_by: null,
  submitted_at: null,
  decision_by: null,
  decision_at: null,
  rejection_reason: null,
  reopen_requested_by: null,
  reopen_requested_at: null,
  reopen_reason: null,
  created_on: null,
  updated_on: null,
  period_emissions_tco2e: null,
  previous_period_emissions_tco2e: null,
  all_periods_emissions_tco2e: null,
};

describe("PeriodWorkflowModal reopen failures", () => {
  it("shows the API error and retains the reason so the user can retry", async () => {
    const onConfirm = vi.fn().mockRejectedValue({ response: { data: { detail: "Period is no longer approved" } } });
    render(
      <PeriodWorkflowModal
        open
        action="requestReopen"
        period={period}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );

    const reason = screen.getByPlaceholderText("Enter reason for reopening…");
    fireEvent.change(reason, { target: { value: "Please correct the report" } });
    fireEvent.click(screen.getByRole("button", { name: "Send Request" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Period is no longer approved");
    expect(reason).toHaveValue("Please correct the report");
    expect(onConfirm).toHaveBeenCalledWith("Please correct the report");
  });
});
