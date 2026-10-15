import { act, renderHook } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import type { RoadParams, RoadUserYearData } from "../roadUserTypes";
import { useLargeRoadUserEditing } from "./useLargeRoadUserEditing";

const params: RoadParams = {
  ev_uptake_scenario: "Step Change",
  roughness: "Smooth",
  gradient: "Flat",
  curvature: "Straight",
};
const initialYear: RoadUserYearData = {
  params,
  rows: [{
    id: "road-1",
    vehicleType: "Bus",
    vkt: "100",
    vht: "",
    avgSpeed: "",
    lastEdited: null,
    notes: "",
  }],
};

function renderEditing({ readOnly = false, years = [2030] }: { readOnly?: boolean; years?: number[] } = {}) {
  return renderHook(() => {
    const [yearData, setYearData] = useState<Record<number, RoadUserYearData>>({ 2030: initialYear });
    const [globalParams, setGlobalParams] = useState(params);
    const editing = useLargeRoadUserEditing({
      readOnly,
      displayedActiveYear: 2030,
      largeUsersYears: years,
      vehicleTypes: ["Bus"],
      globalParams,
      setGlobalParams,
      setYearData,
    });
    return { yearData, globalParams, editing };
  });
}

describe("useLargeRoadUserEditing", () => {
  it("derives the paired road metric when VHT is edited", () => {
    const { result } = renderEditing();

    act(() => result.current.editing.updateRow("road-1", { vht: "5", lastEdited: "vht" }));

    expect(result.current.yearData[2030].rows[0]).toMatchObject({ vkt: "100", vht: "5", avgSpeed: "20.00" });
  });

  it("propagates road parameters to every year and initializes required years", () => {
    const { result } = renderEditing({ years: [2030, 2040] });

    act(() => result.current.editing.updateParams({ roughness: "Rough" }));

    expect(result.current.globalParams.roughness).toBe("Rough");
    expect(result.current.yearData[2030].params.roughness).toBe("Rough");
    expect(result.current.yearData[2040].params).toMatchObject({ roughness: "Rough" });
    expect(result.current.yearData[2040].rows[0].vehicleType).toBe("Bus");
  });

  it("does not edit rows or parameters in read-only mode", () => {
    const { result } = renderEditing({ readOnly: true });

    act(() => {
      result.current.editing.updateRow("road-1", { vkt: "200" });
      result.current.editing.updateParams({ roughness: "Rough" });
    });

    expect(result.current.yearData[2030].rows[0].vkt).toBe("100");
    expect(result.current.globalParams.roughness).toBe("Smooth");
  });
});
