import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectOptionsService from "@/services/ProjectOptions.service";
import ManageOptionsModal from "./ManageOptionsModal";

vi.mock("@/services/ProjectOptions.service", () => ({
  default: {
    createSubOption: vi.fn(),
    renameOption: vi.fn(),
    setDefaultOption: vi.fn(),
  },
}));

describe("ManageOptionsModal errors", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows an actionable error when creating an option fails", async () => {
    vi.mocked(ProjectOptionsService.createSubOption).mockRejectedValueOnce(new Error("Option limit reached"));
    render(
      <ManageOptionsModal
        open
        onClose={vi.fn()}
        activeStage="Business case"
        projectId="project-1"
        stageInstanceId="stage-1"
        reportNumber={1}
        options={[]}
        onOptionsChange={vi.fn(async () => undefined)}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /add option/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Option limit reached");
  });
});
