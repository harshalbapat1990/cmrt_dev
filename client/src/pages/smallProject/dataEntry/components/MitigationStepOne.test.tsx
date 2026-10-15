import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Step1Modal } from "./MitigationStepOne";

describe("Step1Modal", () => {
  it("requires a mitigation name before proceeding", () => {
    const onNext = vi.fn();
    render(<Step1Modal isOpen onClose={vi.fn()} onNext={onNext} submissionStage="Design" />);

    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByText("Mitigation name is required.")).toBeTruthy();
    expect(onNext).not.toHaveBeenCalled();
  });
});
