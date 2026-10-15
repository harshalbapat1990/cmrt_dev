import { useCallback, useEffect, useRef, useState, type SetStateAction } from "react";
import http from "@/http";
import ProjectsService from "@/services/Projects.service";
import ProjectAccessService from "@/services/ProjectAccess.service";
import ProjectOptionsService, { type ProjectOption } from "@/services/ProjectOptions.service";
import type { StageAccess } from "@/types/authorization";
import { filterAccessibleStageInstances } from "../stageAccessUi";
import { STAGE_ENUM_TO_LABEL, SUBSTAGES_FOR } from "../stageConstants";
import { normalizeProjectClass } from "../dataEntryTypes";
import type {
  JurisdictionContext,
  ProjectClass,
  ProjectDetails,
  ReportingBoundary,
  StageCode,
  StageInstance,
  StageLabel,
} from "../dataEntryTypes";

export interface DataEntryProjectBootstrapState {
  isLoaded: boolean;
  loadError: string | null;
  projectData: ProjectDetails | null;
  projectName: string;
  programName: string;
  stageInstances: StageInstance[];
  stageAccess: StageAccess[];
  projectOptions: ProjectOption[];
  lockedStages: Set<StageCode>;
  frequency: string;
  firstSubmissionMonth: string | null;
  reportingBoundaries: ReportingBoundary[];
  projectClass: ProjectClass | null;
  projectTypeName: string | null;
  projectClosed: boolean;
  projectGridCtx: JurisdictionContext | null;
  operationalLifeYears: number | null;
  opsStartYear: number | null;
  constructionStartDate: string | null;
  constructionEndDate: string | null;
  accessDenied: boolean;
}

const initialState: DataEntryProjectBootstrapState = {
  isLoaded: false,
  loadError: null,
  projectData: null,
  projectName: "",
  programName: "",
  stageInstances: [],
  stageAccess: [],
  projectOptions: [],
  lockedStages: new Set(),
  frequency: "Monthly",
  firstSubmissionMonth: null,
  reportingBoundaries: [],
  projectClass: null,
  projectTypeName: null,
  projectClosed: false,
  projectGridCtx: null,
  operationalLifeYears: null,
  opsStartYear: null,
  constructionStartDate: null,
  constructionEndDate: null,
  accessDenied: false,
};

interface UseDataEntryProjectBootstrapArgs {
  projectId: string;
  stageInstanceIdParam: string | null;
  reportNumberParam: number;
  setProjectHeader: (name: string, saved: boolean, id?: string) => void;
  clearProjectHeader: () => void;
  setActiveStage: (stage: StageLabel) => void;
  setActiveSubStage: (subStage: string) => void;
  setActiveReportNumber: (reportNumber: number) => void;
}

export function useDataEntryProjectBootstrap({
  projectId,
  stageInstanceIdParam,
  reportNumberParam,
  setProjectHeader,
  clearProjectHeader,
  setActiveStage,
  setActiveSubStage,
  setActiveReportNumber,
}: UseDataEntryProjectBootstrapArgs) {
  const [state, setState] = useState(initialState);
  const pendingOptions = useRef<Map<string, Promise<ProjectOption[]>>>(new Map());

  const loadStageOptions = useCallback((stageInstanceId: string, access: StageAccess["access"]) => {
    if (access === "NONE") return Promise.resolve([] as ProjectOption[]);
    const pending = pendingOptions.current.get(stageInstanceId);
    if (pending) return pending;

    const request = access === "VIEW"
      ? ProjectOptionsService.fetchOptions(stageInstanceId)
      : ProjectOptionsService.ensureOptions(stageInstanceId);
    const trackedRequest = request
      .then((options) => {
        setState((current) => ({
          ...current,
          projectOptions: [
            ...current.projectOptions.filter((option) => option.stage_instance_id !== stageInstanceId),
            ...options,
          ],
        }));
        return options;
      })
      .finally(() => pendingOptions.current.delete(stageInstanceId));
    pendingOptions.current.set(stageInstanceId, trackedRequest);
    return trackedRequest;
  }, []);

  const refreshStageOptions = useCallback(async (stageInstanceId: string) => {
    const options = await ProjectOptionsService.fetchOptions(stageInstanceId);
    setState((current) => ({
      ...current,
      projectOptions: [
        ...current.projectOptions.filter((option) => option.stage_instance_id !== stageInstanceId),
        ...options,
      ],
    }));
    return options;
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadProject = async () => {
      if (!projectId) {
        setState((current) => ({ ...current, isLoaded: true }));
        return;
      }

      try {
        setState((current) => ({ ...current, isLoaded: false, loadError: null, accessDenied: false }));
        const project = await ProjectsService.fetchProjectDetails(projectId) as ProjectDetails;
        if (cancelled) return;

        const projectName = project.name ?? project.project_name ?? "";
        const projectClass = normalizeProjectClass(project.project_class);
        setState((current) => ({
          ...current,
          projectData: project,
          projectName,
          programName: project.program_name ?? "",
          projectClass,
          projectClosed: !(project.is_active ?? true),
          frequency:
            project.stage_configs?.find((stage) => stage.stage === "CONSTRUCTION")?.frequency ??
            "Monthly",
          firstSubmissionMonth: project.first_submission_month ?? null,
        }));
        setProjectHeader(projectName, true, projectId);

        const access = await ProjectAccessService.fetchMyProjectAccess(projectId);
        if (cancelled) return;
        const stageAccess = access.stage_access ?? [];
        const accessibleInstances = filterAccessibleStageInstances(
          project.stage_instances ?? [],
          stageAccess,
        );

        if (!accessibleInstances.length) {
          setState((current) => ({ ...current, accessDenied: true, isLoaded: true }));
          return;
        }

        setState((current) => ({
          ...current,
          stageAccess,
          stageInstances: accessibleInstances,
          lockedStages: new Set(
            accessibleInstances
              .filter((instance) => instance.approval_status === "final_approved")
              .map((instance) => instance.stage),
          ),
          projectTypeName: project.project_type_name ?? null,
          operationalLifeYears: project.operational_life_years ?? null,
          opsStartYear: project.commencement_of_operations
            ? new Date(project.commencement_of_operations).getFullYear()
            : null,
          constructionStartDate: project.construction_start_date ?? null,
          constructionEndDate: project.construction_end_date ?? null,
        }));

        const firstPostcode = [...(project.postcodes ?? [])].sort(
          (left, right) =>
            new Date(left.created_on ?? 0).getTime() - new Date(right.created_on ?? 0).getTime(),
        )[0];
        const gridContext: JurisdictionContext =
          firstPostcode?.jurisdiction_name && firstPostcode.grid_region
            ? {
                jurisdiction: firstPostcode.jurisdiction_name.toLowerCase().includes("new zealand")
                  ? "New Zealand"
                  : "Australia",
                region: firstPostcode.grid_region,
              }
            : { jurisdiction: "Australia", region: "New South Wales" };
        setState((current) => ({ ...current, projectGridCtx: gridContext }));

        const targetInstance =
          (stageInstanceIdParam
            ? accessibleInstances.find((instance) => instance.id === stageInstanceIdParam)
            : undefined) ?? accessibleInstances[0];
        const initialStage: StageLabel =
          STAGE_ENUM_TO_LABEL[targetInstance.stage as StageCode] ??
          (projectClass === "RECURRING" ? "Recurring" : "Business case");

        if ((targetInstance.num_reports_required ?? 1) > 0) {
          const stageAccessLevel =
            stageAccess.find((entry) => entry.stage_instance_id === targetInstance.id)?.access ?? "NONE";
          if (stageAccessLevel !== "NONE") {
            try {
              await loadStageOptions(targetInstance.id, stageAccessLevel);
            } catch (error) {
              console.warn("Failed to load options for stage instance:", targetInstance.id, error);
            }
          }
        }
        if (cancelled) return;
        setActiveReportNumber(reportNumberParam);

        const boundariesResponse = await http.get(`/api/projects/${projectId}/reporting-boundaries`);
        if (cancelled) return;
        setActiveStage(initialStage);
        setActiveSubStage(SUBSTAGES_FOR(initialStage, projectClass)[0] ?? "Construction");
        setState((current) => ({
          ...current,
          isLoaded: true,
          loadError: null,
          reportingBoundaries: Array.isArray(boundariesResponse.data)
            ? boundariesResponse.data as ReportingBoundary[]
            : [],
        }));
      } catch (error) {
        if (!cancelled) {
          console.error("Error loading:", error);
          setState((current) => ({
            ...current,
            isLoaded: true,
            loadError: "We couldn't load this project's data. Please try again or return to the project page.",
          }));
        }
      }
    };

    void loadProject();
    return () => {
      cancelled = true;
      clearProjectHeader();
    };
  }, [
    projectId,
    stageInstanceIdParam,
    reportNumberParam,
    setProjectHeader,
    clearProjectHeader,
    setActiveStage,
    setActiveSubStage,
    setActiveReportNumber,
    loadStageOptions,
  ]);

  const setProjectOptions = useCallback((value: SetStateAction<ProjectOption[]>) => {
    setState((current) => ({
      ...current,
      projectOptions: typeof value === "function" ? value(current.projectOptions) : value,
    }));
  }, []);

  return { ...state, setProjectOptions, loadStageOptions, refreshStageOptions };
}
