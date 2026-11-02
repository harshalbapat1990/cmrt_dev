import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ConfirmDeleteRowModal from "./ConfirmDeleteRowModal";

describe("ConfirmDeleteRowModal", () => {
  it("closes without deleting when cancelled", () => {
    const onClose = vi.fn();
    const onConfirm = vi.fn(async () => undefined);
    render(<ConfirmDeleteRowModal open onClose={onClose} onConfirm={onConfirm} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledOnce();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("runs the delete action when confirmed", async () => {
    const onClose = vi.fn();
    const onConfirm = vi.fn(async () => undefined);
    render(<ConfirmDeleteRowModal open onClose={onClose} onConfirm={onConfirm} />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    });

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("keeps the confirmation busy until the async delete finishes", async () => {
    let finishDelete!: () => void;
    const onConfirm = vi.fn(() => new Promise<void>((resolve) => {
      finishDelete = resolve;
    }));
    render(<ConfirmDeleteRowModal open onClose={vi.fn()} onConfirm={onConfirm} />);

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(screen.getByRole("button", { name: "Deleting..." }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: "Cancel" }).hasAttribute("disabled")).toBe(true);

    await act(async () => finishDelete());

    expect(screen.getByRole("button", { name: "Delete" }).hasAttribute("disabled")).toBe(false);
  });

  it("shows delete failures and keeps the confirmation available for retry", async () => {
    const onConfirm = vi.fn(async () => { throw new Error("Delete was rejected"); });
    render(<ConfirmDeleteRowModal open onClose={vi.fn()} onConfirm={onConfirm} />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    });

    expect(screen.getByRole("alert").textContent).toBe("Delete was rejected");
    expect(screen.getByRole("button", { name: "Delete" }).hasAttribute("disabled")).toBe(false);
  });
});
