import http from "@/http";
import type {
  MyProjectAccess,
  ProjectAccess,
  ProjectStageAssignment,
} from "@/types/authorization";

export type AssignableProjectUser = {
  user_id: string;
  display_name: string;
  email: string;
};

class ProjectAccessService {
  async fetchMyProjectAccess(projectId: string): Promise<MyProjectAccess> {
    const response = await http.get<MyProjectAccess>("/api/me/access", {
      params: { project_id: projectId },
    });
    return response.data;
  }

  async fetchProjectAccess(projectId: string): Promise<ProjectAccess> {
    const response = await http.get<ProjectAccess>(
      `/api/projects/${projectId}/access`,
    );
    return response.data;
  }

  async searchAssignableUsers(projectId: string, query: string): Promise<AssignableProjectUser[]> {
    const response = await http.get<AssignableProjectUser[]>(
      `/api/projects/${projectId}/user-search`, { params: { q: query } },
    );
    return response.data;
  }

  async searchProjectSetupUsers(organisationId: string, query: string): Promise<AssignableProjectUser[]> {
    const response = await http.get<AssignableProjectUser[]>(
      "/api/projects/setup-user-search",
      { params: { organisation_id: organisationId, q: query } },
    );
    return response.data;
  }

  async updateUserStageAccess(
    projectId: string,
    userId: string,
    assignments: ProjectStageAssignment[],
  ): Promise<ProjectAccess> {
    const response = await http.put<ProjectAccess>(
      `/api/projects/${projectId}/users/${userId}/stage-access`,
      { assignments },
    );
    return response.data;
  }
}

export default new ProjectAccessService();
