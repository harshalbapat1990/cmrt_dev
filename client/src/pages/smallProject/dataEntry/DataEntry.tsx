import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { SelectListbox } from "../../../components/common/Select";
import { assetTableConfig } from "./assetConfig";
import { componentTableConfig } from "./componentConfig";
import { refurbishmentTableConfig, fetchAllActiveMrFactors } from "./refurbishmentTableConfig";
import { componentReplacementConfig } from "./componentReplacementConfig";
import { opEnergyTableConfig } from "./opEnergyTableConfig";
import { constructionG2Config } from "./constructionG2Config";
import { constructionG3Config } from "./constructionG3Config";
import { ACTIVITY_CATEGORY_MAP } from "@/components/ReportingBoundaryActivity";
import { electricityConfig } from "./electricityConfig";
import { useB1G2Config } from "./useB1G2Config";
import { useB1G3Config } from "./useB1G3Config";
import LeftNavigation from "@/components/LeftNavigation";
import ProjectsService from "../../../services/Projects.service";
import ProjectAccessService from "@/services/ProjectAccess.service";
import ActivityDataService from "@/services/ActivityData.service";
import ProjectOptionsService, { type ProjectOption } from "@/services/ProjectOptions.service";
import { fetchStageResubmissionAudit } from "@/services/AuditLog.service";
import StageResubmissionAuditPanel from "@/pages/auditLog/StageResubmissionAuditPanel";
import http from "@/http";
import TableWrapper from "@/components/common/TableWrapper";
import UsersSubStage from "./UsersSubStage";
import { useToast } from "../../../components/common/ToastProvider";
import { useProjectHeader } from "@/context/ProjectHeaderContext";
import { useUser } from "../../../context/UserContext";
import type { StageAccess, StageAccessLevel } from "@/types/authorization";
import { ConstructionPeriodsService } from "@/services/ConstructionPeriods.service";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import { useNavigate } from "react-router-dom";
import CheckCircleGreen from "@/assets/icons/check-circle-green.svg";
import Info from "@/assets/icons/info.svg";
import Mitigations from "./Mitigations";
import { formatEmissionsOrQuantity } from "@/utils/utils";
import LookupsService from "@/services/Lookups.service";
import { concreteRegSimplifiedConfig } from "./ConcreteRegSimplifiedConfig";
import { concreteRegDetailedConfig } from "./concreteRegDetailedConfig";
import ShortcutTools from "./ShortcutTools";
import {
    type UploadKey,
    STAGE_ENUM_TO_LABEL,
    STAGE_LABEL_TO_ENUM,
    REPLACEMENT_LABEL,
    REPLACEMENT_LABEL_LARGE,
    SUBSTAGES_FOR,
    GROUPS_FOR,
    COMPLETENESS_LABEL,
} from "./stageConstants";
import {
    GRADE34_IDS,
    apiRowToUiRow as apiRowToUiRowFn,
    resolveBoundaryComponentIds as resolveBoundaryComponentIdsFn,
} from "./rowTransforms";
import { useOutsideClick } from "./useOutsideClick";
import { useTableRows } from "./useTableRows";
import { useEmissionsCalc } from "./useEmissionsCalc";
import { useMitigationHandlers } from "./useMitigationHandlers";
import { useExecSummary } from "./hooks/useExecSummary";
import { useLargeUserYears } from "./hooks/useLargeUserYears";
import { useWorkflowActions } from "./hooks/useWorkflowActions";
import { useRowOperations } from "./hooks/useRowOperations";
import { DataEntryModals } from "./components/DataEntryModals";
import Completeness from "./Completeness";
import {
    canAdminStage,
    canEditStage,
    canShowCompleteness,
    canShowMitigations,
    filterAccessibleStageInstances,
    canRequestStageReopen,
} from "./stageAccessUi";

export type { UploadKey };


type ProjectDetails = {
    stage_configs?: any[];
    [key: string]: any;
};

const ConstructionStage = () => {
    const { user } = useUser();
    const [searchParams] = useSearchParams();
    const { success } = useToast();
    const navigate = useNavigate();
    const projectId = searchParams.get("projectId") ?? "";

    const stageInstanceIdParam = searchParams.get("stageInstanceId") ?? null;
    const reportNumberParam = parseInt(searchParams.get("reportNumber") ?? "1", 10) || 1;

    const { setProjectHeader, clearProjectHeader } = useProjectHeader();
    const [_projectName, setProjectName] = useState<string>("");
    const [_programName, setProgramName] = useState<string>("");
    const [stageInstances, setStageInstances] = useState<any[]>([]);
    const [stages, setStages] = useState<any[]>([]);
    const [activeStage, setActiveStage] = useState("Business case");
    const [activeSubStage, setActiveSubStage] = useState("Construction");
    const [showMitigations, setShowMitigations] = useState(false);
    const [showCompleteness, setShowCompleteness] = useState(false);
    const [activeReportNumber, setActiveReportNumber] = useState(1);
    // Per-stage_instance_id override for the "Currently editing" option picker (Business Case only).
    const [selectedOptionByStage, setSelectedOptionByStage] = useState<Record<string, string>>({});
    const [lockedStages, setLockedStages] = useState<Set<string>>(new Set());
    const [moreMenuOpen, setMoreMenuOpen] = useState(false);
    const [manageOptionsOpen, setManageOptionsOpen] = useState(false);
    const [copyDataOpen, setCopyDataOpen] = useState(false);
    const moreMenuRef = useRef<HTMLDivElement>(null);
    // De-dupes concurrent ProjectOptionsService.ensureOptions() calls for the same stage instance.
    const pendingEnsureOptions = useRef<Set<string>>(new Set());
    const [projectOptions, setProjectOptions] = useState<ProjectOption[]>([]);
    const [frequency, setFrequency] = useState<string>("Monthly");
    const [firstSubmissionMonth, setFirstSubmissionMonth] = useState<string | null>(null);

    const [accordionState, setAccordionState] = useState({
        asset: true,
        component: true,
        componentRepl: true,
        refurbishment: true,
        opEnergy: true,
        opEnergyDetailed: true,
        opEnergyElectricity: true,
        construction: true,
        constructionG2: true,
        constructionG3: true,
        bcDetailedLevel: true,
        electricity: true,
        useB1G2: true,
        useB1G3: true,
        concreteRegSimplified: true,
        concreteRegDetailed: true,
        replDetailed: true,
        recurringG3: true,
    });

    const { tableRows, setTableRows, getRows, updateRows, tableErrors, setErrorForKey } = useTableRows();
    const [reportingBoundaries, setReportingBoundaries] = useState<any[]>([]);

    const [concreteMixModalType, setConcreteMixModalType] = useState<"mix_design" | "epd_pcf" | null>(null);
    const [concreteMixEditTarget, setConcreteMixEditTarget] = useState<any | null>(null);

    const [_reportSubmitted, _setReportSubmitted] = useState<boolean>(false);
    const [fugitiveList, setFugitiveList] = useState<any[]>([]);
    const [selectedConstructionMonth, setSelectedConstructionMonth] = useState<string | null>(null);
    const [constructionReportStates, _setConstructionReportStates] = useState<
        { month: string; status: string }[]
    >([]);
    const [constructionPeriods, setConstructionPeriods] = useState<ConstructionPeriod[]>([]);

const [constructionStartDate, setConstructionStartDate] = useState<string | null>(null);
const [constructionEndDate, setConstructionEndDate] = useState<string | null>(null);

    const [reviewMenuOpen, setReviewMenuOpen] = useState(false);
    const reviewMenuRef = useRef<HTMLDivElement>(null);

    const [projectClass, setProjectClass] = useState<string | null>(null);
    const [projectTypeName, setProjectTypeName] = useState<string | null>(null);

    useEffect(() => {
        if (projectClass !== null && projectClass !== "LARGE") {
            setShowMitigations(false);
        }
    }, [projectClass]);

     useEffect(() => {
        if (activeStage === "Business case") {
            setShowMitigations(false);
        }
    }, [activeStage]);

    // useEffect(() => {
    //     if (!completenessEnabled) {
    //         setShowCompleteness(false);
    //     }
    // }, [completenessEnabled]);

    const [projectGridCtx, setProjectGridCtx] = useState<{ jurisdiction: string; region: string } | null>(null);
    const [operationalLifeYears, setOperationalLifeYears] = useState<number | null>(null);
    const [opsStartYear, setOpsStartYear] = useState<number | null>(null);

    // Design → Construction seed state
    const [designReportNum, setDesignReportNum] = useState<number>(1);
    const [pendingDesignReportNum, setPendingDesignReportNum] = useState<number | null>(null);
    const [designSeedConfirmOpen, setDesignSeedConfirmOpen] = useState(false);
    const [reDesignSeedLoading, setReDesignSeedLoading] = useState(false);
    const [stageAccess, setStageAccess] = useState<StageAccess[]>([]);
    const [projectClosed, setProjectClosed] = useState<boolean>(false);
    const [accessDenied, setAccessDenied] = useState(false);

    const charLimit = 1000;


    const [hasResubmission, setHasResubmission] = useState(false);
    const [showAuditPanel, setShowAuditPanel] = useState(false);

    useOutsideClick(reviewMenuRef, () => setReviewMenuOpen(false), reviewMenuOpen);
    useOutsideClick(moreMenuRef, () => setMoreMenuOpen(false), moreMenuOpen);
    const assetColumns = useMemo(() => assetTableConfig(projectId).columns(), [projectId]); //bc construction -asset level
    const componentColumns = useMemo(() => componentTableConfig(projectId).columns(), [projectId]);// bc construction - comp level
    const componentReplColumns = useMemo(() => componentReplacementConfig(projectId).columns(), [projectId]);
    const refurbColumns = useMemo(() => refurbishmentTableConfig(projectGridCtx?.jurisdiction ?? null).columns(), [projectGridCtx]);
    const opEnergyColumns = useMemo(() => opEnergyTableConfig(projectId).columns(), [projectId]);
    const opEnergyDetailedColumns = useMemo(() => useB1G3Config(projectId, ["Fuels", "Water"]).columns(), [projectId]);
    const opEnergyElectricityColumns = useMemo(() => electricityConfig(projectId).columns(), [projectId]);
    const constructionG2Columns = useMemo(() => constructionG2Config(projectId).columns(), [projectId]);
    const constructionG3Columns = useMemo(() => constructionG3Config(projectId, "constructionG3").columns(), [projectId]);
    const bcDetailedColumns = useMemo(() => constructionG3Config(projectId, "bcDetailedLevel").columns(), [projectId]); //bc construction - detailed level 
    const electricityColumns = useMemo(() => electricityConfig(projectId).columns(), [projectId]); // bc construction - elec
    const useB1G2Columns = useMemo(() => useB1G2Config(projectGridCtx?.jurisdiction ?? null, projectId).columns(), [projectGridCtx, projectId]); // use b1 component 
    const useB1G3Columns = useMemo(() => useB1G3Config(projectId, ["Gases"]).columns(), [projectId]); //use b1 detailed 
    const concreteRegSimplifiedColumns = useMemo(() => concreteRegSimplifiedConfig().columns(), []);
    const concreteRegDetailedColumns = useMemo(() => concreteRegDetailedConfig().columns(), []);
    const replDetailedColumns = useMemo(() => useB1G3Config(projectId).columns(), [projectId]); // replacement detailed uses the same config as useB1G3
    const [projectData, setProjectData] = useState<any>({});

    const getStageNameByValue = useCallback(
        (value: string) => {
            const s = stages.find((x: any) => x.id === value || x.name === value);
            return s?.name ?? value;
        },
        [stages]
    );

    const activeStageInstance = useMemo(() => {
        const stageEnum = STAGE_LABEL_TO_ENUM[activeStage];
        return stageInstances.find((si: any) => si.stage === stageEnum) ?? null;
    }, [stageInstances, activeStage]);

    const activeStageAccess: StageAccessLevel = useMemo(() => {
        if (!activeStageInstance?.id) return "NONE";
        return stageAccess.find((item) => item.stage_instance_id === activeStageInstance.id)?.access ?? "NONE";
    }, [activeStageInstance, stageAccess]);

    const canEditActiveStage = canEditStage(activeStageAccess);
    const canAdminActiveStage = canAdminStage(activeStageAccess);
    const isProjAdmin = canAdminActiveStage;
    const isProjEditor = canEditActiveStage;

    /** Mitigations persist under DESIGN or CONSTRUCTION instances, not BUSINESS_CASE when that tab is active */
    const mitigationBucketStageEnum = useMemo(
        () => (activeStage === "Construction" ? "CONSTRUCTION" : "DESIGN"),
        [activeStage],
    );

    const mitigationStageInstance = useMemo(() => {
        return (
            stageInstances.find((si: any) => si.stage === mitigationBucketStageEnum) ?? null
        );
    }, [stageInstances, mitigationBucketStageEnum]);

    const mitigationOptionId = useMemo(() => {
        if (!mitigationStageInstance || !projectOptions.length) return null;
        const opts = projectOptions.filter(
            (o) =>
                o.stage_instance_id === mitigationStageInstance.id &&
                o.report_number === activeReportNumber,
        );
        return opts.find((o) => o.is_default)?.id ?? opts[0]?.id ?? null;
    }, [mitigationStageInstance, projectOptions, activeReportNumber]);

    // Computed values for Design → Construction seed feature
    const designStageInstance = useMemo(
        () => stageInstances.find((si: any) => si.stage === "DESIGN") ?? null,
        [stageInstances]
    );
    const designReportNums = useMemo(() => {
        if (!designStageInstance) return [];
        const nums = projectOptions
            .filter((o) => o.stage_instance_id === designStageInstance.id)
            .map((o) => o.report_number);
        return [...new Set(nums)].sort((a, b) => a - b);
    }, [designStageInstance, projectOptions]);
    const designSeedOptionId = useMemo(() => {
        if (!designStageInstance) return null;
        const opts = projectOptions.filter(
            (o) => o.stage_instance_id === designStageInstance.id && o.report_number === designReportNum
        );
        return opts.find((o) => o.is_default)?.id ?? opts[0]?.id ?? null;
    }, [designStageInstance, projectOptions, designReportNum]);

    const activePeriod = useMemo(
        () => constructionPeriods.find((p) => p.id === selectedConstructionMonth) ?? null,
        [constructionPeriods, selectedConstructionMonth]
    );

    const recurringActivities = useMemo(() => {
        const seen = new Set<string>();
        const ordered: string[] = [];
        for (const b of reportingBoundaries) {
            const act = b.stage_or_activity ?? "";
            if (act && !seen.has(act)) { seen.add(act); ordered.push(act); }
        }
        return ordered;
    }, [reportingBoundaries]);

    const boundaryIdToActivity = useMemo(() => {
        const map: Record<string, string> = {};
        for (const b of reportingBoundaries) map[b.id] = b.stage_or_activity ?? "";
        return map;
    }, [reportingBoundaries]);

    const recurringRowsByActivity = useMemo(() => {
        const map: Record<string, any[]> = {};
        for (const act of recurringActivities) map[act] = [];
        for (const r of getRows("recurringG3")) {
            const bid = r.reporting_boundary_id ?? r.extra_fields?.reporting_boundary_id;
            const act = (bid ? boundaryIdToActivity[bid] : null) ?? r.extra_fields?.stage_or_activity ?? null;
            if (act && map[act] !== undefined) map[act].push(r);
        }
        return map;
    }, [tableRows, recurringActivities, boundaryIdToActivity]);

    const currentReportSubOptions = useMemo(() => {
        if (!activeStageInstance) return [];
        return projectOptions.filter(
            (o) => o.stage_instance_id === activeStageInstance.id && o.report_number === activeReportNumber
        );
    }, [projectOptions, activeStageInstance, activeReportNumber]);

    const baseCaseOptions = useMemo(
        () => currentReportSubOptions.map((o) => ({ label: o.label, value: o.id })),
        [currentReportSubOptions]
    );

    const enrichedStages = useMemo(
        () => {
            // Stage navigation is driven exclusively by the stage instances returned
            // after the current user's stage-access check. Do not fall back to
            // stage_configs here because that can briefly expose inaccessible stages
            // while /api/me/access is still loading.
            const sorted = [...stageInstances]
                .filter((inst: any) => {
                    if (projectClass === "RECURRING") return inst.stage === "RECURRING";
                    return inst.stage !== "RECURRING";
                })
                .sort((a: any, b: any) => (a.sequence ?? 0) - (b.sequence ?? 0));
            const items: { label: string; value: string; stageLabel: string; reportNumber: number; disabled: boolean }[] = [];
            for (const inst of sorted) {
                const stageLabel = STAGE_ENUM_TO_LABEL[inst.stage] ?? inst.stage;
                const n = inst.num_reports_required ?? 1;
                const disabled = false;
                if (n <= 1) {
                    items.push({ label: stageLabel, value: `${stageLabel}__1`, stageLabel, reportNumber: 1, disabled });
                } else {
                    for (let i = 1; i <= n; i++) {
                        items.push({
                            label: `${stageLabel} (${i} of ${n})`,
                            value: `${stageLabel}__${i}`,
                            stageLabel,
                            reportNumber: i,
                            disabled,
                        });
                    }
                }
            }
            
items.push({
        label: "Results dashboard",
        value: "RESULTS_DASHBOARD",
        stageLabel: "RESULTS_DASHBOARD",
        reportNumber: 1,
        disabled: false,
    });

            return items;
        },
        [stages, stageInstances, projectClass]
    );

    const subStages = useMemo(
        () => SUBSTAGES_FOR(getStageNameByValue(activeStage), projectClass),
        [activeStage, getStageNameByValue, projectClass]
    );

    async function resolveBoundaryComponentIds(b: { category: string; sub_category: string; source?: string | null }) {
        return resolveBoundaryComponentIdsFn(b, projectId);
    }


    const goToNextSubStage = () => {
        const idx = subStages.indexOf(activeSubStage);
        if (idx === -1) return;

        const next = subStages[idx + 1];
        if (next) {
            setActiveSubStage(next);
        }
    };


    // Derived (never stored) so it can't go stale after a stage/report switch —
    // it recomputes from the current stage/report/options on every render.
    const activeOptionId = useMemo(() => {
        if (!activeStageInstance || !currentReportSubOptions.length) return null;
        const override = selectedOptionByStage[activeStageInstance.id];
        if (override && currentReportSubOptions.some((o) => o.id === override)) return override;
        return currentReportSubOptions.find((o) => o.is_default)?.id ?? currentReportSubOptions[0].id;
    }, [activeStageInstance, currentReportSubOptions, selectedOptionByStage]);

    const activeOption = useMemo(
        () => projectOptions.find((o) => o.id === activeOptionId) ?? null,
        [projectOptions, activeOptionId]
    );


    const optionTotalEmissions = useMemo(() => {
        const v = activeOption?.total_emissions_tco2e;
        if (v == null || v === "" || Number.isNaN(Number(v))) return 0;
        return Number(v);
    }, [activeOption?.total_emissions_tco2e]);


    const resolveMetricId = useCallback(async (draft: any, tableKey: UploadKey): Promise<string | null> => {
        try {
            const params = new URLSearchParams({ limit: "1" });
            if (tableKey === "asset") {
                if (draft.mastertype_id) params.set("mastertype_id", draft.mastertype_id);
                if (draft.typecast_id) params.set("typecast_id", draft.typecast_id);
                if (draft.band_code) params.set("band_code", draft.band_code);
            } else if (["component", "componentRepl"].includes(tableKey)) {
                if (draft.emissions_category_id) params.set("emissions_category_id", draft.emissions_category_id);
                if (draft.emissions_subcategory_id) params.set("emissions_subcategory_id", draft.emissions_subcategory_id);
            } else if (tableKey === "constructionG2" || tableKey === "constructionG3" || tableKey === "bcDetailedLevel" || tableKey === "useB1G2" || tableKey === "useB1G3" || tableKey === "opEnergyDetailed" || tableKey === "replDetailed" || tableKey === "recurringG3") {
                if (draft.emissions_category_id) params.set("emissions_category_id", draft.emissions_category_id);
                const subCatId = draft.emissions_subcategory_id ?? draft.emission_subcategory_id;
                if (subCatId) params.set("emissions_subcategory_id", subCatId);
            } else {
                return null;
            }
            const resp = await http.get(`/api/background-grade-metrics?${params.toString()}`);
            const metrics = Array.isArray(resp.data) ? resp.data : [];
            return metrics[0]?.id ?? null;
        } catch {
            return null;
        }
    }, []);


    const apiRowToUiRow = useCallback((apiRow: any): any => apiRowToUiRowFn(apiRow), []);

    useEffect(() => {
        let ignore = false;

        async function loadInitialData() {
            if (!projectId) return;
            try {
                setAccessDenied(false);
                const projectData = await ProjectsService.fetchProjectDetails(projectId) as ProjectDetails;
                setProjectData(projectData);
                const stagesList = projectData?.stage_configs ?? [];
                if (ignore) return;
                const name = projectData?.name ?? projectData?.project_name ?? "";
                setProjectName(name);
                setProgramName(projectData?.program_name ?? "");
                setProjectHeader(name, true, projectId);
                const instances: any[] = projectData?.stage_instances ?? [];
                setStages(stagesList);
                setFrequency(projectData?.stage_configs?.find((s: any) => s.stage === "CONSTRUCTION")?.frequency ?? "Monthly");
                setFirstSubmissionMonth(projectData?.first_submission_month ?? null);
                // Capture project class for conditional table rendering
                const pClass = projectData?.project_class ?? null;
                setProjectClass(pClass);
                setProjectClosed(!(projectData?.is_active ?? true));
                const accessRes = await ProjectAccessService.fetchMyProjectAccess(projectId);
                const resolvedStageAccess: StageAccess[] = accessRes.stage_access ?? [];
                const accessibleInstances = filterAccessibleStageInstances(
                    instances,
                    resolvedStageAccess,
                );

                if (!accessibleInstances.length) {
                    if (!ignore) setAccessDenied(true);
                    return;
                }

                if (!ignore) {
                    setStageAccess(resolvedStageAccess);
                    setStageInstances(accessibleInstances);
                }
                setProjectTypeName(projectData?.project_type_name ?? null);
                setOperationalLifeYears(projectData?.operational_life_years ?? null);
                const coDate = projectData?.commencement_of_operations;
                setOpsStartYear(coDate ? new Date(coDate).getFullYear() : null);
                setConstructionStartDate(projectData?.construction_start_date ?? null);
                setConstructionEndDate(projectData?.construction_end_date ?? null);

                // Derive grid context from the first project postcode (sorted by creation order)
                const firstPostcode = (projectData?.postcodes ?? []).slice().sort(
                    (a: any, b: any) => new Date(a.created_on ?? 0).getTime() - new Date(b.created_on ?? 0).getTime()
                )[0] ?? null;
                if (firstPostcode?.jurisdiction_name && firstPostcode?.grid_region) {
                    const jur = firstPostcode.jurisdiction_name.toLowerCase().includes("new zealand")
                        ? "New Zealand"
                        : "Australia";
                    setProjectGridCtx({ jurisdiction: jur, region: firstPostcode.grid_region });
                } else {
                    // Fallback: no postcodes yet — default to NSW so tables remain functional
                    setProjectGridCtx({ jurisdiction: "Australia", region: "New South Wales" });
                }

                const locked = new Set<string>();
                for (const inst of accessibleInstances) {
                    if (inst.approval_status === "final_approved") {
                        locked.add(inst.stage as string);
                    }
                }
                setLockedStages(locked);

                const firstInstance = accessibleInstances[0];

                // Determine which stage to activate based on URL parameter or default to first
                let targetInstance = firstInstance;
                if (stageInstanceIdParam) {
                    const paramInstance = accessibleInstances.find((inst: any) => inst.id === stageInstanceIdParam);
                    if (paramInstance) {
                        targetInstance = paramInstance;
                    }
                }

                const targetStageEnum = targetInstance?.stage;
                const initialLabel = STAGE_ENUM_TO_LABEL[targetStageEnum] ?? (pClass === "RECURRING" ? "Recurring" : "Business case");

                // Only ensure options for the target/active stage — other stages load lazily on switch
                const optionsMap: ProjectOption[] = [];
                if (targetInstance && (targetInstance.num_reports_required ?? 1) > 0) {
                    const sid = targetInstance.id;
                    const targetAccess =
                        resolvedStageAccess.find((item) => item.stage_instance_id === sid)?.access ?? "NONE";
                    if (targetAccess !== "NONE" && !pendingEnsureOptions.current.has(sid)) {
                        pendingEnsureOptions.current.add(sid);
                        try {
                            const opts = targetAccess === "VIEW"
                                ? await ProjectOptionsService.fetchOptions(sid)
                                : await ProjectOptionsService.ensureOptions(sid);
                            optionsMap.push(...opts);
                        } catch (e) {
                            console.warn("Failed to load options for stage instance:", sid, e);
                        } finally {
                            pendingEnsureOptions.current.delete(sid);
                        }
                    }
                }
                if (!ignore) {
                    setProjectOptions(optionsMap);
                    if (targetInstance) {
                        setActiveReportNumber(reportNumberParam);
                    }
                }

                try {
                    const rbResp = await http.get(`/api/projects/${projectId}/reporting-boundaries`);
                    if (!ignore) setReportingBoundaries(Array.isArray(rbResp.data) ? rbResp.data : []);
                } catch (e) {
                    throw e;
                }

                setActiveStage(initialLabel);
                setActiveSubStage(SUBSTAGES_FOR(initialLabel, pClass)[0] ?? "Construction");
            } catch (err) {
                console.error("Error loading:", err);
            }
        }
        loadInitialData();
        return () => { ignore = true; clearProjectHeader(); };
    }, [projectId]);

    // Lazily ensure options when switching to a stage whose options haven't been loaded yet.
    // This fires whenever activeStageInstance changes (i.e. user selects a different stage).
    // Construction uses construction-periods for its workflow — project options are not needed there.
    useEffect(() => {
        if (!activeStageInstance) return;
        if (isConstructionStage) return;
        const activeAccess =
            stageAccess.find((item) => item.stage_instance_id === activeStageInstance.id)?.access ?? "NONE";
        if (activeAccess === "NONE") return;
        const alreadyLoaded = projectOptions.some(
            (o) => o.stage_instance_id === activeStageInstance.id
        );
        if (alreadyLoaded) return;
        let ignore = false;
        (async () => {
            const sid = activeStageInstance.id;
            if (pendingEnsureOptions.current.has(sid)) return;
            pendingEnsureOptions.current.add(sid);
            try {
                const opts = activeAccess === "VIEW"
                    ? await ProjectOptionsService.fetchOptions(sid)
                    : await ProjectOptionsService.ensureOptions(sid);
                if (ignore) return;
                setProjectOptions((prev) => {
                    const existing = prev.filter((o) => o.stage_instance_id !== sid);
                    return [...existing, ...opts];
                });
            } catch (e) {
                console.warn("Failed to lazily load options for stage instance:", sid, e);
            } finally {
                pendingEnsureOptions.current.delete(sid);
            }
        })();
        return () => { ignore = true; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeStageInstance?.id, activeReportNumber]);

    // Design-bucket mitigations use the Design stage_instance_id; ensure its project_options exist
    // when opening Mitigations while the nav tab is still Business case (or another non-matching stage).
    useEffect(() => {
        if (projectClass !== "LARGE" || !showMitigations) return;
        if (!mitigationStageInstance?.id) return;
        if (mitigationBucketStageEnum === "CONSTRUCTION") return;
        if (activeStageInstance?.id === mitigationStageInstance.id) return;
        const mitigationAccess =
            stageAccess.find((item) => item.stage_instance_id === mitigationStageInstance.id)?.access ?? "NONE";
        if (mitigationAccess === "NONE") return;
        const alreadyLoaded = projectOptions.some(
            (o) => o.stage_instance_id === mitigationStageInstance.id,
        );
        if (alreadyLoaded) return;
        let ignore = false;
        (async () => {
            const sid = mitigationStageInstance.id;
            if (pendingEnsureOptions.current.has(sid)) return;
            pendingEnsureOptions.current.add(sid);
            try {
                const opts = mitigationAccess === "VIEW"
                    ? await ProjectOptionsService.fetchOptions(sid)
                    : await ProjectOptionsService.ensureOptions(sid);
                if (ignore) return;
                setProjectOptions((prev) => {
                    const existing = prev.filter((o) => o.stage_instance_id !== sid);
                    return [...existing, ...opts];
                });
            } catch (e) {
                console.warn(
                    "Failed to ensure options for mitigation stage instance:",
                    mitigationStageInstance.id,
                    e,
                );
            } finally {
                pendingEnsureOptions.current.delete(sid);
            }
        })();
        return () => {
            ignore = true;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [
        projectClass,
        showMitigations,
        mitigationStageInstance?.id,
        mitigationBucketStageEnum,
        activeStageInstance?.id,
        stageAccess,
        projectOptions,
    ]);

    // Load Design stage project_options when viewing Construction as a LARGE project
    // so that designSeedOptionId can be resolved for the seed-from-design feature.
    useEffect(() => {
        if (activeStage !== "Construction" || projectClass !== "LARGE") return;
        if (!designStageInstance?.id) return;
        const designAccess =
            stageAccess.find((item) => item.stage_instance_id === designStageInstance.id)?.access ?? "NONE";
        if (designAccess === "NONE") return;
        const alreadyLoaded = projectOptions.some((o) => o.stage_instance_id === designStageInstance.id);
        if (alreadyLoaded) return;
        let ignore = false;
        (async () => {
            const sid = designStageInstance.id;
            if (pendingEnsureOptions.current.has(sid)) return;
            pendingEnsureOptions.current.add(sid);
            try {
                const opts = designAccess === "VIEW"
                    ? await ProjectOptionsService.fetchOptions(sid)
                    : await ProjectOptionsService.ensureOptions(sid);
                if (ignore) return;
                setProjectOptions((prev) => {
                    const existing = prev.filter((o) => o.stage_instance_id !== sid);
                    return [...existing, ...opts];
                });
            } catch (e) {
                console.warn("Failed to load Design options for Construction seed feature:", e);
            } finally {
                pendingEnsureOptions.current.delete(sid);
            }
        })();
        return () => { ignore = true; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeStage, projectClass, designStageInstance?.id, stageAccess, projectOptions]);

    useEffect(() => {
        if (!isProjAdmin || !activeStageInstance?.id || activeOption?.approval_status !== "submitted") {
            setHasResubmission(false);
            return;
        }
        let cancelled = false;
        fetchStageResubmissionAudit(activeStageInstance.id, activeOption?.id)
            .then((result) => { if (!cancelled) setHasResubmission(result.has_prior_rejection); })
            .catch(() => { if (!cancelled) setHasResubmission(false); });
        return () => { cancelled = true; };
    }, [isProjAdmin, activeStageInstance?.id, activeOption?.approval_status]);

    useEffect(() => {
        let ignore = false;

        (async () => {
            try {
                const stageName = getStageNameByValue(activeStage);

                // Preserve concrete rows — they are managed by a separate effect
                // with its own deps and must not be wiped on every sub-stage change.
                const CONCRETE_KEYS = new Set(["concreteRegSimplified", "concreteRegDetailed"]);
                setTableRows((prev) => Object.fromEntries(
                    Object.keys(prev).map((k) => [k, CONCRETE_KEYS.has(k) ? prev[k as UploadKey] : []])
                ) as unknown as Record<UploadKey, any[]>);

                const stageEnum = STAGE_LABEL_TO_ENUM[stageName];
                const stageInst = stageInstances.find((si: any) => si.stage === stageEnum);
                if (!stageInst) return;

                if ((stageName === "Business case" || stageName === "Design") && activeOptionId === null) return;

                if (stageName === "Business case" || stageName === "Design") {
                    if (activeSubStage === "Construction") {
                        const fetches: Promise<any>[] = [
                            ActivityDataService.fetchRows(stageInst.id, "asset", activeOptionId ?? undefined),
                            ActivityDataService.fetchRows(stageInst.id, "component", activeOptionId ?? undefined),
                            ActivityDataService.fetchRows(stageInst.id, "componentRepl", activeOptionId ?? undefined),
                        ];
                        if (projectClass === "LARGE") {
                            fetches.push(
                                ActivityDataService.fetchRows(stageInst.id, "bcDetailedLevel", activeOptionId ?? undefined),
                                ActivityDataService.fetchRows(stageInst.id, "electricity", activeOptionId ?? undefined),
                            );
                        }
                        const results = await Promise.all(fetches);
                        if (ignore) return;
                        const asset = (Array.isArray(results[0]) ? results[0] : []).map(apiRowToUiRow);
                        updateRows("asset", asset);
                        if (asset.some((r) => r.emissions_tco2e == null)) recalcAndPersistRows("asset", asset, (u) => updateRows("asset", u));
                        // setComponentRows((Array.isArray(results[1]) ? results[1] : []).map(apiRowToUiRow));

                        const comp = (Array.isArray(results[1]) ? results[1] : []).map(apiRowToUiRow);

                        let componentRowsToRender = comp;
                        if (reportingBoundaries.length > 0) {
                            const constrBoundsComp = reportingBoundaries.filter(
                                (b) => b.stage_or_activity === "Construction"
                            );
                            const unresolvedBounds = constrBoundsComp.filter(
                                (b) =>
                                    !comp.some(
                                        (r) =>
                                            r.reporting_boundary_id === b.id ||
                                            r.extra_fields?.reporting_boundary_id === b.id
                                    )
                            );
                            const compBoundaryPlaceholders = await Promise.all(
                                unresolvedBounds.map(async (b) => {
                                    const ids = await resolveBoundaryComponentIds(b);
                                    return {
                                        id: `__BOUNDARY_${b.id}__`,
                                        _fromBoundary: true,
                                        emissions_category: b.category,
                                        emissions_subcategory: b.sub_category,
                                        emissions_source_name: b.source ?? "",
                                        emissions_category_id: ids.emissions_category_id,
                                        emissions_subcategory_id: ids.emissions_subcategory_id,
                                        emissions_source: ids.emissions_source,
                                        unit_code: null,
                                        unit_id: null,
                                        quantity: null,
                                        emissions_tco2e: null,
                                    };
                                })
                            );
                            componentRowsToRender = [...comp, ...compBoundaryPlaceholders];
                        }
                        updateRows("component", componentRowsToRender);
                        if (comp.some((r) => r.emissions_tco2e == null)) recalcAndPersistRows("component", comp, (u) => updateRows("component", u));

                        updateRows("componentRepl", (Array.isArray(results[2]) ? results[2] : []).map(apiRowToUiRow));

                        if (projectClass === "LARGE") {
                            updateRows("bcDetailedLevel", (Array.isArray(results[3]) ? results[3] : []).map(apiRowToUiRow));
                            const elecRows = (Array.isArray(results[4]) ? results[4] : []).map(apiRowToUiRow);
                            updateRows("electricity", elecRows);

                            if (elecRows.some((r) => r.emissions_tco2e == null)) {
                                recalcAndPersistRows("electricity", elecRows, (u) => updateRows("electricity", u));
                            }
                        }
                    } else if (activeSubStage === "Use (B1)" && projectClass === "LARGE") {
                        const [rawG2, rawG3] = await Promise.all([
                            ActivityDataService.fetchRows(stageInst.id, "useB1G2", activeOptionId ?? undefined),
                            ActivityDataService.fetchRows(stageInst.id, "useB1G3", activeOptionId ?? undefined),
                        ]);
                        if (ignore) return;
                        // setUseB1G2Rows((Array.isArray(rawG2) ? rawG2 : []).map(apiRowToUiRow));
                        const g2Rows = (Array.isArray(rawG2) ? rawG2 : []).map(apiRowToUiRow);
                        updateRows("useB1G2", g2Rows);
                        if (g2Rows.some(r => r.emissions_tco2e == null)) {
                            recalcAndPersistRows("useB1G2", g2Rows, (u) => updateRows("useB1G2", u));
                        }
                        // setUseB1G3Rows((Array.isArray(rawG3) ? rawG3 : []).map(apiRowToUiRow));
                        const g3Rows = (Array.isArray(rawG3) ? rawG3 : []).map(apiRowToUiRow);
                        updateRows("useB1G3", g3Rows);
                        if (g3Rows.some(r => r.emissions_tco2e == null)) {
                            recalcAndPersistRows("useB1G3", g3Rows, (u) => updateRows("useB1G3", u));
                        }
                    } else if (activeSubStage === REPLACEMENT_LABEL || activeSubStage === REPLACEMENT_LABEL_LARGE) {
                        const [rawComp, rawRefurb, rawReplDetailed] = await Promise.all([
                            ActivityDataService.fetchRows(stageInst.id, "componentRepl", activeOptionId ?? undefined),
                            ActivityDataService.fetchRows(stageInst.id, "refurbishment", activeOptionId ?? undefined),
                            ActivityDataService.fetchRows(stageInst.id, "replDetailed", activeOptionId ?? undefined),
                        ]);
                        if (ignore) return;
                        const repl = (Array.isArray(rawComp) ? rawComp : []).map(apiRowToUiRow);
                        updateRows("componentRepl", repl);
                        if (repl.some((r) => r.emissions_tco2e == null)) recalcAndPersistRows("componentRepl", repl, (u) => updateRows("componentRepl", u));
                        const refurb = (Array.isArray(rawRefurb) ? rawRefurb : []).map(apiRowToUiRow);

                        const replDetailedRows = (Array.isArray(rawReplDetailed) ? rawReplDetailed : []).map(apiRowToUiRow);
                        updateRows("replDetailed", replDetailedRows);


                        if (!reportingBoundaries.length) {
                            updateRows("refurbishment", refurb);
                            return;
                        }

                        const maintBounds = reportingBoundaries.filter((b) => b.stage_or_activity === "Maintenance");
                        await fetchAllActiveMrFactors();
                        const mrFactors = await fetchAllActiveMrFactors();
                        const refurbBoundaryPlaceholders = maintBounds
                            .filter((b) => !refurb.some((r) => r.extra_fields?.reporting_boundary_id === b.id))
                            .map((b) => {
                                const factor = mrFactors.find((f) => f.activity_type === b.category && f.item === b.sub_category);
                                return {
                                    id: `__BOUNDARY_${b.id}__`,
                                    _fromBoundary: true,
                                    activityType: b.category,
                                    item: b.sub_category,
                                    mr_factor_id: factor?.id ?? null,
                                    unit_code: (factor as any)?.unit?.code ?? "m2",
                                    frequency: (factor as any)?.default_frequency_years ?? null,
                                    quantity: null,
                                    emissions_tco2e: null,
                                };
                            });
                        updateRows("refurbishment", [...refurb, ...refurbBoundaryPlaceholders]);
                        if (refurb.some((r) => r.emissions_tco2e == null)) {
                            await fetchAllActiveMrFactors(); // warm cache before recalc
                            recalcAndPersistRows("refurbishment", refurb, (u) => updateRows("refurbishment", u));
                        }
                    } else if (activeSubStage === "Operational energy (B6)") {
                            const [rawOp, rawDetailed, rawOpElec] = await Promise.all([
                                    ActivityDataService.fetchRows(stageInst.id, "opEnergy", activeOptionId ?? undefined),
                                    projectClass === "LARGE"
                                        ? ActivityDataService.fetchRows(stageInst.id, "opEnergyDetailed", activeOptionId ?? undefined)
                                        : Promise.resolve([]),
                                    projectClass === "LARGE"
                                        ? ActivityDataService.fetchRows(stageInst.id, "opEnergyElectricity", activeOptionId ?? undefined)
                                        : Promise.resolve([]),
                                ]);

                                if (ignore) return;
                                const opRows = (Array.isArray(rawOp) ? rawOp : []).map(apiRowToUiRow);
                                if (!reportingBoundaries.length) {
                                    updateRows("opEnergy", opRows);
                                } else {
                                    const opsBounds = reportingBoundaries.filter(
                                        (b) => b.stage_or_activity === "Operations"
                                    );
                                    const opsBoundaryPlaceholders = opsBounds
                                        .filter((b) => !opRows.some((r) => r.extra_fields?.reporting_boundary_id === b.id))
                                        .map((b) => ({
                                            id: `__BOUNDARY_${b.id}__`,
                                            _fromBoundary: true,
                                            emissions_category: "Electricity",
                                            group_name: b.category,
                                            item: b.sub_category,
                                            unit_code: "Each",
                                            quantity: null,
                                            location_based_total_tco2e: null,
                                            market_based_total_tco2e: null,
                                            emissions_tco2e: null,
                                        }));
                                    updateRows("opEnergy", [...opRows, ...opsBoundaryPlaceholders]);
                                }
                                if (projectClass === "LARGE") {
                                    const detailedRows = (Array.isArray(rawDetailed) ? rawDetailed : []).map(apiRowToUiRow);
                                    const opElecRows = (Array.isArray(rawOpElec) ? rawOpElec : []).map(apiRowToUiRow);

                                    updateRows("opEnergyDetailed", detailedRows);
                                    updateRows("opEnergyElectricity", opElecRows);

                                    if (opElecRows.some((r) => r.emissions_tco2e == null)) {
                                        recalcAndPersistRows(
                                            "opEnergyElectricity",
                                            opElecRows,
                                            (u) => updateRows("opEnergyElectricity", u)
                                        );
                                    }
                                }
                                                }
                                            }
            } catch (err) {
                console.error("Error fetching data:", err);
            }
        })();

        return () => {
            ignore = true;
        };
    }, [activeStage, activeSubStage, getStageNameByValue, stageInstances, apiRowToUiRow, activeReportNumber, activeOptionId, reportingBoundaries]);


    const {
        adminDecisionOpen, setAdminDecisionOpen,
        decisionComments, setDecisionComments,
        reopenModalOpen, setReopenModalOpen,
        reopenJustification, setReopenJustification,
        submitModalOpen, setSubmitModalOpen,
        periodWorkflowOpen, setPeriodWorkflowOpen,
        refreshOptionTotals,
        handleReportSubmission,
        triggerAdminDecision,
        submitReopenRequest,
        handlePeriodWorkflowConfirm,
        seedPeriodsFromDesign,
    } = useWorkflowActions({
        activeStage,
        activeStageInstance,
        activeOptionId,
        activeOption,
        activePeriod,
        constructionPeriods,
        designSeedOptionId,
        success,
        setProjectOptions,
        setConstructionPeriods,
        setSelectedConstructionMonth,
    });

    const { getCalcConfig, computeEmissionsForRow, recalcAndPersistRows, recalcElectricitySiblings } =
        useEmissionsCalc({
            projectId,
            projectGridCtx,
            operationalLifeYears,
            opsStartYear,
            constructionStartDate,
            constructionEndDate,
            refreshOptionTotals,
            projectOptionId: activeOptionId,
            projectStageInstanceId: activeStageInstance?.id ?? null,
        });

    const { mitigationPersistence } =
        useMitigationHandlers({
            projectId,
            projectClass,
            activeStage,
            activePeriod,
            mitigationStageInstance,
            mitigationOptionId,
            user,
            resolveMetricId,
            computeEmissionsForRow,
            getCalcConfig,
            apiRowToUiRow,
            refreshOptionTotals,
            operationalLifeYears,
            fugitiveList,
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
        });

    const {
        execSummary, setExecSummary,
        execSummaryDirty, setExecSummaryDirty,
        execSummaryAuthor, execSummaryDate,
        saveExecSummary,
    } = useExecSummary({
        activeStage,
        activeOption,
        activePeriod,
        activeOptionId,
        user,
        success,
        setConstructionPeriods,
        setProjectOptions,
    });

    const {
        largeUsersYears,
        activeLargeUsersYear, setActiveLargeUsersYear,
        addLargeYearOpen, setAddLargeYearOpen,
        addLargeYearInput, setAddLargeYearInput,
        addLargeYearError, setAddLargeYearError,
        copyLargeYearSource, setCopyLargeYearSource,
        copyLargeYearConfirmOpen, setCopyLargeYearConfirmOpen,
        deleteLargeYearConfirmOpen, setDeleteLargeYearConfirmOpen,
        usersRefreshKey, setUsersRefreshKey,
        handleAddLargeYear,
        handleCopyLargeYear,
        handleDeleteLargeYear,
    } = useLargeUserYears({
        isUsersSubStage: (activeStage === "Business case" || activeStage === "Design") && activeSubStage === "Users (B8)",
        activeStageInstance,
        activeOptionId,
        projectClass,
        isLargeUsersNZ: projectClass === "LARGE" && !!(projectGridCtx?.jurisdiction?.toLowerCase().includes("new zealand")),
        opsStartYear,
        projectId: projectId || null,
    });

    const {
        deleteTarget, setDeleteTarget,
        uploadTarget, setUploadTarget,
        onCellChange,
        onRowPatch,
        doDeleteRow,
        renderEditor,
        handleSaveNewRow,
        parseFile,
        validateUpload,
        onUploadSuccess,
    } = useRowOperations({
        activeStageInstance,
        projectId,
        activeOptionId,
        activePeriod,
        constructionStartDate,
        constructionEndDate,
        opsStartYear,
        operationalLifeYears,
        user,
        fugitiveList,
        tableRows,
        getRows,
        updateRows,
        setErrorForKey,
        resolveMetricId,
        apiRowToUiRow,
        computeEmissionsForRow,
        getCalcConfig,
        refreshOptionTotals,
        recalcElectricitySiblings,
    });

    useEffect(() => {
        if ((activeStage !== "Construction" && activeStage !== "Recurring") || !activeStageInstance) return;
        let ignore = false;
        (async () => {
            try {
                const periods = await ConstructionPeriodsService.listPeriods(activeStageInstance.id);
                if (!ignore) {
                    const list = Array.isArray(periods) ? periods : [];
                    setConstructionPeriods(list);
                    if (list.length > 0) {
                        const isValidId = list.some((p) => p.id === selectedConstructionMonth);
                        if (!isValidId) {
                            const current = list.find((p) => p.status !== "approved") ?? list[list.length - 1];
                            setSelectedConstructionMonth(current.id);
                        }
                    }
                }
            } catch (e) {
                console.error("Failed to fetch construction periods", e);
            }
        })();
        return () => {
            ignore = true;
        };
    }, [activeStage, activeStageInstance]);


    useEffect(() => {
        if ((activeStage !== "Construction" && activeStage !== "Recurring") || !activeStageInstance || !selectedConstructionMonth) {
            return;
        }

        // ── RECURRING stage: load recurringG3 rows, one per boundary ─────────
        if (activeStage === "Recurring") {
            updateRows("recurringG3", []);
            let ignore = false;
            (async () => {
                try {
                    const rawRec = await ActivityDataService.fetchRows(
                        activeStageInstance.id, "recurringG3", undefined, selectedConstructionMonth
                    );
                    if (ignore) return;
                    const mapped = (Array.isArray(rawRec) ? rawRec : []).map(apiRowToUiRow);
                    const byBoundary: Record<string, boolean> = {};
                    for (const r of mapped) {
                        const bid = r.reporting_boundary_id ?? r.extra_fields?.reporting_boundary_id;
                        if (bid) byBoundary[bid] = true;
                    }
                    const placeholders = await Promise.all(
                        reportingBoundaries
                            .filter((b) => !byBoundary[b.id])
                            .map(async (b) => {
                                const normalize = (s: string) => s?.trim().toLowerCase() ?? "";
                                const matchByName = (raw: string, list: any[]) =>
                                    list.find((x) => normalize(x.name ?? x.label ?? "") === normalize(raw));
                                try {
                                    const cats = await LookupsService.fetchBgmCategories(GRADE34_IDS, projectId);
                                    const catObj = matchByName(b.category, cats);
                                    const catId = catObj?.id ?? catObj?.value ?? null;
                                    let subId: string | null = null;
                                    if (catId) {
                                        const subs = await LookupsService.fetchBgmSubcategories(GRADE34_IDS, catId, projectId);
                                        const subObj = matchByName(b.sub_category, subs);
                                        subId = subObj?.id ?? subObj?.value ?? null;
                                    }
                                    let sourceId: string | null = null;
                                    if (subId && b.source) {
                                        const srcs = await LookupsService.fetchBgmSources(GRADE34_IDS, subId, projectId);
                                        const srcObj = matchByName(b.source, srcs);
                                        sourceId = srcObj?.id ?? srcObj?.value ?? null;
                                    }
                                    return {
                                        id: `__BOUNDARY_${b.id}__`,
                                        _fromBoundary: true,
                                        reporting_boundary_id: b.id,
                                        emissions_category: b.category,
                                        emissions_subcategory: b.sub_category,
                                        emissions_source_name: b.source ?? "",
                                        emissions_category_id: catId,
                                        emissions_subcategory_id: subId,
                                        emissions_source: sourceId,
                                        unit_code: null,
                                        unit_id: null,
                                        quantity: null,
                                        emissions_tco2e: null,
                                        total_emissions_tco2e: null,
                                    };
                                } catch {
                                    return {
                                        id: `__BOUNDARY_${b.id}__`,
                                        _fromBoundary: true,
                                        reporting_boundary_id: b.id,
                                        emissions_category: b.category,
                                        emissions_subcategory: b.sub_category,
                                        emissions_source_name: b.source ?? "",
                                        emissions_category_id: null,
                                        emissions_subcategory_id: null,
                                        emissions_source: null,
                                        unit_code: null,
                                        unit_id: null,
                                        quantity: null,
                                        emissions_tco2e: null,
                                        total_emissions_tco2e: null,
                                    };
                                }
                            })
                    );
                    if (!ignore) updateRows("recurringG3", [...mapped, ...placeholders]);
                } catch (e) {
                    console.error("Failed to load recurringG3 rows:", e);
                }
            })();
            return () => { ignore = true; };
        }

        if (projectClass === "LARGE" && activeSubStage !== "Construction") {
            let ignore = false;
            (async () => {
                try {
                    if (activeSubStage === "Use (B1)") {
                        updateRows("useB1G2", []);
                        updateRows("useB1G3", []);
                        const [rawG2, rawG3]: [any, any] = await Promise.all([
                            ActivityDataService.fetchRows(activeStageInstance.id, "useB1G2", undefined, selectedConstructionMonth),
                            ActivityDataService.fetchRows(activeStageInstance.id, "useB1G3", undefined, selectedConstructionMonth),
                        ]);
                        if (!ignore) {
                            // setUseB1G2Rows((Array.isArray(rawG2) ? rawG2 : []).map(apiRowToUiRow));
                            const g2Rows = (Array.isArray(rawG2) ? rawG2 : []).map(apiRowToUiRow);
                            updateRows("useB1G2", g2Rows);
                            if (g2Rows.some(r => r.emissions_tco2e == null)) {
                                recalcAndPersistRows("useB1G2", g2Rows, (u) => updateRows("useB1G2", u));
                            }
                            // setUseB1G3Rows((Array.isArray(rawG3) ? rawG3 : []).map(apiRowToUiRow));
                            const g3Rows = (Array.isArray(rawG3) ? rawG3 : []).map(apiRowToUiRow);
                            updateRows("useB1G3", g3Rows);
                            if (g3Rows.some(r => r.emissions_tco2e == null)) {
                                recalcAndPersistRows("useB1G3", g3Rows, (u) => updateRows("useB1G3", u));
                            }
                        }
                    } else if (activeSubStage === REPLACEMENT_LABEL || activeSubStage === REPLACEMENT_LABEL_LARGE) {
                        updateRows("componentRepl", []);
                        updateRows("refurbishment", []);
                        updateRows("replDetailed", []);
                        const [rawComp, rawRefurb, rawReplDetailed]: [any, any, any] = await Promise.all([
                            ActivityDataService.fetchRows(activeStageInstance.id, "componentRepl", undefined, selectedConstructionMonth),
                            ActivityDataService.fetchRows(activeStageInstance.id, "refurbishment", undefined, selectedConstructionMonth),
                            ActivityDataService.fetchRows(activeStageInstance.id, "replDetailed", undefined, selectedConstructionMonth),
                        ]);
                        if (!ignore) {
                            updateRows("componentRepl", (Array.isArray(rawComp) ? rawComp : []).map(apiRowToUiRow));
                            updateRows("refurbishment", (Array.isArray(rawRefurb) ? rawRefurb : []).map(apiRowToUiRow));
                            updateRows("replDetailed", (Array.isArray(rawReplDetailed) ? rawReplDetailed : []).map(apiRowToUiRow));
                        }
                    } else if (activeSubStage === "Operational energy (B6) and Water (B7)") {
                        updateRows("opEnergy", []);
                        updateRows("opEnergyDetailed", []);
                        updateRows("opEnergyElectricity", []);
                        const [rawOp, rawOpDetailed, rawOpElec]: [any, any, any] = await Promise.all([
                            ActivityDataService.fetchRows(activeStageInstance.id, "opEnergy", undefined, selectedConstructionMonth),
                            ActivityDataService.fetchRows(activeStageInstance.id, "opEnergyDetailed", undefined, selectedConstructionMonth),
                            ActivityDataService.fetchRows(activeStageInstance.id, "opEnergyElectricity", undefined, selectedConstructionMonth),
                        ]);
                        if (!ignore) {
                            updateRows("opEnergy", (Array.isArray(rawOp) ? rawOp : []).map(apiRowToUiRow));
                            updateRows("opEnergyDetailed", (Array.isArray(rawOpDetailed) ? rawOpDetailed : []).map(apiRowToUiRow));
                            const opElecRows = (Array.isArray(rawOpElec) ? rawOpElec : []).map(apiRowToUiRow);
                            updateRows("opEnergyElectricity", opElecRows);

                            if (opElecRows.some((r) => r.emissions_tco2e == null)) {
                                recalcAndPersistRows(
                                    "opEnergyElectricity",
                                    opElecRows,
                                    (u) => updateRows("opEnergyElectricity", u)
                                );
                            }
                            // setOpEnergyElectricityRows((Array.isArray(rawOpElec) ? rawOpElec : []).map(apiRowToUiRow));
                        }
                    }
                } catch (e) {
                    console.error("Failed to fetch construction operations data for period", e);
                }
            })();
            return () => { ignore = true; };
        }
		
        updateRows("constructionG2", []);
        updateRows("constructionG3", []);
        updateRows("electricity", []);
        let ignore = false;
        (async () => {
            try {
                const [rawG2, rawG3, rawElectricity] = await Promise.all([
                    ActivityDataService.fetchRows(activeStageInstance.id, "constructionG2", undefined, selectedConstructionMonth),
                    ActivityDataService.fetchRows(activeStageInstance.id, "constructionG3", undefined, selectedConstructionMonth),
                    ActivityDataService.fetchRows(activeStageInstance.id, "electricity", undefined, selectedConstructionMonth),
                ]);
                if (!ignore) {
                    const g2 = (Array.isArray(rawG2) ? rawG2 : []).map(apiRowToUiRow);
                    const constrBoundsG2 = reportingBoundaries.filter((b) => b.stage_or_activity === "Construction");
                    const unresolvedG2 = constrBoundsG2.filter((b) => !g2.some((r) => r.extra_fields?.reporting_boundary_id === b.id));
                    const g2BoundaryPlaceholders = await Promise.all(
                        unresolvedG2.map(async (b) => {
                            const ids = await resolveBoundaryComponentIds(b);
                            return {
                                id: `__BOUNDARY_${b.id}__`,
                                _fromBoundary: true,
                                emissions_category: b.category,
                                emissions_subcategory: b.sub_category,
                                emissions_source_name: b.source ?? "",
                                emissions_category_id: ids.emissions_category_id,
                                emissions_subcategory_id: ids.emissions_subcategory_id,
                                emissions_source: ids.emissions_source,
                                unit_code: null,
                                unit_id: null,
                                quantity: null,
                                emissions_tco2e: null,
                            };
                        })
                    );
                    updateRows("constructionG2", [...g2, ...g2BoundaryPlaceholders]);
                    updateRows("constructionG3", (Array.isArray(rawG3) ? rawG3 : []).map(apiRowToUiRow));
                    const elecRows = (Array.isArray(rawElectricity) ? rawElectricity : []).map(apiRowToUiRow);
                    updateRows("electricity", elecRows);

                    // Auto-recalculate if values are "-", null, or otherwise not a valid number
                    const invalidElec = elecRows.filter((r) =>
                        !r.location_based_tco2e || r.location_based_tco2e === "-" || Number.isNaN(Number(r.location_based_tco2e))
                    );
                    if (invalidElec.length > 0) {
                        recalcAndPersistRows("electricity", invalidElec, (u) => updateRows("electricity", u));
                    }
                    // setElectricityRows((Array.isArray(rawElectricity) ? rawElectricity : []).map(apiRowToUiRow));
                }
            } catch (e) {
                console.error("Failed to fetch construction data for period", e);
            }
        })();
        return () => { ignore = true; };
}, [activeStage, activeStageInstance, selectedConstructionMonth, activeSubStage, projectClass]);


    // Load concrete register rows (simplified + detailed) from activity_data
    // Uses a separate effect so sub-stage changes don't wipe concrete rows.
    useEffect(() => {
        const needsConcrete =
            projectClass === "LARGE" &&
            (activeStage === "Design" || activeStage === "Business case" || activeStage === "Construction");
        updateRows("concreteRegSimplified", []);
        updateRows("concreteRegDetailed", []);
        if (!needsConcrete || !activeStageInstance) return;
        if ((activeStage === "Design" || activeStage === "Business case") && activeOptionId === null) return;
        let ignore = false;
        (async () => {
            try {
                const [rawSimp, rawDet] = await Promise.all([
                    ActivityDataService.fetchRows(activeStageInstance.id, "concreteRegSimplified", activeOptionId ?? undefined),
                    ActivityDataService.fetchRows(activeStageInstance.id, "concreteRegDetailed", activeOptionId ?? undefined),
                ]);
                if (ignore) return;
                const simpRows = (Array.isArray(rawSimp) ? rawSimp : []).map(apiRowToUiRow);
                const detRows = (Array.isArray(rawDet) ? rawDet : []).map(apiRowToUiRow);
                updateRows("concreteRegSimplified", simpRows);
                updateRows("concreteRegDetailed", detRows);
                if (simpRows.some(r => r.emissions_tco2e == null))
                    recalcAndPersistRows("concreteRegSimplified", simpRows, u => updateRows("concreteRegSimplified", u));
                if (detRows.some(r => r.emissions_tco2e == null))
                    recalcAndPersistRows("concreteRegDetailed", detRows, u => updateRows("concreteRegDetailed", u));
            } catch (e) {
                console.error("Failed to load concrete register:", e);
            }
        })();
        return () => { ignore = true; };
    }, [projectClass, activeStage, activeStageInstance, activeOptionId, apiRowToUiRow, recalcAndPersistRows]);

    useEffect(() => {					 
        if (activeSubStage !== "Use (B1)" || projectClass !== "LARGE") return;
        let ignore = false;
        (async () => {
            try {
                const datasetRevisionId = projectId
                    ? await LookupsService.resolveProjectDatasetRevisionId(projectId)
                    : null;
                if (!datasetRevisionId) {
                    if (!ignore) setFugitiveList([]);
                    return;
                }
                const res = await http.get("/api/fugitives", {
                    params: { limit: 500, dataset_revision_id: datasetRevisionId, global_only: false },
                });
                if (!ignore) setFugitiveList(Array.isArray(res.data) ? res.data : []);
            } catch (e) {
                console.warn("Failed to load fugitive list:", e);
            }
        })();
        return () => { ignore = true; };
    }, [activeSubStage, projectClass, projectId]);

    const onOptionsChange = useCallback(async () => {
        if (!activeStageInstance) return;
        try {
            const opts = await ProjectOptionsService.fetchOptions(activeStageInstance.id);
            setProjectOptions(prev => {
                const others = prev.filter((o) => o.stage_instance_id !== activeStageInstance.id);
                return [...others, ...opts];
            });
            // Drop the manual override if the option it pointed to no longer exists.
            setSelectedOptionByStage((prev) => {
                const sid = activeStageInstance.id;
                if (!prev[sid] || opts.some((o) => o.id === prev[sid])) return prev;
                const { [sid]: _removed, ...rest } = prev;
                return rest;
            });
        } catch (e) {
            console.warn("Failed to refresh options:", e);
        }
    }, [activeStageInstance]);


    const stageEnumMap: Record<string, string> = {
        "Business case": "BUSINESS_CASE",
        "Design": "DESIGN",
        "Construction": "CONSTRUCTION",
        "Recurring": "RECURRING",
    };
    const currentStageEnum = stageEnumMap[activeStage];
    const isCurrentStageLocked = !!(currentStageEnum && lockedStages.has(currentStageEnum));
    const isUsersSubStage = (activeStage === "Business case" || activeStage === "Design") && activeSubStage === "Users (B8)";

    const status = activeOption?.approval_status ?? 'draft';
    const isSubmitted = (activeStage === "Construction" || activeStage === "Recurring")
        ? activePeriod?.status === "awaiting_approval"
        : status === 'submitted';

    const isApproved = (activeStage === "Construction" || activeStage === "Recurring")
        ? activePeriod?.status === "approved"
        : status === 'final_approved';

    const isRejected = (activeStage === "Construction" || activeStage === "Recurring")
        ? activePeriod?.status === "rejected"
        : status === 'rejected';

    const isReopenRequested = (activeStage === "Construction" || activeStage === "Recurring")
        ? activePeriod?.status === "reopen_requested"
        : status === 'pending_reopen';
    // For Construction/Recurring, read-only is driven by the active period's status, not the project option.
    const isConstructionPeriodReadOnly =
        activePeriod?.status === "awaiting_approval" ||
        activePeriod?.status === "approved" ||
        activePeriod?.status === "reopen_requested";
    const statusBasedReadOnly = (activeStage === "Construction" || activeStage === "Recurring")
        ? isConstructionPeriodReadOnly
        : (isSubmitted || isApproved || isReopenRequested);
    const adminViewOnly = isProjAdmin && !isProjEditor;
    // Business Case / Design tables stay read-only until this stage's own project_options
    // have loaded, so a save can never fire with another stage's option id.
    const isOptionsReadyForStage =
        activeStage !== "Business case" && activeStage !== "Design"
            ? true
            : !!activeStageInstance && currentReportSubOptions.length > 0;
    const isReadOnly =
        !canEditActiveStage ||
        adminViewOnly ||
        statusBasedReadOnly ||
        projectClosed ||
        !isOptionsReadyForStage;


    const isUsersReadOnly = isReadOnly;

    const reopenReasonText = activeOption?.current_justification ?? "";

    const isLastSubStage = useMemo(() => {
        return subStages[subStages.length - 1] === activeSubStage;
    }, [subStages, activeSubStage]);


    const isConstructionStage = activeStage === "Construction";
    const isRecurringStage = activeStage === "Recurring";
    const isBusinessCaseStage = activeStage === "Business case";
    const isDesignStage = activeStage === "Design";
    const isBcOrDesignStage = isBusinessCaseStage || isDesignStage;
    const isLargeProject = projectClass === "LARGE";
    const mitigationsTabEnabled = canShowMitigations(
        activeStage,
        projectClass,
        activeStageAccess,
    );
    const completenessEnabled = canShowCompleteness(
        activeStage,
        projectClass,
        projectGridCtx?.jurisdiction,
        activeStageAccess,
    );
    const completenessSubmissionStage =
        completenessEnabled &&
        (isBusinessCaseStage || isDesignStage || isConstructionStage);
    const isSubStageConstruction = activeSubStage === "Construction";
    const isSubStageUseB1 = activeSubStage === "Use (B1)";
    const isSubStageReplacement = activeSubStage === REPLACEMENT_LABEL || activeSubStage === REPLACEMENT_LABEL_LARGE;
    const isSubStageOpEnergy = activeSubStage === "Operational energy (B6)";
    const isSubStageOpEnergyW = activeSubStage === "Operational energy (B6) and Water (B7)";

    const shouldShowSubmit =
         !adminViewOnly &&
        !isReadOnly &&
        (completenessSubmissionStage
            ? showCompleteness
            : isLastSubStage || isConstructionStage || isRecurringStage);
    const showMitigationsNextBtn =
        mitigationsTabEnabled && isLastSubStage && !adminViewOnly && !isReadOnly;
    const showCompletenessNextBtn =
        completenessSubmissionStage &&
        !showCompleteness &&
        !showMitigations &&
        !adminViewOnly &&
        !isReadOnly &&
        !showMitigationsNextBtn &&
        (isLastSubStage || (isConstructionStage && subStages.length === 0));
    const shouldShowMitigationSubmit = !adminViewOnly && !isReadOnly;

    const goToPreviousSubStage = () => {
        const idx = subStages.indexOf(activeSubStage);
        if (idx > 0) {
            setActiveSubStage(subStages[idx - 1]);
        }
    };

    const guardedAction = async (action: "exit" | "next") => {
        // if (hasUnsavedChanges) {
        //      const isValid = await validateAllDrafts();
        //     if (!isValid) return;
        //     setPendingAction(action);
        //     setConfirmSaveOpen(true);
        //     return;
        // }

        if (action === "next") goToNextSubStage();
        if (action === "exit") {
            navigate(`/projects/${projectId}`);
        }
    };

    const handleCopyDataLoaded = useCallback(async () => {
        setCopyDataOpen(false);
        const stageName = getStageNameByValue(activeStage);
        const stageEnum = STAGE_LABEL_TO_ENUM[stageName];
        const stageInst = stageInstances.find((si: any) => si.stage === stageEnum);
        if (!stageInst || !activeOptionId) return;
        if (activeSubStage === "Construction") {
            const fetches: Promise<any>[] = [
                ActivityDataService.fetchRows(stageInst.id, "asset", activeOptionId),
                ActivityDataService.fetchRows(stageInst.id, "component", activeOptionId),
            ];
            if (projectClass === "LARGE") {
                fetches.push(
                    ActivityDataService.fetchRows(stageInst.id, "bcDetailedLevel", activeOptionId),
                    ActivityDataService.fetchRows(stageInst.id, "electricity", activeOptionId),
                );
            }
            const results = await Promise.all(fetches);
            updateRows("asset", (Array.isArray(results[0]) ? results[0] : []).map(apiRowToUiRow));
            const copiedComp = (Array.isArray(results[1]) ? results[1] : []).map(apiRowToUiRow);
            const constrBoundsCopy = reportingBoundaries.filter((b) => b.stage_or_activity === "Construction");
            const unresolvedCopy = constrBoundsCopy.filter((b) => !copiedComp.some((r) => r.extra_fields?.reporting_boundary_id === b.id));
            const compCopyPlaceholders = await Promise.all(
                unresolvedCopy.map(async (b) => {
                    const ids = await resolveBoundaryComponentIds(b);
                    return {
                        id: `__BOUNDARY_${b.id}__`,
                        _fromBoundary: true,
                        emissions_category: b.category,
                        emissions_subcategory: b.sub_category,
                        emissions_source_name: b.source ?? "",
                        emissions_category_id: ids.emissions_category_id,
                        emissions_subcategory_id: ids.emissions_subcategory_id,
                        emissions_source: ids.emissions_source,
                        unit_code: null,
                        unit_id: null,
                        quantity: null,
                        emissions_tco2e: null,
                    };
                })
            );
            updateRows("component", [...copiedComp, ...compCopyPlaceholders]);
            if (projectClass === "LARGE") {
                updateRows("bcDetailedLevel", (Array.isArray(results[2]) ? results[2] : []).map(apiRowToUiRow));
                updateRows("electricity",
                    (Array.isArray(results[3]) ? results[3] : []).map((r: any) => ({
                        _fromApi: true,
                        ...(r.extra_fields ?? {}),
                        id: r.id,
                        metric_id: r.metric_id,
                        quantity: r.quantity,
                        unit_id: r.unit_id,
                        emissions_tco2e: r.emissions_tco2e,
                        location_based_tco2e: r.extra_fields?.location_based_tco2e ?? null,
                        market_based_tco2e: r.extra_fields?.market_based_tco2e ?? null,
                    }))
                );
            }
        } else if (activeSubStage === "Use (B1)" && projectClass === "LARGE") {
            const [rawG2, rawG3] = await Promise.all([
                ActivityDataService.fetchRows(stageInst.id, "useB1G2", activeOptionId),
                ActivityDataService.fetchRows(stageInst.id, "useB1G3", activeOptionId),
            ]);
            updateRows("useB1G2", (Array.isArray(rawG2) ? rawG2 : []).map(apiRowToUiRow));
            updateRows("useB1G3", (Array.isArray(rawG3) ? rawG3 : []).map(apiRowToUiRow));
        } else if (activeSubStage === REPLACEMENT_LABEL || activeSubStage === REPLACEMENT_LABEL_LARGE) {
            const [rawComp, rawRefurb] = await Promise.all([
                ActivityDataService.fetchRows(stageInst.id, "componentRepl", activeOptionId),
                ActivityDataService.fetchRows(stageInst.id, "refurbishment", activeOptionId),
            ]);
            updateRows("componentRepl", (Array.isArray(rawComp) ? rawComp : []).map(apiRowToUiRow));
            updateRows("refurbishment", (Array.isArray(rawRefurb) ? rawRefurb : []).map(apiRowToUiRow));
        } else if (activeSubStage === "Operational energy (B6)") {
            const rawOp = await ActivityDataService.fetchRows(stageInst.id, "opEnergy", activeOptionId);
            updateRows("opEnergy", (Array.isArray(rawOp) ? rawOp : []).map(apiRowToUiRow));
        } else if (activeSubStage === "Users (B8)") {
            setUsersRefreshKey(k => k + 1);
        }
    }, [activeStage, activeSubStage, activeOptionId, stageInstances, projectClass, reportingBoundaries, updateRows, apiRowToUiRow, getStageNameByValue]);

    if (accessDenied) {
        return (
            <div className="flex h-full items-center justify-center bg-neutral-98 p-8">
                <div className="rounded border border-slate-200 bg-white p-8 text-center shadow-sm">
                    <h2 className="text-lg font-medium text-slate-800">No stage access</h2>
                    <p className="mt-2 text-sm text-slate-500">You do not have access to any active stage in this project.</p>
                    <button
                        type="button"
                        onClick={() => navigate(`/projects/${projectId}`)}
                        className="mt-5 rounded bg-primary px-4 py-2 text-sm font-medium text-white"
                    >
                        Back to project
                    </button>
                </div>
            </div>
        );
    }

    return (
        <>
            <DataEntryModals
                uploadTarget={uploadTarget}
                setUploadTarget={setUploadTarget}
                parseFile={parseFile}
                validateUpload={validateUpload}
                onUploadSuccess={onUploadSuccess}
                deleteTarget={deleteTarget}
                setDeleteTarget={setDeleteTarget}
                doDeleteRow={doDeleteRow}
                designSeedConfirmOpen={designSeedConfirmOpen}
                pendingDesignReportNum={pendingDesignReportNum}
                reDesignSeedLoading={reDesignSeedLoading}
                setDesignSeedConfirmOpen={setDesignSeedConfirmOpen}
                setPendingDesignReportNum={setPendingDesignReportNum}
                setDesignReportNum={setDesignReportNum}
                setReDesignSeedLoading={setReDesignSeedLoading}
                seedPeriodsFromDesign={seedPeriodsFromDesign}
                constructionPeriods={constructionPeriods}
                addLargeYearOpen={addLargeYearOpen}
                addLargeYearInput={addLargeYearInput}
                addLargeYearError={addLargeYearError}
                setAddLargeYearOpen={setAddLargeYearOpen}
                setAddLargeYearInput={setAddLargeYearInput}
                setAddLargeYearError={setAddLargeYearError}
                handleAddLargeYear={handleAddLargeYear}
                copyLargeYearConfirmOpen={copyLargeYearConfirmOpen}
                copyLargeYearSource={copyLargeYearSource}
                activeLargeUsersYear={activeLargeUsersYear}
                largeUsersYears={largeUsersYears}
                setCopyLargeYearConfirmOpen={setCopyLargeYearConfirmOpen}
                setCopyLargeYearSource={setCopyLargeYearSource}
                handleCopyLargeYear={handleCopyLargeYear}
                deleteLargeYearConfirmOpen={deleteLargeYearConfirmOpen}
                setDeleteLargeYearConfirmOpen={setDeleteLargeYearConfirmOpen}
                handleDeleteLargeYear={handleDeleteLargeYear}
                concreteMixModalType={concreteMixModalType}
                setConcreteMixModalType={setConcreteMixModalType}
                concreteMixEditTarget={concreteMixEditTarget}
                setConcreteMixEditTarget={setConcreteMixEditTarget}
                projectId={projectId}
                updateRows={updateRows}
                computeEmissionsForRow={computeEmissionsForRow}
                adminDecisionOpen={adminDecisionOpen}
                setAdminDecisionOpen={setAdminDecisionOpen}
                decisionComments={decisionComments}
                setDecisionComments={setDecisionComments}
                triggerAdminDecision={triggerAdminDecision}
                reopenModalOpen={reopenModalOpen}
                setReopenModalOpen={setReopenModalOpen}
                activeStage={activeStage}
                _projectName={_projectName}
                reopenJustification={reopenJustification}
                setReopenJustification={setReopenJustification}
                submitReopenRequest={submitReopenRequest}
                submitModalOpen={submitModalOpen}
                setSubmitModalOpen={setSubmitModalOpen}
                handleReportSubmission={handleReportSubmission}
                isBusinessCaseStage={isBusinessCaseStage}
                activeStageInstance={activeStageInstance}
                manageOptionsOpen={manageOptionsOpen}
                setManageOptionsOpen={setManageOptionsOpen}
                activeReportNumber={activeReportNumber}
                currentReportSubOptions={currentReportSubOptions}
                onOptionsChange={onOptionsChange}
                copyDataOpen={copyDataOpen}
                setCopyDataOpen={setCopyDataOpen}
                baseCaseOptions={baseCaseOptions}
                activeOptionId={activeOptionId}
                onCopied={handleCopyDataLoaded}
                periodWorkflowOpen={periodWorkflowOpen as any}
                setPeriodWorkflowOpen={setPeriodWorkflowOpen as any}
                activePeriod={activePeriod}
                handlePeriodWorkflowConfirm={handlePeriodWorkflowConfirm}
            />
            <div className="flex flex-col h-full overflow-hidden">

                <div className="flex flex-1 min-h-0 overflow-hidden">
                    <div className="shrink-0">
                        <LeftNavigation
                            stageType={activeStage}
                            stages={enrichedStages}
                            onSelectStage={(val: string) => {
                                if (val === "RESULTS_DASHBOARD") {
                                    navigate(`/resultsDashboard?projectId=${projectId}`, {
                                        state: {
                                            projectData,
                                        },
                                    }
                                    );
                                    return;
                                }
                                const stage = enrichedStages.find((s: any) => s.value === val);
                                if (!stage || stage.disabled) return;
                                const newStageLabel = stage.stageLabel;
                                const newReportNum = stage.reportNumber;
                                setActiveStage(newStageLabel);
                                setActiveReportNumber(newReportNum);
                                const available = SUBSTAGES_FOR(newStageLabel, projectClass);
                                setActiveSubStage(available[0] ?? "Construction");
                                setShowMitigations(false);
                                setShowCompleteness(false);
                                setShowAuditPanel(false);
                                // activeOptionId derives automatically from the new activeStage/activeReportNumber above.
                            }}
                            activeSubStage={activeSubStage}
                            onSelectSubStage={(val: string) => {
                                setShowAuditPanel(false);
                                setActiveSubStage(val);
                                setShowMitigations(false);
                                setShowCompleteness(false);
                            }}
                            showMitigations={showMitigations}
                            onSelectMitigations={() => {
                                if (!mitigationsTabEnabled) return;
                                setShowMitigations(true);
                                setShowCompleteness(false);
                                setShowAuditPanel(false);
                                setActiveSubStage("");
                            }}
                            mitigationsTabEnabled={mitigationsTabEnabled}
                            subStages={subStages.map((s) => ({ label: s, value: s }))}
                            groups={GROUPS_FOR(getStageNameByValue(activeStage), projectClass)}
                            selectedReportId={selectedConstructionMonth}
                            onSelectReport={(month: string) => setSelectedConstructionMonth(month)}
                            reportFrequency={frequency}
                            firstSubmissionMonth={firstSubmissionMonth}
                            constructionReportStates={constructionReportStates}
                            constructionPeriods={constructionPeriods}
                            projectName={isProjAdmin ? _projectName : ""}
                            activeStageInstance={activeStageInstance}
                            isStageAdmin={isProjAdmin}
                            programName={_programName}
                            activeReportNumber={activeReportNumber}
                            showCompleteness={showCompleteness}
                            onSelectCompleteness={() => {
                                if (!completenessEnabled) return;
                                setShowMitigations(false);
                                setShowCompleteness(true);
                                setActiveSubStage(COMPLETENESS_LABEL);
                            }}
                            completenessTabEnabled={completenessEnabled}

                            hasResubmissionAudit={hasResubmission}
                            onViewResubmissionAudit={() => setShowAuditPanel(true)}
                        />
                    </div>

                    <div className="flex flex-col flex-1 bg-neutral-98 min-h-0 overflow-hidden">
                        {showAuditPanel && activeStageInstance?.id ? (
                            <StageResubmissionAuditPanel
                                stageInstanceId={activeStageInstance.id}
                                projectOptionId={activeOption?.id}
                                onClose={() => setShowAuditPanel(false)}
                            />
                        ) : (
                        <><div className="border-b px-12 py-4 border-neutral-90 text-base text-text-base">
                            {activeStage}
                            {showMitigations && mitigationsTabEnabled ? (
                                <>
                                    <span className="mx-1 font-bold text-text-base">•</span>
                                    Mitigations
                                </>
                            ) : showCompleteness ? (
                                <>
                                    <span className="mx-1 font-bold text-text-base">•</span>
                                    {COMPLETENESS_LABEL}
                                </>
                            ) : (
                                (!isRecurringStage && (!isConstructionStage || (isConstructionStage && projectClass === "LARGE" && subStages.length > 0))) && (
                                    <>
                                        <span className="mx-1 font-bold text-text-base">•</span>
                                        {activeSubStage}
                                    </>
                                )
                            )}
                        </div>
                       {showMitigations && mitigationsTabEnabled && (
                            <Mitigations
                                stage={
                                    isConstructionStage ? "Construction" : "Design"
                                }
                                projectId={projectId ?? ""}
                                jurisdictionName={projectGridCtx?.jurisdiction ?? null}
                                canSubmit={shouldShowMitigationSubmit}
                                onSubmitStage={() =>
                                    isConstructionStage
                                        ? setPeriodWorkflowOpen("submit")
                                        : setSubmitModalOpen(true)
                                }
                                useCompletenessSubmissionFlow={completenessSubmissionStage}
                                onNextStage={() => {
                                    setShowMitigations(false);
                                    setActiveSubStage(COMPLETENESS_LABEL);
                                }}
                                persistence={mitigationPersistence}
                                editorLocked={isReadOnly}
                                isSubmitted={isSubmitted}
                                mitigationStageInstanceId={
                                    mitigationStageInstance?.id ?? null
                                }
                                mitigationProjectOptionId={mitigationOptionId}
                                projectTypeName={projectTypeName}
                                opsStartYear={opsStartYear}
                            />
                        )}
                        {showCompleteness && completenessEnabled && (
                            <div className="flex-1 overflow-y-auto bg-neutral-98 pb-40">
                               <Completeness
                                    projectId={projectId ?? ""}
                                    stageInstanceId={activeStageInstance?.id ?? ""}
                                    projectOptionId={activeOptionId}
                                    submissionPeriodId={
                                        activeStage === "Construction"
                                            ? selectedConstructionMonth
                                            : null
                                    }
                                    editorLocked={isReadOnly}
                                    onTotalsUpdated={refreshOptionTotals}
                                />
                            </div>
                        )}
                        {!showMitigations && !isProjAdmin && !isReopenRequested && (isApproved || isCurrentStageLocked) && (
                            <div className="flex flex-col gap-2 mx-12 mt-4 px-4 py-3 rounded bg-light-green border border-success/35 text-success text-sm">
                                <div className="flex items-center gap-2">
                                    <img src={CheckCircleGreen} alt="Approved" className="w-5 h-5" />
                                    <div className="font-bold">This report has been approved</div>
                                </div>
                                <div className="px-7">This report is read-only and can no longer be edited. You can submit a request to reopen it if you need to update it.</div>
                            </div>
                        )}

                        {!showMitigations && !isProjAdmin && isReopenRequested && !((isConstructionStage || isRecurringStage) && constructionPeriods.length > 0) && (
                            <div className="flex flex-col gap-2 mx-12 mt-4 px-4 py-3 rounded bg-info-bg border border-in-progress/35 text-in-progress text-sm">
                                <div className="flex items-center gap-2">
                                    <img src={Info} alt="Approved" className="w-5 h-5 text-in-progress" />
                                    <div className="font-bold">Reopen requested</div>
                                </div>
                                <div className="px-7">Awaiting administrator approval to reopen</div>
                            </div>
                        )}


                        {/* Status banners */}
                        {!showMitigations && !isProjAdmin && isSubmitted && <div className="m-6 p-4 bg-info-bg border border-in-progress/35 rounded text-in-progress font-medium">This report is submitted and currently under review.</div>}
                        {!showMitigations && !isProjAdmin && isRejected && (
                            <div className="flex flex-col gap-2 mx-12 mt-4 px-4 py-3 bg-red-50 border border-red-200 rounded">
                                <p className="font-bold text-danger">Submission Rejected</p>
                                <p className="text-sm text-danger">Admin Comment: {activeOption?.current_justification}</p>
                            </div>
                        )}
                        {/* 2. Reopen Justification (Display above tables for Admin) */}
                        {!showMitigations && isProjAdmin && isReopenRequested && (
                            <div className="mx-12 mt-6 p-6 bg-info-bg border border-info-border/35 rounded">
                                <h3 className="text-sm font-bold text-info-border uppercase mb-2">Request to Reopen Justification</h3>
                                <p className="text-text-base">{reopenReasonText ? `${reopenReasonText}` : "—"}</p>
                            </div>
                        )}
                        {!showMitigations && adminViewOnly && !statusBasedReadOnly && (
                            <div className="flex flex-col gap-2 mx-12 mt-4 px-4 py-3 rounded bg-info-bg border border-in-progress/35 text-in-progress text-sm">
                                <div className="flex items-center gap-2">
                                    <img src={Info} alt="Info" className="w-5 h-5" />
                                    <div className="font-bold">View-only access</div>
                                </div>
                                <div className="px-7">A submission is currently in progress. You have view-only access as a project admin. To make edits, contact your organisation admin to be assigned the Editor role.</div>
                            </div>
                        )}


                       {!showMitigations && !showCompleteness && (<div className="flex-1 overflow-y-auto bg-neutral-98 pb-40">
                            <div className="flex px-12 pt-10 pb-6 items-center justify-between">
                                {!isConstructionStage && (
                                    <div className="flex flex-col gap-0.5">
                                        {optionTotalEmissions > 0 && <div className="text-sm text-text-faint">Total Emissions
                                        </div>}
                                        {optionTotalEmissions > 0 && (
                                            <div className="text-[28px] font-bold text-text-dark leading-tight">
                                                {formatEmissionsOrQuantity(optionTotalEmissions, "en-US")}{" "}
                                                <span className="font-light">
                                                    tCO<sub>2</sub>e
                                                </span>
                                            </div>
                                        )}
                                    </div>)}
                                <div className="flex items-center gap-4">
                                    {isConstructionStage && isLargeProject && designReportNums.length > 1 && (
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm text-text-base">Design Report</span>
                                            <select
                                                className="h-9 border border-border-input rounded px-2 text-sm bg-white"
                                                value={designReportNum}
                                                disabled={isReadOnly}
                                                onChange={e => {
                                                    if (isReadOnly) return;
                                                    const num = Number(e.target.value);
                                                    if (num !== designReportNum) {
                                                        setPendingDesignReportNum(num);
                                                        setDesignSeedConfirmOpen(true);
                                                    }
                                                }}
                                            >
                                                {designReportNums.map(n => (
                                                    <option key={n} value={n}>Design Report {n}</option>
                                                ))}
                                            </select>
                                        </div>
                                    )}
                                    {isBusinessCaseStage && (
                                        <>
                                            <span className="text-sm text-text-base">Currently editing</span>
                                            <SelectListbox
                                                value={activeOptionId ?? ""}
                                                onChange={(value: any) =>
                                                    activeStageInstance &&
                                                    setSelectedOptionByStage((prev) => ({ ...prev, [activeStageInstance.id]: value }))
                                                }
                                                options={baseCaseOptions}
                                            />
                                            <div className="relative" ref={moreMenuRef}>

                                                {!isReadOnly && (
                                                    <button className="p-2 rounded hover:bg-neutral-200 cursor-pointer transition-colors"
                                                        onClick={() => setMoreMenuOpen(o => !o)}
                                                        aria-label="More options">
                                                        <span className="material-symbols-rounded">more_vert</span>
                                                    </button>
                                                )}

                                                {moreMenuOpen && (
                                                    <div className="absolute cursor-pointer right-0 mt-1 w-44 rounded-lg border border-neutral-200 bg-white shadow-lg z-30 py-1">
                                                        <button
                                                            className="w-full text-left px-4 py-2 text-sm text-text-base hover:bg-neutral-50 transition-colors"
                                                            onClick={() => { setMoreMenuOpen(false); setCopyDataOpen(true); }}
                                                        >
                                                            Copy data
                                                        </button>
                                                        <button
                                                            className="w-full text-left px-4 py-2 text-sm text-text-base hover:bg-neutral-50 transition-colors"
                                                            onClick={() => { setMoreMenuOpen(false); setManageOptionsOpen(true); }}
                                                        >
                                                            Manage options
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                            {!isConstructionStage && !isRecurringStage && <div className="text-text-base text-sm px-12 mb-4">{`Operational life of project: ${operationalLifeYears} years`}</div>}

                            {isBusinessCaseStage && isSubStageConstruction && (
                                <TableWrapper
                                    title="Asset level"
                                    tooltip="Asset level data should only be used when Component level data is not available."
                                    rows={getRows("asset")}
                                    setRows={(u) => updateRows("asset", u)}
                                    columns={assetColumns}
                                    exportFileName="AssetLevel.csv"
                                    uploadKey="asset"
                                    renderEditor={renderEditor}
                                    onRequestUpload={(key: any) => setUploadTarget(key)}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionKey="asset"
                                    accordionState={accordionState as any}
                                    setAccordionState={setAccordionState as any}
                                    error={tableErrors["asset"]}
                                    onCellChange={onCellChange("asset", (u) => updateRows("asset", u))}
                                    onRowPatch={onRowPatch("asset", (u) => updateRows("asset", u))}
                                    readOnly={isReadOnly}
                                    onCancel={() => setErrorForKey("asset", null)}
                                    onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'asset' }) : undefined}
                                />
                            )}

                            {isBcOrDesignStage && isSubStageConstruction && (
                                <TableWrapper
                                    title="Component level"
                                    rows={getRows("component")}
                                    setRows={(u) => updateRows("component", u)}
                                    columns={componentColumns}
                                    exportFileName="ComponentLevel.csv"
                                    uploadKey="component"
                                    renderEditor={renderEditor}
                                    onRequestUpload={(key: any) => setUploadTarget(key)}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionKey="component"
                                    accordionState={accordionState as any}
                                    setAccordionState={setAccordionState as any}
                                    error={tableErrors["component"]}
                                    onCellChange={onCellChange("component", (u) => updateRows("component", u))}
                                    onRowPatch={onRowPatch("component", (u) => updateRows("component", u))}
                                    readOnly={isReadOnly}
                                    onCancel={() => setErrorForKey("component", null)}
                                    onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'component' }) : undefined}
                                />
                            )}

                            {isBcOrDesignStage && isSubStageConstruction && isLargeProject && (
                                <TableWrapper
                                    title="Detailed level (Grade 3)"
                                    rows={getRows("bcDetailedLevel")}
                                    setRows={(u) => updateRows("bcDetailedLevel", u)}
                                    columns={bcDetailedColumns}
                                    exportFileName="DetailedLevel.csv"
                                    uploadKey="bcDetailedLevel"
                                    renderEditor={renderEditor}
                                    onRequestUpload={(key: any) => setUploadTarget(key)}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionKey="bcDetailedLevel"
                                    accordionState={accordionState as any}
                                    setAccordionState={setAccordionState as any}
                                    error={tableErrors["bcDetailedLevel"]}
                                    onCellChange={onCellChange("bcDetailedLevel", (u) => updateRows("bcDetailedLevel", u))}
                                    onRowPatch={onRowPatch("bcDetailedLevel", (u) => updateRows("bcDetailedLevel", u))}
                                    onCancel={() => setErrorForKey("bcDetailedLevel", null)}
                                    onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'bcDetailedLevel' }) : undefined}
                                    readOnly={isReadOnly}
                                />
                            )}

                            {isBcOrDesignStage && isSubStageConstruction && isLargeProject && (
                                <TableWrapper
                                    title="Electricity"
                                    rows={getRows("electricity")}
                                    setRows={(u) => updateRows("electricity", u)}
                                    columns={electricityColumns}
                                    exportFileName="Electricity.csv"
                                    uploadKey="electricity"
                                    renderEditor={renderEditor}
                                    onRequestUpload={(key: any) => setUploadTarget(key)}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionKey="electricity"
                                    accordionState={accordionState as any}
                                    setAccordionState={setAccordionState as any}
                                    error={tableErrors["electricity"]}
                                    onCellChange={onCellChange("electricity", (u) => updateRows("electricity", u))}
                                    onRowPatch={onRowPatch("electricity", (u) => updateRows("electricity", u))}
                                    onCancel={() => setErrorForKey("electricity", null)}
                                    onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'electricity' }) : undefined}
                                    readOnly={isReadOnly}
                                />
                            )}

                            {isBcOrDesignStage && isSubStageReplacement && (
                                <>
                                    <TableWrapper
                                        title="Component level replacement"
                                        tooltip="Component level data will be visible when component level data under construction is available."
                                        rows={getRows("componentRepl")}
                                        setRows={(u) => updateRows("componentRepl", u)}
                                        columns={componentReplColumns}
                                        exportFileName="ComponentLevel.csv"
                                        uploadKey="componentRepl"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="componentRepl"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["componentRepl"]}
                                        onCellChange={onCellChange("componentRepl", (u) => updateRows("componentRepl", u))}
                                        onRowPatch={onRowPatch("componentRepl", (u) => updateRows("componentRepl", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("componentRepl", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'componentRepl' }) : undefined}
                                    />
                                    <TableWrapper
                                        title="Other partial replacement or refurbishment activities"
                                        rows={getRows("refurbishment")}
                                        setRows={(u) => updateRows("refurbishment", u)}
                                        columns={refurbColumns}
                                        exportFileName="Replacement and Refurbishment.csv"
                                        uploadKey="refurbishment"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="refurbishment"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["refurbishment"]}
                                        onCellChange={onCellChange("refurbishment", (u) => updateRows("refurbishment", u))}
                                        onRowPatch={onRowPatch("refurbishment", (u) => updateRows("refurbishment", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("refurbishment", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'refurbishment' }) : undefined}
                                    />
                                     {isLargeProject && (
                                        <TableWrapper
                                        title="Detailed Level (Grade 3)"
                                        rows={getRows("replDetailed")}
                                        setRows={(u) => updateRows("replDetailed", u)}
                                        columns={replDetailedColumns}
                                        exportFileName="DetailedLevel-replacement.csv"
                                        uploadKey="replDetailed"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="replDetailed"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["replDetailed"]}
                                        onCellChange={onCellChange("replDetailed", (u) => updateRows("replDetailed", u))}
                                        onRowPatch={onRowPatch("replDetailed", (u) => updateRows("replDetailed", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("replDetailed", null)}
                                        onDeleteRow={!isReadOnly ? (id: any) => setDeleteTarget({ id: id as string, tableKey: 'replDetailed' }) : undefined}
                                    />
                                     )}
                                </>
                            )}
                            {isBcOrDesignStage && isSubStageOpEnergy && (
                                <>
                                <TableWrapper
                                    title="Component level (grade 2)"
                                    rows={getRows("opEnergy")}
                                    setRows={(u) => updateRows("opEnergy", u)}
                                    columns={opEnergyColumns}
                                    exportFileName="OperationalEnergy.csv"
                                    uploadKey="opEnergy"
                                    renderEditor={renderEditor}
                                    onRequestUpload={(key: any) => setUploadTarget(key)}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionKey="opEnergy"
                                    accordionState={accordionState as any}
                                    setAccordionState={setAccordionState as any}
                                    error={tableErrors["opEnergy"]}
                                    onCellChange={onCellChange("opEnergy", (u) => updateRows("opEnergy", u))}
                                    onRowPatch={onRowPatch("opEnergy", (u) => updateRows("opEnergy", u))}
                                    readOnly={isReadOnly}
                                    onCancel={() => setErrorForKey("opEnergy", null)}
                                    onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'opEnergy' }) : undefined}
                                />
                                {isLargeProject && (
                                    <>
                                     <TableWrapper
                                        title="Detailed Level (Grade 3)"
                                        rows={getRows("opEnergyDetailed")}
                                        setRows={(u) => updateRows("opEnergyDetailed", u)}
                                        columns={opEnergyDetailedColumns}
                                        exportFileName="OperationalEnergy_DetailedLevel.csv"
                                        uploadKey="opEnergyDetailed"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="opEnergyDetailed"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["opEnergyDetailed"]}
                                        onCellChange={onCellChange("opEnergyDetailed", (u) => updateRows("opEnergyDetailed", u))}
                                        onRowPatch={onRowPatch("opEnergyDetailed", (u) => updateRows("opEnergyDetailed", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("opEnergyDetailed", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: "opEnergyDetailed" }) : undefined}
                                    />
                                    <TableWrapper
                                        title="Electricity"
                                        rows={getRows("opEnergyElectricity")}
                                        setRows={(u) => updateRows("opEnergyElectricity", u)}
                                        columns={opEnergyElectricityColumns}
                                        exportFileName="OperationalEnergy_Electricity.csv"
                                        uploadKey="opEnergyElectricity"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="opEnergyElectricity"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["opEnergyElectricity"]}
                                        onCellChange={onCellChange("opEnergyElectricity", (u) => updateRows("opEnergyElectricity", u))}
                                        onRowPatch={onRowPatch("opEnergyElectricity", (u) => updateRows("opEnergyElectricity", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("opEnergyElectricity", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: "opEnergyElectricity" }) : undefined}
                                    />
                                    </>
                                )}
                                </>
                            )}

                            {isUsersSubStage && activeStageInstance && (
                                <UsersSubStage
                                    stageInstanceId={activeStageInstance.id}
                                    projectId={projectId ?? ""}
                                    optionId={activeOptionId ?? null}
                                    refreshKey={usersRefreshKey}
                                    readOnly={isUsersReadOnly}
                                    jurisdiction={projectGridCtx?.jurisdiction ?? null}
                                    projectClass={projectClass}
                                    projectTypeName={projectTypeName}
                                    opsStartYear={opsStartYear}
                                    activeLargeUsersYear={activeLargeUsersYear}
                                    largeUsersYears={largeUsersYears}
                                    onActiveLargeUsersYearChange={setActiveLargeUsersYear}
                                    onOpenAddLargeYear={() => setAddLargeYearOpen(true)}
                                    onOpenCopyLargeYear={() => setCopyLargeYearConfirmOpen(true)}
                                    onOpenDeleteLargeYear={() => setDeleteLargeYearConfirmOpen(true)}
                                    onTotalsUpdated={refreshOptionTotals}
                                />
                            )}

                            {isConstructionStage && (
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white p-5 mb-6 mx-12 rounded-[var(--radius-3)] shadow-sm">
                                    <div className="pb-6">
                                        <div className="text-sm text-text-faint mb-1">Total emissions reported</div>
                                        <div className="text-[28px] font-bold text-text-dark">
                                            {activePeriod?.all_periods_emissions_tco2e != null
                                                ? formatEmissionsOrQuantity(parseFloat(activePeriod.all_periods_emissions_tco2e))
                                                : "—"}{" "}
                                            <span className="text-[28px] font-light text-text-dark">
                                                tCO<sub>2</sub>e
                                            </span>
                                        </div>
                                    </div>
                                    <div className="pb-6">
                                        <div className="text-sm text-text-faint mb-1">Emissions this period</div>
                                        <div className="text-[28px] font-bold text-text-dark">
                                            {activePeriod?.period_emissions_tco2e != null
                                                ? formatEmissionsOrQuantity(parseFloat(activePeriod.period_emissions_tco2e))
                                                : "—"}{" "}
                                            <span className="text-[28px] font-light text-text-dark">
                                                tCO<sub>2</sub>e
                                            </span>
                                        </div>
                                    </div>
                                    <div className=" pb-6 md:border-x md:border-neutral-90 md:px-6">
                                        <div className="text-sm text-text-faint mb-1">Emissions last period</div>
                                        <div className="text-[28px] font-bold text-text-dark">
                                            {activePeriod?.previous_period_emissions_tco2e != null
                                                ? formatEmissionsOrQuantity(parseFloat(activePeriod.previous_period_emissions_tco2e))
                                                : "—"}{" "}
                                            <span className="text-[28px] font-light text-text-dark">
                                                tCO<sub>2</sub>e
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {(isBcOrDesignStage || isConstructionStage) && isLargeProject && isSubStageUseB1 && (
                                <>
                                    <TableWrapper
                                        title="Component Level (Grade 2)"
                                        rows={getRows("useB1G2")}
                                        setRows={(u) => updateRows("useB1G2", u)}
                                        columns={useB1G2Columns}
                                        exportFileName="UseB1_ComponentLevel.csv"
                                        uploadKey="useB1G2"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="useB1G2"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["useB1G2"]}
                                        onCellChange={onCellChange("useB1G2", (u) => updateRows("useB1G2", u))}
                                        onRowPatch={onRowPatch("useB1G2", (u) => updateRows("useB1G2", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("useB1G2", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: "useB1G2" }) : undefined}
                                        isConstructionStage={activeStage === "Construction"}
                                    />
                                    <TableWrapper
                                        title="Detailed Level (Grade 3)"
                                        rows={getRows("useB1G3")}
                                        setRows={(u) => updateRows("useB1G3", u)}
                                        columns={useB1G3Columns}
                                        exportFileName="UseB1_DetailedLevel.csv"
                                        uploadKey="useB1G3"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="useB1G3"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["useB1G3"]}
                                        onCellChange={onCellChange("useB1G3", (u) => updateRows("useB1G3", u))}
                                        onRowPatch={onRowPatch("useB1G3", (u) => updateRows("useB1G3", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("useB1G3", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: "useB1G3" }) : undefined}
                                        isConstructionStage={activeStage === "Construction"}
                                    />
                                </>
                            )}
                            {isConstructionStage && isLargeProject && isSubStageReplacement && (
                                <>
                                    <TableWrapper
                                        title="Component level replacement"
                                        rows={getRows("componentRepl")}
                                        setRows={(u) => updateRows("componentRepl", u)}
                                        columns={componentReplColumns}
                                        exportFileName="ComponentLevel.csv"
                                        uploadKey="componentRepl"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="componentRepl"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["componentRepl"]}
                                        onCellChange={onCellChange("componentRepl", (u) => updateRows("componentRepl", u))}
                                        onRowPatch={onRowPatch("componentRepl", (u) => updateRows("componentRepl", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("componentRepl", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: "componentRepl" }) : undefined}
                                        isConstructionStage={activeStage === "Construction"}
                                    />
                                    <TableWrapper
                                        title="Other partial replacement or refurbishment activities"
                                        rows={getRows("refurbishment")}
                                        setRows={(u) => updateRows("refurbishment", u)}
                                        columns={refurbColumns}
                                        exportFileName="Replacement and Refurbishment.csv"
                                        uploadKey="refurbishment"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="refurbishment"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["refurbishment"]}
                                        onCellChange={onCellChange("refurbishment", (u) => updateRows("refurbishment", u))}
                                        onRowPatch={onRowPatch("refurbishment", (u) => updateRows("refurbishment", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("refurbishment", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: "refurbishment" }) : undefined}
                                        isConstructionStage={activeStage === "Construction"}
                                    />
                                    <TableWrapper
                                        title="Detailed Level (Grade 3)"
                                        rows={getRows("replDetailed")}
                                        setRows={(u) => updateRows("replDetailed", u)}
                                        columns={replDetailedColumns}
                                        exportFileName="DetailedLevel-replacement.csv"
                                        uploadKey="replDetailed"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="replDetailed"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["replDetailed"]}
                                        onCellChange={onCellChange("replDetailed", (u) => updateRows("replDetailed", u))}
                                        onRowPatch={onRowPatch("replDetailed", (u) => updateRows("replDetailed", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("replDetailed", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'replDetailed' }) : undefined}
                                        isConstructionStage={activeStage === "Construction"}
                                    />
                                </>
                            )}
                            
                            {isConstructionStage && isLargeProject && isSubStageOpEnergyW && (
                                <>
                                    <TableWrapper
                                        title="Component Level (Grade 2)"
                                        rows={getRows("opEnergy")}
                                        setRows={(u) => updateRows("opEnergy", u)}
                                        columns={opEnergyColumns}
                                        exportFileName="OperationalEnergy_ComponentLevel.csv"
                                        uploadKey="opEnergy"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="opEnergy"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["opEnergy"]}
                                        onCellChange={onCellChange("opEnergy", (u) => updateRows("opEnergy", u))}
                                        onRowPatch={onRowPatch("opEnergy", (u) => updateRows("opEnergy", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("opEnergy", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: "opEnergy" }) : undefined}
                                        isConstructionStage={activeStage === "Construction"}
                                    />
                                    <TableWrapper
                                        title="Detailed Level (Grade 3)"
                                        rows={getRows("opEnergyDetailed")}
                                        setRows={(u) => updateRows("opEnergyDetailed", u)}
                                        columns={opEnergyDetailedColumns}
                                        exportFileName="OperationalEnergy_DetailedLevel.csv"
                                        uploadKey="opEnergyDetailed"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="opEnergyDetailed"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["opEnergyDetailed"]}
                                        onCellChange={onCellChange("opEnergyDetailed", (u) => updateRows("opEnergyDetailed", u))}
                                        onRowPatch={onRowPatch("opEnergyDetailed", (u) => updateRows("opEnergyDetailed", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("opEnergyDetailed", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: "opEnergyDetailed" }) : undefined}
                                        isConstructionStage={activeStage === "Construction"}
                                    />
                                    <TableWrapper
                                        title="Electricity"
                                        rows={getRows("opEnergyElectricity")}
                                        setRows={(u) => updateRows("opEnergyElectricity", u)}
                                        columns={opEnergyElectricityColumns}
                                        exportFileName="OperationalEnergy_Electricity.csv"
                                        uploadKey="opEnergyElectricity"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="opEnergyElectricity"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["opEnergyElectricity"]}
                                        onCellChange={onCellChange("opEnergyElectricity", (u) => updateRows("opEnergyElectricity", u))}
                                        onRowPatch={onRowPatch("opEnergyElectricity", (u) => updateRows("opEnergyElectricity", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("opEnergyElectricity", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: "opEnergyElectricity" }) : undefined}
                                        isConstructionStage={activeStage === "Construction"}
                                    />
                                </>
                            )}

                            {isConstructionStage && isSubStageConstruction && (
                                <>
                                    {/* <TableWrapper
                                        title="Component level"
                                        rows={getRows("component")}
                                        setRows={(u) => updateRows("component", u)}
                                        columns={componentColumns}
                                        exportFileName="ConstructionG2Data.csv"
                                        uploadKey="component"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="component"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["component"]}
                                        onCellChange={onCellChange("component", (u) => updateRows("component", u))}
                                        onRowPatch={onRowPatch("component", (u) => updateRows("component", u))}
                                        readOnly={isReadOnly}
                                        // readOnly={activePeriod === null || activePeriod.status !== "in_progress"}
                                        onDeleteRow={!(activePeriod === null || activePeriod.status !== "in_progress") ? (id) => setDeleteTarget({ id: id as string, tableKey: 'component' }) : undefined}
                                    /> */}
                                    <TableWrapper
                                        title="Component level"
                                        rows={getRows("constructionG2")}
                                        setRows={(u) => updateRows("constructionG2", u)}
                                        columns={constructionG2Columns}
                                        exportFileName="ConstructionG2Data.csv"
                                        uploadKey="constructionG2"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="constructionG2"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["constructionG2"]}
                                        onCellChange={onCellChange("constructionG2", (u) => updateRows("constructionG2", u))}
                                        onRowPatch={onRowPatch("constructionG2", (u) => updateRows("constructionG2", u))}
                                        readOnly={isReadOnly}
                                        // readOnly={activePeriod === null || activePeriod.status !== "in_progress"}
                                        onDeleteRow={!(activePeriod === null || activePeriod.status !== "in_progress") ? (id) => setDeleteTarget({ id: id as string, tableKey: 'constructionG2' }) : undefined}
                                    />
                                    <TableWrapper
                                        title="Detailed level - construction stage"
                                        rows={getRows("constructionG3")}
                                        setRows={(u) => updateRows("constructionG3", u)}
                                        columns={constructionG3Columns}
                                        exportFileName="ConstructionG3Data.csv"
                                        uploadKey="constructionG3"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="constructionG3"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["constructionG3"]}
                                        onCellChange={onCellChange("constructionG3", (u) => updateRows("constructionG3", u))}
                                        onRowPatch={onRowPatch("constructionG3", (u) => updateRows("constructionG3", u))}
                                        readOnly={isReadOnly}
                                        // readOnly={activePeriod === null || activePeriod.status !== "in_progress"}
                                        onDeleteRow={!(activePeriod === null || activePeriod.status !== "in_progress") ? (id) => setDeleteTarget({ id: id as string, tableKey: 'constructionG3' }) : undefined}
                                    />
                                    <TableWrapper
                                        title="Electricity"
                                        rows={getRows("electricity")}
                                        setRows={(u) => updateRows("electricity", u)}
                                        columns={electricityColumns}
                                        exportFileName="Electricity.csv"
                                        uploadKey="electricity"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="electricity"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["electricity"]}
                                        onCellChange={onCellChange("electricity", (u) => updateRows("electricity", u))}
                                        onRowPatch={onRowPatch("electricity", (u) => updateRows("electricity", u))}
                                        readOnly={isReadOnly}
                                        // readOnly={activePeriod === null || activePeriod.status !== "in_progress"}
                                        onDeleteRow={
                                            !(activePeriod === null || activePeriod.status !== "in_progress")
                                                ? (id) => setDeleteTarget({ id: id as string, tableKey: "electricity" })
                                                : undefined
                                        }
                                    />
                                </>
                            )}

                            {(isDesignStage || isConstructionStage) && isSubStageConstruction && isLargeProject && (
                                <>
                                    <TableWrapper
                                        title="Concrete register (grade 3) - simplified"
                                        rows={getRows("concreteRegSimplified")}
                                        setRows={(u) => updateRows("concreteRegSimplified", u)}
                                        columns={concreteRegSimplifiedColumns}
                                        exportFileName="Concrete_Register_simplified.csv"
                                        uploadKey="concreteRegSimplified"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="concreteRegSimplified"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["concreteRegSimplified"]}
                                        onCellChange={onCellChange("concreteRegSimplified", (u) => updateRows("concreteRegSimplified", u))}
                                        onRowPatch={onRowPatch("concreteRegSimplified", (u) => updateRows("concreteRegSimplified", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("concreteRegSimplified", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'concreteRegSimplified' }) : undefined}
                                    />
                                    <TableWrapper
                                        title="Concrete register (grade 3) - detailed"
                                        rows={getRows("concreteRegDetailed")}
                                        setRows={(u) => updateRows("concreteRegDetailed", u)}
                                        columns={concreteRegDetailedColumns}
                                        exportFileName="Concrete_Register_detailed.csv"
                                        uploadKey="concreteRegDetailed"
                                        renderEditor={renderEditor}
                                        onRequestUpload={(key: any) => setUploadTarget(key)}
                                        onNewRowSave={handleSaveNewRow}
                                        accordionKey="concreteRegDetailed"
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["concreteRegDetailed"]}
                                        onCellChange={onCellChange("concreteRegDetailed", (u) => updateRows("concreteRegDetailed", u))}
                                        onRowPatch={onRowPatch("concreteRegDetailed", (u) => updateRows("concreteRegDetailed", u))}
                                        readOnly={isReadOnly}
                                        onCancel={() => setErrorForKey("concreteRegDetailed", null)}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: id as string, tableKey: 'concreteRegDetailed' }) : undefined}
                                        onEditRow={!isReadOnly ? (row) => {
                                            setConcreteMixEditTarget(row);
                                        } : undefined}
                                        onActionSelect={(value: string) => {
                                            if (value === "New mix with mix design") setConcreteMixModalType("mix_design");
                                            else if (value === "New mix with EPD/PCF") setConcreteMixModalType("epd_pcf");
                                        }}
                                        onCellDoubleClick={(key, row) => {
                                            if (key === "mixId") {
                                                setConcreteMixEditTarget(row);
                                            }
                                        }}
                                    />
                                    <ShortcutTools
                                        stageInstanceId={activeStageInstance?.id ?? ""}
                                        projectId={projectId}
                                        projectOptionId={activeOptionId}
                                        readOnly={isReadOnly}
                                        onSaved={refreshOptionTotals}
                                    />
                                </>
                            )}

                            {isRecurringStage && activePeriod && (
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white p-5 mb-6 mx-12 rounded-[var(--radius-3)] shadow-sm">
                                    <div className="pb-6">
                                        <div className="text-sm text-text-faint mb-1">Total emissions reported</div>
                                        <div className="text-[28px] font-bold text-text-dark">
                                            {activePeriod?.all_periods_emissions_tco2e != null
                                                ? formatEmissionsOrQuantity(parseFloat(activePeriod.all_periods_emissions_tco2e))
                                                : "—"}{" "}
                                            <span className="text-[28px] font-light text-text-dark">
                                                tCO<sub>2</sub>e
                                            </span>
                                        </div>
                                    </div>
                                    <div className="pb-6">
                                        <div className="text-sm text-text-faint mb-1">Emissions this period</div>
                                        <div className="text-[28px] font-bold text-text-dark">
                                            {activePeriod?.period_emissions_tco2e != null
                                                ? formatEmissionsOrQuantity(parseFloat(activePeriod.period_emissions_tco2e))
                                                : "—"}{" "}
                                            <span className="text-[28px] font-light text-text-dark">
                                                tCO<sub>2</sub>e
                                            </span>
                                        </div>
                                    </div>
                                    <div className="pb-6 md:border-x md:border-neutral-90 md:px-6">
                                        <div className="text-sm text-text-faint mb-1">Emissions last period</div>
                                        <div className="text-[28px] font-bold text-text-dark">
                                            {activePeriod?.previous_period_emissions_tco2e != null
                                                ? formatEmissionsOrQuantity(parseFloat(activePeriod.previous_period_emissions_tco2e))
                                                : "—"}{" "}
                                            <span className="text-[28px] font-light text-text-dark">
                                                tCO<sub>2</sub>e
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {isRecurringStage && activePeriod && recurringActivities.map((activity) => {
                                const activityRows = recurringRowsByActivity[activity] ?? [];
                                return (
                                    <TableWrapper
                                        key={activity}
                                        title={activity}
                                        rows={activityRows}
                                        setRows={(updater: any) => {
                                            const updated = typeof updater === "function" ? updater(activityRows) : updater;
                                            updateRows("recurringG3", (prev) => [
                                                ...prev.filter((r) => {
                                                    const bid = r.reporting_boundary_id ?? r.extra_fields?.reporting_boundary_id;
                                                    const act = (bid ? boundaryIdToActivity[bid] : null) ?? r.extra_fields?.stage_or_activity ?? null;
                                                    return act !== activity;
                                                }),
                                                ...updated,
                                            ]);
                                        }}
                                        columns={constructionG3Config(projectId,"recurringG3", ACTIVITY_CATEGORY_MAP[activity]).columns()}
                                        exportFileName={`Recurring_${activity}.csv`}
                                        uploadKey="recurringG3"
                                        renderEditor={renderEditor}
                                        onRequestUpload={() => {}}
                                        onNewRowSave={(draft: any, tk: any) =>
                                            handleSaveNewRow({
                                                ...draft,
                                                extra_fields: { ...(draft.extra_fields ?? {}), stage_or_activity: activity },
                                            }, tk)
                                        }
                                        accordionKey={activity as any}
                                        accordionState={accordionState as any}
                                        setAccordionState={setAccordionState as any}
                                        error={tableErrors["recurringG3"]}
                                        onCancel={() => setErrorForKey("recurringG3", null)}
                                        readOnly={isReadOnly}
                                        onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: String(id), tableKey: "recurringG3" }) : undefined}
                                        onCellChange={onCellChange("recurringG3", (u) => updateRows("recurringG3", u))}
                                        onRowPatch={onRowPatch("recurringG3", (u) => updateRows("recurringG3", u))}
                                    />
                                );
                            })}

                            <div className="border border-neutral-90 bg-white p-6 rounded-[var(--radius-3)] mx-12 mb-12">
                                <div className="mb-2">
                                    <label className="text-sm text-text-base font-medium">
                                        {isUsersSubStage ? "Notes/comments" : "Executive summary"}{" "}
                                        <span className="font-normal">(optional)</span>
                                    </label>
                                    <div className="text-xs text-text-faint">
                                        {execSummary.length}/{charLimit}
                                    </div>
                                </div>
                                <textarea
                                    className={`border border-border-input w-full rounded-[var(--radius-3)] h-32 p-3 outline-none focus:ring-2 focus:ring-border-input focus:border-transparent
                                    ${isReadOnly ? "bg-neutral-95" : ""}`}
                                    value={execSummary}
                                    onChange={(e) => {
                                        setExecSummary(e.target.value.slice(0, charLimit));
                                        setExecSummaryDirty(true);
                                    }}
                                    maxLength={charLimit}
                                    aria-label={isUsersSubStage ? "Notes/comments" : "Executive summary"}
                                    disabled={isReadOnly}
                                />
                                {!execSummaryDirty && execSummary && (execSummaryAuthor || execSummaryDate) && (
                                    <div className="text-xs text-neutral-400 mt-1">
                                        {[
                                            execSummaryAuthor,
                                            execSummaryDate
                                                ? new Date(execSummaryDate).toLocaleDateString("en-AU", {
                                                    day: "numeric",
                                                    month: "short",
                                                    year: "numeric",
                                                })
                                                : null,
                                        ]
                                            .filter(Boolean)
                                            .join(" • ")}
                                    </div>
                                )}
                                {!isReadOnly && (
                                    <div className="flex justify-end mt-3">
                                        <button
                                            type="button"
                                            disabled={!execSummaryDirty}
                                            onClick={saveExecSummary}
                                            className="px-4 py-2 text-sm font-medium cursor-pointer rounded-[var(--radius-3)] bg-primary text-white disabled:opacity-40 hover:bg-primary/90 transition-colors"
                                        >
                                            Save
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>)}
                        {!showMitigations && (<div className="bg-white p-5 px-12 flex justify-end gap-3 border-t border-neutral-90 sticky bottom-0 z-20">
                            {(isConstructionStage || isRecurringStage) && isProjAdmin && activePeriod?.status === "awaiting_approval" ? (
                                <>
                                    <button
                                        className="border border-border-input text-text-dark px-6 cursor-pointer py-3 rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors"
                                        type="button"
                                        onClick={() => navigate(`/projects/${projectId}`)}
                                    >
                                        Exit
                                    </button>
                                    <button
                                        className="px-6 py-3 rounded-[var(--radius-3)] text-sm font-medium cursor-pointer bg-red-600 text-white hover:bg-red-700 transition-colors"
                                        type="button"
                                        onClick={() => setPeriodWorkflowOpen("reject")}
                                    >
                                        Reject Period
                                    </button>
                                    <button
                                        className="px-6 py-3 rounded-[var(--radius-3)] text-sm  cursor-pointer font-medium bg-green-600 text-white hover:bg-green-700 transition-colors"
                                        type="button"
                                        onClick={() => setPeriodWorkflowOpen("approve")}
                                    >
                                        Approve Period
                                    </button>
                                </>
                            ) : isProjAdmin && (isSubmitted || isReopenRequested) ? (
                                <>
                                    <button
                                        className="border border-border-input text-text-dark px-6 py-3 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors"
                                        type="button"
                                        onClick={() => {
                                            navigate(`/projects/${projectId}`)
                                        }}
                                    >
                                        Exit
                                    </button>

                                    <button
                                        className="border border-primary text-primary px-6 py-3 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors"
                                        type="button"
                                        onClick={goToPreviousSubStage}
                                        disabled={subStages.indexOf(activeSubStage) === 0}
                                    >
                                        Back
                                    </button>

                                    <div className="relative" ref={reviewMenuRef}>
                                        <button
                                            className="bg-primary text-white px-6 py-3 cursor-pointer rounded-[var(--radius-3)] flex items-center gap-2"
                                            type="button"
                                            onClick={() => setReviewMenuOpen(o => !o)}
                                        >
                                            Review and respond
                                            <span className="material-symbols-rounded text-base">
                                                {reviewMenuOpen ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                                            </span>
                                        </button>

                                        {reviewMenuOpen && (
                                            <div className="absolute right-0 bottom-full mb-2 rounded-lg border border-neutral-200 bg-white shadow-lg z-30 overflow-hidden">
                                                <div className="p-3 text-xs text-info-border bg-info-bg leading-4">
                                                    <span className="font-medium">Note:</span>{" "}Selecting an option in this panel will make changes to confirm before submission.
                                                </div>

                                                <div className="flex flex-col">
                                                    <button
                                                        className="w-full text-text-base text-left px-4 py-2 text-sm cursor-pointer hover:bg-neutral-50 border-b border-neutral-95"
                                                        onClick={() => {
                                                            setReviewMenuOpen(false);
                                                            setAdminDecisionOpen(isReopenRequested ? "approveReopen" : "approve");
                                                            setDecisionComments(""); // optional justification
                                                        }}
                                                    >
                                                        Approve
                                                    </button>
                                                    <button
                                                        className="w-full text-left px-4 py-2 text-sm cursor-pointer hover:bg-neutral-50 text-red-700"
                                                        onClick={() => {
                                                            setReviewMenuOpen(false);
                                                            setAdminDecisionOpen(isReopenRequested ? "denyReopen" : "reject");
                                                            setDecisionComments(""); // required justification
                                                        }}
                                                    >
                                                        Reject
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <>
                                    {!adminViewOnly && (isSubmitted || isApproved) ? (
                                        <>
                                            <button
                                                className="border border-primary text-primary px-6 py-3 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors"
                                                type="button"
                                                onClick={() => navigate(`/projects/${projectId}`)}
                                            >
                                                Exit
                                            </button>
                                        </>
                                    ) : (
                                        <button
                                            className="border border-primary text-primary px-6 py-3 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors"
                                            type="button"

                                            onClick={() => guardedAction("exit")}
                                        >
                                            Exit and continue later
                                        </button>
                                    )}

                                    {showMitigationsNextBtn ? (
                                        <button
                                            onClick={() => { setShowMitigations(true); setActiveSubStage(""); }}
                                            className="bg-primary text-white px-6 py-3 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium hover:bg-opacity-90 transition-colors"
                                            type="button"
                                        >
                                            Next
                                        </button>
                                        ) : showCompletenessNextBtn ? (
                                        <button
                                            onClick={() => {
                                                setShowMitigations(false);
                                                setActiveSubStage(COMPLETENESS_LABEL);
                                            }}
                                            className="bg-primary text-white px-6 py-3 rounded-[var(--radius-3)] text-sm font-medium hover:bg-opacity-90 transition-colors"
                                            type="button"
                                        >
                                            Next
                                        </button>
                                    ) : shouldShowSubmit ? (
                                        <button
                                            onClick={() => (isConstructionStage || isRecurringStage) ? setPeriodWorkflowOpen("submit") : setSubmitModalOpen(true)}
                                            className="bg-primary text-white px-6 py-3 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium hover:bg-opacity-90 transition-colors"
                                            type="button"
                                        >
                                            Submit
                                        </button>
                                    ) : !(isConstructionStage || isRecurringStage) && (

                                        <button
                                            className={`px-6 py-3 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium transition-colors
                                                    ${isLastSubStage
                                                    ? "bg-neutral-300 text-neutral-600 cursor-not-allowed"
                                                    : "bg-primary text-white hover:bg-opacity-90"
                                                }
                                                `}
                                            type="button"
                                            disabled={isLastSubStage}
                                            onClick={() => {
                                                if (!isLastSubStage) {
                                                    guardedAction("next");
                                                }
                                            }}
                                        >
                                            Next
                                        </button>

                                    )}
                                </>
                            )}
                        </div>)}
                        </>
                        )}
                        {!showMitigations && canRequestStageReopen(activeStageAccess, isProjAdmin, isApproved) && (
                            <div className="fixed bottom-6 left-6 z-30">
                                <button
                                    onClick={() => setReopenModalOpen(true)}
                                    className="w-[250px] bg-white cursor-pointer text-text-table-cell border border-text-table-cell rounded-[var(--radius-3)] px-4 py-2 text-sm hover:bg-neutral-50"
                                >
                                    Request to reopen
                                </button>
                            </div>
                        )}

                    </div>
                </div>
            </div>
        </>
    );
}

export default ConstructionStage;
