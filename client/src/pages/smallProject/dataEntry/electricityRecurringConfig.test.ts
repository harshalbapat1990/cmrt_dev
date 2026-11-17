import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useDataEntryTableColumns } from "./hooks/useDataEntryTableColumns";
import { electricityConfig } from "./electricityConfig";

describe("recurring electricity configuration", () => {
    it("hides the year column while preserving the period-derived year in the calculation request", () => {
        const { result } = renderHook(() => useDataEntryTableColumns("project-1", "Australia"));
        expect(result.current.recurringElectricityColumns.map((column) => column.header)).not.toContain("Year");

        const config = electricityConfig("project-1");
        const payload = config.calculation.buildPayload({
            emission_source: "Grid Electricity",
            year: 2035,
            quantity_mwh: 25,
        }, {
            jurisdiction: "Australia",
            ops_start_year: 2028,
            reference_period: 71,
            construction_start_year: "",
            construction_end_year: "",
            project_id: "project-1",
            tableKey: "electricity",
            project_option_id: null,
            project_stage_instance_id: "recurring-stage",
            active_stage: "Recurring",
            submission_period_id: "period-2035",
        });
        expect(payload).toMatchObject({ year: 2035, submission_period_id: "period-2035" });
    });
});
