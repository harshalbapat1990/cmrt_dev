import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectsService from "@/services/Projects.service";
import ProjectAccessService from "@/services/ProjectAccess.service";
import ProjectOptionsService from "@/services/ProjectOptions.service";
import http from "@/http";
import { useDataEntryProjectBootstrap } from "./useDataEntryProjectBootstrap";

vi.mock("@/services/Projects.service", () => ({
  default: { fetchProjectDetails: vi.fn() },
}));
vi.mock("@/services/ProjectAccess.service", () => ({
  default: { fetchMyProjectAccess: vi.fn() },
}));
vi.mock("@/services/ProjectOptions.service", () => ({
  default: {
    fetchOptions: vi.fn(),
    ensureOptions: vi.fn(),
  },
}));
vi.mock("@/http", () => ({ default: { get: vi.fn() } }));

const callbacks = () => ({
  setProjectHeader: vi.fn(),
  clearProjectHeader: vi.fn(),
  setActiveStage: vi.fn(),
  setActiveSubStage: vi.fn(),
  setActiveReportNumber: vi.fn(),
});

describe("useDataEntryProjectBootstrap", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads project context, filters inaccessible stages, and initializes navigation", async () => {
    vi.mocked(ProjectsService.fetchProjectDetails).mockResolvedValue({
      name: "Road project",
      project_class: "LARGE",
      is_active: true,
      stage_instances: [
        { id: "business-case", stage: "BUSINESS_CASE", sequence: 1 },
        { id: "design", stage: "DESIGN", sequence: 2 },
      ],
      stage_configs: [{ stage: "CONSTRUCTION", frequency: "Quarterly" }],
      postcodes: [{ jurisdiction_name: "New Zealand", grid_region: "Auckland" }],
    });
    vi.mocked(ProjectAccessService.fetchMyProjectAccess).mockResolvedValue({
      stage_access: [
        { stage_instance_id: "business-case", access: "EDIT" },
        { stage_instance_id: "design", access: "NONE" },
      ],
    } as never);
    vi.mocked(ProjectOptionsService.ensureOptions).mockResolvedValue([
      { id: "option-1", stage_instance_id: "business-case", report_number: 1 },
    ] as never);
    vi.mocked(http.get).mockResolvedValue({ data: [] } as never);
    const navigation = callbacks();

    const { result } = renderHook(() => useDataEntryProjectBootstrap({
      projectId: "project-1",
      stageInstanceIdParam: null,
      reportNumberParam: 1,
      ...navigation,
    }));

    await waitFor(() => expect(result.current.stageInstances).toHaveLength(1));
    expect(result.current.projectName).toBe("Road project");
    expect(result.current.frequency).toBe("Quarterly");
    expect(result.current.projectGridCtx).toEqual({
      jurisdiction: "New Zealand",
      region: "Auckland",
    });
    expect(navigation.setActiveStage).toHaveBeenCalledWith("Business case");
    expect(navigation.setActiveSubStage).toHaveBeenCalledWith("Construction");
    expect(result.current.projectOptions).toHaveLength(1);
  });

  it("reports the no-access state when the user has no visible stages", async () => {
    vi.mocked(ProjectsService.fetchProjectDetails).mockResolvedValue({
      stage_instances: [{ id: "business-case", stage: "BUSINESS_CASE" }],
    });
    vi.mocked(ProjectAccessService.fetchMyProjectAccess).mockResolvedValue({ stage_access: [] } as never);
    const navigation = callbacks();

    const { result } = renderHook(() => useDataEntryProjectBootstrap({
      projectId: "project-1",
      stageInstanceIdParam: null,
      reportNumberParam: 1,
      ...navigation,
    }));

    await waitFor(() => expect(result.current.accessDenied).toBe(true));
    expect(ProjectOptionsService.ensureOptions).not.toHaveBeenCalled();
    expect(http.get).not.toHaveBeenCalled();
  });

  it("deduplicates concurrent option requests and stores the returned options", async () => {
    let resolveRequest!: (options: Array<{ id: string; stage_instance_id: string }>) => void;
    vi.mocked(ProjectOptionsService.ensureOptions).mockImplementation(() => new Promise((resolve) => {
      resolveRequest = resolve as typeof resolveRequest;
    }));
    const navigation = callbacks();
    const { result } = renderHook(() => useDataEntryProjectBootstrap({
      projectId: "",
      stageInstanceIdParam: null,
      reportNumberParam: 1,
      ...navigation,
    }));

    let first!: Promise<unknown>;
    let second!: Promise<unknown>;
    act(() => {
      first = result.current.loadStageOptions("stage-1", "EDIT");
      second = result.current.loadStageOptions("stage-1", "EDIT");
    });
    expect(ProjectOptionsService.ensureOptions).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveRequest([{ id: "option-1", stage_instance_id: "stage-1" }]);
      await Promise.all([first, second]);
    });
    expect(result.current.projectOptions.map((option) => option.id)).toEqual(["option-1"]);
  });
});
