import React, { useState, useRef, useEffect, useMemo, useCallback } from "react";
import SteppedProgressBar from "../../components/common/SteppedProgressBar";
import ProjectCategory, { type ProjectCategoryValue } from "../../components/ProjectCategory";
import ReportingStage from "../../components/ReportingStage";
import CostAndSchedule from "../../components/CostAndSchedule";
import ProjectSummary, { type ProjectSummaryState } from "../../components/ProjectSummary";
import ReportingFrequency from "../../components/ReportingFrequency";
import type { Step3Errors } from "../../types/error";
import type { FormErrors } from "../../types/addnewproject";
import type { StageValue, SubmissionMap } from "../../types/addnewproject";

import ProjectCategoryImg from "../../assets/icons/projectCategory.svg";
import ReportSubmissionImg from "../../assets/icons/reportSubmission.svg";
import ProjectInfoImg from "../../assets/icons/projectInfo.svg";
import CheckCircle from "../../assets/icons/check-circle-green.svg";

import DeliveryPartners from "../../components/DeliveryPartner";
import OrganizationService from "../../services/organization.service";
import ReportingBoundarySmall from "../../components/ReportingBoundarySmall";
import ReportingBoundaryActivity from "../../components/ReportingBoundaryActivity";

import type { EmissionRow } from "../../components/common/EmissionTable";

import type { YearMonth } from "../../components/common/DatePicker";

import ProjectAccess, { type AccessTableRow } from "../../components/ProjectAccess";
import { Modal } from "../../components/common/Modal";

import { type PostcodeRow } from "../../components/ProjectSummary";
import { useNavigate, useParams } from "react-router-dom";
import http from "@/http";
import { useUser } from "../../context/UserContext";

const steps = [
  "Select project category",
  "Define reporting stage",
  "Enter project information",
  "Manage project access",
];
//Annually was not slected showing in drodown.
const UI_TO_API_FREQUENCY: Record<string, string> = {
  monthly: "MONTHLY",
  quarterly: "QUARTERLY",
  annually: "ANNUAL",
  "bi-monthly": "BI_MONTHLY",
};

const API_TO_UI_FREQUENCY: Record<string, string> = {
  MONTHLY: "monthly",
  QUARTERLY: "quarterly",
  ANNUAL: "annually",
  BI_MONTHLY: "bi-monthly",
};

function apiFrequencyToUi(freq: string): string {
  const normalized = freq.toUpperCase().replace(/-/g, "_");
  return API_TO_UI_FREQUENCY[normalized] ?? freq.toLowerCase();
}

function uiFrequencyToApi(freq: string): string | undefined {
  if (!freq) return undefined;
  return UI_TO_API_FREQUENCY[freq.toLowerCase()] ?? freq.toUpperCase();
}


interface ProjectData {
  id: string;
  project_name: string;
  project_type_id: string;
  project_typecast_id?: string;
  project_type_name?: string;
  project_typecast_name?: string;
  benchmark_mastertype?: { id: string; code: string; name: string };
  benchmark_typecast?: { id: string; code: string; name: string };
  project_class: string;
  description?: string;
  program_name?: string;
  location_text?: string;
  construction_start_date?: string;
  construction_end_date?: string;
  commencement_of_operations?: string;
  operational_life_years?: number;
  project_capex_million?: number;
  project_opex?: number;
  declared_unit_value?: number;
  declared_unit_type?: string;
  first_submission_month?: string;
  contract_number?: string;
  design_contract_number?: string;
  construction_contract_number?: string;
  stage_configs?: Array<{
    stage: string;
    enabled: boolean;
    num_reports_required?: number;
    frequency?: string;
  }>;
  org_links?: Array<{
    organization_id: string;
    role: string;
    organization_name?: string;
  }>;
  postcodes?: Array<{
    postcode: string;
    area_class: string;
  }>;
  reporting_boundaries?: Array<{
    stage_or_activity: string;
    category: string;
    sub_category: string;
    source?: string;
  }>;
  member_accesses?: Array<{
    user_id: string;
    role: string;
    user_email?: string;
  }>;
}

interface BenchmarkType {
  id: string;
  code: string;
  name: string;
}

interface BenchmarkTypecast {
  id: string;
  code: string;
  name: string;
  mastertype_id: string;
}

type Props = {
  mode?: "create" | "edit";
};

export default function AddNewProject({ mode = "create" }: Props) {
  const isEdit = mode === "edit";
  const { projectId } = useParams<{ projectId: string }>();

  const navigate = typeof useNavigate === "function" ? useNavigate() : null;
  const { user } = useUser();
  const [loading, setLoading] = useState(isEdit);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [step, setStep] = useState<number>(1);
  const [selectedCategory, setSelectedCategory] = useState<ProjectCategoryValue | "">("");
  const prevCategoryRef = useRef<ProjectCategoryValue | "">("");
  const [selectedStage, setSelectedStage] = useState<StageValue | "">("");
  const [submissions, setSubmissions] = useState<SubmissionMap>({
    business: "",
    design: "",
    construction: "",
  });
  const [frequency, setFrequency] = useState("");
  const [period, setPeriod] = useState<YearMonth | null>(null);

  const [projectSummary, setProjectSummary] = useState<ProjectSummaryState>({
    projectName: "",
    programName: "",
    projectType: "",
    projectTypecast: "",
    projectLocation: "",
    projectDescription: "",
  });

  const [postcodeRows, setPostcodeRows] = useState<PostcodeRow[]>([]);
  const [postcodeInput, setPostcodeInput] = useState("");
  const startDateRef = useRef<HTMLInputElement | null>(null);
  const endDateRef = useRef<HTMLInputElement | null>(null);
  const commenceDateRef = useRef<HTMLInputElement | null>(null);
  const [operationalLife, setOperationalLife] = useState("");
  const [capex, setCapex] = useState("");
  const [opex, setOpex] = useState("");
  const [declaredUnitValue, setDeclaredUnitValue] = useState("");
  const [declaredUnitType, setDeclaredUnitType] = useState("");
  const [commenceOpsDate, setCommenceOpsDate] = useState<Date | null>(null);
  const [constructionStartDate, setConstructionStartDate] = useState<Date | null>(null);
  const [constructionEndDate, setConstructionEndDate] = useState<Date | null>(null);

  const [designContract, setDesignContract] = useState("");
  const [designerOrg, setDesignerOrg] = useState("");
  const [constructionContract, setConstructionContract] = useState("");
  const [constructionOrg, setConstructionOrg] = useState("");

  const [boundaryRows, setBoundaryRows] = useState<EmissionRow[]>([]);

  const [accessRows, setAccessRows] = useState<AccessTableRow[]>([]);
  const [editingRow, setEditingRow] = useState<AccessTableRow | null>(null);

  const [designerOrgId, setDesignerOrgId] = useState("");
  const [constructionOrgId, setConstructionOrgId] = useState("");

  const [benchmarkTypes, setBenchmarkTypes] = useState<BenchmarkType[]>([]);
  const [benchmarkTypecasts, setBenchmarkTypecasts] = useState<BenchmarkTypecast[]>([]);
  const [projectTypeId, setProjectTypeId] = useState<string>("");
  const [projectTypecastId, setProjectTypecastId] = useState<string>("");

  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [step3Errors, setStep3Errors] = useState<Step3Errors>({});

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteSuccessEmail, setInviteSuccessEmail] = useState<string | null>(null);
  const inviteDraftRef = useRef<string>("");

  const [pendingInvites, setPendingInvites] = useState<string[]>([]);
  const inviteSuccessTimerRef = useRef<number | null>(null);

  const [showRequestAccess, setShowRequestAccess] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const [showCompleteConfirm, setShowCompleteConfirm] = useState(false);
  const projectSummaryRef = useRef<HTMLDivElement | null>(null);
  const costScheduleRef = useRef<HTMLDivElement | null>(null);
  const reportingBoundaryRef = useRef<HTMLDivElement | null>(null);

  const openCompleteConfirm = useCallback(() => setShowCompleteConfirm(true), []);
  const closeCompleteConfirm = useCallback(() => setShowCompleteConfirm(false), []);
  const inviteInputRef = useRef<HTMLInputElement | null>(null);

  type CancelOrigin = "request" | "request-edit" | "invite" | "page" | null;
  const [cancelOrigin, setCancelOrigin] = useState<CancelOrigin>(null);

  const isContractor = useMemo(() => selectedCategory === "contractor", [selectedCategory]);

  useEffect(() => {
    if (!isEdit || !projectId) return;

    let ignore = false;

    async function loadProjectData() {
      try {
        const response = await http.get<ProjectData>(`/api/projects/${projectId}`);
        if (ignore) return;

        const project = response.data;

        const categoryMap: Record<string, ProjectCategoryValue> = {
          SMALL: "small",
          LARGE: "large",
          RECURRING: "contractor",
        };
        setSelectedCategory(categoryMap[project.project_class]);

        setProjectSummary({
          projectName: project.project_name ?? "",
          programName: project.program_name ?? "",
          projectType: project.project_type_id ?? project.benchmark_mastertype?.id ?? "",
          projectTypecast: project.project_typecast_id ?? project.benchmark_typecast?.id ?? "",
          projectLocation: project.location_text ?? "",
          projectDescription: project.description ?? "",
        });

        if (project.project_type_id) {
          setProjectTypeId(project.project_type_id);
        }
        if (project.project_typecast_id) {
          setProjectTypecastId(project.project_typecast_id);
        }

        if (project.postcodes) {
          setPostcodeRows(
            project.postcodes.map((p, i) => ({
              id: `${i}`,
              postcode: p.postcode,
              area_class: p.area_class,
            }))
          );
        }

        if (project.construction_start_date) {
          setConstructionStartDate(new Date(project.construction_start_date));
        }
        if (project.construction_end_date) {
          setConstructionEndDate(new Date(project.construction_end_date));
        }
        if (project.commencement_of_operations) {
          setCommenceOpsDate(new Date(project.commencement_of_operations));
        }

        if (project.operational_life_years != null) {
          setOperationalLife(String(project.operational_life_years));
        }
        if (project.project_capex_million != null) {
          setCapex(String(project.project_capex_million));
        }
        if (project.project_opex != null) {
          setOpex(String(project.project_opex));
        }
        if (project.declared_unit_value != null) {
          setDeclaredUnitValue(String(project.declared_unit_value));
        }
        if (project.declared_unit_type) {
          setDeclaredUnitType(project.declared_unit_type);
        }

        if (project.org_links) {
          for (const link of project.org_links) {
            if (link.role === "DELIVERY") {
              setConstructionOrgId(link.organization_id);
              setConstructionOrg(link.organization_name ?? "");
            }
            if (link.role === "DESIGNER") {
              setDesignerOrgId(link.organization_id);
              setDesignerOrg(link.organization_name ?? "");
            }
          }
        }

        if (project.design_contract_number) {
          setDesignContract(project.design_contract_number);
        }
        if (project.construction_contract_number) {
          setConstructionContract(project.construction_contract_number);
        }

        if (project.first_submission_month) {
          const date = new Date(project.first_submission_month);
          setPeriod({ year: date.getFullYear(), month: date.getMonth() + 1 });
        }

        if (project.stage_configs && project.stage_configs.length > 0) {
          const enabledStages = project.stage_configs
            .filter((sc) => sc.enabled)
            .map((sc) => sc.stage);

          if (enabledStages.includes("BUSINESS_CASE")) {
            setSelectedStage("business");
          } else if (enabledStages.includes("DESIGN")) {
            setSelectedStage("design");
          } else if (enabledStages.includes("CONSTRUCTION")) {
            setSelectedStage("construction");
          }

          for (const sc of project.stage_configs) {
            if (sc.stage === "BUSINESS_CASE" && sc.num_reports_required) {
              setSubmissions((prev) => ({ ...prev, business: sc.num_reports_required?.toString() || "" }));
            } else if (sc.stage === "DESIGN" && sc.num_reports_required) {
              setSubmissions((prev) => ({ ...prev, design: sc.num_reports_required?.toString() || "" }));
            } else if (sc.stage === "CONSTRUCTION" && sc.frequency) {
              //setFrequency(sc.frequency.toLowerCase());
              setFrequency(apiFrequencyToUi(sc.frequency));
            }
          }
        }

        if (project.reporting_boundaries) {
          setBoundaryRows(
            project.reporting_boundaries.map((rb, idx) => ({
              id: rb.source ? `${rb.category}-${rb.sub_category}-${idx}` : `rb-${idx}`,
              stageOrActivity: rb.stage_or_activity,
              category: rb.category,
              subCategory: rb.sub_category,
              source: rb.source ?? "",
            }))
          );
        }

        if (!isEdit && project.member_accesses && Array.isArray(project.member_accesses) && project.stage_configs) {
          const enabledStages: Array<{ stage: string; label: string }> = [];
          const stageLabels: Record<string, string> = {
            BUSINESS_CASE: "Business case",
            DESIGN: "Design",
            CONSTRUCTION: "Construction",
          };

          for (const sc of project.stage_configs) {
            if (sc.enabled) {
              enabledStages.push({
                stage: sc.stage,
                label: stageLabels[sc.stage as keyof typeof stageLabels] || sc.stage,
              });
            }
          }

          const loadedRows: AccessTableRow[] = [];
          let rowIndex = 0;

          for (const ma of project.member_accesses) {
            const accessLevel = ma.role === "PROJECT_EDITOR" ? ("Can edit" as const) : ("Can view" as const);

            for (const stageInfo of enabledStages) {
              loadedRows.push({
                id: `${ma.user_id}-${stageInfo.stage}-${rowIndex}`,
                userId: ma.user_id,
                name: ma.user_email || "",
                email: ma.user_email || "",
                stage: stageInfo.label,
                access: accessLevel,
              });
              rowIndex++;
            }
          }

          setAccessRows(loadedRows);
        }

        setLoadError(null);
      } catch (err) {
        console.error("Failed to load project for edit", err);
        setLoadError("Failed to load project. Please try again.");
      } finally {
        setLoading(false);
      }
    }

    loadProjectData();
    return () => {
      ignore = true;
    };
  }, [isEdit, projectId]);


  useEffect(() => {
    return () => {
      if (inviteSuccessTimerRef.current) window.clearTimeout(inviteSuccessTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (prevCategoryRef.current && prevCategoryRef.current !== selectedCategory) {
      setBoundaryRows([]);
    }
    prevCategoryRef.current = selectedCategory;
  }, [selectedCategory]);

  // Fetch benchmark types and typecasts
  useEffect(() => {
    const fetchBenchmarks = async () => {
      try {
        // Fetch all benchmark types
        const typesRes = await http.get<BenchmarkType[]>("/api/benchmark-mastertypes");
        setBenchmarkTypes(typesRes.data);

        // Fetch all benchmark typecasts
        const typecastsRes = await http.get<BenchmarkTypecast[]>("/api/benchmark-typecasts");
        setBenchmarkTypecasts(typecastsRes.data);
      } catch (err) {
        console.error("Failed to fetch benchmark types/typecasts", err);
      }
    };

    fetchBenchmarks();
  }, []);

  const declaredUnitOptions = useMemo((): string[] => {
    if (!projectTypecastId || !projectTypeId) return [];
    const mastertype = benchmarkTypes.find(t => t.id === projectTypeId);
    const typecast = benchmarkTypecasts.find(tc => tc.id === projectTypecastId);
    if (!mastertype || !typecast) return [];
    const mc = mastertype.code;
    const tc = typecast.code;
    if (mc === "transport_building") return ["m2 GFA"];
    if (mc === "rail" && tc === "station_rail") return ["m2 GFA"];
    if (mc === "road") return ["lane.km", "m2", "passenger.km", "tonne.km"];
    if (mc === "road_rail") return ["lane.km", "track.km", "m2", "passenger.km", "tonne.km"];
    if (mc === "rail") return ["track.km", "passenger.km", "tonne.km"];
    return [];
  }, [projectTypeId, projectTypecastId, benchmarkTypes, benchmarkTypecasts]);

  useEffect(() => {
    if (declaredUnitOptions.length === 0) return;
    if (declaredUnitType && !declaredUnitOptions.includes(declaredUnitType)) {
      setDeclaredUnitType("");
    }
  }, [declaredUnitOptions, declaredUnitType]);

  // Handle ProjectSummary changes and extract type/typecast IDs
  const handleProjectSummaryChange = useCallback((patch: Partial<typeof projectSummary>) => {
    setProjectSummary(prev => ({ ...prev, ...patch }));

    // Extract ID when projectType changes
    if (patch.projectType) {
      //const selectedType = benchmarkTypes.find(t => t.name === patch.projectType || t.code === patch.projectType || t.id === patch.projectType);     
      const selectedType = benchmarkTypes.find(t => t.id === patch.projectType);
      if (selectedType) {
        setProjectTypeId(selectedType.id);
        // Reset typecast when type changes
        setProjectTypecastId("");
      }
    }

    // Extract ID when projectTypecast changes
    if (patch.projectTypecast) {
      const selectedTypecast = benchmarkTypecasts.find(tc => tc.name === patch.projectTypecast || tc.code === patch.projectTypecast || tc.id === patch.projectTypecast);
      if (selectedTypecast) {
        setProjectTypecastId(selectedTypecast.id);
      }
    }
  }, [benchmarkTypes, benchmarkTypecasts]);

  const validateReportingFrequency = useCallback(() => {
    let hasError = false;
    setFormErrors(prev => ({ ...prev, frequency: null, period: null }));

    if (!frequency || !period) {
      setFormErrors({ submissions: "You must define frequency details for Construction stage" });
    }
    if (!frequency) {
      hasError = true;
      setFormErrors(prev => ({ ...prev, frequency: "Reporting frequency is required" }));
    }
    if (!period) {
      hasError = true;
      setFormErrors(prev => ({ ...prev, period: "First reporting period is required" }));
    }
    return !hasError;
  }, [frequency, period]);

  const scrollToRef = (ref: React.RefObject<HTMLDivElement | null>) => {
    if (ref.current) {
      ref.current.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  };


  const validateStep3 = useCallback((): boolean => {
  const ps = projectSummary;
  const psErrors: Step3Errors["projectSummary"] = {};

  if (!ps.projectName?.trim()) psErrors.projectName = "Project name is required";
  if (!projectTypeId) psErrors.projectType = "Project type is required";
  if (!projectTypecastId) psErrors.projectTypecast = "Project typecast is required";
  if (!ps.projectLocation?.trim()) psErrors.projectLocation = "Project location is required";

  const csErrors: Step3Errors["costAndSchedule"] = {};
  const needCS = selectedCategory === "small" || selectedCategory === "large";

  if (needCS) {
    if (!commenceOpsDate) {
      csErrors.commenceDate = "Commencement of operations is required";
    }
    if (!operationalLife) {
      csErrors.operationalLifeYears = "Operational life is required";
    }
    if (!capex) {
      csErrors.projectCapexM = "Project CAPEX is required";
    }
  }

  const dpErrors: Step3Errors["deliveryPartners"] = {};
  // delivery partners are optional — no required validation

  const rbErrors: Step3Errors["reportingBoundary"] = {};

if (selectedCategory === "contractor" && boundaryRows.length === 0) {
  rbErrors.required = "At least one emission source is required";
}

const nextErrors: Step3Errors = {
  projectSummary: psErrors,
  costAndSchedule: needCS ? csErrors : undefined,
  deliveryPartners: selectedCategory === "contractor" ? dpErrors : undefined,
  reportingBoundary:
    selectedCategory === "contractor" ? rbErrors : undefined,
};


  setStep3Errors(nextErrors);

 setTimeout(() => {
  if (Object.keys(psErrors).length > 0) {
    scrollToRef(projectSummaryRef);
  } else if (Object.keys(csErrors).length > 0) {
    scrollToRef(costScheduleRef);
  } else if (Object.keys(rbErrors).length > 0) {
    scrollToRef(reportingBoundaryRef);
  }
}, 200);


  return (
    Object.keys(psErrors).length === 0 &&
    Object.keys(csErrors).length === 0 &&
    Object.keys(dpErrors).length === 0
  );
}, [
  projectSummary,
  selectedCategory,
  operationalLife,
  capex,
  commenceOpsDate,
]);
  const addAccessRows = useCallback((rows: AccessTableRow[]) => {
    setAccessRows(prev => {
      const existing = new Set(prev.map(r => r.id));
      const merged = [...prev];
      for (const r of rows) {
        if (!existing.has(r.id)) {
          merged.push(r);
          existing.add(r.id);
        }
      }
      return merged;
    });
  }, []);

  const removeAccessRow = useCallback((id: string) => {
    setAccessRows(prev => prev.filter(r => r.id !== id));
  }, []);

  const editAccessRow = useCallback((row: AccessTableRow) => {
    setEditingRow(row);
    setShowRequestAccess(true);
  }, []);

  const updateAccessRow = useCallback((updatedRow: AccessTableRow) => {
    setAccessRows(prev => prev.map(row => (row.id === updatedRow.id ? updatedRow : row)));
  }, []);

  const isValidEmail = useCallback((email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()), []);

  // const openInviteModal = useCallback(() => {
  //   setInviteEmail("");
  //   setInviteError(null);
  //   setInviteSuccessEmail(null);
  //   setShowInviteModal(true);
  // }, []);

  const closeInviteModal = useCallback(() => setShowInviteModal(false), []);

  const openCancelModal = useCallback(() => setShowCancelConfirm(true), []);
  const closeCancelModal = useCallback(() => setShowCancelConfirm(false), []);

  const closeAllModals = useCallback(() => {
    setShowRequestAccess(false);
    setShowCancelConfirm(false);
    setShowInviteModal(false);
  }, []);

  const handleSendInvite = useCallback(() => {
    const email = inviteEmail.trim();
    if (!isValidEmail(email)) {
      setInviteError("Please enter a valid email address");
      return;
    }

    setInviteError(null);
    setInviteSuccessEmail(email);

    setPendingInvites(prev => (prev.includes(email) ? prev : [...prev, email]));

    if (inviteSuccessTimerRef.current) {
      window.clearTimeout(inviteSuccessTimerRef.current);
    }
    inviteSuccessTimerRef.current = window.setTimeout(() => {
      setInviteSuccessEmail(null);
      setInviteEmail("");
      if (inviteInputRef.current) {
        inviteInputRef.current.focus();
      }
    }, 3000);
  }, [inviteEmail, isValidEmail]);

  const handleContinue = useCallback(() => {
    setFormErrors({});

    if (step === 1 && !selectedCategory) {
      setFormErrors({
        stage: "You must select a project category to continue to the next step",
      });
      return;
    }

    if (step === 2) {
      if (isContractor) {
        if (!validateReportingFrequency()) return;
      } else {
        if (!selectedStage) {
          setFormErrors({ stage: "You must select the current stage of your project." });
          return;
        }
        if (selectedStage === "construction") {
          setFormErrors({ submissions: "You must define frequency details for Construction stage" });
          if (!validateReportingFrequency()) return;
        } else if (selectedStage === "design") {
          const dCount = Number(submissions.design ?? "");
          if (!Number.isFinite(dCount) || dCount < 1) {
            setFormErrors({ submissions: "You must define at least one submission for the Design stage" });
            return;
          }
          if (!validateReportingFrequency()) return;
        } else if (selectedStage === "business") {
          const bCount = Number(submissions.business ?? "");
          if (!Number.isFinite(bCount) || bCount < 1) {
            setFormErrors({ submissions: "You must define at least one submission for the Business case stage" });
            return;
          }
          const dCount = Number(submissions.design ?? "");
          if (!Number.isFinite(dCount) || dCount < 1) {
            setFormErrors({ submissions: "You must define at least one submission for the Design stage" });
            return;
          }
          if (!validateReportingFrequency()) return;
        }
      }
    }
    if (step === 3) {
      if (!validateStep3()) return;
    }
    if (step === 4) {
    }

    setStep(s => Math.min(s + 1, 4));
  }, [
    step,
    selectedCategory,
    isContractor,
    validateReportingFrequency,
    selectedStage,
    submissions,
    validateStep3,
    frequency,
    period,
    projectSummary,
    operationalLife,
    capex,
    opex,
    designContract,
    designerOrg,
    constructionContract,
    constructionOrg,
    boundaryRows,
    accessRows,
    pendingInvites,
  ]);

  const handleConfirmComplete = useCallback(async () => {
    if (!user) return;
    setIsSubmitting(true);
    setSubmitError(null);

    const classMap: Record<string, string> = { small: "SMALL", large: "LARGE", contractor: "RECURRING" };
    const project_class = classMap[selectedCategory as string];

    //const freqMap: Record<string, string> = { monthly: "MONTHLY", quarterly: "QUARTERLY", annually: "ANNUAL", "bi-monthly": "BI_MONTHLY" };
    //const freqEnum: string | undefined = frequency ? (freqMap[frequency.toLowerCase()] ?? frequency.toUpperCase()) : undefined;
    const freqEnum = uiFrequencyToApi(frequency);
    const stageEnumMap: Record<string, string> = { business: "BUSINESS_CASE", design: "DESIGN", construction: "CONSTRUCTION" };
    let stage_configs: object[];
    if (selectedCategory === "contractor") {
      stage_configs = [{ stage: "CONSTRUCTION", enabled: true, frequency: freqEnum }];
    } else {
      const stageEnum = stageEnumMap[selectedStage as string];
      if (!stageEnum) {
        stage_configs = [];
      } else if (selectedStage === "construction") {
        stage_configs = [{ stage: "CONSTRUCTION", enabled: true, frequency: freqEnum }];
      } else if (selectedStage === "design") {
        const designNum = parseInt(submissions.design || "0", 10);
        stage_configs = [
          { stage: "DESIGN", enabled: true, num_reports_required: isNaN(designNum) ? 0 : designNum },
          { stage: "CONSTRUCTION", enabled: true, frequency: freqEnum },
        ];
      } else {
        const businessNum = parseInt(submissions.business || "0", 10);
        const designNum = parseInt(submissions.design || "0", 10);
        stage_configs = [
          { stage: "BUSINESS_CASE", enabled: true, num_reports_required: isNaN(businessNum) ? 0 : businessNum },
          { stage: "DESIGN", enabled: true, num_reports_required: isNaN(designNum) ? 0 : designNum },
          { stage: "CONSTRUCTION", enabled: true, frequency: freqEnum },
        ];
      }
    }

    const org_links: ({ organization_id: string; role: string } | { org_name: string; role: string })[] = [];
    if (constructionOrgId) {
      org_links.push({ organization_id: constructionOrgId, role: "DELIVERY" });
    } else if (constructionOrg.trim()) {
      org_links.push({ org_name: constructionOrg.trim().toUpperCase(), role: "DELIVERY" });
    }
    if (designerOrgId) {
      org_links.push({ organization_id: designerOrgId, role: "DESIGNER" });
    } else if (designerOrg.trim()) {
      org_links.push({ org_name: designerOrg.trim().toUpperCase(), role: "DESIGNER" });
    }

    const accessRoleMap = new Map<string, "Can edit" | "Can view">();
    for (const row of accessRows) {
      const uid = row.userId;
      if (!uid) continue;
      const existing = accessRoleMap.get(uid);
      if (!existing || (row.access === "Can edit" && existing !== "Can edit")) {
        accessRoleMap.set(uid, row.access);
      }
    }
    const member_accesses = Array.from(accessRoleMap.entries()).map(([user_id, access]) => ({
      user_id,
      role: access === "Can edit" ? "PROJECT_EDITOR" : "PROJECT_VIEWER",
    }));

    const toDateStr = (d: Date | null | undefined) => (d ? d.toISOString().split("T")[0] : null);

    //payload - common for both create and edit
    const payload = {
      project_name: projectSummary.projectName.trim(),
      project_type_id: projectTypeId,
      project_typecast_id: projectTypecastId,
      description: projectSummary.projectDescription?.trim() || null,
      project_class,
      contract_number: constructionContract.trim() || designContract.trim() || "",
      design_contract_number: designContract.trim() || null,
      construction_contract_number: constructionContract.trim() || null,
      program_name: projectSummary.programName?.trim() || null,
      location_text: projectSummary.projectLocation?.trim() || null,
      construction_start_date: toDateStr(constructionStartDate),
      construction_end_date: toDateStr(constructionEndDate),
      commencement_of_operations: toDateStr(commenceOpsDate),
      operational_life_years: operationalLife ? parseInt(operationalLife, 10) : null,
      project_capex_million: capex ? parseFloat(capex) : null,
      project_opex: opex ? parseFloat(opex) : null,
      declared_unit_value: declaredUnitValue ? parseFloat(declaredUnitValue) : null,
      declared_unit_type: declaredUnitType || null,
      first_submission_month: period
        ? `${period.year}-${String(period.month).padStart(2, "0")}-01`
        : null,
      stage_configs,
      org_links,
      postcodes: postcodeRows.map((r) => ({ postcode: r.postcode })),
      reporting_boundaries: boundaryRows.map((r) => ({
        stage_or_activity: r.stageOrActivity,
        category: r.category,
        sub_category: r.subCategory,
        source: r.source || null,
      })),
      is_active: true,
      simple_carbon_assessment: false,
      proponent_org_id: user.organisation_id,
      created_by_user_id: user.user_id,
      ...(isEdit ? {} : { member_accesses }),
    };

    // Add create-only fields for POST
    /* const payload = isEdit 
      ? basePayload
      : {
          ...basePayload,
          is_active: true,
          simple_carbon_assessment: false,
          proponent_org_id: user.organisation_id,
          created_by_user_id: user.user_id,
          member_accesses,
        }; */

    try {
      // bust org cache when free-text names were entered so autocomplete stays fresh
      const hasFreeTextOrg = (!constructionOrgId && constructionOrg.trim()) || (!designerOrgId && designerOrg.trim());
      if (isEdit && projectId) {
        // PATCH request for edit mode
        await http.patch(`/api/projects/${projectId}`, payload);
        if (hasFreeTextOrg) OrganizationService.clearCacheAll();
        closeCompleteConfirm();
        navigate?.(`/projects/${projectId}`);
      } else {
        // POST request for create mode
        await http.post("/api/projects", { ...payload, member_accesses });
        if (hasFreeTextOrg) OrganizationService.clearCacheAll();
        closeCompleteConfirm();
        navigate?.("/Home/user");
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: any) => d.msg ?? String(d)).join(", ")
            : `Failed to ${isEdit ? "update" : "create"} project. Please try again.`;
      setSubmitError(msg);
    } finally {
      setIsSubmitting(false);
    }
  }, [
    user,
    isEdit,
    projectId,
    selectedCategory,
    selectedStage,
    submissions,
    frequency,
    period,
    projectSummary,
    postcodeRows,
    accessRows,
    constructionOrgId,
    designerOrgId,
    constructionOrg,
    designerOrg,
    constructionContract,
    designContract,
    operationalLife,
    capex,
    opex,
    declaredUnitValue,
    declaredUnitType,
    commenceOpsDate,
    constructionStartDate,
    constructionEndDate,
    navigate,
    boundaryRows,
    closeCompleteConfirm,
  ]);

  return (
    <div className="flex h-full flex-col lg:flex-row items-stretch bg-bg-content">
      {loading && (
        <div className="flex items-center justify-center h-full w-full text-slate-400">
          <div className="text-center">
            <div className="text-lg mb-4">Loading project...</div>
          </div>
        </div>
      )}

      {loadError && (
        <div className="flex items-center justify-center h-full w-full">
          <div className="text-center max-w-md">
            <div className="text-lg text-danger mb-4">Error Loading Project</div>
            <div className="text-sm text-text-base mb-6">{loadError}</div>
            <button
              type="button"
              className="cursor-pointer rounded-[var(--radius-3)] border bg-primary px-4 py-2.5 font-medium text-white hover:brightness-95"
              onClick={() => navigate?.("/Home/user")}
            >
              Go Back to Home
            </button>
          </div>
        </div>
      )}

      {!loading && !loadError && (
        <>
          <div className="hidden lg:block lg:w-[40%] h-full">
            <div className="relative w-full lg:h-full">
              <img
                src={step === 1 ? ProjectCategoryImg : step === 2 ? ReportSubmissionImg : ProjectInfoImg}
                alt="Project"
                className="absolute inset-0 h-full w-full object-cover"
                loading="lazy"
              />
            </div>
          </div>

          <div className="flex w-full lg:w-[60%] flex-col overflow-y-auto custom-scrollbar">
            <div className="flex flex-col px-6 py-10 lg:ml-[8.25rem] lg:mt-[6.875rem] lg:mr-[9.75rem] text-text-dark">
              <div className="mb-10 text-10 sm:text-[2.5rem] font-light">
                {step === 1 ? "Let's get started" : step === 2 ? "Define reporting submissions" : "Enter project information"}
              </div>

              <div className="mt-3.5 mb-12">
                <SteppedProgressBar steps={steps} currentStep={step} />
              </div>

              {step === 1 && (
                isEdit ? (
                  <>
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-[var(--radius-3)] mb-4 text-sm text-blue-700">
                      <strong>Note:</strong> Project category cannot be changed and is shown for reference.
                    </div>

                    <div className="p-6 bg-gray-50 border border-gray-200 rounded-[var(--radius-3)]">
                      <h3 className="text-lg font-medium text-text-dark mb-2">
                        Current Project Category
                      </h3>
                      <p className="text-sm text-text-base">
                        {selectedCategory === "small"
                          ? "Small project"
                          : selectedCategory === "large"
                            ? "Large project"
                            : "Contractor or maintenance reporting"}
                      </p>
                    </div>
                  </>
                ) : (
                  <ProjectCategory
                    selectedCategory={selectedCategory}
                    showerror={formErrors?.stage ?? null}
                    onSelectCategory={(val) => {
                      if (formErrors) setFormErrors({});
                      setSelectedCategory(val);
                    }}
                  />
                )
              )}

              {step === 2 && (
                <>
                  {isContractor ? (
                    <div className="rounded-lg bg-white p-3 ">
                      {isEdit && (
                        <div className="p-4 bg-blue-50 border border-blue-200 rounded-[var(--radius-3)] mb-4 text-sm text-blue-700">
                          <strong>Note:</strong> Project Stages and corresponding submissions cannot be changed. They are shown here for reference only.
                        </div>
                      )}
                      <ReportingFrequency
                        frequency={frequency}
                        setFrequency={val => {
                          setFrequency(val);
                          setFormErrors(prev => (prev.frequency ? { ...prev, frequency: null } : prev));
                        }}
                        period={period}
                        setPeriod={val => {
                          setPeriod(val);
                          setFormErrors(prev => (prev.period ? { ...prev, period: null } : prev));
                        }}
                        frequencyError={formErrors.frequency ?? null}
                        periodError={formErrors.period ?? null}
                        disabled={isEdit}
                      />
                    </div>
                  ) : (
                    <ReportingStage
                      readOnly={isEdit}
                      selectedStage={selectedStage}
                      stageError={formErrors.stage ?? null}
                      submissionsError={formErrors.submissions ?? null}
                      onSelectStage={val => {
                        if (formErrors.stage) setFormErrors(e => ({ ...e, stage: null }));
                        if (selectedStage && selectedStage !== val) {
                          setSubmissions(prev => ({ ...prev, [selectedStage]: "" }));
                          if (formErrors.submissions) setFormErrors(e => ({ ...e, submissions: null }));
                        }
                        setSelectedStage(val);
                      }}
                      submissions={submissions}
                      onChangeSubmissions={next => {
                        if (formErrors.submissions && selectedStage) {
                          const raw = next[selectedStage];
                          const n = Number(raw);
                          if (Number.isFinite(n) && n >= 1) {
                            setFormErrors(e => ({ ...e, submissions: null }));
                          }
                        }
                        setSubmissions(next);
                      }}
                      rfFrequency={frequency}
                      onRfFrequencyChange={setFrequency}
                      rfPeriod={period}
                      onRfPeriodChange={setPeriod}
                      rfFrequencyError={formErrors.frequency ?? null}
                      rfPeriodError={formErrors.period ?? null}
                    />
                  )}
                </>
              )}

              {step === 3 && (
                <form>
                  <div className="mb-4 text-sm text-text-faint">All fields are required unless marked optional.</div>

                  <div ref = {projectSummaryRef}>
                    <ProjectSummary
                    value={projectSummary}
                    onChange={handleProjectSummaryChange}
                    errors={step3Errors.projectSummary}
                    postcodeRows={postcodeRows}
                    setPostcodeRows={setPostcodeRows}
                    postcodeInput={postcodeInput}
                    setPostcodeInput={setPostcodeInput}
                  />
                  </div>  

                  {(selectedCategory === "small" || selectedCategory === "large") && (
                    <div ref = {costScheduleRef}>
                      <CostAndSchedule
                      startDateRef={startDateRef}
                      endDateRef={endDateRef}
                      commenceDateRef={commenceDateRef}
                      commenceDateValue={commenceOpsDate}
                      setCommenceDateValue={setCommenceOpsDate}
                      operationalLife={operationalLife}
                      setOperationalLife={setOperationalLife}
                      capex={capex}
                      setCapex={setCapex}
                      opex={opex}
                      setOpex={setOpex}
                      declaredUnitValue={declaredUnitValue}
                      setDeclaredUnitValue={setDeclaredUnitValue}
                      declaredUnitType={declaredUnitType}
                      setDeclaredUnitType={setDeclaredUnitType}
                      declaredUnitOptions={declaredUnitOptions}
                      constructionStartDate={constructionStartDate}
                      setConstructionStartDate={setConstructionStartDate}
                      constructionEndDate={constructionEndDate}
                      setConstructionEndDate={setConstructionEndDate}
                      errors={step3Errors.costAndSchedule}
                      onFieldValid={field => {
                        setStep3Errors(prev => {
                          const next = { ...prev };
                          const cs = { ...(next.costAndSchedule ?? {}) };
                          cs[field] = null as any;
                          const hasAny = Object.values(cs).some(Boolean);
                          if (hasAny) next.costAndSchedule = cs;
                          else delete next.costAndSchedule;
                          return next;
                        });
                      }}
                    />
                    </div>       
                  )}
                  <DeliveryPartners
                    category={selectedCategory as ProjectCategoryValue}
                    designContract={designContract}
                    setDesignContract={setDesignContract}
                    designerOrg={designerOrg}
                    setDesignerOrg={setDesignerOrg}
                    onDesignerOrgSelect={(id) => setDesignerOrgId(id)}
                    constructionContract={constructionContract}
                    setConstructionContract={setConstructionContract}
                    constructionOrg={constructionOrg}
                    setConstructionOrg={setConstructionOrg}
                    onConstructionOrgSelect={(id) => setConstructionOrgId(id)}
                  />

                  {selectedCategory === "small" && (
                    <ReportingBoundarySmall value={boundaryRows} onChange={setBoundaryRows} />
                  )}
                  {selectedCategory === "contractor" && (
                  <div ref={reportingBoundaryRef}>
                    <ReportingBoundaryActivity
                      value={boundaryRows}
                      onChange={setBoundaryRows}
                      errors={step3Errors.reportingBoundary}
                    />
                  </div>
                )}
                </form>
              )}

              {step === 4 && (
                <div>
                  <div className="mb-4 text-2xl text-text-base">{isEdit ? "Review project access" : `Grant access to ${projectSummary.projectName}`}</div>
                  {isEdit ? (
                    <div className="p-6 bg-blue-50 border border-blue-200 rounded-[var(--radius-3)] text-sm text-blue-700">
                      <strong>Note:</strong> Stage-level access is managed from Manage User Access. Project setup editing will not change existing stage assignments.
                    </div>
                  ) : (
                    <div className="p-6 bg-white rounded-[var(--radius-3)]">
                      <div className="mb-4 text-text-dark text-base">Search and add users</div>
                      <button
                        type="button"
                        className="border border-text-table-cell rounded-[var(--radius-3)] px-3 py-1.5 flex cursor-pointer items-center gap-1 text-sm text-text-table-cell hover:bg-neutral-95 transition-colors"
                        onClick={() => setShowRequestAccess(true)}
                      >
                        <span className="material-symbols-rounded">add</span> Add user
                      </button>
                    </div>
                  )}
                  {/* <div className="my-4 text-text-dark text-sm">
                    Need to add someone not yet in the Carbon Measurement &amp; Reporting Tool?{" "}
                    <button
                      type="button"
                      className="text-primary cursor-pointer underline-offset-2 hover:underline"
                      onClick={openInviteModal}
                    >
                      Send an invite.
                    </button>
                  </div> */}
                  {!isEdit && (
                    <>
                      {accessRows.length > 0 && (
                                        <div className="mt-6 overflow-x-auto">
                                          {(() => {
                                            const groups = accessRows.reduce<Record<string, AccessTableRow[]>>((acc, row) => {
                                              const key = `${row.name}::${row.email ?? ""}`;
                                              (acc[key] ||= []).push(row);
                                              return acc;
                                            }, {});

                                            const toDisplayAccess = (a: AccessTableRow["access"]) =>
                                              a === "Can edit" ? "Edit" : a === "Can view" ? "View" : a;

                                            const sortedGroupKeys = Object.keys(groups).sort((a, b) => {
                                              const [an] = a.split("::");
                                              const [bn] = b.split("::");
                                              return an.localeCompare(bn);
                                            });

                                            return (
                                              <table className="w-full text-left border-collapse border border-neutral-90">
                                                <thead>
                                                  <tr className="border border-light-grey text-text-base text-sm h-10 bg-neutral-90 rounded-[var(--radius-3)] ">
                                                    <th className="font-semibold w-1/3 pl-4">NAME</th>
                                                    {selectedCategory !== "contractor" && <th className="font-semibold pl-4">PROJECT STAGE</th>}
                                                    <th className="font-semibold pl-4 ">ACCESS TYPE</th>
                                                    <th className="font-semibold w-1/6" />
                                                  </tr>
                                                </thead>
                                                <tbody className="bg-white">
                                                  {sortedGroupKeys.map(gk => {
                                                    const rows = groups[gk];
                                                    const sortedRows = [...rows];
                                                    const [first, ...rest] = sortedRows;
                                                    const nameCell = (
                                                      <td className="text-sm text-text-dark align-top pl-4 pt-3" rowSpan={sortedRows.length}>
                                                        {first.name}
                                                      </td>
                                                    );
                                                    return (
                                                      <React.Fragment key={gk}>
                                                        <tr className="border-b border-neutral-90 h-10">
                                                          {nameCell}
                                                          {selectedCategory !== "contractor" && <td className="text-sm text-text-base pl-4 border-l border-neutral-90">{first.stage}</td>}
                                                          <td className="text-sm text-text-base pl-4 border-l border-neutral-90">
                                                            {toDisplayAccess(first.access)}
                                                          </td>
                                                          <td className="text-sm">
                                                            <div className="flex gap-2">
                                                              <button
                                                                type="button"
                                                                onClick={() => editAccessRow(first)}
                                                                className="px-2 pt-1 hover:rounded-full text-text-table-cell hover:bg-neutral-90 cursor-pointer"
                                                                title="Edit"
                                                              >
                                                                <span className="material-symbols-rounded">edit</span>
                                                              </button>
                                                              <button
                                                                type="button"
                                                                onClick={() => removeAccessRow(first.id)}
                                                                className="px-2 pt-1 hover:rounded-full text-text-table-cell hover:bg-neutral-90 cursor-pointer"
                                                                title="Remove"
                                                              >
                                                                <span className="material-symbols-rounded">close</span>
                                                              </button>
                                                            </div>
                                                          </td>
                                                        </tr>
                                                        {rest.map(row => (
                                                          <tr key={row.id} className="border-b border-neutral-90 h-10">
                                                            {selectedCategory !== "contractor" && <td className="text-sm text-text-base pl-4  border-l border-neutral-90">{row.stage}</td>}
                                                            <td className="text-sm text-text-base pl-4 border-l border-neutral-90">
                                                              {toDisplayAccess(row.access)}
                                                            </td>
                                                            <td className="text-sm">
                                                              <div className="flex gap-2">
                                                                <button
                                                                  type="button"
                                                                  onClick={() => editAccessRow(row)}
                                                                  className="px-2 pt-1 hover:rounded-full text-text-table-cell hover:bg-neutral-90 cursor-pointer"
                                                                  title="Edit"
                                                                >
                                                                  <span className="material-symbols-rounded">edit</span>
                                                                </button>
                                                                <button
                                                                  type="button"
                                                                  onClick={() => removeAccessRow(row.id)}
                                                                  className="px-2 pt-1 hover:rounded-full text-text-table-cell hover:bg-neutral-90 cursor-pointer"
                                                                  title="Remove"
                                                                >
                                                                  <span className="material-symbols-rounded">close</span>
                                                                </button>
                                                              </div>
                                                            </td>
                                                          </tr>
                                                        ))}
                                                      </React.Fragment>
                                                    );
                                                  })}
                                                </tbody>
                                              </table>
                                            );
                                          })()}
                                        </div>
                                      )}

                                      {pendingInvites.length > 0 && (
                                        <div className="mt-6">
                                          <div className="mb-2 text-text-dark text-base font-medium">Pending invites</div>
                                          <table className="w-full text-left border-collapse border border-neutral-90 bg-white">
                                            <thead>
                                              <tr className="bg-neutral-90 text-sm h-10">
                                                <th className="font-semibold pl-4">EMAIL</th>
                                              </tr>
                                            </thead>
                                            <tbody>
                                              {pendingInvites.map(email => (
                                                <tr key={email} className="border-b border-neutral-90 h-10">
                                                  <td className="text-sm text-text-base pl-4">{email}</td>
                                                </tr>
                                              ))}
                                            </tbody>
                                          </table>
                                        </div>
                                      )}

                                      <Modal isOpen={showRequestAccess} onClose={() => setShowRequestAccess(false)} className="max-w-150 p-6">
                                        <ProjectAccess
                                          category={selectedCategory}
                                          editingRow={editingRow}
                                          onCloseRequestModal={() => {
                                            setEditingRow(null);
                                            setShowRequestAccess(false);
                                          }}
                                          onOpenCancelModal={() => {
                                            setCancelOrigin("request");
                                            openCancelModal();
                                            setCancelOrigin(editingRow ? "request-edit" : "request");
                                            setShowRequestAccess(false);
                                            openCancelModal();
                                          }}
                                          onCloseAllModals={() => {
                                            setEditingRow(null);
                                            closeAllModals();
                                            setCancelOrigin(null);
                                          }}
                                          onAddAccessRows={addAccessRows}
                                          onUpdateAccessRow={updateAccessRow}
                                          selectedReportingStage={selectedStage || undefined}
                                        />
                                      </Modal>
                    </>
                  )}

                  {(
                    <Modal isOpen={showInviteModal} onClose={() => closeInviteModal()} className="max-w-150">
                      <div className="bg-white p-6 sm:p-6 w-full">
                        <div className="text-lg sm:text-2xl text-text-dark">Send an invite</div>

                        {inviteSuccessEmail && (
                          <div className="my-6 rounded-[var(--radius-3)] border border-success bg-light-green p-4 text-sm text-success font-bold">
                            <img src={CheckCircle} alt="Check icon" className="inline mr-2 w-4 h-4" />
                            Invite sent to {inviteSuccessEmail}
                          </div>
                        )}

                        <div className="mt-4">
                          <label htmlFor="invite-email" className="text-sm text-text-base block">
                            Invite by email
                          </label>
                          <input
                            id="invite-email"
                            type="email"
                            ref={inviteInputRef}
                            className="mt-1 h-10 w-full rounded-[var(--radius-3)] border border-border-input p-4 text-sm text-text-base focus:border-border-input focus:ring-border-input disabled:bg-neutral-95 disabled:cursor-not-allowed"
                            value={inviteEmail}
                            onChange={e => {
                              setInviteEmail(e.target.value);
                              if (inviteError) setInviteError(null);
                            }}
                            disabled={!!inviteSuccessEmail}
                            onKeyDown={e => {
                              if (e.key === "Enter" && !inviteSuccessEmail) {
                                e.preventDefault();
                                handleSendInvite();
                              }
                            }}
                          />
                          {inviteError && <div className="mt-1 text-xs text-danger">{inviteError}</div>}
                        </div>

                        <div className="mt-12 flex justify-end gap-3">
                          <button
                            type="button"
                            className="cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 text-sm font-medium text-text-table-cell transition-colors hover:bg-neutral-95 disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={closeInviteModal}
                            disabled={!!inviteSuccessEmail}
                          >
                            Close
                          </button>
                          <button
                            type="button"
                            className="cursor-pointer rounded-[var(--radius-3)] border bg-primary px-4 py-2.5 font-medium text-white hover:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={handleSendInvite}
                            disabled={!isValidEmail(inviteEmail) || !!inviteSuccessEmail}
                          >
                            Invite
                          </button>
                        </div>
                      </div>
                    </Modal>
                  )}


                  <Modal isOpen={showCompleteConfirm} onClose={closeCompleteConfirm} className="max-w-md">
                    <div className="bg-white p-6">
                      <div className="text-lg sm:text-2xl text-text-dark font-medium">
                        {isEdit ? "Confirm project update" : "Confirm project creation"}
                      </div>
                      <div className="mt-4 text-sm text-text-base whitespace-pre-line">
                        {isEdit ? (
                          <>
                            You're about to update{" "}
                            <strong>{projectSummary.projectName || "this project"}</strong>{" "}
                            with the changes you've made. Once updated, the updated information
                            will be available to assigned users.
                          </>
                        ) : (
                          <>
                            You're about to create{" "}
                            <strong>{projectSummary.projectName || "this project"}</strong>{" "}
                            based on the information you've provided. Once created, the project
                            will be available to assigned users.
                          </>
                        )}

                      </div>
                      <div className="mt-4 text-sm text-text-base whitespace-pre-line">

                        {isEdit ? (
                          <>Please review all changes before confirming. The project category cannot be changed.</>
                        ) : (
                          <>
                            Please note that the <strong>project category</strong> cannot be changed after project
                            creation. Other details provided in steps 2-4 can be updated later.
                          </>
                        )}

                      </div>
                      {submitError && (
                        <div className="mt-4 rounded-[var(--radius-3)] border border-danger bg-red-50 p-3 text-sm text-danger">
                          {submitError}
                        </div>
                      )}
                      <div className="mt-6 flex justify-end gap-3">
                        <button
                          type="button"
                          className="cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 text-sm font-medium text-text-table-cell transition-colors hover:bg-neutral-95 disabled:opacity-50"
                          onClick={closeCompleteConfirm}
                          disabled={isSubmitting}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          className="cursor-pointer rounded-[var(--radius-3)] border bg-primary px-4 py-2.5 font-medium text-white hover:brightness-95 disabled:opacity-60 disabled:cursor-not-allowed"
                          onClick={handleConfirmComplete}
                          disabled={isSubmitting}
                        >
                          {isSubmitting ? (isEdit ? "Updating…" : "Creating…") : (isEdit ? "Update" : "Confirm")}
                        </button>
                      </div>
                    </div>
                  </Modal>
                </div>
              )}

              <Modal isOpen={showCancelConfirm} onClose={closeCancelModal} className="max-w-md">
                <div className="bg-white p-2 sm:p-4">
                  <div className="text-lg sm:text-2xl text-text-dark font-medium">
                    {cancelOrigin === "page" ? "Leave project setup?" : "Discard changes?"}
                  </div>
                  <div className="mt-3 sm:mt-4 text-sm text-text-base">
                    {cancelOrigin === "page"
                      ? "All changes will be lost if you leave now. Are you sure you want to continue?"
                      : "Are you sure you want to discard your changes?"}
                  </div>

                  <div className="mt-6 flex justify-end gap-3">
                    <button
                      className="cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 text-sm font-medium text-text-table-cell transition-colors hover:bg-neutral-95"
                      type="button"
                      onClick={() => {
                        closeCancelModal();
                        if (cancelOrigin === "request" || cancelOrigin === "request-edit") {
                          setShowRequestAccess(true);
                        }
                      }}
                    >
                      {cancelOrigin === "page" ? "Stay" : "Keep editing"}
                    </button>
                    <button
                      className="cursor-pointer rounded-[var(--radius-3)] border bg-primary px-4 py-2.5 font-medium text-white hover:brightness-95"
                      type="button"
                      onClick={() => {
                        if (cancelOrigin === "invite") {
                          const email = inviteDraftRef.current.trim();
                          if (email) {
                            setPendingInvites(prev => (prev.includes(email) ? prev : [...prev, email]));
                          }
                          inviteDraftRef.current = "";
                          setInviteEmail("");
                        }
                        const isPageClose = cancelOrigin === "page";
                        setEditingRow(null);
                        closeAllModals();
                        setCancelOrigin(null);
                        setInviteSuccessEmail(null);
                        if (inviteSuccessTimerRef.current) {
                          window.clearTimeout(inviteSuccessTimerRef.current);
                        }
                        if (isPageClose) {
                          navigate?.("/Home/user");
                        }
                      }}
                    >
                      {cancelOrigin === "page" ? "Leave" : "Discard changes"}
                    </button>
                  </div>
                </div>
              </Modal>

              <div className="mt-8 pb-10 flex flex-wrap items-center justify-between gap-4 text-sm ">
                <button
                  className="cursor-pointer bg-transparent font-medium text-border-neutral px-4 py-2.5"
                  type="button"
                  onClick={() => {
                    if (!selectedCategory) {
                      navigate?.("/Home/user");
                    } else {
                      setCancelOrigin("page");
                      openCancelModal();
                    }
                  }}
                >
                  Close
                </button>

                <div className="flex flex-wrap gap-3">
                  {step > 1 && (
                    <button
                      className="cursor-pointer rounded-[var(--radius-3)] border border-primary bg-white px-4 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-primary-weak"
                      type="button"
                      onClick={() => setStep(step - 1)}
                    >
                      Back
                    </button>
                  )}
                  <button
                    className="cursor-pointer rounded-[var(--radius-3)] border-0 bg-primary px-4 py-2.5 font-semibold text-white transition-colors hover:brightness-95"
                    type="button"
                    onClick={step === 4 ? openCompleteConfirm : handleContinue}
                  >
                    {step === 4 ? "Complete project setup" : "Continue"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}