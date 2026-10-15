import { useCallback, useState, useMemo } from "react";
import { formatDisplayNumber } from "@/utils/utils";
import { NumericInput } from "@/components/common/NumericInput";
import LargeRoadUsersSubStage from "./LargeRoadUsersSubStage";
import { emptySummary, UserEmissionsSummary } from "./UserEmissionSummary";
import {
    mitigationUiKey,
    type MitigationSubstitutionLeg,
} from "./mitigationConstants";
import InfoTooltip from "@/components/common/InfoTooltip";
import {SelectListbox} from "@/components/common/Select";
import { isNewZealandJurisdiction, type UserCalculationSummary } from "./roadUserCalculations";
import type { RoadUserRow } from "./roadUserTypes";
import { emptyRoadUserRows, type RailUserRow } from "./userDataMapping";
import { buildRailActivityPayload, buildRoadActivityPayload } from "./userDataPayloads";
import { useUsersStageLoader } from "./hooks/useUsersStageLoader";
import { useUserRowsPersistence } from "./hooks/useUserRowsPersistence";
import { useRailUserCalculations } from "./hooks/useRailUserCalculations";
import { useSmallRoadUserCalculations } from "./hooks/useSmallRoadUserCalculations";
import { useUsersRowEditing } from "./hooks/useUsersRowEditing";
import { useSmallRoadUserSave } from "./hooks/useSmallRoadUserSave";

const VEHICLE_TYPES = [
    "Light vehicle",
    "Medium vehicle",
    "Heavy vehicle",
    "Super heavy vehicle",
];

const NZ_ROAD_VEHICLE_TYPES = [
    "General Fleet",
    "Light Vehicle",
    "Heavy Vehicle",
    "Bus",
];
const TERRAIN_OPTIONS = [
  { label: "Flat", value: "Flat" },
  { label: "Curvy", value: "Curvy" },
  { label: "Hilly", value: "Hilly" },
  { label: "Mountain", value: "Mountain" },
];

const INITIAL_RAIL_USERS: RailUserRow[] = [
    {
        id: "rail-1",
        vehicleType: "Container Train",
        terrain: "Flat",
        freight: "",
        dieselEmissionsIntensity: "",
        dieselEmissions: "",
        dieselEmissionsTotalRefPeriod: "",
        notes: "",
    },
    {
        id: "rail-2",
        vehicleType: "General Purpose Train",
        terrain: "Curvy",
        freight: "",
        dieselEmissionsIntensity: "",
        dieselEmissions: "",
        dieselEmissionsTotalRefPeriod: "",
        notes: "",
    },
    {
        id: "rail-3",
        vehicleType: "Grain Train",
        terrain: "Hilly",
        freight: "",
        dieselEmissionsIntensity: "",
        dieselEmissions: "",
        dieselEmissionsTotalRefPeriod: "",
        notes: "",
    },
    {
        id: "rail-4",
        vehicleType: "Heavy Haul Mineral",
        terrain: "Mountain",
        freight: "",
        dieselEmissionsIntensity: "",
        dieselEmissions: "",
        dieselEmissionsTotalRefPeriod: "",
        notes: "",
    },
];

interface Props {
    stageInstanceId: string;
    projectId: string;
    optionId?: string | null;
    refreshKey?: number;
    readOnly?: boolean;
    projectClass?: string | null;
    projectTypeName?: string | null;
    jurisdiction?: string | null;
    opsStartYear?: number | null;
    activeLargeUsersYear?: number | null;
    largeUsersYears?: number[];
    onActiveLargeUsersYearChange?: (year: number) => void;
    onOpenAddLargeYear?: () => void;
    onOpenCopyLargeYear?: () => void;
    onOpenDeleteLargeYear?: () => void;
    projectMitigationId?: string | null;
    mitigationSubstitutionLeg?: MitigationSubstitutionLeg | null;
    onTotalsUpdated?: () => void | Promise<void>;
}

const UsersSubStage = ({ stageInstanceId, projectId, optionId, refreshKey, readOnly = false, projectClass, projectTypeName, jurisdiction, opsStartYear, activeLargeUsersYear,
    largeUsersYears = [], onActiveLargeUsersYearChange, onOpenAddLargeYear, onOpenCopyLargeYear, onOpenDeleteLargeYear,
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

    const normalizedProjectType = (projectTypeName ?? "").trim().toLowerCase().replace(/[_-]+/g, " ");

    const projectHasRoad =normalizedProjectType.includes("road");

    const projectHasRail = normalizedProjectType.includes("rail");

    const showRoad = !projectTypeName ||projectHasRoad ||projectHasRail;

    const showRail = projectHasRail;


   const roadVehicleTypes = useMemo(() => {
    return isNZ ? NZ_ROAD_VEHICLE_TYPES : VEHICLE_TYPES;
}, [isNZ]);


    const [roadExpanded, setRoadExpanded] = useState(true);
    const [railExpanded, setRailExpanded] = useState(true);
    const [railRows, setRailRows] = useState<RailUserRow[]>(INITIAL_RAIL_USERS);
    const [roadRows, setRoadRows] = useState<RoadUserRow[]>(() => emptyRoadUserRows(roadVehicleTypes));

    const [roadEmissionSummary, setRoadEmissionSummary] = useState<UserCalculationSummary>(emptySummary);
    const {
        loading: roadEmissionLoading,
        buildPayload: buildSmallRoadPayload,
        calculateSummary: calculateRoadSummary,
    } = useSmallRoadUserCalculations({
        projectId,
        stageInstanceId,
        projectOptionId: optionId,
        region: isNZ ? "NZ" : "AU",
        showRoad,
        isLargeProject: projectClass === "LARGE",
        setSummary: setRoadEmissionSummary,
    });

    const displayRailRows = railRows;

    const nzGeneralFleetHasData = isNZ && !!(roadRows.find(r => r.vehicleType === "General Fleet")?.vkt);
    const nzOthersHaveData = isNZ && roadRows.some(r => r.vehicleType !== "General Fleet" && !!r.vkt);


const buildRailPayload = useCallback(
    (
        rows: RailUserRow[],
        tableKey: "railUsers",
        modelledYear?: number
    ) => {
        return buildRailActivityPayload(rows, {
            projectId,
            stageInstanceId,
            projectOptionId: optionId,
            projectMitigationId,
        }, scopeUiTableKey(tableKey), modelledYear);
    },
    [projectId, stageInstanceId, optionId, scopeUiTableKey, projectMitigationId]
);

const { saveState: railSaveState, persistRows: persistRailUsers } = useUserRowsPersistence<RailUserRow>({
    readOnly,
    stageInstanceId,
    tableKey: scopeUiTableKey("railUsers"),
    projectMitigationId,
    setRows: setRailRows,
    buildPayload: (rows) => buildRailPayload(rows, "railUsers"),
    onTotalsUpdated,
    errorLabel: "rail users data",
});

const displayRailSaveState = railSaveState;

    const {
        scheduleCalculation: scheduleRailRowCalculation,
        scheduleSave: scheduleRailSave,
    } = useRailUserCalculations({
        projectId,
        setRows: setRailRows,
        persistRows: persistRailUsers,
    });

    useUsersStageLoader({
        stageInstanceId,
        optionId,
        refreshKey,
        projectMitigationId,
        scopeUiTableKey,
        roadVehicleTypes,
        initialRailRows: INITIAL_RAIL_USERS,
        setRoadRows,
        setRailRows,
        setRoadSummary: setRoadEmissionSummary,
    });


    const { saveState, persistRows } = useUserRowsPersistence<RoadUserRow>({
        readOnly,
        stageInstanceId,
        tableKey: scopeUiTableKey("roadUsers"),
        projectMitigationId,
        setRows: setRoadRows,
        buildPayload: (rows, summary) => buildRoadActivityPayload(rows, {
            projectId,
            stageInstanceId,
            projectOptionId: optionId,
            projectMitigationId,
        }, scopeUiTableKey("roadUsers"), summary ?? roadEmissionSummary),
        onTotalsUpdated,
        errorLabel: "road users data",
    });

    const { updateRoadRow: updateRow, updateRailRow } = useUsersRowEditing({
        readOnly,
        setRoadRows,
        setRailRows,
        scheduleRailCalculation: scheduleRailRowCalculation,
        scheduleRailSave,
    });

    const handleSaveRoadUsers = useSmallRoadUserSave({
        readOnly,
        rows: roadRows,
        currentSummary: roadEmissionSummary,
        buildPayload: buildSmallRoadPayload,
        calculateSummary: calculateRoadSummary,
        persistRows,
    });

    

    return (
        <>
            {showRoad && (projectClass === "LARGE" ? (
                <LargeRoadUsersSubStage
                    stageInstanceId={stageInstanceId}
                    projectId={projectId}
                    optionId={optionId}
                    refreshKey={refreshKey}
                    readOnly={readOnly}
                    projectTypeName={projectTypeName ?? null}
                    jurisdiction={jurisdiction ?? null}
                    opsStartYear={opsStartYear ?? null}
                    activeYear={activeLargeUsersYear ?? null}
                    largeUsersYears={largeUsersYears}
                    onActiveYearChange={onActiveLargeUsersYearChange}
                    onOpenAddYear={onOpenAddLargeYear}
                    onOpenCopyYear={onOpenCopyLargeYear}
                    onOpenDeleteYear={onOpenDeleteLargeYear}
                    projectMitigationId={projectMitigationId}
                    mitigationSubstitutionLeg={mitigationSubstitutionLeg}
                    onTotalsUpdated={onTotalsUpdated}
                />
            ) : (
                <div className="mx-12 mb-8 bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)]">
                    <div className="flex items-center justify-between mb-4">
                        <div className="text-2xl font-light text-text-dark flex items-center gap-1">
                            Road users
                                <InfoTooltip
                                    text="The user emissions attributable to each option for B8 are only the change in emissions relative to the Base Case. The Base Case is assigned 0 emissions for B8."
                                    iconSize={20}
                                    trigger="auto"
                                    placement="top"
                                    offset={20}
                                    arrowOffset={80}
                                />
                        </div>
                        <div className="flex items-center gap-3">
                            {saveState === "saving" && (
                                <span className="text-xs text-text-faint animate-pulse">Saving…</span>
                            )}
                            {saveState === "saved" && (
                                <span className="text-xs text-green-600">Saved</span>
                            )}


                            {!readOnly && (
                                <button
                                    type="button"
                                    className="px-3 py-2 text-sm cursor-pointer bg-primary text-white rounded cursor-pointer disabled:opacity-50"
                                    disabled={saveState === "saving" || roadEmissionLoading}
                                    onClick={() => void handleSaveRoadUsers()}
                                >
                                    Save
                                </button>
                            )}

                            <button
                                type="button"
                                onClick={() => setRoadExpanded(v => !v)}
                                className="w-5 h-5 inline-flex cursor-pointer items-center justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded"
                            >
                                <span className="material-symbols-rounded">
                                    {roadExpanded ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                                </span>
                            </button>
                        </div>
                    </div>

                    {roadExpanded && (
                        <>
                            <UserEmissionsSummary
                                summary={roadEmissionSummary}
                                loading={roadEmissionLoading}
                            />
                            <div className="overflow-x-auto">
                                <table className="min-w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-neutral-200 text-xs font-medium text-text-base">
                                            <th className="px-4 py-3 text-left w-44">Vehicle type</th>
                                            <th className="px-4 py-3 text-right ">
                                                Average Annual Vehicle Kilometres Travelled (VKT)<span className="text-danger">*</span>
                                            </th>
                                            <th className="px-4 py-3 text-right">Average Annual Vehicle Hours Travelled (VHT)</th>
                                            <th className="px-4 py-3 text-right">Average Speed (km/h)</th>
                                            <th className="px-4 py-3 text-left">
                                                Notes / Comments <span className="font-normal">(optional)</span>
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {roadRows.flatMap(row => {
                                            const vhtIsComputed = row.lastEdited === "avgSpeed";
                                            const speedIsComputed = row.lastEdited === "vht";
                                            const isNzLocked = isNZ && (
                                                row.vehicleType === "General Fleet" ? nzOthersHaveData : nzGeneralFleetHasData
                                            );
                                            const isDisabled = readOnly || isNzLocked;
                                            const rowEl = (
                                                <tr key={row.id} className={`border-b border-neutral-100 last:border-0 hover:bg-neutral-50 text-text-table-cell${isNzLocked ? " opacity-40" : ""}`}>
                                                    <td className="px-4 py-3 bg-neutral-95">{row.vehicleType}</td>

                                                    <td className="px-4 py-2">
                                                        <NumericInput
                                                            value={row.vkt}
                                                            onChange={(v) => updateRow(row.id, { vkt: v != null ? String(v) : "" })}
                                                            onCommit={() => { }}
                                                            allowDecimal
                                                            disabled={isDisabled}
                                                        />
                                                    </td>

                                                    <td className="px-4 py-2">
                                                        <div className="relative">
                                                            <NumericInput
                                                                value={row.vht}
                                                                onChange={(v) =>
                                                                    updateRow(row.id, { vht: v != null ? String(v) : "", lastEdited: "vht" })
                                                                }
                                                                onCommit={() => { }}
                                                                allowDecimal
                                                                disabled={isDisabled}
                                                                className={vhtIsComputed ? "bg-neutral-50 text-text-faint" : ""}
                                                            />
                                                            {vhtIsComputed && (
                                                                <span
                                                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-neutral-400 pointer-events-none select-none"
                                                                    title="Computed from VKT ÷ Speed"
                                                                >auto</span>
                                                            )}
                                                        </div>
                                                    </td>

                                                    <td className="px-4 py-2">
                                                        <div className="relative">
                                                            <NumericInput
                                                                value={row.avgSpeed}
                                                                onChange={(v) =>
                                                                    updateRow(row.id, { avgSpeed: v != null ? String(v) : "", lastEdited: "avgSpeed" })
                                                                }
                                                                onCommit={() => { }}
                                                                allowDecimal
                                                                disabled={isDisabled}
                                                                className={speedIsComputed ? "bg-neutral-50 text-text-faint" : ""}
                                                            />
                                                            {speedIsComputed && (
                                                                <span
                                                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-neutral-400 pointer-events-none select-none"
                                                                    title="Computed from VKT ÷ VHT"
                                                                >auto</span>
                                                            )}
                                                        </div>
                                                    </td>

                                                    <td className="px-4 py-2">
                                                        <input
                                                            className="h-10 w-full border border-border-input rounded px-2 py-1 text-sm"
                                                            value={row.notes}
                                                            onChange={e => updateRow(row.id, { notes: e.target.value })}
                                                            disabled={isDisabled}
                                                        />
                                                    </td>
                                                </tr>
                                            );
                                            if (isNZ && row.vehicleType === "General Fleet") {
                                                return [
                                                    rowEl,
                                                    <tr key="nz-or-sep" className="bg-neutral-50">
                                                        <td colSpan={5} className="px-4 py-1 text-center text-[10px] text-text-faint italic border-b border-neutral-200">— OR —</td>
                                                    </tr>
                                                ];
                                            }
                                            return [rowEl];
                                        })}
                                    </tbody>
                                </table>
                                <p className="mt-2 text-xs text-text-faint">
                                    <span className="text-danger">*</span> Avg Annual VKT is required.
                                    Enter either <strong>VHT</strong> or <strong>Avg Speed</strong> — the other calculates automatically
                                    using <em>VKT = Speed × VHT</em>.
                                    Fields marked <span className="font-medium">auto</span> are computed and update as you type.
                                </p>
                                {isNZ && (
                                    <p className="mt-1 text-xs text-text-faint">
                                        Enter data for <strong>General Fleet</strong> OR <strong>Light / Heavy Vehicle / Bus</strong> — not both.
                                    </p>
                                )}
                            </div>
                        </>
                    )}
                </div>
            ))}

            {showRail && <div className="mx-12 mb-8 bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)]">
                <div className="flex items-center justify-between mb-4">
                    <div className="text-2xl font-light text-text-dark flex items-center gap-1">
                        Rail users
                        <InfoTooltip
                            text="The user emissions attributable to each option for B8 are only the change in emissions relative to the Base Case."
                            iconSize={20}
                            trigger="auto"
                            placement="top"
                            offset={10}
                            arrowOffset={20}
                        />
                    </div>
                    <div className="flex items-center gap-3">
                        {displayRailSaveState === "saving" && (
                            <span className="text-xs text-text-faint animate-pulse">Saving…</span>
                        )}
                        {displayRailSaveState === "saved" && (
                            <span className="text-xs text-green-600">Saved</span>
                        )}
                        <button
                            type="button"
                            onClick={() => setRailExpanded(v => !v)}
                            className="w-5 h-5 inline-flex cursor-pointer items-center justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded"
                        >
                            <span className="material-symbols-rounded">
                                {railExpanded ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                            </span>
                        </button>
                    </div>
                </div>
                {railExpanded && (
                    <>
                        <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="border-b border-neutral-200  font-medium text-text-base tet-xs">
                                        <th className="px-4 py-3 text-left w-44">Rail type</th>
                                        <th className="px-4 py-3 text-left">Terrain</th>
                                        <th className="px-4 py-3 text-right">Freight quantity ('000 GTK/year)</th>
                                        <th className="px-4 py-3 text-right">Emissions (tCO₂e)</th>
                                        <th className="px-4 py-3 text-left">
                                            Notes / Comments <span className="font-normal">(optional)</span>
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {displayRailRows.map(row => (
                                        <tr key={row.id} className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50 text-text-table-cell">
                                            <td className="px-4 py-3 bg-neutral-95">{row.vehicleType}</td>
                                            <td className="px-4 py-2">
                                                
                                                <SelectListbox
                                                    value={row.terrain}
                                                    options={TERRAIN_OPTIONS}
                                                    onChange={(val) =>
                                                    updateRailRow(row.id, { terrain: val })
                                                    }
                                                    disabled={readOnly}
                                                    placeholder="Select terrain"
                                                    minMenuWidth={200}
                                                />

                                            </td>
                                            <td className="px-4 py-2 text-right">
                                                <NumericInput
                                                    value={row.freight}
                                                    onChange={(v) =>
                                                        updateRailRow(
                                                            row.id,
                                                            {
                                                                freight: v != null ? String(v) : "",
                                                            }
                                                        )
                                                    }
                                                    onCommit={() => { }}
                                                    allowDecimal
                                                    disabled={readOnly}
                                                />

                                            </td>
                                            <td className="px-4 py-2 text-right">
                                                {formatDisplayNumber(row.dieselEmissionsTotalRefPeriod)}
                                            </td>
                                            <td className="px-4 py-2">
                                                <input
                                                    className="h-10 w-full border border-border-input rounded px-2 py-1 text-sm"
                                                    value={row.notes}
                                                    onChange={e => updateRailRow(row.id, { notes: e.target.value })}
                                                    disabled={readOnly}
                                                />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </>
                )}
            </div>}
        </>
    );
};

export default UsersSubStage;
