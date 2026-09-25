import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { NumericInput } from "@/components/common/NumericInput";
import { SelectListbox } from "@/components/common/Select";
import ActivityDataService from "@/services/ActivityData.service";
import type { ActivityDataCreate } from "@/services/ActivityData.service";
import { emptySummary, UserEmissionsSummary } from "./UserEmissionSummary";
import EmissionCalculationsService from "@/services/EmissionCalculations.service";
import {
    mitigationUiKey,
    type MitigationSubstitutionLeg,
} from "./mitigationConstants";
import InfoTooltip from "@/components/common/InfoTooltip";

const AU_VEHICLE_TYPES = [
    "Small Car",
    "Medium Car",
    "Large Car",
    "Courier Van-Utility",
    "4WD Mid Size Petrol",
    "Light Rigid",
    "Medium Rigid",
    "Heavy Rigid",
    "Heavy Bus",
    "Artic 4 Axle",
    "Artic 5 Axle",
    "Artic 6 Axle",
    "Rigid + 5 Axle Dog",
    "B-Double",
    "Twin steer + 5 Axle Dog",
    "A-Double",
    "B Triple",
    "A B Combination",
    "A-Triple",
    "Double B-Double",
];

const NZ_ROAD_VEHICLE_TYPES = [
    "General Fleet",
    "Light Vehicle",
    "Heavy Vehicle",
    "Bus",
];


const ROUGHNESS_OPTIONS = [
    { label: "Very smooth (IRI = 1 m/km)", value: "Very smooth" },
    { label: "Smooth (IRI = 2 m/km)", value: "Smooth" },
    { label: "Moderate (IRI = 3 m/km)", value: "Moderate" },
    { label: "Rough (IRI = 4 m/km)", value: "Rough" },
    { label: "Very rough (IRI = 5 m/km)", value: "Very rough" },
    { label: "Severely Rough (IRI = 6 m/km)", value: "Severely Rough" },
];

const GRADIENT_OPTIONS = [
    { label: "Flat (0 m/km)", value: "Flat" },
    { label: "Moderate (40 m/km)", value: "Moderate" },
    { label: "Steep (60 m/km)", value: "Steep" },
    { label: "Very steep (80 m/km)", value: "Very steep" },
];

const CURVATURE_OPTIONS = [
    { label: "Straight (20 deg/km)", value: "Straight" },
    { label: "Gently curved (120 deg/km)", value: "Gently curved" },
    { label: "Very winding (300 deg/km)", value: "Very winding" },
];

const EV_UPTAKE_OPTIONS = [
    { label: "Step Change", value: "Step Change" },
    { label: "Accelerated Transition", value: "Accelerated Transition" },
    { label: "Slower Growth", value: "Slower Growth" },
];


interface LargeRoadRow {
    id: string;
    vehicleType: string;
    vkt: string;
    vht: string;
    avgSpeed: string;
    lastEdited: "vht" | "avgSpeed" | null;
    notes: string;
}

interface RoadParams {
    ev_uptake_scenario: string;
    roughness: string;
    gradient: string;
    curvature: string;
}

interface YearData {
    params: RoadParams;
    rows: LargeRoadRow[];
}

const DEFAULT_ROAD_PARAMS: RoadParams = {
    ev_uptake_scenario: "Step Change",
    roughness: "Smooth",
    gradient: "Flat",
    curvature: "Straight",
};



const normalizeCalculationSummary = (summary: any) => ({
    absoluteEmissions:
        summary?.interim_total_tco2e ??
        summary?.absoluteEmissions ??
        summary?.absolute_emissions ??
        summary?.absolute_emissions_tco2e ??
        0,

    baseCaseAbsoluteEmissions:
        summary?.base_case_emissions_tco2e ??
        summary?.baseCaseAbsoluteEmissions ??
        summary?.base_case_absolute_emissions ??
        summary?.base_case_absolute_emissions_tco2e ??
        null,

    relativeUserEmissions:
        summary?.final_user_emissions_tco2e ??
        summary?.relativeUserEmissions ??
        summary?.relative_user_emissions ??
        summary?.relative_user_emissions_tco2e ??
        null,
});

const isNewZealandJurisdiction = (jurisdiction?: string | null): boolean => {
    const value = (jurisdiction ?? "").trim().toLowerCase();
    return (
        value === "nz" ||
        value === "nzl" ||
        value.includes("new zealand")
    );
};

interface Props {
    stageInstanceId: string;
    projectId: string;
    optionId?: string | null;
    refreshKey?: number;
    readOnly?: boolean;
    jurisdiction: string | null;
    opsStartYear: number | null;
    activeYear: number | null;
    largeUsersYears?: number[];
    onActiveYearChange?: (year: number) => void;
    onOpenAddYear?: () => void;
    onOpenCopyYear?: () => void;
    onOpenDeleteYear?: () => void;
    projectTypeName?: string | null;
    projectMitigationId?: string | null;
    mitigationSubstitutionLeg?: MitigationSubstitutionLeg | null;
    onTotalsUpdated?: () => void | Promise<void>;
}

function computeDerived(row: LargeRoadRow): LargeRoadRow {
    const vktNum = parseFloat(row.vkt);
    if (isNaN(vktNum) || vktNum <= 0) return row;
    if (row.lastEdited === "vht") {
        const vhtNum = parseFloat(row.vht);
        return { ...row, avgSpeed: (!isNaN(vhtNum) && vhtNum > 0) ? (vktNum / vhtNum).toFixed(2) : "" };
    }
    if (row.lastEdited === "avgSpeed") {
        const speedNum = parseFloat(row.avgSpeed);
        return { ...row, vht: (!isNaN(speedNum) && speedNum > 0) ? (vktNum / speedNum).toFixed(2) : "" };
    }
    return row;
}

function emptyYearData(vehicleTypes: string[]): YearData {
    return {
        params: { ...DEFAULT_ROAD_PARAMS },
        rows: vehicleTypes.map((vt, i) => ({
            id: `road-new-${i}`,
            vehicleType: vt,
            vkt: "",
            vht: "",
            avgSpeed: "",
            lastEdited: null,
            notes: "",
        })),
    };
}

const toNumberOrNull = (value: any): number | null => {
    if (value === "" || value == null) return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
};

const getSpeed = (row: LargeRoadRow): number | null => {
    const speed = toNumberOrNull(row.avgSpeed);
    if (speed != null) return speed;
    const vkt = toNumberOrNull(row.vkt);
    const vht = toNumberOrNull(row.vht);
    if (vkt != null && vht != null && vht > 0) return vkt / vht;
    return null;
};

const isLargeRoadRowComplete = (row: LargeRoadRow) => {
    return toNumberOrNull(row.vkt) != null && getSpeed(row) != null;
};



const LargeRoadUsersSubStage = ({
    stageInstanceId,
    projectId,
    optionId,
    refreshKey,
    readOnly = false,
    jurisdiction,
    opsStartYear: _opsStartYear,
    activeYear,
    largeUsersYears = [],
    onActiveYearChange,
    onOpenAddYear,
    onOpenCopyYear,
    onOpenDeleteYear,
    projectMitigationId = null,
    mitigationSubstitutionLeg = null,
    onTotalsUpdated,
}: Props) => {
    const isNZ = isNewZealandJurisdiction(jurisdiction);

    const scopeUiTableKey = useCallback(
        (base: string) =>
            projectMitigationId
                ? mitigationUiKey(base, mitigationSubstitutionLeg ?? undefined)
                : base,
        [projectMitigationId, mitigationSubstitutionLeg],
    );

    const vehicleTypes = useMemo(() => {
        return isNZ ? NZ_ROAD_VEHICLE_TYPES : AU_VEHICLE_TYPES;
    }, [isNZ]);

    const [yearData, setYearData] = useState<Record<number, YearData>>({});
    const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
    const [expanded, setExpanded] = useState(true);

    const [emissionSummary, setEmissionSummary] = useState<any>(emptySummary);
    const [emissionLoading, setEmissionLoading] = useState(false);
    const [globalParams, setGlobalParams] = useState<RoadParams>(DEFAULT_ROAD_PARAMS);

    const [yearMenuOpen, setYearMenuOpen] = useState(false);
    const yearMenuRef = useRef<HTMLDivElement>(null);

    const getAllModelledYears = useCallback(
        (allYearData: Record<number, YearData>) => {
            return Array.from(
                new Set([
                    ...largeUsersYears,
                    ...Object.keys(allYearData).map(Number),
                    ...(activeYear != null ? [activeYear] : []),
                ])
            ).sort((a, b) => a - b);
        },
        [largeUsersYears, activeYear]
    );


    const availableModelledYears = useMemo(() => {
        return Array.from(
            new Set([
                ...largeUsersYears,
                ...Object.keys(yearData).map(Number),
                ...(activeYear != null ? [activeYear] : []),
            ])
        ).sort((a, b) => a - b);
    }, [largeUsersYears, yearData]);

    const displayedActiveYear =
        activeYear ??
        availableModelledYears[0] ??
        null;


    const activeYearData = useMemo(() => {
        if (displayedActiveYear === null) return null;

        return (
            yearData[displayedActiveYear] ?? {
                ...emptyYearData(vehicleTypes),
                params: globalParams,
            }
        );
    }, [displayedActiveYear, yearData, vehicleTypes, globalParams]);



    useEffect(() => {
        if (activeYear == null && availableModelledYears.length > 0) {
            onActiveYearChange?.(availableModelledYears[0]);
        }
    }, [activeYear, availableModelledYears, onActiveYearChange]);


    useEffect(() => {
        if (!stageInstanceId) return;

        let cancelled = false;

        (async () => {
            try {
                const [paramsRows, userRows] = await Promise.all([
                    ActivityDataService.fetchRows(
                        stageInstanceId,
                        scopeUiTableKey("largeRoadParams"),
                        optionId ?? null,
                        undefined,
                        projectMitigationId ?? undefined,
                    ),
                    ActivityDataService.fetchRows(
                        stageInstanceId,
                        scopeUiTableKey("largeRoadUsers"),
                        optionId ?? null,
                        undefined,
                        projectMitigationId ?? undefined,
                    ),
                ]);

                if (cancelled) return;

                const firstParamsExtra = paramsRows.find((r: any) => r.extra_fields)?.extra_fields;

                const loadedGlobalParams: RoadParams = {
                    ev_uptake_scenario:
                        firstParamsExtra?.ev_uptake_scenario ??
                        DEFAULT_ROAD_PARAMS.ev_uptake_scenario,
                    roughness:
                        firstParamsExtra?.roughness ??
                        DEFAULT_ROAD_PARAMS.roughness,
                    gradient:
                        firstParamsExtra?.gradient ??
                        DEFAULT_ROAD_PARAMS.gradient,
                    curvature:
                        firstParamsExtra?.curvature ??
                        DEFAULT_ROAD_PARAMS.curvature,
                };

                setGlobalParams(loadedGlobalParams);
                setEmissionSummary(normalizeCalculationSummary(firstParamsExtra));

                const built: Record<number, YearData> = {};

                for (const row of paramsRows) {
                    const year = row.extra_fields?.modelled_year;
                    if (typeof year !== "number") continue;

                    built[year] = {
                        params: loadedGlobalParams,
                        rows: vehicleTypes.map((vt, i) => ({
                            id: `road-empty-${year}-${i}`,
                            vehicleType: vt,
                            vkt: "",
                            vht: "",
                            avgSpeed: "",
                            lastEdited: null,
                            notes: "",
                        })),
                    };
                }

                for (const row of userRows) {
                    const year = row.extra_fields?.modelled_year;
                    if (typeof year !== "number") continue;

                    if (!built[year]) {
                        built[year] = {
                            ...emptyYearData(vehicleTypes),
                            params: loadedGlobalParams,
                        };
                    }

                    const vt = row.extra_fields?.vehicle_type;
                    const idx = built[year].rows.findIndex((r) => r.vehicleType === vt);

                    if (idx >= 0) {
                        built[year].rows[idx] = {
                            id: row.id,
                            vehicleType: vt,
                            vkt: row.extra_fields?.vkt != null ? String(row.extra_fields.vkt) : "",
                            vht: row.extra_fields?.vht != null ? String(row.extra_fields.vht) : "",
                            avgSpeed: row.extra_fields?.avg_speed != null ? String(row.extra_fields.avg_speed) : "",
                            lastEdited: row.extra_fields?.last_edited ?? null,
                            notes: row.extra_fields?.notes ?? "",
                        };
                    }
                }
                for (const year of largeUsersYears) {
                    if (!built[year]) {
                        built[year] = {
                            ...emptyYearData(vehicleTypes),
                            params: loadedGlobalParams,
                        };
                    }
                }

                setYearData(built);
            } catch (e) {
                console.error("Failed to load large road users data:", e);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [
        stageInstanceId,
        optionId,
        refreshKey,
        vehicleTypes,
        largeUsersYears,
        scopeUiTableKey,
        projectMitigationId,
    ]);

    const buildLargeNzRoadPayload = useCallback(
        (allYearData: Record<number, YearData>) => {
            const years = getAllModelledYears(allYearData);

            const anchor_years = years
                .map((year) => {
                    const rows =
                        allYearData[year]?.rows ??
                        emptyYearData(vehicleTypes).rows;

                    const vehicles = rows
                        .filter(isLargeRoadRowComplete)
                        .map((row) => ({
                            vehicle_type: row.vehicleType
                                .toLowerCase()
                                .replace(/\s+/g, "_"),
                            vkt: Number(row.vkt),
                            speed_kmh: Number(getSpeed(row)),
                        }));

                    return {
                        year,
                        vehicles,
                    };
                })
                .filter((anchorYear) => anchorYear.vehicles.length > 0);

            if (!anchor_years.length) return null;

            return {
                project_id: projectId,
                project_option_id: optionId,
                project_stage_instance_id: stageInstanceId,
                anchor_years,
            };
        },
        [
            projectId,
            optionId,
            stageInstanceId,
            vehicleTypes,
            getAllModelledYears,
        ]
    );

    const buildLargeAusRoadPayload = useCallback(
        (
            allYearData: Record<number, YearData>,
            params: RoadParams
        ) => {
            const years = getAllModelledYears(allYearData);

            const anchor_years = years
                .map((year) => {
                    const rows =
                        allYearData[year]?.rows ??
                        emptyYearData(vehicleTypes).rows;

                    const vehicles = rows
                        .filter(isLargeRoadRowComplete)
                        .map((row) => ({
                            vehicle_type: row.vehicleType,
                            vkt: Number(row.vkt),
                            average_speed_kph: Number(getSpeed(row)),
                        }));

                    return {
                        year,
                        vehicles,
                    };
                })
                .filter((anchorYear) => anchorYear.vehicles.length > 0);

            if (!anchor_years.length) return null;

            return {
                project_id: projectId,
                project_option_id: optionId,
                project_stage_instance_id: stageInstanceId,
                roughness: params.roughness,
                gradient: params.gradient,
                curvature: params.curvature,
                ev_uptake_scenario: params.ev_uptake_scenario,
                anchor_years,
            };
        },
        [
            projectId,
            optionId,
            stageInstanceId,
            vehicleTypes,
            getAllModelledYears,
        ]
    );

    const calculateLargeNzRoadSummary = useCallback(
        async (yearData: Record<number, YearData>): Promise<any | null> => {
            const payload = buildLargeNzRoadPayload(yearData);

            if (!payload) return null;

            try {
                setEmissionLoading(true);

                const summary =
                    await EmissionCalculationsService.calculateLargeNzRoads(payload);

                const normalized = normalizeCalculationSummary(summary);

                setEmissionSummary(normalized);

                return normalized;
            } catch (e) {
                console.error("NZ road calculation failed:", e);
                return null;
            } finally {
                setEmissionLoading(false);
            }
        },
        [buildLargeNzRoadPayload]
    );

    const persistAll = useCallback(
        async (
            allYearData: Record<number, YearData>,
            params: RoadParams = globalParams,
            summary: any = emissionSummary
        ) => {
            if (readOnly) return;

            setSaveState("saving");

            try {
                const years = getAllModelledYears(allYearData);
                const paramsSk = scopeUiTableKey("largeRoadParams");
                const usersSk = scopeUiTableKey("largeRoadUsers");

                const allParamsPayload: ActivityDataCreate[] = years.map((year) => ({
                    project_id: projectId,
                    project_stage_instance_id: stageInstanceId,
                    project_option_id: optionId ?? null,
                    metric_id: null,
                    quantity: 0,
                    unit_id: null,
                    ui_table_key: paramsSk,
                    extra_fields: {
                        modelled_year: year,

                        ev_uptake_scenario: params.ev_uptake_scenario,
                        roughness: params.roughness,
                        gradient: params.gradient,
                        curvature: params.curvature,

                        interim_total_tco2e: summary?.absoluteEmissions ?? null,
                        base_case_emissions_tco2e:
                            summary?.baseCaseAbsoluteEmissions ?? null,
                        final_user_emissions_tco2e:
                            summary?.relativeUserEmissions ?? null,
                    },
                    ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
                }));

                const allUsersPayload: ActivityDataCreate[] = years.flatMap((year) => {
                    const rows = allYearData[year]?.rows ?? [];

                    return rows
                        .filter((r) => toNumberOrNull(r.vkt) != null)
                        .map((r) => ({
                            project_id: projectId,
                            project_stage_instance_id: stageInstanceId,
                            project_option_id: optionId ?? null,
                            metric_id: null,
                            quantity: toNumberOrNull(r.vkt) ?? 0,
                            unit_id: null,
                            ui_table_key: usersSk,
                            extra_fields: {
                                modelled_year: year,
                                vehicle_type: r.vehicleType,
                                vkt: r.vkt,
                                vht: r.vht || null,
                                avg_speed: r.avgSpeed || null,
                                last_edited: r.lastEdited,
                                notes: r.notes || null,
                            },
                            ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
                        }));
                });

                if (allParamsPayload.length > 0) {
                    await ActivityDataService.bulkUpsert(
                        stageInstanceId,
                        paramsSk,
                        allParamsPayload,
                        projectMitigationId ?? undefined,
                    );
                }

                if (allUsersPayload.length > 0) {
                    await ActivityDataService.bulkUpsert(
                        stageInstanceId,
                        usersSk,
                        allUsersPayload,
                        projectMitigationId ?? undefined,
                    );
                }
                await onTotalsUpdated?.();

                setSaveState("saved");
                setTimeout(() => setSaveState("idle"), 2000);
            } catch (e) {
                console.error("Failed to save large road users data:", e);
                setSaveState("idle");
            }
        },
        [
            stageInstanceId,
            projectId,
            optionId,
            readOnly,
            globalParams,
            emissionSummary,
            getAllModelledYears,
            scopeUiTableKey,
            projectMitigationId,
            onTotalsUpdated,
        ]
    );

    const calculateLargeAusRoadSummary = useCallback(
        async (
            allYearData: Record<number, YearData>,
            params: RoadParams
        ): Promise<any | null> => {
            const payload = buildLargeAusRoadPayload(allYearData, params);

            if (!payload) return null;

            try {
                setEmissionLoading(true);

                const summary =
                    await EmissionCalculationsService.calculateLargeAusRoads(payload);

                const normalizedSummary = normalizeCalculationSummary(summary);

                setEmissionSummary(normalizedSummary);

                return normalizedSummary;
            } catch (e) {
                console.error("Failed to calculate large road user emissions:", e);
                return null;
            } finally {
                setEmissionLoading(false);
            }
        },
        [buildLargeAusRoadPayload]
    );

    const handleSaveLargeRoadUsers = useCallback(async () => {
        if (readOnly) return;

        try {
            const calculatedSummary = isNZ
                ? await calculateLargeNzRoadSummary(yearData)
                : await calculateLargeAusRoadSummary(yearData, globalParams);

            await persistAll(
                yearData,
                globalParams,
                calculatedSummary ?? emissionSummary
            );
        } catch (e) {
            console.error("Failed to save large road users data:", e);
        }
    }, [
        readOnly,
        isNZ,
        yearData,
        globalParams,
        emissionSummary,
        calculateLargeNzRoadSummary,
        calculateLargeAusRoadSummary,
        persistAll,
    ]);

    const updateRow = (rowId: string, changes: Partial<LargeRoadRow>) => {
        if (readOnly || displayedActiveYear === null) return;

        setYearData((prev) => {
            const yd =
                prev[displayedActiveYear] ?? {
                    ...emptyYearData(vehicleTypes),
                    params: globalParams,
                };

            return {
                ...prev,
                [displayedActiveYear]: {
                    ...yd,
                    rows: yd.rows.map((row) =>
                        row.id !== rowId
                            ? row
                            : computeDerived({
                                ...row,
                                ...changes,
                            })
                    ),
                },
            };
        });
    };

    const updateParams = (changes: Partial<RoadParams>) => {
        if (readOnly) return;

        setGlobalParams((prevParams) => {
            const nextParams: RoadParams = {
                ...prevParams,
                ...changes,
            };

            setYearData((prevYearData) => {
                const nextYearData: Record<number, YearData> = {};

                for (const [year, data] of Object.entries(prevYearData)) {
                    nextYearData[Number(year)] = {
                        ...data,
                        params: nextParams,
                    };
                }

                return nextYearData;
            });

            return nextParams;
        });
    };

    useEffect(() => {
        if (!yearMenuOpen) return;

        const handler = (e: MouseEvent) => {
            if (
                yearMenuRef.current &&
                !yearMenuRef.current.contains(e.target as Node)
            ) {
                setYearMenuOpen(false);
            }
        };

        document.addEventListener("mousedown", handler);

        return () => {
            document.removeEventListener("mousedown", handler);
        };
    }, [yearMenuOpen]);

    useEffect(() => {
        if (!largeUsersYears.length) return;

        setYearData((prev) => {
            let changed = false;
            const next = { ...prev };

            for (const year of largeUsersYears) {
                if (!next[year]) {
                    next[year] = {
                        ...emptyYearData(vehicleTypes),
                        params: globalParams,
                    };
                    changed = true;
                }
            }

            return changed ? next : prev;
        });
    }, [largeUsersYears, vehicleTypes, globalParams]);

    return (
        <div className="mx-12 mb-8 bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)]">
            <div className="flex items-center justify-between mb-4">
                <div className="text-2xl font-light text-text-dark flex items-center gap-1">
                    Road users
                    {/* <span
                        className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-neutral-700 text-white text-xs ml-1 cursor-help"
                        title="Large project road user traffic data — enter VKT for each vehicle type per modelled year. Enter either VHT or Avg Speed; the other is computed automatically."
                    >?</span> */}
                    <InfoTooltip
                        text="The user emissions attributable to each option for B8 are only the change in emissions relative to the Base Case. The Base Case is assigned 0 emissions for B8."
                        iconSize={20}
                        trigger="auto"
                        placement="top"
                        offset={10}
                        arrowOffset={20}
                    />
                </div>
                <div className="flex items-center gap-3">
                    {saveState === "saving" && (
                        <span className="text-xs text-text-faint animate-pulse">Saving…</span>
                    )}
                    {saveState === "saved" && (
                        <span className="text-xs text-success">Saved</span>
                    )}
                    <button
                        type="button"
                        onClick={() => setExpanded(v => !v)}
                        className="w-5 h-5 inline-flex items-center justify-center  cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary rounded"
                    >
                        <span className="material-symbols-rounded">
                            {expanded ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                        </span>
                    </button>
                </div>
            </div>

            {/* Outside accordion */}
            <UserEmissionsSummary
                summary={emissionSummary}
                loading={emissionLoading}
            />

            {expanded && (
                <>
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                        {/* Left side: Modelled year dropdown + vertical menu */}
                        <div className="flex flex-wrap items-center gap-3">
                            <span className="text-sm text-text-base font-medium mr-12">
                                Modelled year: 
                            </span>

                            {availableModelledYears.length > 0 ? (
                                <SelectListbox
                                    value={String(displayedActiveYear ?? "")}
                                    options={availableModelledYears.map((year) => ({
                                        label: String(year),
                                        value: String(year),
                                    }))}
                                    onChange={(val: string) =>
                                        onActiveYearChange?.(Number(val))
                                    }
                                    disabled={readOnly}
                                    className="h-9 w-48"
                                />
                            ) : (
                                <span className="text-sm text-text-faint italic">
                                    No years
                                </span>
                            )}

                            {!readOnly && (
                                <div className="relative" ref={yearMenuRef}>
                                    <button
                                        type="button"
                                        className="p-2 rounded hover:bg-neutral-200 cursor-pointer transition-colors"
                                        onClick={() => setYearMenuOpen((open) => !open)}
                                        aria-label="More modelled year options"
                                    >
                                        <span className="material-symbols-rounded">
                                            more_vert
                                        </span>
                                    </button>

                                    {yearMenuOpen && (
                                        <div className="absolute left-0 mt-1 w-48 rounded-lg border border-neutral-200 bg-white shadow-lg z-30 py-1">
                                            <button
                                                type="button"
                                                className="w-full text-left px-4 cursor-pointer py-2 text-sm hover:bg-neutral-50"
                                                onClick={() => {
                                                    setYearMenuOpen(false);
                                                    onOpenAddYear?.();
                                                }}
                                            >
                                                Add year
                                            </button>

                                            {availableModelledYears.length > 1 && (
                                                <button
                                                    type="button"
                                                    className="w-full text-left px-4 py-2 cursor-pointer text-sm hover:bg-neutral-50"
                                                    onClick={() => {
                                                        setYearMenuOpen(false);
                                                        onOpenCopyYear?.();
                                                    }}
                                                >
                                                    Copy from…
                                                </button>
                                            )}

                                            {displayedActiveYear !== null && (
                                                <button
                                                    type="button"
                                                    className="w-full text-left px-4 py-2 text-sm cursor-pointer text-danger hover:bg-red-50"
                                                    onClick={() => {
                                                        setYearMenuOpen(false);
                                                        onOpenDeleteYear?.();
                                                    }}
                                                >
                                                    Delete year {displayedActiveYear}
                                                </button>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Right side: Save button */}
                        {!readOnly && (
                            <button
                                type="button"
                                className="px-3 py-2 text-sm bg-primary text-white rounded cursor-pointer ml-auto disabled:opacity-50"
                                disabled={readOnly || saveState === "saving" || emissionLoading}
                                onClick={() => void handleSaveLargeRoadUsers()}
                            >
                                Save
                            </button>
                        )}
                    </div>
                    {!isNZ && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div className="flex items-center gap-2">
                        <label className="text-sm font-medium text-text-base min-w-[145px]">
                            EV Uptake Scenario:
                        </label>
                        <SelectListbox
                            value={globalParams.ev_uptake_scenario}
                            options={EV_UPTAKE_OPTIONS}
                            onChange={(val: string) =>
                                updateParams({ ev_uptake_scenario: val })
                            }
                            disabled={readOnly}
                            className="h-9 flex-1"
                            minMenuWidth={240}
                        />

                    </div>

                    <div className="flex items-center gap-2">
                        <label className="text-sm font-medium text-text-base min-w-[145px]">
                            Roughness:
                        </label>
                        <SelectListbox
                            value={globalParams.roughness}
                            options={ROUGHNESS_OPTIONS}
                            onChange={(val: string) =>
                                updateParams({ roughness: val })
                            }
                            disabled={readOnly}
                            className="h-9 flex-1"
                            minMenuWidth={260}
                        />
                    </div>

                    <div className="flex items-center gap-2">
                        <label className="text-sm font-medium text-text-base min-w-[145px]">
                            Gradient:
                        </label>
                        <SelectListbox
                            value={globalParams.gradient}
                            options={GRADIENT_OPTIONS}
                            onChange={(val: string) =>
                                updateParams({ gradient: val })
                            }
                            disabled={readOnly}
                            className="h-9 flex-1 w-full"
                            minMenuWidth={240}
                        />

                    </div>

                    <div className="flex items-center gap-2">
                        <label className="text-sm font-medium text-text-base min-w-[145px]">
                            Curvature:
                        </label>
                        <SelectListbox
                            value={globalParams.curvature}
                            options={CURVATURE_OPTIONS}
                            onChange={(val: string) =>
                                updateParams({ curvature: val })
                            }
                            disabled={readOnly}
                            className="h-9 flex-1 w-full"
                            minMenuWidth={260}
                        />

                    </div>
                </div>
            )}

                    {activeYearData ? (
                        <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="border-b border-neutral-200 text-xs font-medium text-text-base">
                                        <th className="px-4 py-3 text-left w-52">
                                            Vehicle type
                                        </th>
                                        <th className="px-4 py-3 text-right">
                                            Average Annual VKT
                                            <span className="text-danger">*</span>
                                        </th>
                                        <th className="px-4 py-3 text-right">
                                            Average Annual VHT
                                        </th>
                                        <th className="px-4 py-3 text-right">
                                            Average Speed (km/h)
                                        </th>
                                        <th className="px-4 py-3 text-left">
                                            Notes / Comments{" "}
                                            <span className="font-normal">
                                                (optional)
                                            </span>
                                        </th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {activeYearData.rows.map((row) => {
                                        const vhtIsComputed =
                                            row.lastEdited === "avgSpeed";
                                        const speedIsComputed =
                                            row.lastEdited === "vht";

                                        return (
                                            <tr
                                                key={row.id}
                                                className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50 text-text-table-cell"
                                            >
                                                <td className="px-4 py-3 bg-neutral-95 text-xs">
                                                    {row.vehicleType}
                                                </td>

                                                <td className="px-4 py-2">
                                                    <NumericInput
                                                        value={row.vkt}
                                                        onChange={(v: any) =>
                                                            updateRow(row.id, {
                                                                vkt:
                                                                    v != null
                                                                        ? String(v)
                                                                        : "",
                                                            })
                                                        }
                                                        onCommit={() => { }}
                                                        allowDecimal
                                                        disabled={readOnly}
                                                    />
                                                </td>

                                                <td className="px-4 py-2">
                                                    <div className="relative">
                                                        <NumericInput
                                                            value={row.vht}
                                                            onChange={(v: any) =>
                                                                updateRow(row.id, {
                                                                    vht:
                                                                        v != null
                                                                            ? String(v)
                                                                            : "",
                                                                    lastEdited:
                                                                        "vht",
                                                                })
                                                            }
                                                            onCommit={() => { }}
                                                            allowDecimal
                                                            disabled={readOnly}
                                                            className={
                                                                vhtIsComputed
                                                                    ? "bg-neutral-50 text-text-faint"
                                                                    : ""
                                                            }
                                                        />

                                                        {vhtIsComputed && (
                                                            <span
                                                                className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-neutral-400 pointer-events-none select-none"
                                                                title="Computed from VKT ÷ Speed"
                                                            >
                                                                auto
                                                            </span>
                                                        )}
                                                    </div>
                                                </td>

                                                <td className="px-4 py-2">
                                                    <div className="relative">
                                                        <NumericInput
                                                            value={row.avgSpeed}
                                                            onChange={(v: any) =>
                                                                updateRow(row.id, {
                                                                    avgSpeed:
                                                                        v != null
                                                                            ? String(v)
                                                                            : "",
                                                                    lastEdited:
                                                                        "avgSpeed",
                                                                })
                                                            }
                                                            onCommit={() => { }}
                                                            allowDecimal
                                                            disabled={readOnly}
                                                            className={
                                                                speedIsComputed
                                                                    ? "bg-neutral-50 text-text-faint"
                                                                    : ""
                                                            }
                                                        />

                                                        {speedIsComputed && (
                                                            <span
                                                                className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-neutral-400 pointer-events-none select-none"
                                                                title="Computed from VKT ÷ VHT"
                                                            >
                                                                auto
                                                            </span>
                                                        )}
                                                    </div>
                                                </td>

                                                <td className="px-4 py-2">
                                                    <input
                                                        className="h-10 w-full border border-border-input rounded px-2 py-1 text-sm"
                                                        value={row.notes}
                                                        onChange={(e) =>
                                                            updateRow(row.id, {
                                                                notes: e.target.value,
                                                            })
                                                        }
                                                        disabled={readOnly}
                                                    />
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>

                            <p className="mt-2 text-xs text-text-faint">
                                <span className="text-danger">*</span> Avg Annual
                                VKT is required. Enter either{" "}
                                <strong>VHT</strong> or{" "}
                                <strong>Avg Speed</strong> — the other calculates
                                automatically using{" "}
                                <em>VKT = Speed × VHT</em>. Fields marked{" "}
                                <span className="font-medium">auto</span> are
                                computed and update as you type.
                            </p>
                        </div>
                    ) : (
                        <p className="text-sm text-text-faint italic py-4">
                            Select a modelled year above to view road user data.
                        </p>
                    )}
                </>
            )}
        </div>
    );
};

export default LargeRoadUsersSubStage;
