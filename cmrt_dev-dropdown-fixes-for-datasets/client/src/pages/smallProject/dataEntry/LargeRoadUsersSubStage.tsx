import { useCallback, useEffect, useState, useMemo } from "react";
import { NumericInput } from "@/components/common/NumericInput";
import { SelectListbox } from "@/components/common/Select";
import { emptySummary, UserEmissionsSummary } from "./UserEmissionSummary";
import {
    mitigationUiKey,
    type MitigationSubstitutionLeg,
} from "./mitigationConstants";
import InfoTooltip from "@/components/common/InfoTooltip";
import { isNewZealandJurisdiction, type UserCalculationSummary } from "./roadUserCalculations";
import type { RoadParams, RoadUserYearData } from "./roadUserTypes";
import { emptyRoadUserYear } from "./largeRoadUsersData";
import { useLargeRoadUsersLoader } from "./hooks/useLargeRoadUsersLoader";
import { useLargeRoadUserPersistence } from "./hooks/useLargeRoadUserPersistence";
import { useLargeRoadUserCalculations } from "./hooks/useLargeRoadUserCalculations";
import { useLargeRoadUserEditing } from "./hooks/useLargeRoadUserEditing";
import { useLargeRoadUserSave } from "./hooks/useLargeRoadUserSave";
import { LargeRoadUsersYearSelector } from "./components/LargeRoadUsersYearSelector";

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

function largeRoadErrorMessage(error: unknown): string {
    if (typeof error === "object" && error !== null) {
        const apiError = error as {
            response?: { data?: { detail?: unknown } };
            message?: unknown;
        };
        if (typeof apiError.response?.data?.detail === "string") {
            return apiError.response.data.detail;
        }
        if (typeof apiError.message === "string") return apiError.message;
    }
    return "Could not calculate and save road user emissions. Please check the dataset factors and try again.";
}


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


type YearData = RoadUserYearData;

const DEFAULT_ROAD_PARAMS: RoadParams = {
    ev_uptake_scenario: "Step Change",
    roughness: "Smooth",
    gradient: "Flat",
    curvature: "Straight",
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

function emptyYearData(vehicleTypes: string[]): YearData {
    return emptyRoadUserYear(vehicleTypes, DEFAULT_ROAD_PARAMS);
}

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
    const [expanded, setExpanded] = useState(true);
    const [calculationError, setCalculationError] = useState<string | null>(null);

    const [emissionSummary, setEmissionSummary] = useState<UserCalculationSummary>(emptySummary);
    const [globalParams, setGlobalParams] = useState<RoadParams>(DEFAULT_ROAD_PARAMS);


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

    const { saveState, persistAll } = useLargeRoadUserPersistence({
        readOnly,
        stageInstanceId,
        projectId,
        projectOptionId: optionId,
        projectMitigationId,
        paramsTableKey: scopeUiTableKey("largeRoadParams"),
        usersTableKey: scopeUiTableKey("largeRoadUsers"),
        getModelledYears: getAllModelledYears,
        defaultParams: globalParams,
        defaultSummary: emissionSummary,
        onTotalsUpdated,
    });


    const availableModelledYears = useMemo(() => {
        return Array.from(
            new Set([
                ...largeUsersYears,
                ...Object.keys(yearData).map(Number),
                ...(activeYear != null ? [activeYear] : []),
            ])
        ).sort((a, b) => a - b);
    }, [largeUsersYears, yearData, activeYear]);

    const displayedActiveYear =
        activeYear ??
        availableModelledYears[0] ??
        null;

    const { updateRow, updateParams } = useLargeRoadUserEditing({
        readOnly,
        displayedActiveYear,
        largeUsersYears,
        vehicleTypes,
        globalParams,
        setGlobalParams,
        setYearData,
    });


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


    useLargeRoadUsersLoader({
        stageInstanceId,
        optionId,
        refreshKey,
        projectMitigationId,
        scopeUiTableKey,
        vehicleTypes,
        largeUsersYears,
        defaultParams: DEFAULT_ROAD_PARAMS,
        setGlobalParams,
        setYearData,
        setEmissionSummary,
    });

    const { loading: emissionLoading, calculateSummary } = useLargeRoadUserCalculations({
        projectId,
        stageInstanceId,
        projectOptionId: optionId,
        getModelledYears: getAllModelledYears,
        setSummary: setEmissionSummary,
    });

    const saveLargeRoadUsers = useLargeRoadUserSave({
        readOnly,
        region: isNZ ? "NZ" : "AU",
        yearData,
        roadParams: globalParams,
        currentSummary: emissionSummary,
        calculateSummary,
        persistAll,
        onError: (error) => setCalculationError(largeRoadErrorMessage(error)),
    });
    const handleSaveLargeRoadUsers = useCallback(async () => {
        setCalculationError(null);
        await saveLargeRoadUsers();
    }, [saveLargeRoadUsers]);
    const editorDisabled = readOnly || saveState === "saving" || emissionLoading;

    return (
        <div
            className="mx-12 mb-8 bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)]"
            aria-busy={editorDisabled}
        >
            <div className="flex items-center justify-between mb-4">
                <div className="text-2xl font-light text-text-dark flex items-center gap-1">
                    Road users
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
                    {saveState === "saved" && !calculationError && (
                        <span className="text-xs text-success">Saved</span>
                    )}
                    <button
                        type="button"
                        onClick={() => setExpanded(v => !v)}
                        disabled={editorDisabled}
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
            {calculationError && (
                <div role="alert" className="mb-4 rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
                    <strong className="block">Emissions calculation failed. The displayed summary may be out of date.</strong>
                    {calculationError}
                </div>
            )}

            {expanded && (
                <>
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                        <LargeRoadUsersYearSelector
                            years={availableModelledYears}
                            activeYear={displayedActiveYear}
                            readOnly={editorDisabled}
                            onYearChange={onActiveYearChange}
                            onAddYear={onOpenAddYear}
                            onCopyYear={onOpenCopyYear}
                            onDeleteYear={onOpenDeleteYear}
                        />

                        {/* Right side: Save button */}
                        {!readOnly && (
                            <button
                                type="button"
                                className="px-3 py-2 text-sm bg-primary text-white rounded cursor-pointer ml-auto disabled:opacity-50"
                                disabled={editorDisabled}
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
                            disabled={editorDisabled}
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
                            disabled={editorDisabled}
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
                            disabled={editorDisabled}
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
                            disabled={editorDisabled}
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
                                                        onChange={(v) =>
                                                            updateRow(row.id, {
                                                                vkt:
                                                                    v != null
                                                                        ? String(v)
                                                                        : "",
                                                            })
                                                        }
                                                        onCommit={() => { }}
                                                        allowDecimal
                                                        disabled={editorDisabled}
                                                    />
                                                </td>

                                                <td className="px-4 py-2">
                                                    <div className="relative">
                                                        <NumericInput
                                                            value={row.vht}
                                                            onChange={(v) =>
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
                                                            disabled={editorDisabled}
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
                                                            onChange={(v) =>
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
                                                            disabled={editorDisabled}
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
                                                        disabled={editorDisabled}
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
