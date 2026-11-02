import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectsService from "@/services/Projects.service";
import { useProjectDashboardProject, type DashboardProject } from "./useProjectDashboardProject";

vi.mock("@/services/Projects.service", () => ({
  default: { fetchProjectDetails: vi.fn() },
}));

const project: DashboardProject = {
  id: "project-1",
  name: "Test Project",
  project_class: "SMALL",
  stage_instances: [{ id: "stage-1", stage: "BUSINESS_CASE" }],
};

describe("useProjectDashboardProject", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses router project data without fetching", () => {
    const { result } = renderHook(() => useProjectDashboardProject("project-1", project));

    expect(result.current).toEqual({ project, loading: false, error: null });
    expect(ProjectsService.fetchProjectDetails).not.toHaveBeenCalled();
  });

  it("loads project data for a direct or refreshed dashboard URL", async () => {
    vi.mocked(ProjectsService.fetchProjectDetails).mockResolvedValueOnce(project);
    const { result } = renderHook(() => useProjectDashboardProject("project-1", null));

    await waitFor(() => expect(result.current.project).toEqual(project));
    expect(ProjectsService.fetchProjectDetails).toHaveBeenCalledWith("project-1");
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("reports a useful error when project loading fails", async () => {
    vi.mocked(ProjectsService.fetchProjectDetails).mockRejectedValueOnce(new Error("offline"));
    const { result } = renderHook(() => useProjectDashboardProject("project-1", null));

    await waitFor(() => expect(result.current.error).toMatch(/couldn't load this project's dashboard/i));
    expect(result.current.project).toBeNull();
    expect(result.current.loading).toBe(false);
  });
});
