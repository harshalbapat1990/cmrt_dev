import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Table from "./Table";

describe("Table unit option loading", () => {
  it("shows lookup failures separately from a valid empty option list", async () => {
    const loadOptions = vi.fn().mockRejectedValue(new Error("revision lookup failed"));
    render(
      <Table
        data={[]}
        columns={[{ header: "Unit", key: "unit", editorType: "select", getOptions: loadOptions }]}
        enableInlineNewRow
        hideToolbarActions
      />,
    );

    fireEvent.click(screen.getByText("Add row"));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Could not load options"));
    expect(loadOptions).toHaveBeenCalled();
  });
});
