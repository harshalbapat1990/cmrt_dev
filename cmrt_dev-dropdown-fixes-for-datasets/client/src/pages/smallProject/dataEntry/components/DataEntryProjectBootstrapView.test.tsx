import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DataEntryProjectBootstrapView } from "./DataEntryProjectBootstrapView";

describe("DataEntryProjectBootstrapView", () => {
  it("shows a loading state while project data is being loaded", () => {
    render(<DataEntryProjectBootstrapView
      accessDenied={false}
      isLoaded={false}
      loadError={null}
      onBack={vi.fn()}
    />);

    expect(screen.getByRole("status").textContent).toContain("Loading project data");
  });

  it("shows the access state before other bootstrap states and returns to the project", () => {
    const onBack = vi.fn();
    render(<DataEntryProjectBootstrapView
      accessDenied
      isLoaded={false}
      loadError="Load failed"
      onBack={onBack}
    />);

    expect(screen.getByRole("heading", { name: "No stage access" })).toBeTruthy();
    expect(screen.queryByText("Load failed")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Back to project" }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it("shows the project load error and retry navigation action", () => {
    const onBack = vi.fn();
    render(<DataEntryProjectBootstrapView
      accessDenied={false}
      isLoaded
      loadError="Project service unavailable"
      onBack={onBack}
    />);

    expect(screen.getByRole("heading", { name: "Project data unavailable" })).toBeTruthy();
    expect(screen.getByText("Project service unavailable")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Back to project" }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it("renders no fallback when project data is ready", () => {
    const { container } = render(<DataEntryProjectBootstrapView
      accessDenied={false}
      isLoaded
      loadError={null}
      onBack={vi.fn()}
    />);

    expect(container.firstChild).toBeNull();
  });
});
