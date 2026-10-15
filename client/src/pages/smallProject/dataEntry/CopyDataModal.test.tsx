import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectOptionsService from "@/services/ProjectOptions.service";
import CopyDataModal from "./CopyDataModal";

vi.mock("@/services/ProjectOptions.service", () => ({
  default: { copyOption: vi.fn() },
}));

describe("CopyDataModal errors", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows a copy failure in the confirmation step and allows retry", async () => {
    vi.mocked(ProjectOptionsService.copyOption).mockRejectedValueOnce(new Error("Copy failed"));
    render(
      <CopyDataModal
        open
        onClose={vi.fn()}
        currentOptionId="target"
        options={[
          { label: "Source option", value: "source" },
          { label: "Target option", value: "target" },
        ]}
        onCopied={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "source" } });
    fireEvent.click(screen.getByRole("button", { name: "Copy data" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm copy" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Copy failed");
    expect(screen.getByRole("button", { name: "Confirm copy" })).toBeEnabled();
  });
});
