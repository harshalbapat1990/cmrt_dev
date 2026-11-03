import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectAccess from "./ProjectAccess";
import http from "@/http";
import OrganizationService from "@/services/organization.service";

vi.mock("@/http", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

vi.mock("@/services/organization.service", () => ({
  default: { fetchRegistrationOrganizations: vi.fn() },
}));

vi.mock("@/components/common/ToastProvider", () => ({
  useToast: () => ({ success: vi.fn() }),
}));

describe("ProjectAccess project lookup", () => {
  beforeEach(() => {
    vi.mocked(OrganizationService.fetchRegistrationOrganizations).mockResolvedValue([
      { id: "org-1", name: "Demonstration_Org" },
    ]);
    vi.mocked(http.get).mockImplementation(async (url) => {
      if (url === "/api/projects/access-request-lookup") {
        return {
          data: {
            id: "project-1",
            project_name: "test proj",
            project_class: "RECURRING",
          },
        } as never;
      }
      if (String(url).startsWith("/api/me/access")) {
        return { data: { effective_roles: [] } } as never;
      }
      throw new Error(`Unexpected GET ${url}`);
    });
  });

  it("finds a project under the selected organisation without listing accessible projects", async () => {
    render(<ProjectAccess />);

    fireEvent.change(screen.getByLabelText("Organisation name"), {
      target: { value: "Demonstration_Org" },
    });
    await screen.findByText("Matched: Demonstration_Org");

    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "test proj" },
    });

    await waitFor(() => {
      expect(http.get).toHaveBeenCalledWith(
        "/api/projects/access-request-lookup",
        {
          params: {
            organisation_id: "org-1",
            project_name: "test proj",
          },
        },
      );
    });
    await screen.findByText("Requested access level");
    expect(http.get).not.toHaveBeenCalledWith("/api/projects?limit=500");
  });
});
