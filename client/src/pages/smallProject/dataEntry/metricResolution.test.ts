import { beforeEach, describe, expect, it, vi } from "vitest";
import http from "@/http";
import LookupsService from "@/services/Lookups.service";
import { buildMetricLookupParams, resolveMetricId } from "./metricResolution";

vi.mock("@/http", () => ({ default: { get: vi.fn() } }));
vi.mock("@/services/Lookups.service", () => ({
    default: { resolveProjectDatasetRevisionId: vi.fn() },
}));

describe("metricResolution", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(LookupsService.resolveProjectDatasetRevisionId).mockResolvedValue("revision-1");
    });

    it("builds asset lookups with the selected master type, typecast, and band", () => {
        const params = buildMetricLookupParams({
            mastertype_id: "master-1",
            typecast_id: "typecast-1",
            band_code: "B2",
        }, "asset");

        expect(params?.get("limit")).toBe("1");
        expect(params?.get("mastertype_id")).toBe("master-1");
        expect(params?.get("typecast_id")).toBe("typecast-1");
        expect(params?.get("band_code")).toBe("B2");
        expect(buildMetricLookupParams({
            mastertype_id: "master-1",
            typecast_id: "typecast-1",
            band_code: "B2",
        }, "asset", "revision-1")?.get("dataset_revision_id")).toBe("revision-1");
    });

    it("does not select an ambiguous generic metric for Grade 3/4 detailed tables", async () => {
        const draft = {
            emissions_category_id: "category-1",
            emission_subcategory_id: "subcategory-1",
        };

        expect(buildMetricLookupParams(draft, "bcDetailedLevel")).toBeNull();
        expect(buildMetricLookupParams(draft, "constructionG3")).toBeNull();
        expect(buildMetricLookupParams(draft, "recurringG3")).toBeNull();
        await expect(resolveMetricId(draft, "bcDetailedLevel", "project-1")).resolves.toBeNull();
        expect(LookupsService.resolveProjectDatasetRevisionId).not.toHaveBeenCalled();
        expect(http.get).not.toHaveBeenCalled();
    });

    it("does not request metrics for unsupported table keys", async () => {
        expect(buildMetricLookupParams({}, "electricity")).toBeNull();
        expect(await resolveMetricId({}, "electricity", "project-1")).toBeNull();
        expect(http.get).not.toHaveBeenCalled();
    });

    it("scopes asset metric lookup to the project's assigned dataset revision", async () => {
        vi.mocked(http.get).mockResolvedValueOnce({ data: [{ id: "asset-metric" }] });

        await expect(resolveMetricId({
            mastertype_id: "master-1",
            typecast_id: "typecast-1",
            band_code: "Mid",
        }, "asset", "project-1")).resolves.toBe("asset-metric");

        expect(LookupsService.resolveProjectDatasetRevisionId).toHaveBeenCalledWith("project-1");
        expect(http.get).toHaveBeenCalledWith(
            "/api/background-grade-metrics?limit=1&dataset_revision_id=revision-1&mastertype_id=master-1&typecast_id=typecast-1&band_code=Mid",
        );
    });

    it("scopes component metric lookup to the project's assigned dataset revision", async () => {
        vi.mocked(http.get).mockResolvedValueOnce({ data: [{ id: "component-metric" }] });

        await expect(resolveMetricId({
            emissions_category_id: "category-1",
            emissions_subcategory_id: "subcategory-1",
        }, "component", "project-1")).resolves.toBe("component-metric");

        expect(http.get).toHaveBeenCalledWith(
            "/api/background-grade-metrics?limit=1&dataset_revision_id=revision-1&emissions_category_id=category-1&emissions_subcategory_id=subcategory-1",
        );
    });

    it("skips the metric request if the project has no assigned revision", async () => {
        vi.mocked(LookupsService.resolveProjectDatasetRevisionId).mockResolvedValueOnce(null);

        await expect(resolveMetricId({ emissions_category_id: "category-1" }, "component", "project-1"))
            .resolves.toBeNull();
        expect(http.get).not.toHaveBeenCalled();
    });

    it("returns the first metric id and treats lookup failures as unresolved", async () => {
        vi.mocked(http.get).mockResolvedValueOnce({ data: [{ id: "metric-1" }, { id: "metric-2" }] });
        expect(await resolveMetricId({ emissions_category_id: "cat" }, "constructionG2", "project-1")).toBe("metric-1");
        expect(http.get).toHaveBeenCalledWith(
            "/api/background-grade-metrics?limit=1&dataset_revision_id=revision-1&emissions_category_id=cat",
        );

        vi.mocked(http.get).mockRejectedValueOnce(new Error("offline"));
        expect(await resolveMetricId({ emissions_category_id: "cat" }, "constructionG2", "project-1")).toBeNull();
    });

    it("treats revision resolution failures as unresolved without querying metrics", async () => {
        vi.mocked(LookupsService.resolveProjectDatasetRevisionId).mockRejectedValueOnce(new Error("offline"));

        await expect(resolveMetricId({ emissions_category_id: "cat" }, "constructionG2", "project-1"))
            .resolves.toBeNull();
        expect(http.get).not.toHaveBeenCalled();
    });
});
