import { useEffect, useState } from "react";
import ProjectsService from "@/services/Projects.service";
import type { ProjectDetails } from "../smallProject/dataEntry/dataEntryTypes";

export type DashboardProject = ProjectDetails & { id: string; projectClass?: string | null };

interface State {
  project: DashboardProject | null;
  loading: boolean;
  error: string | null;
}

function asDashboardProject(value: unknown, expectedId: string): DashboardProject {
  if (typeof value !== "object" || value === null) {
    throw new Error("Project response was invalid");
  }
  const record = value as ProjectDetails;
  if (record.id !== expectedId) {
    throw new Error("Project response did not match the requested project");
  }
  return record as DashboardProject;
}

/** Uses router-provided project data when available and fetches it for direct/reloaded URLs. */
export function useProjectDashboardProject(projectId: string, routeProject: DashboardProject | null) {
  const [state, setState] = useState<State>(() => ({
    project: routeProject,
    loading: !routeProject && Boolean(projectId),
    error: null,
  }));

  useEffect(() => {
    let cancelled = false;

    if (routeProject?.id === projectId) {
      setState({ project: routeProject, loading: false, error: null });
      return () => { cancelled = true; };
    }

    if (!projectId) {
      setState({ project: null, loading: false, error: null });
      return () => { cancelled = true; };
    }

    setState({ project: null, loading: true, error: null });
    void ProjectsService.fetchProjectDetails(projectId)
      .then((response: unknown) => {
        const project = asDashboardProject(response, projectId);
        if (!cancelled) setState({ project, loading: false, error: null });
      })
      .catch(() => {
        if (!cancelled) {
          setState({
            project: null,
            loading: false,
            error: "We couldn't load this project's dashboard. Please return to the project and try again.",
          });
        }
      });

    return () => { cancelled = true; };
  }, [projectId, routeProject]);

  return state;
}
