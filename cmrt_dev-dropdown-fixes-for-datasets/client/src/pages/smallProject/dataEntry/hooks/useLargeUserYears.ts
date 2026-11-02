import { useState, useEffect, useCallback } from "react";
import ActivityDataService, { type ActivityDataCreate, type ActivityDataOut } from "@/services/ActivityData.service";
import {
    mitigationUiKey,
    type MitigationSubstitutionLeg,
} from "../mitigationConstants";
import type { StageInstance } from "../dataEntryTypes";

interface UseLargeUserYearsParams {
    isUsersSubStage: boolean;
    activeStageInstance: Pick<StageInstance, "id"> | null;
    activeOptionId: string | null;
    projectClass: string | null;
    isLargeUsersNZ: boolean;
    opsStartYear: number | null;
    projectId: string | null;
    projectMitigationId?: string | null;
    mitigationSubstitutionLeg?: MitigationSubstitutionLeg | null;
}

const LARGE_USER_YEAR_TABLES = ["largeRoadParams", "largeRoadUsers", "largeRailUsers"] as const;

function getModelledYear(row: ActivityDataOut): number | null {
    const year = row.extra_fields?.modelled_year;
    return typeof year === "number" ? year : null;
}

function toYearUpsert(row: ActivityDataOut, tableKey: string, projectMitigationId: string | null): ActivityDataCreate {
    return {
        project_id: row.project_id,
        project_stage_instance_id: row.project_stage_instance_id,
        project_option_id: row.project_option_id ?? null,
        metric_id: null,
        quantity: row.quantity ?? 0,
        unit_id: null,
        ui_table_key: tableKey,
        extra_fields: row.extra_fields ?? {},
        ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
    };
}

export function useLargeUserYears({
    isUsersSubStage,
    activeStageInstance,
    activeOptionId,
    projectClass,
    isLargeUsersNZ,
    opsStartYear,
    projectId,
    projectMitigationId = null,
    mitigationSubstitutionLeg = null,
}: UseLargeUserYearsParams) {
    const [largeUsersYears, setLargeUsersYears] = useState<number[]>([]);
    const [activeLargeUsersYear, setActiveLargeUsersYear] = useState<number | null>(null);
    const [addLargeYearOpen, setAddLargeYearOpen] = useState(false);
    const [addLargeYearInput, setAddLargeYearInput] = useState("");
    const [addLargeYearError, setAddLargeYearError] = useState<string | null>(null);
    const [copyLargeYearSource, setCopyLargeYearSource] = useState<number | null>(null);
    const [copyLargeYearConfirmOpen, setCopyLargeYearConfirmOpen] = useState(false);
    const [deleteLargeYearConfirmOpen, setDeleteLargeYearConfirmOpen] = useState(false);
    const [usersRefreshKey, setUsersRefreshKey] = useState(0);

    const scopeKey = useCallback(
        (base: string) =>
            projectMitigationId
                ? mitigationUiKey(base, mitigationSubstitutionLeg ?? undefined)
                : base,
        [projectMitigationId, mitigationSubstitutionLeg],
    );

    useEffect(() => {
        if (!isUsersSubStage || projectClass !== "LARGE" || isLargeUsersNZ || !activeStageInstance) return;
        let cancelled = false;
        (async () => {
            const rows = await ActivityDataService.fetchRows(
                activeStageInstance.id,
                scopeKey("largeRoadParams"),
                activeOptionId ?? null,
                undefined,
                projectMitigationId ?? undefined,
            );
            if (cancelled) return;
            const years = [
                ...new Set(
                    rows
                        .map(getModelledYear)
                        .filter((year): year is number => year !== null)
                ),
            ].sort((a: number, b: number) => a - b);
            setLargeUsersYears(years);
            setActiveLargeUsersYear(years[0] ?? null);
        })();
        return () => { cancelled = true; };
    }, [isUsersSubStage, activeStageInstance?.id, activeOptionId, projectClass, isLargeUsersNZ, scopeKey, projectMitigationId]);

    const handleAddLargeYear = async () => {
        const year = parseInt(addLargeYearInput, 10);
        if (isNaN(year) || year < 1900 || year > 2200) {
            setAddLargeYearError("Enter a valid year.");
            return;
        }
        if (opsStartYear !== null && year <= opsStartYear) {
            setAddLargeYearError(`Year must be after ${opsStartYear} (commencement of operations).`);
            return;
        }
        if (largeUsersYears.includes(year)) {
            setAddLargeYearError("That year already exists.");
            return;
        }
        if (!activeStageInstance || !projectId) return;
        const sk = scopeKey("largeRoadParams");
        const existing = await ActivityDataService.fetchRows(
            activeStageInstance.id,
            sk,
            activeOptionId ?? null,
            undefined,
            projectMitigationId ?? undefined,
        );
        const skeleton = {
            project_id: projectId,
            project_stage_instance_id: activeStageInstance.id,
            project_option_id: activeOptionId ?? null,
            metric_id: null,
            quantity: 0,
            unit_id: null,
            ui_table_key: sk,
            extra_fields: { modelled_year: year, roughness: "Smooth", gradient: "Flat", curvature: "Straight" },
            ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
        };
        const all = [
            ...existing.map((row) => toYearUpsert(row, sk, projectMitigationId)),
            skeleton,
        ];
        await ActivityDataService.bulkUpsert(
            activeStageInstance.id,
            sk,
            all,
            projectMitigationId ?? undefined,
        );
        const newYears = [...largeUsersYears, year].sort((a, b) => a - b);
        setLargeUsersYears(newYears);
        setActiveLargeUsersYear(year);
        setAddLargeYearOpen(false);
        setAddLargeYearInput("");
        setAddLargeYearError(null);
        setUsersRefreshKey((k) => k + 1);
    };

    const handleCopyLargeYear = async () => {
        if (copyLargeYearSource === null || activeLargeUsersYear === null || !activeStageInstance) return;
        for (const key of LARGE_USER_YEAR_TABLES) {
            const sk = scopeKey(key);
            const all = await ActivityDataService.fetchRows(
                activeStageInstance.id,
                sk,
                activeOptionId ?? null,
                undefined,
                projectMitigationId ?? undefined,
            );
            const srcRows = all.filter((row) => getModelledYear(row) === copyLargeYearSource);
            const otherRows = all.filter((row) => getModelledYear(row) !== activeLargeUsersYear);
            const cloned = srcRows.map((row) => ({
                project_id: row.project_id,
                project_stage_instance_id: row.project_stage_instance_id,
                project_option_id: row.project_option_id ?? null,
                metric_id: null,
                quantity: row.quantity ?? 0,
                unit_id: null,
                ui_table_key: sk,
                extra_fields: { ...row.extra_fields, modelled_year: activeLargeUsersYear },
                ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
            }));
            const payload = [
                ...otherRows.map((row) => toYearUpsert(row, sk, projectMitigationId)),
                ...cloned,
            ];
            if (payload.length > 0) {
                await ActivityDataService.bulkUpsert(
                    activeStageInstance.id,
                    sk,
                    payload,
                    projectMitigationId ?? undefined,
                );
            }
        }
        setCopyLargeYearConfirmOpen(false);
        setCopyLargeYearSource(null);
        setUsersRefreshKey((k) => k + 1);
    };

    const handleDeleteLargeYear = async () => {
        if (activeLargeUsersYear === null || !activeStageInstance) return;
        for (const key of LARGE_USER_YEAR_TABLES) {
            const sk = scopeKey(key);
            const all = await ActivityDataService.fetchRows(
                activeStageInstance.id,
                sk,
                activeOptionId ?? null,
                undefined,
                projectMitigationId ?? undefined,
            );
            const remaining = all.filter((row) => getModelledYear(row) !== activeLargeUsersYear);
            const toDelete = all.filter((row) => getModelledYear(row) === activeLargeUsersYear);
            if (remaining.length > 0) {
                await ActivityDataService.bulkUpsert(
                    activeStageInstance.id,
                    sk,
                    remaining.map((row) => toYearUpsert(row, sk, projectMitigationId)),
                    projectMitigationId ?? undefined,
                );
            } else {
                for (const row of toDelete) await ActivityDataService.deleteRow(row.id);
            }
        }
        const newYears = largeUsersYears.filter((y) => y !== activeLargeUsersYear).sort((a, b) => a - b);
        setLargeUsersYears(newYears);
        setActiveLargeUsersYear(newYears[0] ?? null);
        setDeleteLargeYearConfirmOpen(false);
        setUsersRefreshKey((k) => k + 1);
    };

    return {
        largeUsersYears,
        setLargeUsersYears,
        activeLargeUsersYear,
        setActiveLargeUsersYear,
        addLargeYearOpen,
        setAddLargeYearOpen,
        addLargeYearInput,
        setAddLargeYearInput,
        addLargeYearError,
        setAddLargeYearError,
        copyLargeYearSource,
        setCopyLargeYearSource,
        copyLargeYearConfirmOpen,
        setCopyLargeYearConfirmOpen,
        deleteLargeYearConfirmOpen,
        setDeleteLargeYearConfirmOpen,
        usersRefreshKey,
        setUsersRefreshKey,
        handleAddLargeYear,
        handleCopyLargeYear,
        handleDeleteLargeYear,
    };
}
