import { useState, useRef, useEffect, useCallback } from "react";
import ActivityDataService from "@/services/ActivityData.service";
import { useOutsideClick } from "../useOutsideClick";
import {
    mitigationUiKey,
    type MitigationSubstitutionLeg,
} from "../mitigationConstants";

interface UseLargeUserYearsParams {
    isUsersSubStage: boolean;
    activeStageInstance: any | null;
    activeOptionId: string | null;
    projectClass: string | null;
    isLargeUsersNZ: boolean;
    opsStartYear: number | null;
    projectId: string | null;
    projectMitigationId?: string | null;
    mitigationSubstitutionLeg?: MitigationSubstitutionLeg | null;
}

const LARGE_USER_YEAR_TABLES = ["largeRoadParams", "largeRoadUsers", "largeRailUsers"] as const;

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
    const [yearMenuOpen, setYearMenuOpen] = useState(false);
    const [addLargeYearOpen, setAddLargeYearOpen] = useState(false);
    const [addLargeYearInput, setAddLargeYearInput] = useState("");
    const [addLargeYearError, setAddLargeYearError] = useState<string | null>(null);
    const [copyLargeYearSource, setCopyLargeYearSource] = useState<number | null>(null);
    const [copyLargeYearConfirmOpen, setCopyLargeYearConfirmOpen] = useState(false);
    const [deleteLargeYearConfirmOpen, setDeleteLargeYearConfirmOpen] = useState(false);
    const [usersRefreshKey, setUsersRefreshKey] = useState(0);

    const yearMenuRef = useRef<HTMLDivElement>(null);
    useOutsideClick(yearMenuRef, () => setYearMenuOpen(false), yearMenuOpen);

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
            ) as any[];
            if (cancelled) return;
            const years = [
                ...new Set(
                    rows
                        .map((r: any) => r.extra_fields?.modelled_year)
                        .filter((y: any) => typeof y === "number") as number[]
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
        if (!activeStageInstance) return;
        const sk = scopeKey("largeRoadParams");
        const existing = await ActivityDataService.fetchRows(
            activeStageInstance.id,
            sk,
            activeOptionId ?? null,
            undefined,
            projectMitigationId ?? undefined,
        ) as any[];
        const skeleton = {
            project_id: projectId!,
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
            ...existing.map((r: any) => ({
                project_id: r.project_id,
                project_stage_instance_id: r.project_stage_instance_id,
                project_option_id: r.project_option_id,
                metric_id: null,
                quantity: r.quantity ?? 0,
                unit_id: null,
                ui_table_key: sk,
                extra_fields: r.extra_fields,
                ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
            })),
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
            ) as any[];
            const srcRows = all.filter((r: any) => r.extra_fields?.modelled_year === copyLargeYearSource);
            const otherRows = all.filter((r: any) => r.extra_fields?.modelled_year !== activeLargeUsersYear);
            const cloned = srcRows.map((r: any) => ({
                project_id: r.project_id,
                project_stage_instance_id: r.project_stage_instance_id,
                project_option_id: r.project_option_id,
                metric_id: null,
                quantity: r.quantity ?? 0,
                unit_id: null,
                ui_table_key: sk,
                extra_fields: { ...r.extra_fields, modelled_year: activeLargeUsersYear },
                ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
            }));
            const payload = [
                ...otherRows.map((r: any) => ({
                    project_id: r.project_id,
                    project_stage_instance_id: r.project_stage_instance_id,
                    project_option_id: r.project_option_id,
                    metric_id: null,
                    quantity: r.quantity ?? 0,
                    unit_id: null,
                    ui_table_key: sk,
                    extra_fields: r.extra_fields,
                    ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
                })),
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
            ) as any[];
            const remaining = all.filter((r: any) => r.extra_fields?.modelled_year !== activeLargeUsersYear);
            const toDelete = all.filter((r: any) => r.extra_fields?.modelled_year === activeLargeUsersYear);
            if (remaining.length > 0) {
                await ActivityDataService.bulkUpsert(
                    activeStageInstance.id,
                    sk,
                    remaining.map((r: any) => ({
                        project_id: r.project_id,
                        project_stage_instance_id: r.project_stage_instance_id,
                        project_option_id: r.project_option_id,
                        metric_id: null,
                        quantity: r.quantity ?? 0,
                        unit_id: null,
                        ui_table_key: sk,
                        extra_fields: r.extra_fields,
                        ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
                    })),
                    projectMitigationId ?? undefined,
                );
            } else {
                for (const r of toDelete) await ActivityDataService.deleteRow(r.id);
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
        yearMenuOpen,
        setYearMenuOpen,
        yearMenuRef,
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