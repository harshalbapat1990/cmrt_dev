import { useCallback, useMemo } from "react";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import {
    type UploadKey,
    isUploadKey,
    MITIGATION_SUBMISSION_PERIOD_KEYS,
} from "./stageConstants";
import { mitigationUiKey, type MitigationSubstitutionLeg } from "./mitigationConstants";
import type { MitigationPanelBaseKey } from "./mitigationConstants";
import ActivityDataService, { type ActivityDataOut } from "@/services/ActivityData.service";
import type { MeProfile } from "@/context/UserContext";
import ProjectMitigationsService from "@/services/ProjectMitigations.service";
import {
    createMitigationOnCellChange,
    createMitigationOnRowPatch,
} from "./mitigationInlineEditHandlers";
import type { DataEntryRow, FugitiveOption, StageInstance, StageLabel } from "./dataEntryTypes";
import type { CalcConfig } from "./useEmissionsCalc";
import { saveMitigationBulkTable } from "./mitigationBulkPersistence";
import { createMitigationNewRowSaver } from "./mitigationNewRowSaver";
import { createMitigationTableUploader } from "./mitigationTableUploader";

interface MitigationHandlersParams {
    projectId: string;
    projectClass: string | null;
    activeStage: StageLabel;
    activePeriod: ConstructionPeriod | null;
    mitigationStageInstance: StageInstance | null;
    mitigationOptionId: string | null;
    user: MeProfile | null;
    resolveMetricId: (draft: DataEntryRow, tableKey: UploadKey) => Promise<string | null>;
    computeEmissionsForRow: (tableKey: UploadKey, row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
    getCalcConfig: (tableKey: UploadKey) => CalcConfig | null;
    apiRowToUiRow: (apiRow: ActivityDataOut) => DataEntryRow;
    refreshOptionTotals: () => Promise<void>;
    operationalLifeYears: number | null;
    fugitiveList: FugitiveOption[];
    constructionStartDate: string | null;
    constructionEndDate: string | null;
    opsStartYear: number | null;
}

export function useMitigationHandlers({
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
}: MitigationHandlersParams) {
    const mitigationActivityUsesSubmissionPeriod = useCallback(
        (tableKey: string) =>
            activeStage === "Construction" &&
            !!activePeriod &&
            isUploadKey(tableKey) && MITIGATION_SUBMISSION_PERIOD_KEYS.includes(tableKey),
        [activeStage, activePeriod],
    );

    const saveMitigationActivityNewRow = useMemo(
        () => createMitigationNewRowSaver({
            projectId,
            mitigationStageInstance,
            mitigationOptionId,
            activePeriod,
            user,
            resolveMetricId,
            computeEmissionsForRow,
            apiRowToUiRow,
            refreshOptionTotals,
            mitigationActivityUsesSubmissionPeriod,
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
            operationalLifeYears,
        }),
        [mitigationStageInstance, projectId, mitigationOptionId, activePeriod, activeStage, user, resolveMetricId, computeEmissionsForRow, apiRowToUiRow, refreshOptionTotals, mitigationActivityUsesSubmissionPeriod, constructionStartDate, constructionEndDate, opsStartYear, operationalLifeYears],
    );

const mitigationInlineEditDeps = useMemo(
        () => ({
            projectId,
            computeEmissionsForRow,
            getCalcConfig,
            user,
            fugitiveList,
            operationalLifeYears,
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
        }),
        [
            projectId,
            computeEmissionsForRow,
            getCalcConfig,
            user,
            fugitiveList,
            operationalLifeYears,
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
        ],
    );

    const mitigationElectricityYearDeps = useMemo(
        () => ({
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
            operationalLifeYears,
        }),
        [constructionStartDate, constructionEndDate, opsStartYear, operationalLifeYears],
    );

    const mitigationOnCellChange = useMemo(
        () => createMitigationOnCellChange(mitigationInlineEditDeps),
        [mitigationInlineEditDeps],
    );

    const mitigationOnRowPatch = useMemo(
        () => createMitigationOnRowPatch(mitigationInlineEditDeps),
        [mitigationInlineEditDeps],
    );

    const mitigationPersistence = useMemo(() => {
        if (!mitigationStageInstance?.id || !projectId || projectClass !== "LARGE") return null;

        const periodForFetch = (baseKey: MitigationPanelBaseKey) =>
            mitigationActivityUsesSubmissionPeriod(baseKey) ? activePeriod!.id : undefined;

        return {
            saveMitigationBulkTable: async (
                baseKey: MitigationPanelBaseKey,
                projectMitigationId: string,
                rows: DataEntryRow[],
                substitutionLeg?: MitigationSubstitutionLeg | null,
            ) => {
                await saveMitigationBulkTable({
                    baseKey,
                    projectMitigationId,
                    rows,
                    substitutionLeg,
                    projectId,
                    stageInstanceId: mitigationStageInstance.id,
                    projectOptionId: mitigationOptionId,
                    activePeriod,
                    shouldUseSubmissionPeriod: mitigationActivityUsesSubmissionPeriod,
                    computeEmissions: computeEmissionsForRow,
                    refreshOptionTotals,
                });
            },
            loadMitigationTable: async (
                baseKey: MitigationPanelBaseKey,
                projectMitigationId: string,
                substitutionLeg?: MitigationSubstitutionLeg | null,
            ) => {
                const mitKey = mitigationUiKey(baseKey, substitutionLeg ?? undefined);
                const raw = await ActivityDataService.fetchRows(
                    mitigationStageInstance.id,
                    mitKey,
                    mitigationOptionId ?? undefined,
                    periodForFetch(baseKey),
                    projectMitigationId,
                );
                return raw.map(apiRowToUiRow);
            },
            patchMitigationMeta: async (
                projectMitigationId: string,
                meta: {
                    name: string;
                    type: string;
                    lifecyclePhase: string;
                    lifecyclePhaseLabel: string;
                    notes?: string;
                    group?: string;
                    submissionStage: string;
                },
            ) => {
                await ProjectMitigationsService.patchMitigation(projectMitigationId, {
                    name: meta.name.trim(),
                    mitigation_type: meta.type || "reduction",
                    lifecycle_phase: meta.lifecyclePhase,
                    lifecycle_phase_label: meta.lifecyclePhaseLabel,
                    notes: meta.notes?.trim() ?? null,
                    group_label: meta.group?.trim() ?? null,
                });
                await refreshOptionTotals();
            },
            createMitigation: async (meta: {
                name: string;
                type: string;
                lifecyclePhase: string;
                lifecyclePhaseLabel: string;
                notes?: string;
                group?: string;
                submissionStage: string;
            }) => {
                const created = await ProjectMitigationsService.create({
                    project_id: projectId,
                    project_stage_instance_id: mitigationStageInstance.id,
                    project_option_id: mitigationOptionId ?? null,
                    submission_stage: meta.submissionStage,
                    name: meta.name.trim(),
                    mitigation_type: meta.type || "reduction",
                    lifecycle_phase: meta.lifecyclePhase,
                    lifecycle_phase_label: meta.lifecyclePhaseLabel,
                    notes: meta.notes?.trim() ?? null,
                    group_label: meta.group?.trim() ?? null,
                });
                await refreshOptionTotals();
                return created.id;
            },
            loadMitigationsForStage: async (submissionStageFilter: string) => {
                const rows = await ProjectMitigationsService.list({
                    project_stage_instance_id: mitigationStageInstance.id,
                    submission_stage: submissionStageFilter,
                });
                return rows.map((r) => ({
                    mitigationId: r.id,
                    name: r.name,
                    type: r.mitigation_type,
                    lifecyclePhase: r.lifecycle_phase,
                    lifecyclePhaseLabel: r.lifecycle_phase_label,
                    notes: r.notes ?? undefined,
                    group: r.group_label ?? undefined,
                    submissionStage: r.submission_stage,
                }));
            },
            deleteMitigation: async (projectMitigationId: string) => {
                await ProjectMitigationsService.remove(projectMitigationId);
                await refreshOptionTotals();
            },
            uploadMitigationTableFile: createMitigationTableUploader({
                projectId,
                mitigationStageInstance,
                mitigationOptionId,
                activePeriod,
                user,
                operationalLifeYears,
                mitigationActivityUsesSubmissionPeriod,
                resolveMetricId,
                computeEmissionsForRow,
                apiRowToUiRow,
                refreshOptionTotals,
                constructionStartDate,
                constructionEndDate,
                opsStartYear,
            }),
            saveMitigationNewRow: saveMitigationActivityNewRow,
            computeEmissionsForRow: (tableKey: string, row: DataEntryRow) =>
                isUploadKey(tableKey) ? computeEmissionsForRow(tableKey, row) : Promise.resolve(null),
            refreshOptionTotals,
            onCellChange: mitigationOnCellChange,
            onRowPatch: mitigationOnRowPatch,
        };
    }, [
        mitigationStageInstance,
        mitigationOptionId,
        projectId,
        projectClass,
        activePeriod,
        activeStage,
        mitigationActivityUsesSubmissionPeriod,
        computeEmissionsForRow,
        apiRowToUiRow,
        refreshOptionTotals,
        saveMitigationActivityNewRow,
        operationalLifeYears,
        mitigationElectricityYearDeps,
        mitigationOnCellChange,
        mitigationOnRowPatch,
    ]);

    return {
        mitigationActivityUsesSubmissionPeriod,
        saveMitigationActivityNewRow,
        mitigationPersistence,
    };
}
