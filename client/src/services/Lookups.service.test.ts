import { beforeEach, describe, expect, it, vi } from "vitest";
import http from "@/http";
import LookupsService from "./Lookups.service";

vi.mock("@/http", () => ({ default: { get: vi.fn() } }));

describe("revision-scoped Grade 3 reporting-boundary lookups", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    LookupsService.clearProjectDatasetRevisionCache();
    LookupsService.clearPublishedDefaultDatasetRevisionCache();
  });

  it("uses the assigned project revision for subcategory and source lookups", async () => {
    vi.mocked(http.get)
      .mockResolvedValueOnce({ data: [{ dataset_revision_id: "project-revision" }] })
      .mockResolvedValueOnce({ data: [{ emissions_subcategory: "Grasses" }] })
      .mockResolvedValueOnce({ data: [{ emissions_source: "Vegetation clearance" }] });

    await LookupsService.fetchGrade3Subcategories("Vegetation", "project-1");
    await LookupsService.fetchGrade3Sources("Vegetation", "Grasses", "project-1");

    expect(http.get).toHaveBeenNthCalledWith(2,
      "/api/background-grade-metrics?grade_id=3&dataset_revision_id=project-revision&emissions_category=Vegetation&limit=500",
    );
    expect(http.get).toHaveBeenNthCalledWith(3,
      "/api/background-grade-metrics?grade_id=3&dataset_revision_id=project-revision&emissions_category=Vegetation&emissions_subcategory=Grasses&limit=500",
    );
  });

  it("uses the published default revision during project creation", async () => {
    vi.mocked(http.get)
      .mockResolvedValueOnce({ data: [{ id: "default-revision", created_at: "2026-01-01" }] })
      .mockResolvedValueOnce({ data: [{ emissions_subcategory: "Grasses" }] });

    await LookupsService.fetchGrade3Subcategories("Vegetation");

    expect(http.get).toHaveBeenNthCalledWith(1,
      "/api/dataset-revisions?scope_type=DEFAULT&status=published&limit=500",
    );
    expect(http.get).toHaveBeenNthCalledWith(2,
      "/api/background-grade-metrics?grade_id=3&dataset_revision_id=default-revision&emissions_category=Vegetation&limit=500",
    );
  });

  it("falls back to the published default when an edited project has no assigned revision", async () => {
    vi.mocked(http.get)
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [{ id: "default-revision", created_at: "2026-01-01" }] })
      .mockResolvedValueOnce({ data: [{ emissions_source: "Vegetation clearance" }] });

    await LookupsService.fetchGrade3Sources("Vegetation", "Grasses", "project-1");

    expect(http.get).toHaveBeenNthCalledWith(3,
      "/api/background-grade-metrics?grade_id=3&dataset_revision_id=default-revision&emissions_category=Vegetation&emissions_subcategory=Grasses&limit=500",
    );
  });

  it("does not issue an unscoped lookup when no published default exists", async () => {
    vi.mocked(http.get).mockResolvedValueOnce({ data: [] });

    await expect(LookupsService.fetchGrade3Subcategories("Vegetation"))
      .rejects.toThrow("No published dataset revision is available for reporting boundary lookups.");
    expect(http.get).toHaveBeenCalledTimes(1);
  });

  it("sorts deduplicated Grade 3 subcategories alphabetically", async () => {
    vi.mocked(http.get)
      .mockResolvedValueOnce({ data: [{ dataset_revision_id: "project-revision" }] })
      .mockResolvedValueOnce({ data: [
        { emissions_subcategory: "Zinc" },
        { emissions_subcategory: "alpha" },
        { emissions_subcategory: "Beta" },
        { emissions_subcategory: "alpha" },
      ] });

    await expect(LookupsService.fetchGrade3Subcategories("Materials", "project-1"))
      .resolves.toEqual([
        { value: "alpha", label: "alpha" },
        { value: "Beta", label: "Beta" },
        { value: "Zinc", label: "Zinc" },
      ]);
  });

  it("sorts deduplicated Grade 3 sources alphabetically", async () => {
    vi.mocked(http.get)
      .mockResolvedValueOnce({ data: [{ dataset_revision_id: "project-revision" }] })
      .mockResolvedValueOnce({ data: [
        { emissions_source: "Timber" },
        { emissions_source: "asphalt" },
        { emissions_source: "Concrete" },
      ] });

    await expect(LookupsService.fetchGrade3Sources("Materials", "Roads", "project-1"))
      .resolves.toEqual([
        { value: "asphalt", label: "asphalt" },
        { value: "Concrete", label: "Concrete" },
        { value: "Timber", label: "Timber" },
      ]);
  });
});

describe("revision-scoped unit options", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    LookupsService.clearProjectDatasetRevisionCache();
    LookupsService.clearPublishedDefaultDatasetRevisionCache();
  });

  it("propagates unit lookup failures instead of disguising them as empty options", async () => {
    vi.mocked(http.get).mockRejectedValueOnce(new Error("forbidden"));

    await expect(LookupsService.fetchUnitsByTypecast("typecast-1", [1], "project-revision"))
      .rejects.toThrow("forbidden");
  });

  it("preserves a valid empty response as an empty option list", async () => {
    vi.mocked(http.get).mockResolvedValueOnce({ data: [] });

    await expect(LookupsService.fetchBgmSourceUnits([2], "sub-1", "Source", "project-revision"))
      .resolves.toEqual([]);
  });

  it("passes the selected revision to Grade 1, Grade 2/3/4, and electricity unit lookups", async () => {
    vi.mocked(http.get)
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] });

    await LookupsService.fetchUnitsByTypecast("typecast-1", [1], "selected-revision");
    await LookupsService.fetchBgmSourceUnits([2, 3, 4], "subcategory-1", "Concrete", "selected-revision");
    await LookupsService.fetchElectricityUnits("selected-revision");

    expect(http.get).toHaveBeenNthCalledWith(1,
      "/api/lookup/benchmark-typecasts/typecast-1/units?grade_ids=1&dataset_revision_id=selected-revision",
    );
    expect(http.get).toHaveBeenNthCalledWith(2,
      "/api/lookup/bgm-source-units?grade_ids=2%2C3%2C4&subcategory_id=subcategory-1&source=Concrete&dataset_revision_id=selected-revision",
    );
    expect(http.get).toHaveBeenNthCalledWith(3,
      "/api/lookup/electricity-units?dataset_revision_id=selected-revision",
    );
  });

  it("does not fall back to DEFAULT units when a project binding request fails", async () => {
    vi.mocked(http.get).mockRejectedValueOnce(new Error("binding lookup failed"));

    await expect(LookupsService.resolveProjectDatasetRevisionId("project-1"))
      .rejects.toThrow("binding lookup failed");
    expect(http.get).toHaveBeenCalledTimes(1);
  });

  it("propagates electricity unit failures rather than returning a canonical-only fallback", async () => {
    vi.mocked(http.get).mockRejectedValueOnce(new Error("lookup unavailable"));

    await expect(LookupsService.fetchElectricityUnits("project-revision"))
      .rejects.toThrow("lookup unavailable");
  });
});
