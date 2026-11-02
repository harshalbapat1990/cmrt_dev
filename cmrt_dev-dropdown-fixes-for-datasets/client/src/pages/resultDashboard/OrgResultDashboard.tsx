import React, { useMemo, useState, useEffect } from "react";

import EmissionsBreakdownTab from "./EmissionsBreakdownTab";
import MaterialHotspotsTab from "./MaterialHotspotsTab";
import RenewableEnergyTab from "./RenewableEnergyTab";
import WasteAndRecycleTab from "./WasteAndRecycleTab";
import { SelectListbox } from "../../components/common/Select";
import { useUser } from "@/context/UserContext";
import ProjectsService from "../../services/Projects.service";
import LookupsService from "../../services/Lookups.service";
import DetailedResultsTab from "./DetailedResultsTab";

/* ================= TYPES ================= */

type AccountingMethod = "Market-based" | "Location-based";
type SubmissionLabel = "Business case" | "Design" | "Construction";
type ProjectCategory = "SMALL" | "LARGE" | "RECURRING";

type OrgSectionId =
  | "emissions-breakdown"
  | "materials-hotspots"
  | "renewable-energy"
  | "waste-recycle-materials"
  | "detailed-results";

type OrgSection = {
  id: OrgSectionId;
  label: string;
};

const ORG_SECTIONS: OrgSection[] = [
  {
    id: "emissions-breakdown",
    label: "Emissions breakdown",
  },
  {
    id: "materials-hotspots",
    label: "Materials hotspots",
  },
  {
    id: "renewable-energy",
    label: "Renewable energy",
  },
  {
    id: "waste-recycle-materials",
    label: "Waste & recycle materials",
  },
  {
    id: "detailed-results",
    label: "Detailed Results",
  },
];

type FilterState = {
  projectCategory: ProjectCategory | "";
  programName: string;
  projectTypecast: string;
  submission: SubmissionLabel | "";
  accountingMethod: AccountingMethod | "";
};


const NONE_PROGRAM_VALUE = "__NONE__";

const EMPTY_FILTERS: FilterState = {
  projectCategory: "",
  programName: "",
  projectTypecast: "",
  submission: "",
  accountingMethod: "",
};

const PROJECT_CATEGORY_OPTIONS = [
  { label: "Small", value: "SMALL" },
  { label: "Large", value: "LARGE" },
  { label: "Recurring", value: "RECURRING" },
];

const SUBMISSION_OPTIONS = [
  { label: "Business case", value: "Business case" },
  { label: "Design", value: "Design" },
  { label: "Construction", value: "Construction" },
];

const ACCOUNTING_METHOD_OPTIONS = [
  { label: "Location-based", value: "Location-based" },
  { label: "Market-based", value: "Market-based" },
];

const getProgramName = (project: any) => {
  return project.program_name ?? project.programName ?? null;
}

const getTypecastLabel = (typecast: any) =>
  typecast.name ?? typecast.code ?? typecast.label ?? "";

const getTypecastValue = (typecast: any) =>
  String(typecast.id);

/* ================= SIDEBAR ================= */

const SidebarTabs = ({
  sections,
  activeSection,
  collapsed,
  onToggle,
  onChange,
}: any) => (
  <aside
    className={`h-screen bg-white border-r border-[#E8E8E8] transition-all duration-300 ${collapsed ? "w-[72px]" : "w-[300px]"
      }`}
  >
    <div className="flex h-full flex-col p-6">

      <div className="mb-6 flex items-center justify-between">
        {!collapsed && (
          <h2 className="text-sm font-medium text-[#3F3A38]">
            Organisation dashboard
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

      <ul className="space-y-1 flex-1">
        {sections
          .filter((s: OrgSection) => s.id !== "detailed-results")
          .map((section: OrgSection) => {
            const isActive = activeSection === section.id;

          return (
            <li key={section.id}>
              <button
                onClick={() => onChange(section.id)}
                className={`relative w-full rounded-[var(--radius-3)] px-4 py-2.5 cursor-pointer text-left text-sm ${
                  isActive ? collapsed ? ""
                    : "bg-[#FFF7ED] text-primary font-medium"
                    : "text-[#6C6C6C] hover:bg-[#F8F8F8]"
                    }`}
                >
                  {isActive && !collapsed && (
                    <span className="absolute inset-y-0 left-0 w-1 bg-primary rounded-r" />
                  )}
                  {!collapsed && section.label}
                </button>
              </li>
            );
          })}
        <li className="pt-2 mt-2 border-t border-[#E8E8E8]" />

        {sections
          .filter((s: OrgSection) => s.id === "detailed-results")
          .map((section: OrgSection) => {
            const isActive = activeSection === section.id;

            return (
              <li key={section.id}>
                <button
                  onClick={() => onChange(section.id)}
                  className={`relative w-full rounded-[var(--radius-3)] px-4 py-2.5 text-left text-sm ${isActive
                      ? !collapsed
                        ? "bg-[#FFF7ED] text-primary font-medium"
                        : ""
                      : "text-[#6C6C6C] hover:bg-[#F8F8F8]"
                    }`}
                >
                  {isActive && !collapsed && (
                    <span className="absolute inset-y-0 left-0 w-1 bg-primary rounded-r" />
                  )}
                  {!collapsed && section.label}
                </button>
              </li>
            );
          })}

      </ul>
    </div>
  </aside>
);

/* ================= FILTER UI (UNCHANGED DESIGN) ================= */

const FilterToolbar = ({ onOpen }: any) => (
  <div className="flex items-center justify-between pr-12 mt-6">
    <button
      onClick={onOpen}
      className="inline-flex items-center gap-2 rounded-[var(--radius-3)] cursor-pointer border border-[#2F2F2F] px-4 py-2 text-sm hover:bg-[#F8F8F8]"
    >
      <span className="material-symbols-rounded">tune</span>
      Filters
    </button>
  </div>
);

const FilterPanel = ({
  onClose,
  onApply,
  draftFilters,
  setDraftFilters,
  programOptions,
  typecastOptions,
  isApplying = false,
  activeSection,
}: any) => {

  const updateFilter = <K extends keyof FilterState>(
    key: K,
    value: FilterState[K]
  ) => {
    setDraftFilters((prev: any) => ({
      ...prev,
      [key]: value,
    }));
  };

  return (
    <div className="absolute left-87 top-53 z-50 w-[340px] rounded-[var(--radius-3)] border-[#1E1F2126] bg-white shadow-sm">
      <div className="flex justify-between  p-4">
        <h3 className="text-lg font-medium">Filters</h3>
        <button onClick={onClose}>
          <span className="material-symbols-rounded">close</span>
        </button>
      </div>

      <div className="space-y-4 p-4">
        <SelectListbox
          value={draftFilters.projectCategory}
          placeholder="Project category"
          options={PROJECT_CATEGORY_OPTIONS}
          onChange={(value) => updateFilter("projectCategory", value as ProjectCategory | "")}
        />

        <SelectListbox
          value={draftFilters.programName}
          placeholder="Program"
          options={programOptions}
          onChange={(value: string) => updateFilter("programName", value)}
        />
        <SelectListbox
          value={draftFilters.projectTypecast}
          placeholder="Project Typecast"
          options={typecastOptions}
          onChange={(value: string) => updateFilter("projectTypecast", value)}
        />

        <SelectListbox
          value={draftFilters.submission}
          placeholder="Submission"
          options={SUBMISSION_OPTIONS}
          onChange={(value: string) => updateFilter("submission", value as SubmissionLabel | "")}
        />

{(activeSection === "emissions-breakdown" || activeSection === "detailed-results") && (
  <SelectListbox
    value={draftFilters.accountingMethod}
    placeholder="Accounting method"
    options={ACCOUNTING_METHOD_OPTIONS}
    onChange={(value: string) =>
      updateFilter("accountingMethod", value as AccountingMethod | "")
    }
  />
)}
        <button
          onClick={onApply}
          disabled={isApplying}
          className="w-full rounded-[var(--radius-3)] bg-primary px-4 py-2.5 text-sm text-white transition-colors hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isApplying ? "Applying..." : "Apply filters"}
        </button>

      </div>
    </div>
  )
};

const FilterChips = ({
  filters,
  clearAll,
  typecastOptions,
  onRemove,
}: any) => {
  const getTypecastLabelFromValue = (value: string) => {
    const match = typecastOptions?.find(
      (opt: any) => opt.value === value
    );
    return match?.label || value;
  };

  const chips = [
    filters.projectCategory,
    filters.programName === NONE_PROGRAM_VALUE ? "None" : filters.programName,
    filters.submission,
    filters.projectTypecast
      ? getTypecastLabelFromValue(filters.projectTypecast)
      : "",
    filters.accountingMethod,
  ].filter(Boolean);

  if (!chips.length) return null;

 

  return (
    <div className="flex flex-wrap items-center gap-3 pt-2 pb-4">
      {chips.map((label, i) => (
<div key={`chip-${i}-${label}`} className="flex gap-1">
  <span
    // key={`chip-${i}-${label}`}
    className="flex items-center gap-1 rounded-full bg-[#EDEDED] px-4 py-2 text-sm"
  >
    {label}
    <span className="material-symbols-rounded text-base leading-none"
    onClick={() => onRemove(label)}>
      close_small
    </span>
  </span>
</div>
      ))}

      <button onClick={clearAll} className="text-sm ml-2 cursor-pointer flex items-center">
        <span className="material-symbols-rounded text-[16px]">close</span>
        Clear filters
      </button>
    </div>
  );
};

/* ================= MAIN ================= */

const OrganisationDashboard: React.FC = () => {
  const { user } = useUser();
  // const navigate = useNavigate();
  const organisationId = user?.organisation_id;
  const [activeSection, setActiveSection] = useState<OrgSectionId>("emissions-breakdown");

  const [collapsed, setCollapsed] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  const [projects, setProjects] = useState<any[]>([]);
  const [typecasts, setTypecasts] = useState<any[]>([]);

  const [draftFilters, setDraftFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] =
    useState<FilterState>(EMPTY_FILTERS);

  const [error, setError] = useState("");

  const visibleSections = useMemo(() => ORG_SECTIONS, []);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setError("");

        const [projectsResponse, typecastsResponse] = await Promise.all([
          ProjectsService.fetchAllProjects(),
          LookupsService.fetchAllTypecasts(),
        ]);

        const projectsJson = Array.isArray(projectsResponse)
          ? projectsResponse
          : projectsResponse?.data ?? projectsResponse?.projects ?? [];

        const typecastsJson = Array.isArray(typecastsResponse)
          ? typecastsResponse
          : typecastsResponse?.data ?? typecastsResponse?.typecasts ?? [];

        setProjects(projectsJson);
        setTypecasts(typecastsJson);
      } catch (err) {
        console.error(err);
        setError("Unable to load filters data.");
      }
    };

    fetchInitialData();
  }, []);

  useEffect(() => {
    if (activeSection !== "detailed-results") {
      return;
    }
    setDraftFilters((prev) => ({
      ...prev,
      accountingMethod: prev.accountingMethod || "Market-based",
    }));
    setAppliedFilters((prev) => ({
      ...prev,
      accountingMethod: prev.accountingMethod || "Market-based",
    }));
  }, [activeSection]);

  const handleRemove = (label: string) => {
  setAppliedFilters((prev) => {
    const updated = { ...prev };

    if (label === prev.projectCategory) updated.projectCategory = "";
    else if (
      label === (prev.programName === NONE_PROGRAM_VALUE ? "None" : prev.programName)
    ) {
      updated.programName = "";
    }
    else if (label === prev.submission) updated.submission = "";
    else if (label === prev.accountingMethod) updated.accountingMethod = "";
    else {
      const matched = typecastOptions.find(
        (opt: any) => opt.label === label
      );
      if (matched && matched.value === prev.projectTypecast) {
        updated.projectTypecast = "";
      }
    }

    return updated;
  });
};


  const programOptions = useMemo(() => {
    const programSet = new Set<string>();
    let hasNoProgram = false;

    projects.forEach((project) => {
      const programName = getProgramName(project);

      if (!programName || !String(programName).trim()) {
        hasNoProgram = true;
      } else {
        programSet.add(String(programName).trim());
      }
    });

    const options = Array.from(programSet)
      .sort((a, b) => a.localeCompare(b))
      .map((programName) => ({
        label: programName,
        value: programName,
      }));

    if (hasNoProgram) {
      options.unshift({
        label: "None",
        value: NONE_PROGRAM_VALUE,
      });
    }

    return options;
  }, [projects]);

  const typecastOptions = useMemo(() => {
    return typecasts
      .map((typecast) => ({
        label: getTypecastLabel(typecast),
        value: getTypecastValue(typecast),
      }))
      .filter((option) => option.label && option.value);
  }, [typecasts]);


  const applyFilters = () => {
    setError("");
    setAppliedFilters({ ...draftFilters });
    setShowFilters(false);
  };


  const clearAll = () => {
    setDraftFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setError("");
  };


  const isFiltersComplete =
    Boolean(appliedFilters.projectCategory) ||
    Boolean(appliedFilters.programName) ||
    Boolean(appliedFilters.projectTypecast) ||
    Boolean(appliedFilters.submission) ||
    Boolean(appliedFilters.accountingMethod);


  const renderContent = () => {
    if (error) {
      return (
        <div className="flex h-full items-center justify-center text-red-600">
          {error}
        </div>
      );
    }
    if (!isFiltersComplete && activeSection !== "detailed-results") {
      return (
        <div className="flex h-full flex-col items-center justify-center">
          <h3>No filters applied</h3>
        </div>
      );
    }

    switch (activeSection) {
      case "emissions-breakdown":
        return (
          <EmissionsBreakdownTab
            orgId={organisationId}
            accountingMethod={appliedFilters.accountingMethod}
            submissionLabel={appliedFilters.submission}
            projectCategory={appliedFilters.projectCategory}
            programName={appliedFilters.programName}
            projectTypecast={appliedFilters.projectTypecast}
            mode="org"
          />
        );

      case "materials-hotspots":
        return (
          <MaterialHotspotsTab
            orgId={organisationId}
            submissionLabel={appliedFilters.submission}
            projectCategory={appliedFilters.projectCategory}
            programName={appliedFilters.programName}
            projectTypecast={appliedFilters.projectTypecast}
            mode="org"
          />
        );

      case "renewable-energy":
        return (
          <RenewableEnergyTab
            orgId={organisationId}
            submissionLabel={appliedFilters.submission}
            projectCategory={appliedFilters.projectCategory}
            programName={appliedFilters.programName}
            projectTypecast={appliedFilters.projectTypecast}
            mode="org"
          />
        );

      case "waste-recycle-materials":
        return <WasteAndRecycleTab orgId={organisationId}
          projectCategory={appliedFilters.projectCategory}
          programName={appliedFilters.programName}
          projectTypecast={appliedFilters.projectTypecast}
          submissionLabel={appliedFilters.submission}
          mode="org" />;

      case "detailed-results":
                return (
                  <DetailedResultsTab
                    orgId={organisationId}
          projectCategory={appliedFilters.projectCategory}
          programName={appliedFilters.programName}
          projectTypecast={appliedFilters.projectTypecast}
          submissionLabel={appliedFilters.submission}
          accountingMethod={appliedFilters.accountingMethod}
          mode="org"/>
                );
      
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen bg-[var(--color-background-page)]">

      {/* SIDEBAR */}
      <SidebarTabs
        sections={visibleSections}
        activeSection={activeSection}
        collapsed={collapsed}
        onToggle={() => setCollapsed((p) => !p)}
        onChange={setActiveSection}
      />

      {/* MAIN */}
      <main className="flex flex-col flex-1 h-screen">

        <div className="border-b p-4 bg-[#FAFAFA] border-[#F0F0F0]">
          <div className="text-[#61605F] text-base ml-8">
            {activeSection}
          </div>
        </div>
        {/* FILTER + ACTION ROW */}
        <div className="flex items-start justify-between px-8">

          {/* LEFT: FILTER + CHIPS */}
          <div className="flex flex-col gap-2 flex-1">

            <FilterToolbar onOpen={() => setShowFilters(true)} />

            {showFilters && (
              <FilterPanel
                onClose={() => setShowFilters(false)}
                onApply={applyFilters}
                draftFilters={draftFilters}
                setDraftFilters={setDraftFilters}
                programOptions={programOptions}
                typecastOptions={typecastOptions}
                activeSection={activeSection}   
              />
            )}

            <FilterChips filters={appliedFilters} clearAll={clearAll} typecastOptions={typecastOptions} onRemove={handleRemove} />
          </div>


        </div>

        {/* CONTENT */}
        <div className="flex-1 overflow-y-auto px-8 p-8">
          {renderContent()}
        </div>

      </main>
    </div>
  );
};

export default OrganisationDashboard;
