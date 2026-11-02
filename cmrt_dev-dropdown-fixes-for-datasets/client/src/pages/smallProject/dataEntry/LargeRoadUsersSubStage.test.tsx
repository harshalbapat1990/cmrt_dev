import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LargeRoadUsersSubStage from "./LargeRoadUsersSubStage";

const hookState = vi.hoisted(() => ({ loading: true, saveState: "idle" as "idle" | "saving" }));

vi.mock("./hooks/useLargeRoadUsersLoader", () => ({
  useLargeRoadUsersLoader: vi.fn(),
}));
vi.mock("./hooks/useLargeRoadUserPersistence", () => ({
  useLargeRoadUserPersistence: () => ({ saveState: hookState.saveState, persistAll: vi.fn() }),
}));
vi.mock("./hooks/useLargeRoadUserCalculations", () => ({
  useLargeRoadUserCalculations: () => ({ loading: hookState.loading, calculateSummary: vi.fn() }),
}));
vi.mock("./hooks/useLargeRoadUserEditing", () => ({
  useLargeRoadUserEditing: () => ({ updateRow: vi.fn(), updateParams: vi.fn() }),
}));
vi.mock("./hooks/useLargeRoadUserSave", () => ({
  useLargeRoadUserSave: () => vi.fn(),
}));

describe("LargeRoadUsersSubStage", () => {
  beforeEach(() => {
    hookState.loading = true;
    hookState.saveState = "idle";
  });

  it.each([
    { loading: true, saveState: "idle" as const },
    { loading: false, saveState: "saving" as const },
  ])("disables the editor and modelled-year controls while busy (%o)", ({ loading, saveState }) => {
    hookState.loading = loading;
    hookState.saveState = saveState;
    vi.stubGlobal("matchMedia", () => ({ matches: false }) as MediaQueryList);
    const { container } = render(
      <LargeRoadUsersSubStage
        stageInstanceId="stage-1"
        projectId="project-1"
        jurisdiction="Australia"
        opsStartYear={2035}
        activeYear={2035}
        largeUsersYears={[2035]}
      />,
    );

    const editor = container.querySelector("[aria-busy='true']");
    expect(editor).not.toBeNull();
    expect(Array.from(editor!.querySelectorAll("input")).length).toBeGreaterThan(0);
    expect(Array.from(editor!.querySelectorAll("input")).every((input) => input.disabled)).toBe(true);
  });
});
