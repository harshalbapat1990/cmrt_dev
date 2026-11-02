import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import EmissionCalculationsService from "@/services/EmissionCalculations.service";
import { calculateRailUserRow, calculateRoadUserSummary, persistUserActivityRows } from "./roadUserWorkflow";

vi.mock("@/services/ActivityData.service", () => ({
  default: { bulkUpsert: vi.fn() },
}));
vi.mock("@/services/EmissionCalculations.service", () => ({
  default: {
    calculateRail: vi.fn(),
    calculateNzRoads: vi.fn(),
    calculateAusRoads: vi.fn(),
    calculateLargeNzRoads: vi.fn(),
    calculateLargeAusRoads: vi.fn(),
  },
}));

describe("roadUserWorkflow", () => {
  beforeEach(() => vi.clearAllMocks());

  it("routes large NZ calculations and normalizes the returned summary", async () => {
    vi.mocked(EmissionCalculationsService.calculateLargeNzRoads).mockResolvedValue({ absoluteEmissions: 12 } as never);

    await expect(calculateRoadUserSummary({ project_id: "project-1" }, "NZ", "large"))
      .resolves.toMatchObject({ absoluteEmissions: 12 });
    expect(EmissionCalculationsService.calculateLargeNzRoads).toHaveBeenCalledWith({ project_id: "project-1" });
  });

  it("maps the rail calculation response back onto the edited row", async () => {
    vi.mocked(EmissionCalculationsService.calculateRail).mockResolvedValue({ emissions_total_ref_period_tco2e: 9 } as never);
    const row = { id: "rail-1", vehicleType: "Train", terrain: "Flat", freight: "10", dieselEmissionsIntensity: "", dieselEmissions: "", dieselEmissionsTotalRefPeriod: "", notes: "" };

    await expect(calculateRailUserRow("project-1", row)).resolves.toMatchObject({
      id: "rail-1",
      dieselEmissionsTotalRefPeriod: "9",
    });
    expect(EmissionCalculationsService.calculateRail).toHaveBeenCalledWith(expect.objectContaining({
      project_id: "project-1",
      freight_quantity_gtk_per_year: 10,
    }));
  });

  it("sends activity rows through the shared scoped persistence boundary", async () => {
    vi.mocked(ActivityDataService.bulkUpsert).mockResolvedValue([]);
    await persistUserActivityRows("stage-1", "roadUsers", [], "mitigation-1");
    expect(ActivityDataService.bulkUpsert).toHaveBeenCalledWith("stage-1", "roadUsers", [], "mitigation-1");
  });
});
