import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import http from "@/http";
import { useProjectHeader } from "@/context/ProjectHeaderContext";
import { StatusBadge } from "@/components/StatusBadge";
import { useUser } from "@/context/UserContext";
import { SelectListbox } from "@/components/common/Select";
import LookupsService from "@/services/Lookups.service";
import ActivityDataService from "@/services/ActivityData.service";
import type { StageAccess } from "@/types/authorization";

type DatasetRevisionInfo = {
  id: string;
  name: string;
  scope_type: "DEFAULT" | "ORG" | "PROJECT";
  status: string;
};

const SCOPE_LABEL: Record<string, string> = {
  DEFAULT: "Global",
  ORG: "Organisation",
  PROJECT: "Project",
};

const SCOPE_BADGE_CLASS: Record<string, string> = {
  DEFAULT: "bg-blue-100 text-blue-700",
  ORG: "bg-purple-100 text-purple-700",
  PROJECT: "bg-green-100 text-green-700",
};

function ScopeBadge({ scope }: { scope: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${SCOPE_BADGE_CLASS[scope] ?? "bg-gray-100 text-gray-700"}`}>
      {SCOPE_LABEL[scope] ?? scope}
    </span>
  );
}

interface StageInstance {
  id: string;
  project_id: string;
  stage: "BUSINESS_CASE" | "DESIGN" | "CONSTRUCTION" | "RECURRING";
  approval_status: "open" | "tech_approved" | "final_approved" | "submitted" | "rejected" | "pending_reopen";
  num_reports_required: number | null;
  approved_by: string | null;
  approved_at: string | null;
  created_on: string | null;
  updated_on: string | null;
}

interface StageConfig {
  id: string;
  stage: string;
  enabled: boolean;
  num_reports_required: number | null;
  frequency: string | null;
}

interface ProjectDetail {
  id: string;
  project_name: string;
  program_name: string | null;
  project_class: string;
  project_type_id: string;
  project_type_name: string | null;
  project_typecast_id: string | null;
  project_typecast_name: string | null;
  benchmark_mastertype?: { id: string; code: string; name: string };
  benchmark_typecast?: { id: string; code: string; name: string };
  is_active: boolean;
  description: string | null;
  construction_start_date: string | null;
  construction_end_date: string | null;
  commencement_of_operations: string | null;
  operational_life_years: number | null;
  project_capex_million: number | null;
  proponent_org_name: string | null;
  proponent_org_id: string | null;
  stage_instances: StageInstance[];
  stage_configs: StageConfig[];
}

const STAGE_ORDER: Record<StageInstance["stage"], number> = {
  BUSINESS_CASE: 1,
  DESIGN: 2,
  CONSTRUCTION: 3,
  RECURRING: 1,
};

const STAGE_LABEL: Record<StageInstance["stage"], string> = {
  BUSINESS_CASE: "Business Case",
  DESIGN: "Design",
  CONSTRUCTION: "Construction",
  RECURRING: "Recurring",
};

const CLASS_LABEL: Record<string, string> = {
  SMALL: "Small",
  LARGE: "Large",
  RECURRING: "Contractor / Maintenance",
};

function ApprovalBadge({ status }: { status: StageInstance["approval_status"] }) {
  if (status === "final_approved") {
    /* return (
     <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
       <span className="material-symbols-rounded text-base leading-none">lock</span>
       Approved
     </span>
   ); */
    return <StatusBadge status={"Approved"} />

  }
  if (status === "tech_approved") {
    return (
      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
        <span className="material-symbols-rounded text-base leading-none">verified</span>
        Tech Approved
      </span>
    );
    //return <StatusBadge status={"Tech Approved"} />
  }
  if (status === "rejected") {
    /* return (
      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-danger/35 text-danger">
        <span className="material-symbols-rounded text-base leading-none">close</span>
        Rejected
      </span>
    ); */
    return <StatusBadge status={"Rejected"} />
  }
  if (status === "submitted") {
    /*  return (
       <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-warning/35 text-warning">
         <span className="material-symbols-rounded text-base leading-none">hourglass_empty</span>
         Awaiting approval
       </span>
     ); */
    return <StatusBadge status={"Awaiting Approval"} />

  }
  if (status === "pending_reopen") {
    /* return (
      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-warning/35 text-warning">
        <span className="material-symbols-rounded text-base leading-none">hourglass_empty</span>
       Reopen requested
      </span>
    ); */
    return <StatusBadge status={"Reopen Requested"} />
  }
  return (
    <>
      {/* <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
      <span className="material-symbols-rounded text-base leading-none">edit</span>
      Open123
    </span> */}
      <StatusBadge status={"In Progress"} />

    </>

  );
}



export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { setProjectHeader, clearProjectHeader } = useProjectHeader();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [showReopenConfirm, setShowReopenConfirm] = useState(false);
  const [actioning, setActioning] = useState(false);
  const [projectRoles, setProjectRoles] = useState<string[]>([]);
  const [stageAccess, setStageAccess] = useState<StageAccess[]>([]);

  const [activeRevision, setActiveRevision] = useState<DatasetRevisionInfo | null>(null);
  const [bindableRevisions, setBindableRevisions] = useState<DatasetRevisionInfo[]>([]);
  const [switchingDataset, setSwitchingDataset] = useState(false);
  const [pendingRevision, setPendingRevision] = useState<DatasetRevisionInfo | null>(null);
  const [datasetIssues, setDatasetIssues] = useState<Array<{
    activity_data_id: string;
    entry: string;
    data_entry_table: string;
    dataset_table: string;
  }>>([]);
  const [calculationErrors, setCalculationErrors] = useState<Array<{
    activity_data_id: string;
    entry: string;
    data_entry_table: string;
    message: string;
  }>>([]);
  const [switchFailure, setSwitchFailure] = useState<{
    message: string;
    errors: Array<{ activity_data_id?: string | null; entry: string; data_entry_table?: string | null; message: string }>;
  } | null>(null);

  const { roles } = useUser();

  const isOrgAdmin = roles.includes("ORG_ADMIN");

  const canEditProjectSetup =
    isOrgAdmin ||
    projectRoles.includes("PROJECT_ADMIN");

  const canCloseReopen = projectRoles.some((r) =>
    ["PROJECT_ADMIN", "ORG_ADMIN"].includes(r)
  );

  useEffect(() => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    Promise.all([
      http.get<ProjectDetail>(`/api/projects/${projectId}`),
      http.get(`/api/me/access?project_id=${projectId}`),
    ])
      .then(([projRes, accessRes]) => {
        setProject(projRes.data);
        setProjectHeader(projRes.data.project_name, false, projectId);
        setProjectRoles(accessRes.data.effective_roles ?? []);
        setStageAccess(accessRes.data.stage_access ?? []);
      })
      .catch((err) => {
        console.error("ProjectDetail load failed:", err);
        console.error("ProjectDetail response:", err?.response?.data);
        console.error("ProjectDetail status:", err?.response?.status);
        console.error("ProjectDetail URL:", err?.config?.url);

        setError(
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "Failed to load project. Please try again."
        );
      })
      .finally(() => setLoading(false));

    Promise.all([
      http.get(`/api/project-dataset-revisions/by-project/${projectId}`),
      http.get(`/api/project-dataset-revisions/bindable/${projectId}`),
    ]).then(([pdrRes, bindableRes]) => {
      const bindings = pdrRes.data as Array<{
        revision?: DatasetRevisionInfo;
        calculation_report?: {
          missing_data?: Array<{ activity_data_id: string; entry: string; data_entry_table: string; dataset_table: string }>;
          calculation_errors?: Array<{ activity_data_id: string; entry: string; data_entry_table: string; message: string }>;
        };
      }>;
      if (bindings.length > 0 && bindings[0].revision) {
        setActiveRevision(bindings[0].revision);
        setDatasetIssues(bindings[0].calculation_report?.missing_data ?? []);
        setCalculationErrors(bindings[0].calculation_report?.calculation_errors ?? []);
      }
      setBindableRevisions(bindableRes.data as DatasetRevisionInfo[]);
    }).catch((loadError: any) => {
      const detail = loadError?.response?.data?.detail;
      if (detail?.code === "dataset_recalculation_failed") {
        setSwitchFailure({
          message: detail.message ?? "The project dataset could not be initialized because recalculation failed.",
          errors: detail.calculation_errors ?? [],
        });
      }
    });

    return () => clearProjectHeader();
  }, [projectId]);

  if (loading) {
    return <div className="p-8 text-slate-400">Loading…</div>;
  }

  if (error || !project) {
    return (
      <div className="p-8 text-red-500">
        {error ?? "Project not found."}
      </div>
    );
  }

  const stageAccessById = new Map(
    stageAccess.map((item) => [item.stage_instance_id, item.access]),
  );

  const sortedInstances = [...(project.stage_instances ?? [])]
    .filter((inst) => {
      if (project.project_class === "RECURRING") return inst.stage === "RECURRING";
      return inst.stage !== "RECURRING";
    })
    .filter((inst) => stageAccessById.get(inst.id) && stageAccessById.get(inst.id) !== "NONE")
    .sort(
      (a, b) => (STAGE_ORDER[a.stage] ?? 99) - (STAGE_ORDER[b.stage] ?? 99)
    );

  type StageRow = { instance: StageInstance; reportNumber: number; totalReports: number };
  const stageRows: StageRow[] = sortedInstances.flatMap((inst) => {
    const total = inst.num_reports_required ?? 1;
    return Array.from({ length: total }, (_, i) => ({
      instance: inst,
      reportNumber: i + 1,
      totalReports: total,
    }));
  });

  const canChangeDataset = canEditProjectSetup && project.is_active;

  async function handleSwitchDataset() {
    if (!project || !pendingRevision) return;
    setSwitchingDataset(true);
    setSwitchFailure(null);
    try {
      const response = await http.post("/api/project-dataset-revisions/migrate", {
        project_id: project.id,
        to_revision_id: pendingRevision.id,
      });
      LookupsService.clearProjectDatasetRevisionCache(project.id);
      ActivityDataService.clearProjectDatasetRevisionCache(project.id);
      setDatasetIssues(response.data?.missing_data ?? []);
      setCalculationErrors(response.data?.calculation_errors ?? []);
      setSwitchFailure(null);
      setActiveRevision(pendingRevision);
      setPendingRevision(null);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      if (detail?.code === "dataset_recalculation_failed") {
        setSwitchFailure({
          message: detail.message ?? "The dataset revision was not changed because recalculation failed.",
          errors: detail.calculation_errors ?? [],
        });
      } else {
        setSwitchFailure({
          message: typeof detail === "string"
            ? detail
            : detail?.message ?? "Failed to switch dataset. Please try again.",
          errors: [],
        });
      }
    } finally {
      setSwitchingDataset(false);
    }
  }

  async function handleCloseProject() {
    if (!project) return;
    setActioning(true);
    try {
      await http.patch(`/api/projects/${project.id}/close`);
      setProject((p) => p ? { ...p, is_active: false } : p);
      setShowCloseConfirm(false);
    } finally {
      setActioning(false);
    }
  }

  async function handleReopenProject() {
    if (!project) return;
    setActioning(true);
    try {
      await http.patch(`/api/projects/${project.id}/reopen`);
      setProject((p) => p ? { ...p, is_active: true } : p);
      setShowReopenConfirm(false);
    } finally {
      setActioning(false);
    }
  }

  const isLocked = (stage: StageInstance) => stage.approval_status === "final_approved";

  return (
    <>
      <div className="min-h-full bg-bg-content">
        {/* Header bar */}
        <div className="flex items-center gap-3 px-8 py-4 border-b border-gray-200 bg-white">
          {/* <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 cursor-pointer text-sm text-gray-500 hover:text-gray-800"
          >
            <span className="material-symbols-rounded text-base">arrow_back</span>
            Back
          </button>
          <span className="text-gray-300">|</span> */}
          <div className="text-sm font-medium text-text-dark truncate">{project.project_name}</div>
          <span
            className={`ml-2 inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${project.is_active ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-600"
              }`}
          >
            {project.is_active ? "Active" : "Inactive"}
          </span>
        </div>

        <div className="max-w-5xl mx-auto px-8 py-8 space-y-8">

          {/* Project summary card */}
          <section className="bg-white rounded-[var(--radius-3)] border border-gray-200 p-6">

            <div className="flex items-center mb-4">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                Project Overview
              </h2>

              <div className="ml-auto flex items-center gap-2">
                {canEditProjectSetup && project.is_active && (
                  <button
                    type="button"
                    onClick={() => navigate(`/projects/${project.id}/edit`)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] bg-primary text-white hover:bg-primary/90"
                  >
                    <span className="material-symbols-rounded text-base leading-none">
                      edit_note
                    </span>
                    Edit Project Setup
                  </button>
                )}

                {isOrgAdmin && (
                  <button
                    type="button"
                    onClick={() => navigate(`/projects/${project.id}/audit`)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] border border-gray-300 text-gray-700 hover:bg-gray-50"
                  >
                    <span className="material-symbols-rounded text-base leading-none">
                      history
                    </span>
                    Audit Log
                  </button>
                )}

                {canCloseReopen && project.is_active && (
                  <button
                    type="button"
                    onClick={() => setShowCloseConfirm(true)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] border border-gray-300 text-gray-700 hover:bg-gray-50"
                  >
                    <span className="material-symbols-rounded text-base leading-none">
                      lock
                    </span>
                    Close Project
                  </button>
                )}

                {canCloseReopen && !project.is_active && (
                  <button
                    type="button"
                    onClick={() => setShowReopenConfirm(true)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] border border-gray-300 text-gray-700 hover:bg-gray-50"
                  >
                    <span className="material-symbols-rounded text-base leading-none">
                      lock_open
                    </span>
                    Reopen Project
                  </button>
                )}
              </div>
            </div>



            <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
              <div>
                <span className="text-gray-500">Category</span>
                <p className="font-medium text-text-dark mt-0.5">
                  {CLASS_LABEL[project.project_class] ?? project.project_class}
                </p>
              </div>
              <div>
                <span className="text-gray-500">Type</span>
                <p className="font-medium text-text-dark mt-0.5">
                  {project.project_type_name ?? "—"}
                </p>
              </div>
              {project.program_name && (
                <div>
                  <span className="text-gray-500">Program</span>
                  <p className="font-medium text-text-dark mt-0.5">{project.program_name}</p>
                </div>
              )}
              {project.proponent_org_name && (
                <div>
                  <span className="text-gray-500">Proponent Organisation</span>
                  <p className="font-medium text-text-dark mt-0.5">{project.proponent_org_name}</p>
                </div>
              )}
              {project.description && (
                <div className="col-span-2">
                  <span className="text-gray-500">Description</span>
                  <p className="text-text-dark mt-0.5">{project.description}</p>
                </div>
              )}
            </div>
          </section>

          {/* Dataset revision selector */}
          <section className="bg-white rounded-[var(--radius-3)] border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Dataset
            </h2>

            <p className="text-xs text-gray-400 mb-4">
              All project calculations use the selected dataset revision. Existing entries are recalculated when you switch revisions.
            </p>

            {activeRevision ? (
              <div className="flex items-center gap-2 text-sm mb-3">
                <span className="text-gray-500">Current:</span>
                <span className="font-medium text-text-dark">{activeRevision.name}</span>
                <ScopeBadge scope={activeRevision.scope_type} />
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic mb-3">No dataset selected — choose one below.</p>
            )}

            <SelectListbox
              value={activeRevision?.id ?? ""}
              options={bindableRevisions.map((r) => ({
                value: r.id,
                label: r.name,
                status: SCOPE_LABEL[r.scope_type],
              }))}
              onChange={(id) => {
                const rev = bindableRevisions.find((r) => r.id === id);
                if (rev && rev.id !== activeRevision?.id) {
                  setSwitchFailure(null);
                  setPendingRevision(rev);
                }
              }}
              disabled={!canChangeDataset || switchingDataset}
              loading={switchingDataset}
              placeholder="Select a dataset revision…"
              noOptionsLabel="No published dataset revisions available"
            />

            {datasetIssues.length > 0 && (
              <div role="alert" className="mt-5 rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
                <h3 className="font-semibold">Some entries could not be calculated from this dataset</h3>
                <p className="mt-1">
                  The following entries lack necessary data to calculate emissions. You may add data to the selected dataset, remove the entries, or change the dataset selection to the previous one.
                </p>
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full border-collapse text-left">
                    <thead>
                      <tr className="border-b border-amber-300">
                        <th className="py-2 pr-4">Entry</th>
                        <th className="py-2 pr-4">Data entry table</th>
                        <th className="py-2">Dataset table missing data</th>
                      </tr>
                    </thead>
                    <tbody>
                      {datasetIssues.map((issue) => (
                        <tr key={issue.activity_data_id} className="border-b border-amber-200 last:border-0">
                          <td className="py-2 pr-4">{issue.entry}</td>
                          <td className="py-2 pr-4">{issue.data_entry_table}</td>
                          <td className="py-2">{issue.dataset_table}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {calculationErrors.length > 0 && (
              <div role="alert" className="mt-4 rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900">
                <h3 className="font-semibold">Some calculations need attention</h3>
                <p className="mt-1">These entries could not be recalculated. Review the calculation errors before trying another dataset revision.</p>
                <ul className="mt-2 list-disc pl-5">
                  {calculationErrors.map((issue) => (
                    <li key={issue.activity_data_id}>{issue.entry} ({issue.data_entry_table}): {issue.message}</li>
                  ))}
                </ul>
              </div>
            )}
            {switchFailure && (
              <div role="alert" className="mt-4 rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900">
                <h3 className="font-semibold">Dataset revision was not changed</h3>
                <p className="mt-1">{switchFailure.message}</p>
                {switchFailure.errors.length > 0 && (
                  <ul className="mt-2 list-disc pl-5">
                  {switchFailure.errors.map((issue, index) => (
                      <li key={issue.activity_data_id ?? `${issue.data_entry_table ?? issue.entry}-${index}`}>
                        {issue.entry}{issue.data_entry_table ? ` (${issue.data_entry_table})` : ""}: {issue.message}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>

          {/* Stage progress */}
          <section className="bg-white rounded-[var(--radius-3)] border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Reporting Stages
            </h2>

            {sortedInstances.length === 0 ? (
              <p className="text-sm text-gray-400 italic">No stage instances found for this project.</p>
            ) : (
              <div className="divide-y divide-gray-100">
                {stageRows.map(({ instance, reportNumber, totalReports }, idx) => {
                  const stageLabel = STAGE_LABEL[instance.stage] ?? instance.stage;
                  const rowLabel =
                    totalReports > 1
                      ? `${stageLabel} — Submission ${reportNumber} of ${totalReports}`
                      : stageLabel;

                  const handleRowClick = () => {
                    navigate(
                      `/dataEntry?projectId=${project.id}&stageInstanceId=${instance.id}&reportNumber=${reportNumber}`
                    );
                  };

                  return (
                    <div
                      key={`${instance.id}-${reportNumber}`}
                      className="flex items-center justify-between py-3.5 px-3 -mx-3 rounded cursor-pointer transition-colors hover:bg-gray-50"
                      onClick={handleRowClick}
                      role="button"
                      aria-label={`View report ${reportNumber}`}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          handleRowClick();
                        }
                      }}
                    >
                      <div className="flex items-center gap-3">
                        {/* Sequence circle */}
                        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-gray-100 text-xs font-semibold text-gray-600 shrink-0">
                          {idx + 1}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-text-dark">
                            {rowLabel}
                          </p>
                          {instance.approved_at && (
                            <p className="text-xs text-gray-400 mt-0.5">
                              {instance.approval_status === "final_approved" ? "Approved" : "Tech approved"}{" "}
                              {new Date(instance.approved_at).toLocaleDateString("en-AU", {
                                day: "numeric",
                                month: "short",
                                year: "numeric",
                              })}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <ApprovalBadge status={instance.approval_status} />
                        {isLocked(instance) && (
                          <span
                            className="text-gray-400 text-sm"
                            title="This stage is locked — no edits allowed"
                          >
                            <span className="material-symbols-rounded text-lg">lock</span>
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

        </div>
      </div>

      {showCloseConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-[var(--radius-3)] shadow-lg w-full max-w-md p-6 space-y-4">
            <h3 className="text-base font-semibold text-text-dark">Close Project?</h3>
            <p className="text-sm text-gray-600">
              Closing this project will make all data entry read-only. You can reopen it later if needed.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowCloseConfirm(false)}
                disabled={actioning}
                className="px-4 py-2 text-sm rounded-[var(--radius-3)] border border-gray-300 cursor-pointer text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCloseProject}
                disabled={actioning}
                className="px-4 py-2 text-sm rounded-[var(--radius-3)] bg-primary cursor-pointer text-white hover:bg-primary/90 disabled:opacity-50"
              >
                {actioning ? "Closing…" : "Close Project"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showReopenConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-[var(--radius-3)] shadow-lg w-full max-w-md p-6 space-y-4">
            <h3 className="text-base font-semibold text-text-dark">Reopen Project?</h3>
            <p className="text-sm text-gray-600">
              Reopening this project will allow data entry again.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowReopenConfirm(false)}
                disabled={actioning}
                className="px-4 py-2 text-sm rounded-[var(--radius-3)] border border-gray-300 cursor-pointer text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReopenProject}
                disabled={actioning}
                className="px-4 py-2 text-sm rounded-[var(--radius-3)] bg-primary text-white cursor-pointer hover:bg-primary/90 disabled:opacity-50"
              >
                {actioning ? "Reopening…" : "Reopen Project"}
              </button>
            </div>
          </div>
        </div>
      )}

      {pendingRevision && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-[var(--radius-3)] shadow-lg w-full max-w-md p-6 space-y-4">
            <h3 className="text-base font-semibold text-text-dark">Switch Dataset?</h3>
            <p className="text-sm text-gray-600">
              Switch to <strong>{pendingRevision.name}</strong>{" "}
              <ScopeBadge scope={pendingRevision.scope_type} />? All project calculations will reference data from this revision going forward.
            </p>
            <p className="text-xs text-gray-400">
              Existing entries will be recalculated against this revision before the switch completes. Entries without required dataset data will be set to zero and listed on the project page. This change is recorded in the audit log.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setPendingRevision(null)}
                disabled={switchingDataset}
                className="px-4 py-2 text-sm rounded-[var(--radius-3)] border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSwitchDataset}
                disabled={switchingDataset}
                className="px-4 py-2 text-sm rounded-[var(--radius-3)] bg-primary text-white hover:bg-primary/90 disabled:opacity-50"
              >
                {switchingDataset ? "Switching…" : "Confirm Switch"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
