import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectOptionsService from "@/services/ProjectOptions.service";
import DeleteOptionModal from "./DeleteOptionModal";

vi.mock("@/services/ProjectOptions.service", () => ({
  default: { deleteOption: vi.fn() },
}));

describe("DeleteOptionModal errors", () => {
  beforeEach(() => vi.clearAllMocks());

  it("keeps the dialog open and shows the reason when deletion fails", async () => {
    vi.mocked(ProjectOptionsService.deleteOption).mockRejectedValueOnce(new Error("Option is in use"));
    const option = { id: "option-1", label: "Option 1" } as never;
    render(<DeleteOptionModal open option={option} onClose={vi.fn()} onDeleted={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Yes, delete this option" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Option is in use");
    expect(screen.getByText("Delete option")).toBeInTheDocument();
  });
});
