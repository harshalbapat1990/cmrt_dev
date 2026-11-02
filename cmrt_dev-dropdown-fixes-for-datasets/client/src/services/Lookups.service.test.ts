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
});
