import { createRef } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Step2Modal, type TablePanelRenderOptions } from "./MitigationStepTwo";
import type { MitigationWizardSnapshot } from "../Mitigations";

describe("Step2Modal", () => {
  it("renders both substitution legs through its table renderer", () => {
    const renderTables = vi.fn((options: TablePanelRenderOptions) => <div>{options.leg}</div>);
    const tablesCollectorRef = createRef<{ collect: () => MitigationWizardSnapshot }>();

    render(
      <Step2Modal
        isOpen
        onClose={vi.fn()}
        draft={{ name: "Trial", type: "substitution", group: "", notes: "", lifecyclePhase: "construction" }}
        submissionStage="Design"
        mitigationScenarioId="scenario"
        persistence={null}
        hydrateSnapshot={null}
        detailReadOnly
        tablesCollectorRef={tablesCollectorRef}
        onPersisted={vi.fn()}
        renderTables={renderTables}
      />,
    );

    expect(screen.getByText("Source(s) replaced")).toBeTruthy();
    expect(screen.getByText("Source(s) adopted")).toBeTruthy();
    expect(renderTables).toHaveBeenCalledWith(expect.objectContaining({ leg: "replaced", scopeKey: "scenario-construction-replaced" }));
    expect(renderTables).toHaveBeenCalledWith(expect.objectContaining({ leg: "adopted", scopeKey: "scenario-construction-adopted" }));
    expect(tablesCollectorRef.current?.collect()).toEqual({
      mode: "substitution", replaced: {}, adopted: {},
    });
  });
});
