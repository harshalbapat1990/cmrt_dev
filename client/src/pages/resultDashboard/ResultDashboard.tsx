import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { useProjectHeader } from "@/context/ProjectHeaderContext";

import EmissionsBreakdownTab from "./EmissionsBreakdownTab";
import MaterialHotspotsTab from "./MaterialHotspotsTab";
import MitigationSummaryTab from "./MitigationSummaryTab";
import RenewableEnergyTab from "./RenewableEnergyTab";
import OffsettingMeasuresTab from "./OffsettingMeasuresTab";
import ConstructionOperationsComparisonTab from "./Comparison";
import ComparisonByOption from "./ComparisonByOption";
import WasteAndRecycleTab from "./WasteAndRecycleTab";
import LcaModuleBreakdownTab from "./LcaModuleBreakdownTab";
import RatingPerformance from "./RatingPerformance";
import DetailedResultsTab from "./DetailedResultsTab";
import { SelectListbox } from "../../components/common/Select";
import { STAGE_ENUM_TO_LABEL } from "../smallProject/dataEntry/stageConstants";
import ProjectOptionsService from "@/services/ProjectOptions.service";
import { ConstructionPeriodsService } from "@/services/ConstructionPeriods.service";
import { useProjectStageAccess } from "@/customHooks/useProjectStageAccess";
import { filterAccessibleStageInstances } from "../smallProject/dataEntry/stageAccessUi";

/* =======================
   Types
======================= */

type AccountingMethod = "market" | "location";
type ProjectCategory = "Small" | "Large" | "Recurring";
type SubmissionLabel = "Business case" | "Design" | "Construction";

type SubmissionOption = {
  label: string;
  value: string;
  stage: string;
  stageLabel: SubmissionLabel;
  stageInstanceId: string;
  reportIndex?: number;
};


type Section =
  | "Emissions breakdown"
  | "Materials hotspots"
  | "Mitigation summary"
  | "Comparison by stage/period"
  | "Options Comparison"
  | "Renewable energy"
  | "Offsetting summary"
  | "Waste & recycle materials"
  | "ITMM reporting"
  | "Rating performance"
  | "Detailed Results";

type ConstructionPeriod = {
  id: string;
  period_label: string;
};


const ALL_SECTIONS: Section[] = [
  "Emissions breakdown",
  "Materials hotspots",
  "Mitigation summary",
  "Comparison by stage/period",
  "Options Comparison",
  "Renewable energy",
  "Offsetting summary",
  "Waste & recycle materials",
  "ITMM reporting",
  "Rating performance",
  "Detailed Results",
];

/* =======================
   Screen rules
======================= */

const SECTION_PROJECT_RULES: Record<Section, ProjectCategory[]> = {
  "Emissions breakdown": ["Small", "Large", "Recurring"],

  "Materials hotspots": ["Small", "Large", "Recurring"],

  "Mitigation summary": ["Large"],

  "Comparison by stage/period": ["Small", "Large", "Recurring"],

  "Options Comparison": ["Small", "Large"],

  "Renewable energy": ["Small", "Large", "Recurring"],

  "Offsetting summary": ["Small", "Large"],

  "Waste & recycle materials": ["Small", "Large", "Recurring"],

  "ITMM reporting": ["Small", "Large"],

  "Rating performance": ["Small", "Large"],

  "Detailed Results": ["Small", "Large", "Recurring"],
};

const SECTION_SUBMISSION_RULES: Record<Section, SubmissionLabel[]> = {
  "Emissions breakdown": ["Business case", "Design", "Construction"],

  "Materials hotspots": ["Business case", "Design", "Construction"],

  "Mitigation summary": ["Design", "Construction"],

  "Comparison by stage/period": ["Business case", "Design", "Construction"],

  "Options Comparison": ["Business case"],

  "Renewable energy": ["Business case", "Design", "Construction"],

  "Offsetting summary": ["Business case", "Design", "Construction"],

  "Waste & recycle materials": ["Business case", "Design", "Construction"],

  "ITMM reporting": ["Business case", "Design", "Construction"],

  "Rating performance": ["Business case", "Design", "Construction"],

  "Detailed Results": ["Business case", "Design", "Construction"],
};


const normalizeProjectClass = (value?: string): ProjectCategory | "" => {
  const normalized = value?.toLowerCase().trim().replace(/[_-]/g, " ") ?? "";

  if (normalized.includes("small")) return "Small";
  if (normalized.includes("large")) return "Large";
  if (normalized.includes("recurring")) return "Recurring";

  return "";
};


const SECTION_FILTER_RULES: Record<
  Section,
  { showSubmission: boolean; showMethod: boolean }
> = {
  "Emissions breakdown": { showSubmission: true, showMethod: true },
  "Materials hotspots": { showSubmission: true, showMethod: false },
  "Mitigation summary": { showSubmission: true, showMethod: true },
  "Comparison by stage/period": { showSubmission: false, showMethod: true },
  "Options Comparison": { showSubmission: false, showMethod: true },
  "Renewable energy": { showSubmission: true, showMethod: false },
  "Offsetting summary": { showSubmission: true, showMethod: false },
  "Waste & recycle materials": { showSubmission: true, showMethod: false },
  "ITMM reporting": { showSubmission: true, showMethod: true },
  "Rating performance": { showSubmission: true, showMethod: true },
  "Detailed Results": { showSubmission: true, showMethod: true },
};

/* =======================
   Sidebar (unchanged)
======================= */

interface SidebarTabsProps {
  sections: Section[];
  activeSection: Section;
  collapsed: boolean;
  onToggle(): void;
  onChange(section: Section): void;
}

const SidebarTabs = ({
  sections,
  activeSection,
  collapsed,
  onToggle,
  onChange,
}: SidebarTabsProps) => (
  <aside
    className={`h-screen bg-white border-r border-[#E8E8E8] transition-all duration-300 ${collapsed ? "w-[72px]" : "w-[300px]"
      }`}
  >
    <div className="flex h-full flex-col p-6">
      <div className="mb-6 flex items-center justify-between">
        {!collapsed && (
          <h2 className="text-sm font-medium text-[#3F3A38]">
            Results dashboard
          </h2>
        )}
        <button
          onClick={onToggle}
          className="flex h-8 w-8 items-center cursor-pointer justify-center rounded hover:bg-[#F5F5F5]"
        >
          <span className="material-symbols-rounded text-[18px] text-[#61605F]">
            {collapsed
              ? "keyboard_double_arrow_right"
              : "keyboard_double_arrow_left"}
          </span>
        </button>
      </div>

      <nav className="flex flex-col flex-1">
        <ul className="space-y-1">
          {sections.filter(s => s !== "Detailed Results").map((section) => {
            const isActive = activeSection === section;
            return (
              <li key={section}>
                <button
                  onClick={() => onChange(section)}
                  className={`relative w-full cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 text-left text-sm transition-colors ${isActive ? collapsed ? "" :
                    "bg-[#FFF7ED] font-medium text-primary"
                    : "text-[#6C6C6C] hover:bg-[#F8F8F8]"
                    }`}
                >
                  {isActive && !collapsed && (
                    <span className="absolute inset-y-0 left-0 w-1 bg-primary rounded-r" />
                  )}
                  {!collapsed && section}
                </button>
              </li>
            );
          })}

          <li className="pt-2 mt-1 border-t border-[#E8E8E8]">
            <button
              onClick={() => onChange("Detailed Results")}
              className={`relative w-full cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 text-left text-sm transition-colors ${
                activeSection === "Detailed Results"
                  ? collapsed ? "" : "bg-[#FFF7ED] font-medium text-primary"
                  : "text-[#6C6C6C] hover:bg-[#F8F8F8]"
              }`}
            >
              {activeSection === "Detailed Results" && !collapsed && (
                <span className="absolute inset-y-0 left-0 w-1 bg-primary rounded-r" />
              )}
              {!collapsed && "Detailed Results"}
            </button>
          </li>
        </ul>
      </nav>
    </div>
  </aside>
);

/* =======================
   Aggregation helper (ALL)
======================= */

/* =======================
   Result Dashboard
======================= */

const ResultDashboard = () => {
  const { state } = useLocation();
  const [searchParams] = useSearchParams();
  const { setProjectHeader, clearProjectHeader } = useProjectHeader();
  const {
    projectData,
  } = state || {};
  const project = projectData;

  const projectId = searchParams.get("projectId") ?? project?.id ?? "";
  const projectName = project?.name ?? project?.project_name ?? "";
  const {
    stageAccess,
    loading: stageAccessLoading,
    error: stageAccessError,
  } = useProjectStageAccess(projectId);

  const [projectOptions, setProjectOptions] = useState<
  { label: string; value: string }[]
>([]);


  useEffect(() => {
    if (projectName && projectId) {
      setProjectHeader(projectName, true, projectId);
    }
    return () => { clearProjectHeader(); };
  }, [projectName, projectId]);
  
const projectCategory = useMemo(() => {
  return normalizeProjectClass(project?.project_class ?? project?.projectClass);
}, [project?.project_class, project?.projectClass]);

  const [activeSection, setActiveSection] =
    useState<Section>("Emissions breakdown");
  const [collapsed, setCollapsed] = useState(false);

  const [submission, setSubmission] = useState<string>("");
  const [intervalId, setIntervalId] = useState("");
  const [accountingMethod, setAccountingMethod] = useState<AccountingMethod>("location");
  const [projectOptionId, setProjectOptionId] = useState<string | undefined>();
  const [submissionPeriodId, setSubmissionPeriodId] = useState<string | undefined>();
  const [intervals, setIntervals] = useState<ConstructionPeriod[]>([]);
  // Resolve enum mapping by indexing, then find the matching stage and get its id

  const formatFrequency = (frequency?: string | null) => {
    if (!frequency) return "";

    return frequency
      .toLowerCase()
      .replace(/_/g, " ");
  };


  useEffect(() => {
    // Reset all filters when section changes
    setSubmission("");
    setIntervalId("");
    setAccountingMethod(activeSection === "Detailed Results" ? "market" : "location");
    setProjectOptionId(undefined);
    setSubmissionPeriodId(undefined);
    setIntervals([]);
  }, [activeSection]);


  const accessibleStageInstances = useMemo(() => {
    if (stageAccessLoading) return [];
    return filterAccessibleStageInstances(
      project?.stage_instances ?? [],
      stageAccess,
    );
  }, [project?.stage_instances, stageAccess, stageAccessLoading]);

  const submissionOptions: SubmissionOption[] = useMemo(() => {
    return (
      accessibleStageInstances.flatMap((stageInstance: any): SubmissionOption[] => {
        const stageLabel =
          STAGE_ENUM_TO_LABEL[
          stageInstance.stage as keyof typeof STAGE_ENUM_TO_LABEL
          ] as SubmissionLabel;

        if (!stageLabel) return [];

        const reportsRequired = stageInstance.num_reports_required ?? 1;

        /**
         * Business case / Design
         * Design (1 of 2)
         */
        if (stageLabel === "Business case" || stageLabel === "Design") {
          return Array.from({ length: reportsRequired }, (_, index) => {
            const reportNumber = index + 1;

            return {
              label:
                reportsRequired > 1
                  ? `${stageLabel} (${reportNumber} of ${reportsRequired})`
                  : stageLabel,
              value: `${stageInstance.stage}_${reportNumber}`,
              stage: stageInstance.stage,
              stageLabel,
              stageInstanceId: stageInstance.id,
              reportIndex: reportNumber,
            };
          });
        }

        /**
         * Construction (monthly)
         */
        if (stageLabel === "Construction") {
          const frequencyLabel = formatFrequency(stageInstance.frequency);

          return [
            {
              label: frequencyLabel
                ? `${stageLabel} (${frequencyLabel})`
                : stageLabel,
              value: stageInstance.stage,
              stage: stageInstance.stage,
              stageLabel,
              stageInstanceId: stageInstance.id,
            },
          ];
        }

        return [
          {
            label: stageLabel,
            value: stageInstance.stage,
            stage: stageInstance.stage,
            stageLabel,
            stageInstanceId: stageInstance.id,
          },
        ];
      }) ?? []
    );
  }, [accessibleStageInstances]);


  const selectedSubmissionOption = useMemo(() => {
    return submissionOptions.find((option) => option.value === submission);
  }, [submissionOptions, submission]);

  useEffect(() => {
    if (submission && !selectedSubmissionOption) {
      setSubmission("");
      setIntervalId("");
      setSubmissionPeriodId(undefined);
      setProjectOptionId(undefined);
      setIntervals([]);
    }
  }, [submission, selectedSubmissionOption]);

  const selectedSubmissionLabel = selectedSubmissionOption?.stageLabel ?? "";

  const stageInstanceId = selectedSubmissionOption?.stageInstanceId ?? "";

  useEffect(() => {
    if (!stageInstanceId || !selectedSubmissionLabel) return;

    let ignore = false;

    (async () => {
      try {
        if (
          selectedSubmissionLabel === "Business case"
        ) {
          const res = await ProjectOptionsService.fetchOptions(stageInstanceId);
          if (ignore) return;
          // setProjectOptionId(res?.[0]?.id);

          const reportIndex = selectedSubmissionOption?.reportIndex;

          const filteredOptions =
            res
              ?.filter(
                (item: any) =>
                  item.report_number === reportIndex
              )
              .map((item: any) => ({
                label: item.label,
                value: item.id,
              })) ?? [];

          setProjectOptions(filteredOptions);

          setProjectOptionId(filteredOptions[0]?.value);

          setSubmissionPeriodId(undefined);
          setIntervals([]);
          setIntervalId("");

        }
        else if (selectedSubmissionLabel === "Design") {
          const res = await ProjectOptionsService.fetchOptions(stageInstanceId);

          if (ignore) return;

          const matchingSubmission = res?.find(
            (item: any) =>
              item.report_number === selectedSubmissionOption?.reportIndex
          );

          setProjectOptionId(matchingSubmission?.id);

          setProjectOptions([]);
          setSubmissionPeriodId(undefined);
          setIntervals([]);
          setIntervalId("");
        }
 else if (selectedSubmissionLabel === "Construction") {
          const res = await ConstructionPeriodsService.listPeriods(stageInstanceId);

          if (ignore) return;

          const periods = res ?? [];
          setIntervals(periods);
          setProjectOptionId(undefined);
          setProjectOptions([]);
          if (periods.length > 0) {
            setIntervalId(periods[0].id);
            setSubmissionPeriodId(periods[0].id);
          } else {
            setIntervalId("");
            setSubmissionPeriodId(undefined);
          }

        }
      } catch (e) {
        console.error("Failed to fetch IDs", e);
      }
    })();

    return () => {
      ignore = true;
    };
  }, [stageInstanceId, selectedSubmissionLabel, submission,]);



  const showIntervalDropdown =
    (selectedSubmissionLabel === "Construction" ||
      projectCategory === "Recurring") &&
    intervals.length > 0;

  const intervalOptions = useMemo(() => {
    return intervals.map((interval) => ({
      label: interval.period_label,
      value: interval.id,
    }));
  }, [intervals]);

const filterRule = SECTION_FILTER_RULES[activeSection as Section];

if (!filterRule) {
  console.warn("No filter rule found for section:", activeSection);
}

const { showSubmission, showMethod } = filterRule;

 const visibleSections = useMemo(() => {
  if (!projectCategory) return [];

  const relevantStageInstances = (project?.stage_instances ?? []).filter((inst: any) =>
    projectCategory === "Recurring"
      ? inst.stage === "RECURRING"
      : inst.stage !== "RECURRING"
  );

  const accessibleIds = new Set(
    accessibleStageInstances.map((inst: any) => inst.id),
  );
  const hasAllRelevantStageAccess = relevantStageInstances.length > 0 &&
    relevantStageInstances.every((inst: any) => accessibleIds.has(inst.id));
  const hasBusinessCaseAccess = accessibleStageInstances.some(
    (inst: any) => inst.stage === "BUSINESS_CASE",
  );

  return ALL_SECTIONS.filter((section) => {
    const allowedForProject =
      SECTION_PROJECT_RULES[section].includes(projectCategory);

    if (!allowedForProject) return false;

    // These views aggregate across stages and do not accept a stage_instance_id.
    // Do not expose them to a user who only has access to a subset of stages.
    if (section === "Comparison by stage/period" && !hasAllRelevantStageAccess) {
      return false;
    }
    if (section === "Options Comparison" && !hasBusinessCaseAccess) {
      return false;
    }

    if (!selectedSubmissionLabel) return true;

    return SECTION_SUBMISSION_RULES[section].includes(
      selectedSubmissionLabel as SubmissionLabel
    );
  });
}, [project?.stage_instances, projectCategory, accessibleStageInstances, selectedSubmissionLabel]);


const showProjectOptionDropdown =
  showSubmission &&
  ["Business case"].includes(selectedSubmissionLabel);


  useEffect(() => {
  if (visibleSections.length === 0) return;
    if (!visibleSections.includes(activeSection)) {
      setActiveSection(visibleSections[0]);
    }
  }, [visibleSections, activeSection]);

  const clearFilters = () => {
    setSubmission("");
    setIntervalId("");
    setAccountingMethod(activeSection === "Detailed Results" ? "market" : "location");
  };

  const NoData = () => (
    <div className="flex h-full flex-col items-center justify-center gap-2">
      <h3 className="text-gray-500">No data</h3>
      <p className="text-sm text-gray-500">
        Select submission, period (if applicable), and accounting
        method
      </p>
    </div>
  );
  
if (!project) {
  return (
    <div className="flex h-screen items-center justify-center text-gray-500">
      Project data not available. Please go back and open the dashboard again.
    </div>
  );
}

if (stageAccessLoading) {
  return (
    <div className="flex h-screen items-center justify-center text-gray-500">
      Checking stage access…
    </div>
  );
}

if (stageAccessError) {
  return (
    <div className="flex h-screen items-center justify-center text-gray-500">
      Failed to load stage access. Please try again.
    </div>
  );
}

if (accessibleStageInstances.length === 0) {
  return (
    <div className="flex h-screen items-center justify-center bg-[var(--color-background-page)]">
      <div className="rounded border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h2 className="text-lg font-medium text-slate-800">No stage access</h2>
        <p className="mt-2 text-sm text-slate-500">
          You do not have access to any active stage in this project.
        </p>
      </div>
    </div>
  );
}

  const renderContent = () => {
    // if (!dataset) return <NoData />;

    try {
      switch (activeSection) {
        case "Emissions breakdown":
          // return dataset.emissionsBreakdown ? (
          return (<EmissionsBreakdownTab
            // data={dataset.emissionsBreakdown}
            mode="project"
            projectId={project.id}
            stageInstanceId={stageInstanceId}
            submissionLabel={selectedSubmissionLabel}
            projectOptionId={projectOptionId}
            submissionPeriodId={submissionPeriodId}
            accountingMethod={accountingMethod}
          />
            // ) : (
            // <NoData />
          );

        case "Materials hotspots":
          // return dataset.materialHotspots ? (
          return (<MaterialHotspotsTab
            mode="project"
            projectId={project.id}
            stageInstanceId={stageInstanceId}
            submissionLabel={selectedSubmissionLabel}
            projectOptionId={projectOptionId}
            submissionPeriodId={submissionPeriodId}

          />
            // ) : (
            // <NoData />
          );

        case "Mitigation summary":
          // return dataset.mitigationSummary ? (
          return ( <MitigationSummaryTab
              projectId={project.id}
            stageInstanceId={stageInstanceId}
            accountingMethod={accountingMethod}
            submissionLabel={selectedSubmissionLabel}
            projectOptionId={projectOptionId}
            submissionPeriodId={submissionPeriodId}
            />
          // ) : (
            // <NoData />
          );

        case "Comparison by stage/period":
          // if (!accountingMethod) return <NoData />;
          return (
            <ConstructionOperationsComparisonTab
              projectId={project.id}
              accountingMethod={accountingMethod}
            />
          );

        case "Options Comparison":
          // return dataset.comparisonByOption ? (
           return (<ComparisonByOption
              // data={dataset.comparisonByOption}
              projectId={project.id}
              accountingMethod={accountingMethod}
            />
          // ) : (
            // <NoData />
          );

        case "Renewable energy":
          // return dataset.renewableEnergySummary ? (
          return (<RenewableEnergyTab
          mode="project"
            // data={dataset.renewableEnergySummary}
            projectId={project.id}
            stageInstanceId={stageInstanceId}
            submissionLabel={selectedSubmissionLabel}
            projectOptionId={projectOptionId}
            submissionPeriodId={submissionPeriodId}
          />
            // ) : (
            // <NoData />
          );

        case "Offsetting summary":
          // return dataset.offsettingSummary ? (
         return ( <OffsettingMeasuresTab
           projectId={project.id}
            stageInstanceId={stageInstanceId}
            submissionLabel={selectedSubmissionLabel}
            projectOptionId={projectOptionId}
            submissionPeriodId={submissionPeriodId}
              // data={dataset.offsettingSummary}
            />
          // ) : (
            // <NoData />
          );

        case "Waste & recycle materials":
          // return dataset.wasteAndRecycle ? (
          return ( <WasteAndRecycleTab
              // data={dataset.wasteAndRecycle}
              projectId={project.id}
              stageInstanceId={stageInstanceId}
              submissionLabel={selectedSubmissionLabel}
              projectOptionId={projectOptionId}
              submissionPeriodId={submissionPeriodId}
            />
          // ) : (
            // <NoData />
          );

        case "ITMM reporting":
          // return dataset.lcaModuleBreakdown ? (
           return (<LcaModuleBreakdownTab
              // data={dataset.lcaModuleBreakdown}
              typeOfProject={projectCategory}
              projectId={project.id}
            stageInstanceId={stageInstanceId}
            submissionLabel={selectedSubmissionLabel}
            projectOptionId={projectOptionId}
            submissionPeriodId={submissionPeriodId}
            accountingMethod={accountingMethod}
            />
          // ) : (
            // <NoData />
          );

        case "Rating performance":
          // return dataset.isCreditsSummary ? (
           return ( <RatingPerformance
               projectId={project.id}
            stageInstanceId={stageInstanceId}
            submissionLabel={selectedSubmissionLabel}
            projectOptionId={projectOptionId}
            submissionPeriodId={submissionPeriodId}
            accountingMethod={accountingMethod}
            />
          // ) : (
            // <NoData />
          );

        case "Detailed Results":
          return (
            <DetailedResultsTab
              projectId={project.id}
              stageInstanceId={stageInstanceId}
              submissionLabel={selectedSubmissionLabel}
              projectOptionId={projectOptionId}
              submissionPeriodId={submissionPeriodId}
              accountingMethod={accountingMethod}
              mode="project"
            />
          );

        default:
          return null;
      }
    } catch {
      return <NoData />;
    }
  };

  return (
    <div className="flex h-screen bg-[var(--color-background-page)]">
      <SidebarTabs
        sections={visibleSections}
        activeSection={activeSection}
        collapsed={collapsed}
        onToggle={() => setCollapsed((p) => !p)}
        onChange={setActiveSection}
      />

      <main className="flex flex-col flex-1 h-screen overflow-hidden">
        <div className="border-b p-4 bg-[#FAFAFA] border-[#F0F0F0]">
          <div className="text-[#61605F] text-base ml-12">
            {activeSection}
          </div>
        </div>

        <div className="flex items-start justify-between px-12 gap-4 mb-6">

          {/* ================= LEFT: FILTERS ================= */}
          <div className="flex flex-wrap gap-4 flex-1  mt-8">
            {/* {(showSubmission || showMethod) && ( */}
              <>
                {showSubmission && (
                  <SelectListbox
                    value={submission}
                    placeholder="Submission"
                    options={submissionOptions}
                    onChange={(val) => {
                      setSubmission(val);
                      setIntervalId("");
                      setSubmissionPeriodId(undefined);
                      setProjectOptionId(undefined);
                    }}
                    className="w-[220px]"
                  />
                )}

                
{showProjectOptionDropdown && (
  <SelectListbox
    value={projectOptionId ?? ""}
    placeholder="Option"
    options={projectOptions}
    onChange={(val) => setProjectOptionId(val)}
    className="w-[220px]"
  />
)}


                {showIntervalDropdown && (
                  <SelectListbox
                    value={intervalId}
                    placeholder="Period"
                    options={intervalOptions}
                    onChange={(val) => {
                      setIntervalId(val);
                      setSubmissionPeriodId(val);
                    }}
                    className="w-[180px]"
                  />
                )}

                {showMethod && (
                  <SelectListbox
                    value={accountingMethod}
                    placeholder="Electricity accounting method"
                    options={[
                      { label: "Market-based", value: "market" },
                      { label: "Location-based", value: "location" },
                    ]}
                    onChange={(val) =>
                      setAccountingMethod(val as AccountingMethod)
                    }
                    className="w-[260px]"
                  />
                )}

                {(submission || intervalId || accountingMethod) && (
                  <button
                    onClick={clearFilters}
                    className="text-sm text-text-table-cell cursor-pointer hover:text-[#1F2937] flex items-center"
                  >
                    <span className="material-symbols-rounded">close_small</span>
                    Clear filters
                  </button>
                )}
              </>
            {/* )} */}
          </div>

          {/* ================= RIGHT: FIXED BUTTON ================= */}
          {/*<div className="flex-shrink-0 pt-2  mt-4">
            <button
              onClick={() =>
                navigate("/resultsDashboard/detailedCalculations", {
                  state: {
                    dataset,
                    visibleSections,
                  },
                })
              }
              className="cursor-pointer rounded-[var(--radius-3)] border-0 bg-primary px-4 py-2.5 font-light text-sm text-white transition-colors hover:brightness-95"
              type="button"
            >
              View detailed results
            </button>
          </div> */}

        </div>

        <div className="flex-1 overflow-y-auto px-8 pb-8 not-[]:bg-[var(--color-background-page)]">
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export default ResultDashboard;
