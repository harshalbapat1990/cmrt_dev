import { act, renderHook } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { RoadUserRow } from "../roadUserTypes";
import type { RailUserRow } from "../userDataMapping";
import { useUsersRowEditing } from "./useUsersRowEditing";

const roadRow: RoadUserRow = {
  id: "road-1",
  vehicleType: "Light vehicle",
  vkt: "100",
  vht: "",
  avgSpeed: "20",
  lastEdited: null,
  notes: "",
};
const railRow: RailUserRow = {
  id: "rail-1",
  vehicleType: "Container Train",
  terrain: "Flat",
  freight: "25",
  dieselEmissionsIntensity: "2",
  dieselEmissions: "3",
  dieselEmissionsTotalRefPeriod: "4",
  notes: "",
};

describe("useUsersRowEditing", () => {
  it("derives road fields and recalculates rail rows when freight or terrain changes", () => {
    const scheduleRailCalculation = vi.fn();
    const scheduleRailSave = vi.fn();
    const { result } = renderHook(() => {
      const [roadRows, setRoadRows] = useState([roadRow]);
      const [railRows, setRailRows] = useState([railRow]);
      return {
        roadRows,
        railRows,
        editing: useUsersRowEditing({
          readOnly: false,
          setRoadRows,
          setRailRows,
          scheduleRailCalculation,
          scheduleRailSave,
        }),
      };
    });

    act(() => result.current.editing.updateRoadRow("road-1", { vht: "5", lastEdited: "vht" }));
    expect(result.current.roadRows[0]).toMatchObject({ vkt: "100", vht: "5", avgSpeed: "20.00" });

    act(() => result.current.editing.updateRailRow("rail-1", { freight: "30" }));
    expect(result.current.railRows[0]).toMatchObject({
      freight: "30",
      dieselEmissionsIntensity: "",
      dieselEmissions: "",
      dieselEmissionsTotalRefPeriod: "",
    });
    expect(scheduleRailCalculation).toHaveBeenCalledWith(result.current.railRows[0], result.current.railRows);
    expect(scheduleRailSave).not.toHaveBeenCalled();
  });

  it("saves notes-only rail changes and ignores edits when read-only", () => {
    const scheduleRailCalculation = vi.fn();
    const scheduleRailSave = vi.fn();
    const { result, rerender } = renderHook(({ readOnly }) => {
      const [roadRows, setRoadRows] = useState([roadRow]);
      const [railRows, setRailRows] = useState([railRow]);
      return {
        roadRows,
        railRows,
        editing: useUsersRowEditing({
          readOnly,
          setRoadRows,
          setRailRows,
          scheduleRailCalculation,
          scheduleRailSave,
        }),
      };
    }, { initialProps: { readOnly: false } });

    act(() => result.current.editing.updateRailRow("rail-1", { notes: "Updated note" }));
    expect(result.current.railRows[0].notes).toBe("Updated note");
    expect(scheduleRailSave).toHaveBeenCalledWith(result.current.railRows);
    expect(scheduleRailCalculation).not.toHaveBeenCalled();

    rerender({ readOnly: true });
    act(() => {
      result.current.editing.updateRoadRow("road-1", { vkt: "999" });
      result.current.editing.updateRailRow("rail-1", { freight: "999" });
    });
    expect(result.current.roadRows[0].vkt).toBe("100");
    expect(result.current.railRows[0].freight).toBe("25");
    expect(scheduleRailCalculation).not.toHaveBeenCalled();
  });
});
