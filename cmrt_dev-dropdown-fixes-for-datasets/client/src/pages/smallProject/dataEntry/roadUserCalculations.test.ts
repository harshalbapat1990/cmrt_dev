import { describe, expect, it } from "vitest";
import {
    computeDerived,
    getSpeed,
    isNewZealandJurisdiction,
    isRoadRowComplete,
    normalizeCalculationSummary,
    toNumberOrNull,
} from "./roadUserCalculations";

describe("roadUserCalculations", () => {
    it("derives average speed or vehicle hours from the last edited field", () => {
        expect(computeDerived({ vkt: "120", vht: "4", avgSpeed: "", lastEdited: "vht", notes: "kept" }))
            .toEqual({ vkt: "120", vht: "4", avgSpeed: "30.00", lastEdited: "vht", notes: "kept" });
        expect(computeDerived({ vkt: "120", vht: "", avgSpeed: "40", lastEdited: "avgSpeed" }).vht)
            .toBe("3.00");
    });

    it("parses numeric inputs and checks road-row completeness", () => {
        expect(toNumberOrNull("1,200")).toBeNull();
        expect(toNumberOrNull("1200")).toBe(1200);
        expect(toNumberOrNull(" ")).toBe(0);
        expect(isRoadRowComplete({ vkt: "120", vht: "4", avgSpeed: "", lastEdited: null })).toBe(true);
        expect(getSpeed({ vkt: "120", vht: "0", avgSpeed: "", lastEdited: null })).toBeNull();
    });

    it("normalizes API summary aliases and recognizes New Zealand labels", () => {
        expect(normalizeCalculationSummary({
            interim_total_tco2e: "10.5",
            base_case_emissions_tco2e: 25,
            final_user_emissions_tco2e: 14.5,
        })).toEqual({ absoluteEmissions: "10.5", baseCaseAbsoluteEmissions: 25, relativeUserEmissions: 14.5 });
        expect(normalizeCalculationSummary(null)).toEqual({ absoluteEmissions: 0, baseCaseAbsoluteEmissions: null, relativeUserEmissions: null });
        expect(isNewZealandJurisdiction("NZL")).toBe(true);
        expect(isNewZealandJurisdiction("New Zealand")).toBe(true);
        expect(isNewZealandJurisdiction("Australia")).toBe(false);
    });
});
