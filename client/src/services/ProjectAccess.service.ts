import http from "@/http";
import type {
  MyProjectAccess,
  ProjectAccess,
  ProjectStageAssignment,
} from "@/types/authorization";

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
