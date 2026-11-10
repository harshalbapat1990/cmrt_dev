import { beforeEach, describe, expect, it, vi } from "vitest";
import http from "@/http";
import ProjectAccessService from "./ProjectAccess.service";

vi.mock("@/http", () => ({ default: { get: vi.fn() } }));

describe("project user search service", () => {
  beforeEach(() => vi.clearAllMocks());

  it("searches project-authorized active users by name or email query", async () => {
    vi.mocked(http.get).mockResolvedValue({ data: [
      { user_id: "user-1", display_name: "A User", email: "a@example.com" },
    ] } as never);

    const result = await ProjectAccessService.searchAssignableUsers("project-1", "a@example.com");

    expect(http.get).toHaveBeenCalledWith("/api/projects/project-1/user-search", {
      params: { q: "a@example.com" },
    });
    expect(result[0].user_id).toBe("user-1");
  });

  it("searches registered users during authorized project setup", async () => {
    vi.mocked(http.get).mockResolvedValue({ data: [] } as never);

    await ProjectAccessService.searchProjectSetupUsers("org-1", "Alex");

    expect(http.get).toHaveBeenCalledWith("/api/projects/setup-user-search", {
      params: { organisation_id: "org-1", q: "Alex" },
    });
  });
});
