import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import LeftNavigation from "@/components/LeftNavigation";
import type { ActivityDataOut } from "@/services/ActivityData.service";
import StageResubmissionAuditPanel from "@/pages/auditLog/StageResubmissionAuditPanel";
import UsersSubStage from "./UsersSubStage";
import { useToast } from "../../../components/common/ToastProvider";
import { useProjectHeader } from "@/context/ProjectHeaderContext";
import { useUser } from "../../../context/UserContext";
import type {
    DataEntryRow,
    FugitiveOption,
    StageLabel,
} from "./dataEntryTypes";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import { useNavigate } from "react-router-dom";
import Mitigations from "./Mitigations";
import {
    type UploadKey,
    GROUPS_FOR,
    COMPLETENESS_LABEL,
} from "./stageConstants";
import {
    apiRowToUiRow as apiRowToUiRowFn,
    resolveBoundaryComponentIds as resolveBoundaryComponentIdsFn,
} from "./rowTransforms";
import { useTableRows } from "./useTableRows";
import { useEmissionsCalc } from "./useEmissionsCalc";
import { useMitigationHandlers } from "./useMitigationHandlers";
import { useExecSummary } from "./hooks/useExecSummary";
import { useLargeUserYears } from "./hooks/useLargeUserYears";
import { useWorkflowActions } from "./hooks/useWorkflowActions";
import { useRowOperations } from "./hooks/useRowOperations";
import { useDataEntryProjectBootstrap } from "./hooks/useDataEntryProjectBootstrap";
import { useConcreteRegisterRows } from "./hooks/useConcreteRegisterRows";
import { useConstructionPeriods } from "./hooks/useConstructionPeriods";
import { useFugitiveOptions } from "./hooks/useFugitiveOptions";
import { useRecurringPeriodRows } from "./hooks/useRecurringPeriodRows";
import { usePrimaryStageRows } from "./hooks/usePrimaryStageRows";
import { useCopyDataLoader } from "./hooks/useCopyDataLoader";
import { useConstructionPeriodRows } from "./hooks/useConstructionPeriodRows";
import { resolveRecurringActivityForRow } from "./recurringSelectors";
import { useDataEntryStageContext } from "./hooks/useDataEntryStageContext";
import { useDataEntryOptionLoading } from "./hooks/useDataEntryOptionLoading";
import { useDataEntryWorkflowViewState } from "./hooks/useDataEntryWorkflowViewState";
import { useDataEntryNavigation } from "./hooks/useDataEntryNavigation";
import { useDataEntryTableColumns } from "./hooks/useDataEntryTableColumns";
import { createDataEntryTableHandlers } from "./hooks/useDataEntryTableHandlers";
import { useDesignSeedWorkflow } from "./hooks/useDesignSeedWorkflow";
import { useStageResubmissionAudit } from "./hooks/useStageResubmissionAudit";
import { resolveMetricId } from "./metricResolution";
import { DataEntryModals } from "./components/DataEntryModals";
import { RecurringStageContent } from "./components/RecurringStageContent";
import { PeriodEmissionSummary } from "./components/PeriodEmissionSummary";
import { ConstructionCoreTables } from "./components/ConstructionCoreTables";
import { UseB1StageTables } from "./components/UseB1StageTables";
import { ConstructionLargeProjectTables } from "./components/ConstructionLargeProjectTables";
import { ConcreteStageTables } from "./components/ConcreteStageTables";
import { PrimaryStageTables } from "./components/PrimaryStageTables";
import { ExecutiveSummaryPanel } from "./components/ExecutiveSummaryPanel";
import { DataEntryWorkflowFooter } from "./components/DataEntryWorkflowFooter";
import { DataEntryStatusNotices } from "./components/DataEntryStatusNotices";
import { DataEntryStageToolbar } from "./components/DataEntryStageToolbar";
import { DataEntryProjectBootstrapView } from "./components/DataEntryProjectBootstrapView";
import Completeness from "./Completeness";
import {
    canRequestStageReopen,
} from "./stageAccessUi";

export type { UploadKey };


const ConstructionStage = () => {
    const { user } = useUser();
    const [searchParams] = useSearchParams();
    const { success } = useToast();
    const navigate = useNavigate();
    const projectId = searchParams.get("projectId") ?? "";
    const resolveProjectMetricId = useCallback(
        (draft: Parameters<typeof resolveMetricId>[0], tableKey: UploadKey) =>
            resolveMetricId(draft, tableKey, projectId),
        [projectId],
    );

    const stageInstanceIdParam = searchParams.get("stageInstanceId") ?? null;
    const reportNumberParam = parseInt(searchParams.get("reportNumber") ?? "1", 10) || 1;

    const { setProjectHeader, clearProjectHeader } = useProjectHeader();
    const [activeStage, setActiveStage] = useState<StageLabel>("Business case");
    const [activeSubStage, setActiveSubStage] = useState("Construction");
    const [showMitigations, setShowMitigations] = useState(false);
    const [showCompleteness, setShowCompleteness] = useState(false);
    const [activeReportNumber, setActiveReportNumber] = useState(1);
    // Per-stage_instance_id override for the "Currently editing" option picker (Business Case only).
    const [selectedOptionByStage, setSelectedOptionByStage] = useState<Record<string, string>>({});
    const [manageOptionsOpen, setManageOptionsOpen] = useState(false);
    const [copyDataOpen, setCopyDataOpen] = useState(false);
    const projectBootstrap = useDataEntryProjectBootstrap({
        projectId,
        stageInstanceIdParam,
        reportNumberParam,
        setProjectHeader,
        clearProjectHeader,
        setActiveStage,
        setActiveSubStage,
        setActiveReportNumber,
    });
    const {
        isLoaded: projectDataLoaded,
        loadError: projectLoadError,
        projectData,
        projectName: _projectName,
        programName: _programName,
        stageInstances,
        stageAccess,
        projectOptions,
        setProjectOptions,
        lockedStages,
        frequency,
        firstSubmissionMonth,
        reportingBoundaries,
        projectClass,
        projectTypeName,
        projectClosed,
        projectGridCtx,
        operationalLifeYears,
        opsStartYear,
        constructionStartDate,
        constructionEndDate,
        accessDenied,
        loadStageOptions,
        refreshStageOptions,
    } = projectBootstrap;
    const projectDataReady = projectDataLoaded && !projectLoadError;

    const [accordionState, setAccordionState] = useState<Record<string, boolean>>({
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
    const [concreteMixModalType, setConcreteMixModalType] = useState<"mix_design" | "epd_pcf" | null>(null);
    const [concreteMixEditTarget, setConcreteMixEditTarget] = useState<DataEntryRow | null>(null);

    const [fugitiveList, setFugitiveList] = useState<FugitiveOption[]>([]);
    const [selectedConstructionMonth, setSelectedConstructionMonth] = useState<string | null>(null);
    const [constructionPeriods, setConstructionPeriods] = useState<ConstructionPeriod[]>([]);
    const {
        designReportNum,
        pendingDesignReportNum,
        confirmOpen: designSeedConfirmOpen,
        isSeeding: reDesignSeedLoading,
        requestReportChange,
        cancelReportChange,
        confirmReportChange,
    } = useDesignSeedWorkflow();


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

    const charLimit = 1000;


    const [showAuditPanel, setShowAuditPanel] = useState(false);

    const {
        assetColumns,
        componentColumns,
        componentReplColumns,
        refurbColumns,
        opEnergyColumns,
        opEnergyDetailedColumns,
        opEnergyElectricityColumns,
        constructionG2Columns,
        constructionG3Columns,
        bcDetailedColumns,
        electricityColumns,
        useB1G2Columns,
        useB1G3Columns,
        concreteRegSimplifiedColumns,
        concreteRegDetailedColumns,
        replDetailedColumns,
        columnsForRecurringActivity,
    } = useDataEntryTableColumns(projectId, projectGridCtx?.jurisdiction ?? null);

    const {
        activeStageInstance,
        activeStageAccess,
        canEditActiveStage,
        isProjAdmin,
        isProjEditor,
        mitigationBucketStageEnum,
        mitigationStageInstance,
        mitigationOptionId,
        designStageInstance,
        designReportNums,
        designSeedOptionId,
        activePeriod,
        recurringActivities,
        recurringRowsByActivity,
        currentReportSubOptions,
        baseCaseOptions,
        activeOptionId,
        activeOption,
        optionTotalEmissions,
        enrichedStages,
        subStages,
    } = useDataEntryStageContext({
        activeStage,
        activeReportNumber,
        stageInstances,
        stageAccess,
        projectOptions,
        projectClass,
        selectedOptionByStage,
        constructionPeriods,
        selectedConstructionMonth,
        designReportNum,
        reportingBoundaries,
        recurringRows: tableRows.recurringG3,
    });
    const hasResubmission = useStageResubmissionAudit({
        enabled: projectDataReady,
        isProjectAdmin: isProjAdmin,
        stageInstanceId: activeStageInstance?.id,
        projectOptionId: activeOption?.id,
        approvalStatus: activeOption?.approval_status,
    });
    const resolveBoundaryComponentIds = useCallback(
        (boundary: { category: string; sub_category: string; source?: string | null }) =>
            resolveBoundaryComponentIdsFn(boundary, projectId),
        [projectId],
    );


    const apiRowToUiRow = useCallback((apiRow: ActivityDataOut): DataEntryRow => apiRowToUiRowFn(apiRow), []);

    const { onOptionsChange } = useDataEntryOptionLoading({
        enabled: projectDataReady,
        activeStage,
        projectClass,
        showMitigations,
        activeStageInstance,
        mitigationStageInstance,
        mitigationBucketStageEnum,
        designStageInstance,
        stageAccess,
        projectOptions,
        loadStageOptions,
        refreshStageOptions,
        setSelectedOptionByStage,
    });
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

    usePrimaryStageRows({
        enabled: projectDataReady,
        activeStage,
        activeSubStage,
        activeStageInstance,
        activeOptionId,
        projectClass,
        reportingBoundaries,
        updateRows,
        setTableRows,
        apiRowToUiRow,
        resolveBoundaryComponentIds,
        recalcAndPersistRows,
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
            resolveMetricId: resolveProjectMetricId,
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
        isUsersSubStage: projectDataReady && (activeStage === "Business case" || activeStage === "Design") && activeSubStage === "Users (B8)",
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
        resolveMetricId: resolveProjectMetricId,
        apiRowToUiRow,
        computeEmissionsForRow,
        getCalcConfig,
        refreshOptionTotals,
        recalcElectricitySiblings,
    });
    useConstructionPeriods({
        enabled: projectDataReady,
        activeStage,
        activeStageInstance,
        setPeriods: setConstructionPeriods,
        setSelectedPeriodId: setSelectedConstructionMonth,
    });
    useRecurringPeriodRows({
        activeStageInstance: projectDataReady && activeStage === "Recurring" ? activeStageInstance : null,
        periodId: selectedConstructionMonth,
        projectId,
        reportingBoundaries,
        apiRowToUiRow,
        updateRows,
    });


    useConstructionPeriodRows({
        enabled: projectDataReady,
        activeStage,
        activeSubStage,
        activeStageInstance,
        periodId: selectedConstructionMonth,
        projectClass,
        reportingBoundaries,
        updateRows,
        apiRowToUiRow,
        resolveBoundaryComponentIds,
        recalcAndPersistRows,
    });


    // Concrete register loading is isolated so sub-stage changes cannot wipe its rows.
    useConcreteRegisterRows({
        enabled: projectDataReady,
        projectClass,
        activeStage,
        activeSubStage,
        activeStageInstance,
        activeOptionId,
        apiRowToUiRow,
        updateRows,
        recalcAndPersistRows,
    });

    useFugitiveOptions({
        enabled: projectDataReady,
        isUseStage: activeSubStage === "Use (B1)",
        projectClass,
        projectId,
        setFugitiveOptions: setFugitiveList,
    });

    const {
        isCurrentStageLocked,
        isUsersSubStage,
        isSubmitted,
        isApproved,
        isRejected,
        isReopenRequested,
        statusBasedReadOnly,
        adminViewOnly,
        isReadOnly,
        isLastSubStage,
        isConstructionStage,
        isRecurringStage,
        isBusinessCaseStage,
        isDesignStage,
        isBcOrDesignStage,
        isLargeProject,
        mitigationsTabEnabled,
        completenessEnabled,
        completenessSubmissionStage,
        isSubStageConstruction,
        isSubStageUseB1,
        isSubStageReplacement,
        isSubStageOpEnergy,
        isSubStageOpEnergyW,
        shouldShowSubmit,
        showMitigationsNextBtn,
        showCompletenessNextBtn,
        shouldShowMitigationSubmit,
        isUsersReadOnly,
        reopenReasonText,
    } = useDataEntryWorkflowViewState({
        activeStage,
        activeSubStage,
        projectClass,
        jurisdiction: projectGridCtx?.jurisdiction,
        activeStageAccess,
        activeStageInstance,
        activeOption,
        activePeriod,
        currentReportOptionCount: currentReportSubOptions.length,
        lockedStages,
        projectClosed,
        canEditActiveStage,
        isProjAdmin,
        isProjEditor,
        showCompleteness,
        showMitigations,
        subStages,
    });
    const {
        onCellChangeFor,
        onRowPatchFor,
        onCancelFor,
        onDeleteForEditableTable,
        onDeleteForConstructionPeriod,
    } = createDataEntryTableHandlers({
        updateRows,
        setErrorForKey,
        onCellChange,
        onRowPatch,
        setDeleteTarget,
        isReadOnly,
        activePeriod,
    });
    const {
        selectStage,
        selectSubStage,
        selectMitigations,
        selectCompleteness,
        goToPreviousSubStage,
        guardedAction,
    } = useDataEntryNavigation({
        projectId,
        projectData,
        projectClass,
        activeSubStage,
        subStages,
        stages: enrichedStages,
        mitigationsEnabled: mitigationsTabEnabled,
        completenessEnabled,
        navigate,
        setActiveStage,
        setActiveReportNumber,
        setActiveSubStage,
        setShowMitigations,
        setShowCompleteness,
        setShowAuditPanel,
    });
    const handleCopyDataLoaded = useCopyDataLoader({
        activeSubStage,
        activeStageInstance,
        activeOptionId,
        projectClass,
        reportingBoundaries,
        updateRows,
        apiRowToUiRow,
        resolveBoundaryComponentIds,
        closeCopyDialog: () => setCopyDataOpen(false),
        refreshUsers: () => setUsersRefreshKey((key) => key + 1),
    });

    const bootstrapView = (
        <DataEntryProjectBootstrapView
            accessDenied={accessDenied}
            isLoaded={projectDataLoaded}
            loadError={projectLoadError}
            onBack={() => navigate(`/projects/${projectId}`)}
        />
    );
    if (accessDenied || !projectDataLoaded || projectLoadError) return bootstrapView;

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
                onCancelDesignSeed={cancelReportChange}
                onConfirmDesignSeed={() =>
                    confirmReportChange(seedPeriodsFromDesign, constructionPeriods.map((period) => period.id))
                }
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
                periodWorkflowOpen={periodWorkflowOpen}
                setPeriodWorkflowOpen={setPeriodWorkflowOpen}
                activePeriod={activePeriod}
                handlePeriodWorkflowConfirm={handlePeriodWorkflowConfirm}
            />
            <div className="flex flex-col h-full overflow-hidden">

                <div className="flex flex-1 min-h-0 overflow-hidden">
                    <div className="shrink-0">
                        <LeftNavigation
                            stageType={activeStage}
                            stages={enrichedStages}
                            onSelectStage={selectStage}
                            activeSubStage={activeSubStage}
                            onSelectSubStage={selectSubStage}
                            showMitigations={showMitigations}
                            onSelectMitigations={selectMitigations}
                            mitigationsTabEnabled={mitigationsTabEnabled}
                            subStages={subStages.map((s) => ({ label: s, value: s }))}
                            groups={GROUPS_FOR(activeStage, projectClass)}
                            selectedReportId={selectedConstructionMonth}
                            onSelectReport={(month: string) => setSelectedConstructionMonth(month)}
                            reportFrequency={frequency}
                            firstSubmissionMonth={firstSubmissionMonth}
                            constructionPeriods={constructionPeriods}
                            projectName={isProjAdmin ? _projectName : ""}
                            activeStageInstance={activeStageInstance}
                            isStageAdmin={isProjAdmin}
                            programName={_programName}
                            activeReportNumber={activeReportNumber}
                            showCompleteness={showCompleteness}
                            onSelectCompleteness={selectCompleteness}
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
                        <DataEntryStatusNotices
                            showMitigations={showMitigations}
                            isProjectAdmin={isProjAdmin}
                            isReopenRequested={isReopenRequested}
                            isApproved={isApproved}
                            isStageLocked={isCurrentStageLocked}
                            isPeriodWorkflowStage={isConstructionStage || isRecurringStage}
                            constructionPeriodCount={constructionPeriods.length}
                            isSubmitted={isSubmitted}
                            isRejected={isRejected}
                            rejectionComment={activeOption?.current_justification}
                            reopenReason={reopenReasonText}
                            adminViewOnly={adminViewOnly}
                            statusBasedReadOnly={statusBasedReadOnly}
                        />
                       {!showMitigations && !showCompleteness && (<div className="flex-1 overflow-y-auto bg-neutral-98 pb-40">
                            <DataEntryStageToolbar
                                isConstructionStage={isConstructionStage}
                                isRecurringStage={isRecurringStage}
                                isLargeProject={isLargeProject}
                                isBusinessCaseStage={isBusinessCaseStage}
                                isReadOnly={isReadOnly}
                                totalEmissions={optionTotalEmissions}
                                operationalLifeYears={operationalLifeYears}
                                designReportNumbers={designReportNums}
                                designReportNumber={designReportNum}
                                onRequestDesignReportChange={requestReportChange}
                                activeOptionId={activeOptionId}
                                options={baseCaseOptions}
                                onOptionChange={(optionId) => {
                                    if (activeStageInstance) {
                                        setSelectedOptionByStage((previous) => ({ ...previous, [activeStageInstance.id]: optionId }));
                                    }
                                }}
                                onOpenCopyData={() => setCopyDataOpen(true)}
                                onOpenManageOptions={() => setManageOptionsOpen(true)}
                            />
                            {(isBcOrDesignStage || isBusinessCaseStage) && (
                                <PrimaryStageTables
                                    visible={{
                                        asset: isBusinessCaseStage && isSubStageConstruction,
                                        component: isBcOrDesignStage && isSubStageConstruction,
                                        bcDetailedLevel: isBcOrDesignStage && isSubStageConstruction && isLargeProject,
                                        electricity: isBcOrDesignStage && isSubStageConstruction && isLargeProject,
                                        componentRepl: isBcOrDesignStage && isSubStageReplacement,
                                        refurbishment: isBcOrDesignStage && isSubStageReplacement,
                                        replDetailed: isBcOrDesignStage && isSubStageReplacement && isLargeProject,
                                        opEnergy: isBcOrDesignStage && isSubStageOpEnergy,
                                        opEnergyDetailed: isBcOrDesignStage && isSubStageOpEnergy && isLargeProject,
                                        opEnergyElectricity: isBcOrDesignStage && isSubStageOpEnergy && isLargeProject,
                                    }}
                                    rowsFor={getRows}
                                    updateRows={updateRows}
                                    columns={{
                                        asset: assetColumns,
                                        component: componentColumns,
                                        bcDetailedLevel: bcDetailedColumns,
                                        electricity: electricityColumns,
                                        componentRepl: componentReplColumns,
                                        refurbishment: refurbColumns,
                                        replDetailed: replDetailedColumns,
                                        opEnergy: opEnergyColumns,
                                        opEnergyDetailed: opEnergyDetailedColumns,
                                        opEnergyElectricity: opEnergyElectricityColumns,
                                    }}
                                    errors={tableErrors}
                                    renderEditor={renderEditor}
                                    onRequestUpload={setUploadTarget}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionState={accordionState}
                                    setAccordionState={setAccordionState}
                                    readOnly={isReadOnly}
                                    onCellChange={onCellChangeFor}
                                    onRowPatch={onRowPatchFor}
                                    onCancel={onCancelFor}
                                    onDelete={onDeleteForEditableTable}
                                />
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

                            {isConstructionStage && <PeriodEmissionSummary period={activePeriod} />}
                            {(isBcOrDesignStage || isConstructionStage) && isLargeProject && isSubStageUseB1 && (
                                <UseB1StageTables
                                    rowsFor={getRows}
                                    updateRows={updateRows}
                                    columns={{ useB1G2: useB1G2Columns, useB1G3: useB1G3Columns }}
                                    errors={tableErrors}
                                    renderEditor={renderEditor}
                                    onRequestUpload={setUploadTarget}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionState={accordionState}
                                    setAccordionState={setAccordionState}
                                    readOnly={isReadOnly}
                                    onCellChange={onCellChangeFor}
                                    onRowPatch={onRowPatchFor}
                                    onCancel={onCancelFor}
                                    onDelete={onDeleteForEditableTable}
                                    isConstructionStage={activeStage === "Construction"}
                                />
                            )}
                            {isConstructionStage && isLargeProject && isSubStageReplacement && (
                                <ConstructionLargeProjectTables
                                    section="replacement"
                                    rowsFor={getRows}
                                    updateRows={updateRows}
                                    columns={{ componentRepl: componentReplColumns, refurbishment: refurbColumns, replDetailed: replDetailedColumns, opEnergy: opEnergyColumns, opEnergyDetailed: opEnergyDetailedColumns, opEnergyElectricity: opEnergyElectricityColumns }}
                                    errors={tableErrors}
                                    renderEditor={renderEditor}
                                    onRequestUpload={setUploadTarget}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionState={accordionState}
                                    setAccordionState={setAccordionState}
                                    readOnly={isReadOnly}
                                    onCellChange={onCellChangeFor}
                                    onRowPatch={onRowPatchFor}
                                    onCancel={onCancelFor}
                                    onDelete={onDeleteForEditableTable}
                                />
                            )}
                            
                            {isConstructionStage && isLargeProject && isSubStageOpEnergyW && (
                                <ConstructionLargeProjectTables
                                    section="operationalEnergyWater"
                                    rowsFor={getRows}
                                    updateRows={updateRows}
                                    columns={{ componentRepl: componentReplColumns, refurbishment: refurbColumns, replDetailed: replDetailedColumns, opEnergy: opEnergyColumns, opEnergyDetailed: opEnergyDetailedColumns, opEnergyElectricity: opEnergyElectricityColumns }}
                                    errors={tableErrors}
                                    renderEditor={renderEditor}
                                    onRequestUpload={setUploadTarget}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionState={accordionState}
                                    setAccordionState={setAccordionState}
                                    readOnly={isReadOnly}
                                    onCellChange={onCellChangeFor}
                                    onRowPatch={onRowPatchFor}
                                    onCancel={onCancelFor}
                                    onDelete={onDeleteForEditableTable}
                                />
                            )}

                            {isConstructionStage && isSubStageConstruction && (
                                <ConstructionCoreTables
                                    rowsFor={getRows}
                                    updateRows={updateRows}
                                    columns={{ constructionG2: constructionG2Columns, constructionG3: constructionG3Columns, electricity: electricityColumns }}
                                    errors={tableErrors}
                                    renderEditor={renderEditor}
                                    onRequestUpload={setUploadTarget}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionState={accordionState}
                                    setAccordionState={setAccordionState}
                                    readOnly={isReadOnly}
                                    onCellChange={onCellChangeFor}
                                    onRowPatch={onRowPatchFor}
                                    onDelete={onDeleteForConstructionPeriod}
                                />
                            )}

                            {(isDesignStage || isConstructionStage) && isSubStageConstruction && isLargeProject && (
                                <ConcreteStageTables
                                    rowsFor={getRows}
                                    updateRows={updateRows}
                                    columns={{ concreteRegSimplified: concreteRegSimplifiedColumns, concreteRegDetailed: concreteRegDetailedColumns }}
                                    errors={tableErrors}
                                    renderEditor={renderEditor}
                                    onRequestUpload={setUploadTarget}
                                    onNewRowSave={handleSaveNewRow}
                                    accordionState={accordionState}
                                    setAccordionState={setAccordionState}
                                    readOnly={isReadOnly}
                                    onCellChange={onCellChangeFor}
                                    onRowPatch={onRowPatchFor}
                                    onCancel={onCancelFor}
                                    onDelete={onDeleteForEditableTable}
                                    onEditDetailedRow={setConcreteMixEditTarget}
                                    onActionSelect={(action) => {
                                        if (action === "New mix with mix design") setConcreteMixModalType("mix_design");
                                        else if (action === "New mix with EPD/PCF") setConcreteMixModalType("epd_pcf");
                                    }}
                                    stageInstanceId={activeStageInstance?.id ?? ""}
                                    projectId={projectId}
                                    projectOptionId={activeOptionId}
                                    onSaved={refreshOptionTotals}
                                />
                            )}

                            {isRecurringStage && activePeriod && (
                                <RecurringStageContent
                                    period={activePeriod}
                                    activities={recurringActivities}
                                    rowsByActivity={recurringRowsByActivity}
                                    columnsForActivity={columnsForRecurringActivity}
                                    onActivityRowsChange={(activity, updater) => {
                                        const currentRows = recurringRowsByActivity[activity] ?? [];
                                        const nextRows = typeof updater === "function" ? updater(currentRows) : updater;
                                        updateRows("recurringG3", (previous) => [
                                            ...previous.filter((row) => resolveRecurringActivityForRow(row, reportingBoundaries) !== activity),
                                            ...nextRows,
                                        ]);
                                    }}
                                    saveNewRow={(draft, tableKey, activity) => handleSaveNewRow({
                                        ...draft,
                                        extra_fields: { ...(draft.extra_fields ?? {}), stage_or_activity: activity },
                                    }, tableKey)}
                                    renderEditor={renderEditor}
                                    accordionState={accordionState}
                                    setAccordionState={setAccordionState}
                                    error={tableErrors["recurringG3"]}
                                    onCancel={onCancelFor("recurringG3")}
                                    readOnly={isReadOnly}
                                    onDeleteRow={!isReadOnly ? (id) => setDeleteTarget({ id: String(id), tableKey: "recurringG3" }) : undefined}
                                    onCellChange={onCellChangeFor("recurringG3")}
                                    onRowPatch={onRowPatchFor("recurringG3")}
                                />
                            )}
                            <ExecutiveSummaryPanel
                                isNotes={isUsersSubStage}
                                value={execSummary}
                                onValueChange={(value) => {
                                    setExecSummary(value);
                                    setExecSummaryDirty(true);
                                }}
                                dirty={execSummaryDirty}
                                author={execSummaryAuthor}
                                date={execSummaryDate}
                                characterLimit={charLimit}
                                readOnly={isReadOnly}
                                onSave={saveExecSummary}
                            />
                        </div>)}
                        {!showMitigations && (
                            <DataEntryWorkflowFooter
                                isConstructionStage={isConstructionStage}
                                isRecurringStage={isRecurringStage}
                                isProjectAdmin={isProjAdmin}
                                periodStatus={activePeriod?.status ?? null}
                                isSubmitted={isSubmitted}
                                isApproved={isApproved}
                                isReopenRequested={isReopenRequested}
                                adminViewOnly={adminViewOnly}
                                showMitigationsNext={showMitigationsNextBtn}
                                showCompletenessNext={showCompletenessNextBtn}
                                shouldShowSubmit={shouldShowSubmit}
                                isLastSubStage={isLastSubStage}
                                isFirstSubStage={subStages.indexOf(activeSubStage) === 0}
                                onExitToProject={() => navigate("/projects/" + projectId)}
                                onExitLater={() => guardedAction("exit")}
                                onBack={goToPreviousSubStage}
                                onPeriodWorkflow={setPeriodWorkflowOpen}
                                onAdminDecision={(decision) => {
                                    setAdminDecisionOpen(decision);
                                    setDecisionComments("");
                                }}
                                onShowMitigations={() => {
                                    setShowMitigations(true);
                                    setActiveSubStage("");
                                }}
                                onShowCompleteness={() => {
                                    setShowMitigations(false);
                                    setActiveSubStage(COMPLETENESS_LABEL);
                                }}
                                onSubmit={() => (isConstructionStage || isRecurringStage)
                                    ? setPeriodWorkflowOpen("submit")
                                    : setSubmitModalOpen(true)}
                                onNextSubStage={() => guardedAction("next")}
                            />
                        )}
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
