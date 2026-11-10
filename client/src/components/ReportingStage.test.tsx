import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ReportingStage from "./ReportingStage";

vi.mock("./ReportingFrequency", () => ({
  default: () => <div data-testid="construction-frequency">Construction schedule fields</div>,
}));
vi.mock("./common/InfoTooltip", () => ({ default: () => null }));

describe("optional construction reporting setup", () => {
  it("lets a design-stage project defer construction schedule details", () => {
    render(
      <ReportingStage
        selectedStage="design"
        onSelectStage={vi.fn()}
        submissions={{ business: "", design: "2", construction: "" }}
        onChangeSubmissions={vi.fn()}
        constructionEnabled={false}
        onConstructionEnabledChange={vi.fn()}
      />,
    );

    expect(screen.getByRole("checkbox")).not.toBeChecked();
    expect(screen.queryByText("Construction schedule fields")).toBeNull();
    expect(screen.getByText(/An administrator can configure it later/)).toBeTruthy();
  });

  it("shows construction schedule details when opted in and prevents disabling an existing schedule", () => {
    const onConstructionEnabledChange = vi.fn();
    const { rerender } = render(
      <ReportingStage
        selectedStage="design"
        onSelectStage={vi.fn()}
        submissions={{ business: "", design: "2", construction: "" }}
        onChangeSubmissions={vi.fn()}
        constructionEnabled={false}
        onConstructionEnabledChange={onConstructionEnabledChange}
      />,
    );
    fireEvent.click(screen.getByRole("checkbox"));
    expect(onConstructionEnabledChange).toHaveBeenCalledWith(true);

    rerender(
      <ReportingStage
        selectedStage="design"
        onSelectStage={vi.fn()}
        submissions={{ business: "", design: "2", construction: "" }}
        onChangeSubmissions={vi.fn()}
        constructionEnabled
        constructionReadOnly
        onConstructionEnabledChange={onConstructionEnabledChange}
      />,
    );
    expect(screen.getByRole("checkbox")).toBeDisabled();
  });
});
