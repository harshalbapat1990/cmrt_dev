import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { EpdRow } from "../concreteRegisterTypes";
import { ConcreteEpdPcfTable } from "./ConcreteEpdPcfTable";
import type { ConcreteEpdPcfTableActions } from "./ConcreteEpdPcfTable";

const epdRow: EpdRow = {
  id: "epd-1",
  mixId: "MIX-01",
  gwpA1A3: 320,
  volumeM3: 12,
  notes: "Supplier declaration",
  emissions_tco2e: 3.84,
};

function createActions(overrides: Partial<ConcreteEpdPcfTableActions> = {}): ConcreteEpdPcfTableActions {
  return {
    addEpdRow: vi.fn(async () => undefined),
    updateEpdRow: vi.fn() as ConcreteEpdPcfTableActions["updateEpdRow"],
    syncEpdRow: vi.fn(async () => undefined),
    deleteEpdRow: vi.fn(async () => undefined),
    getEpdEmissions: vi.fn(() => 3.84),
    ...overrides,
  };
}

describe("ConcreteEpdPcfTable", () => {
  it("renders EPD values read-only without edit actions", () => {
    render(<ConcreteEpdPcfTable rows={[epdRow]} readOnly actions={createActions()} />);

    expect(screen.getByText("MIX-01")).toBeTruthy();
    expect(screen.queryByLabelText("Mix ID")).toBeNull();
    expect(screen.queryByTitle("Delete row")).toBeNull();
    expect(screen.queryByText("Add row")).toBeNull();
  });

  it("updates and syncs a mix identifier on blur", () => {
    const updateEpdRow = vi.fn() as ConcreteEpdPcfTableActions["updateEpdRow"];
    const syncEpdRow = vi.fn();
    render(<ConcreteEpdPcfTable rows={[epdRow]} readOnly={false} actions={createActions({ updateEpdRow, syncEpdRow })} />);

    const mixIdInput = screen.getByLabelText("Mix ID");
    fireEvent.change(mixIdInput, { target: { value: "MIX-02" } });
    fireEvent.blur(mixIdInput);

    expect(updateEpdRow).toHaveBeenCalledWith("epd-1", "mixId", "MIX-02");
    expect(syncEpdRow).toHaveBeenCalledWith(epdRow);
  });
});
