import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { useLargeUserYears } from "./useLargeUserYears";

vi.mock("@/services/ActivityData.service", () => ({
  default: {
    fetchRows: vi.fn(),
    bulkUpsert: vi.fn(),
    deleteRow: vi.fn(),
  },
}));

describe("useLargeUserYears", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ActivityDataService.fetchRows).mockResolvedValue([]);
    vi.mocked(ActivityDataService.bulkUpsert).mockResolvedValue([]);
  });

  it("validates and adds a year with the active project scope", async () => {
    const { result } = renderHook(() => useLargeUserYears({
      isUsersSubStage: true,
      activeStageInstance: { id: "stage-1", stage: "BUSINESS_CASE" },
      activeOptionId: "option-1",
      projectClass: "LARGE",
      isLargeUsersNZ: false,
      opsStartYear: 2020,
      projectId: "project-1",
    }));

    act(() => result.current.setAddLargeYearInput("2024"));
    await act(async () => result.current.handleAddLargeYear());

    expect(ActivityDataService.bulkUpsert).toHaveBeenCalledWith(
      "stage-1",
      "largeRoadParams",
      expect.arrayContaining([expect.objectContaining({
        project_id: "project-1",
        project_option_id: "option-1",
        extra_fields: expect.objectContaining({ modelled_year: 2024 }),
      })]),
      undefined,
    );
    expect(result.current.activeLargeUsersYear).toBe(2024);
    expect(result.current.largeUsersYears).toEqual([2024]);
  });

  it("rejects duplicate years without writing them", async () => {
    vi.mocked(ActivityDataService.fetchRows).mockResolvedValue([{
      id: "row-2024",
      project_id: "project-1",
      project_stage_instance_id: "stage-1",
      quantity: 0,
      ui_table_key: "largeRoadParams",
      extra_fields: { modelled_year: 2024 },
    }]);
    const { result } = renderHook(() => useLargeUserYears({
      isUsersSubStage: true,
      activeStageInstance: { id: "stage-1", stage: "BUSINESS_CASE" },
      activeOptionId: "option-1",
      projectClass: "LARGE",
      isLargeUsersNZ: false,
      opsStartYear: 2020,
      projectId: "project-1",
    }));

    await waitFor(() => expect(result.current.largeUsersYears).toEqual([2024]));
    act(() => result.current.setAddLargeYearInput("2024"));
    await act(async () => result.current.handleAddLargeYear());

    expect(result.current.addLargeYearError).toBe("That year already exists.");
    expect(ActivityDataService.bulkUpsert).not.toHaveBeenCalled();
  });

  it("copies source-year rows into the active year for each large-user table", async () => {
    vi.mocked(ActivityDataService.fetchRows).mockImplementation(async (_stageId, tableKey) => [
      {
        id: `${tableKey}-source`,
        project_id: "project-1",
        project_stage_instance_id: "stage-1",
        project_option_id: "option-1",
        quantity: 12,
        ui_table_key: tableKey,
        extra_fields: { modelled_year: 2020, vehicle_type: "Bus", marker: "source" },
      },
      {
        id: `${tableKey}-target`,
        project_id: "project-1",
        project_stage_instance_id: "stage-1",
        project_option_id: "option-1",
        quantity: 5,
        ui_table_key: tableKey,
        extra_fields: { modelled_year: 2030, vehicle_type: "Bus", marker: "old-target" },
      },
    ]);
    const { result } = renderHook(() => useLargeUserYears({
      isUsersSubStage: false,
      activeStageInstance: { id: "stage-1", stage: "BUSINESS_CASE" },
      activeOptionId: "option-1",
      projectClass: "LARGE",
      isLargeUsersNZ: false,
      opsStartYear: 2020,
      projectId: "project-1",
    }));
    act(() => {
      result.current.setLargeUsersYears([2020, 2030]);
      result.current.setActiveLargeUsersYear(2030);
      result.current.setCopyLargeYearSource(2020);
      result.current.setCopyLargeYearConfirmOpen(true);
    });

    await act(async () => result.current.handleCopyLargeYear());

    expect(ActivityDataService.bulkUpsert).toHaveBeenCalledTimes(3);
    for (const [, tableKey, payload] of vi.mocked(ActivityDataService.bulkUpsert).mock.calls) {
      expect(payload).toHaveLength(2);
      expect(payload).toEqual(expect.arrayContaining([
        expect.objectContaining({ ui_table_key: tableKey, extra_fields: expect.objectContaining({ modelled_year: 2020 }) }),
        expect.objectContaining({ ui_table_key: tableKey, extra_fields: expect.objectContaining({ modelled_year: 2030, marker: "source" }) }),
      ]));
    }
    expect(result.current.copyLargeYearConfirmOpen).toBe(false);
    expect(result.current.copyLargeYearSource).toBeNull();
    expect(result.current.usersRefreshKey).toBe(1);
  });

  it("deletes rows for the final modelled year and clears the active year", async () => {
    vi.mocked(ActivityDataService.fetchRows).mockImplementation(async (_stageId, tableKey) => [{
      id: `${tableKey}-2030`,
      project_id: "project-1",
      project_stage_instance_id: "stage-1",
      project_option_id: "option-1",
      quantity: 0,
      ui_table_key: tableKey,
      extra_fields: { modelled_year: 2030 },
    }]);
    const { result } = renderHook(() => useLargeUserYears({
      isUsersSubStage: false,
      activeStageInstance: { id: "stage-1", stage: "BUSINESS_CASE" },
      activeOptionId: "option-1",
      projectClass: "LARGE",
      isLargeUsersNZ: false,
      opsStartYear: 2020,
      projectId: "project-1",
    }));
    act(() => {
      result.current.setLargeUsersYears([2030]);
      result.current.setActiveLargeUsersYear(2030);
      result.current.setDeleteLargeYearConfirmOpen(true);
    });

    await act(async () => result.current.handleDeleteLargeYear());

    expect(ActivityDataService.deleteRow).toHaveBeenCalledTimes(3);
    expect(result.current.largeUsersYears).toEqual([]);
    expect(result.current.activeLargeUsersYear).toBeNull();
    expect(result.current.deleteLargeYearConfirmOpen).toBe(false);
    expect(result.current.usersRefreshKey).toBe(1);
  });
});
