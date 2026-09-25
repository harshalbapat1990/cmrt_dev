import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { NumericInput } from "@/components/common/NumericInput";
import ActivityDataService from "@/services/ActivityData.service";
import type { ActivityDataCreate } from "@/services/ActivityData.service";
import LargeRoadUsersSubStage from "./LargeRoadUsersSubStage";
import EmissionCalculationsService from "@/services/EmissionCalculations.service";
import { emptySummary, UserEmissionsSummary } from "./UserEmissionSummary";
import {
    mitigationUiKey,
    type MitigationSubstitutionLeg,
} from "./mitigationConstants";
import InfoTooltip from "@/components/common/InfoTooltip";
import {SelectListbox} from "@/components/common/Select";
interface RoadUserRow {
    id: string;
    vehicleType: string;
    vkt: string;
    vht: string;
    avgSpeed: string;
    lastEdited: "vht" | "avgSpeed" | null;
    notes: string;
}

interface RailUserRow {
    id: string;
    vehicleType: string;
    terrain: string;
    freight: string;
    dieselEmissionsIntensity: string;
    dieselEmissions: string;
    dieselEmissionsTotalRefPeriod: string;
    notes: string;
}

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

function apiToRailRow(apiRow: any, defaultRow: RailUserRow): RailUserRow {
    const ef = apiRow.extra_fields ?? {};
    return {
        id: apiRow.id,
        vehicleType: defaultRow.vehicleType,
        terrain: ef.terrain ?? defaultRow.terrain,
        freight: ef.freight != null ? String(ef.freight) : "",
        dieselEmissionsIntensity:
            ef.dieselEmissionsIntensity ??
            ef.diesel_emissions_intensity ??
            ef.emissions_intensity_tco2e_kl ??
            "",
        dieselEmissions:
            ef.dieselEmissions ??
            ef.diesel_emissions ??
            ef.emissions_annual_tco2e ??
            "",
        dieselEmissionsTotalRefPeriod:
            ef.dieselEmissionsTotalRefPeriod ??
            ef.diesel_emissions_total_ref_period ??
            ef.emissions_total_ref_period_tco2e ??
            "",
        notes: ef.notes ?? "",
    };
}


function computeDerived(row: RoadUserRow): RoadUserRow {
    const vktNum = parseFloat(row.vkt);
    if (isNaN(vktNum) || vktNum <= 0) return row;

    if (row.lastEdited === "vht") {
        const vhtNum = parseFloat(row.vht);
        return {
            ...row,
            avgSpeed: (!isNaN(vhtNum) && vhtNum > 0) ? (vktNum / vhtNum).toFixed(2) : "",
        };
    }
    if (row.lastEdited === "avgSpeed") {
        const speedNum = parseFloat(row.avgSpeed);
        return {
            ...row,
            vht: (!isNaN(speedNum) && speedNum > 0) ? (vktNum / speedNum).toFixed(2) : "",
        };
    }
    return row;
}

function emptyRows(vehicleTypes: string[]): RoadUserRow[] {
    return vehicleTypes.map((vt, i) => ({
        id: `road-${i + 1}`,
        vehicleType: vt,
        vkt: "",
        vht: "",
        avgSpeed: "",
        lastEdited: null,
        notes: "",
    }));
}

function apiToRow(apiRow: any, vehicleType: string): RoadUserRow {
    const ef = apiRow.extra_fields ?? {};
    return {
        id: apiRow.id,
        vehicleType,
        vkt: ef.vkt != null ? String(ef.vkt) : "",
        vht: ef.vht != null ? String(ef.vht) : "",
        avgSpeed: ef.avg_speed != null ? String(ef.avg_speed) : "",
        lastEdited: ef.last_edited ?? null,
        notes: ef.notes ?? "",
    };
}

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

const toNumberOrNull = (value: any): number | null => {
    if (value === "" || value == null) return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
};

const getSpeed = (row: RoadUserRow): number | null => {
    const speed = toNumberOrNull(row.avgSpeed);
    if (speed != null) return speed;
    const vkt = toNumberOrNull(row.vkt);
    const vht = toNumberOrNull(row.vht);

    if (vkt != null && vht != null && vht > 0) {
        return vkt / vht;
    }
    return null;
};

const isRoadRowComplete = (row: RoadUserRow) => {
    return toNumberOrNull(row.vkt) != null && getSpeed(row) != null;
};

const isRailRowComplete = (row: RailUserRow) => {
    return (
        row.vehicleType !== "" &&
        row.terrain !== "" &&
        toNumberOrNull(row.freight) != null
    );
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


const normalizeVehicleType = (vehicleType: string) =>vehicleType.trim().toLowerCase();


const roadKeyMap: Record<string, { vkt: string; speed: string }> = {
    "light vehicle": {
        vkt: "light_vehicle_vkt",
        speed: "light_vehicle_speed_kmh",
    },
    "medium vehicle": {
        vkt: "medium_vehicle_vkt",
        speed: "medium_vehicle_speed_kmh",
    },
    "heavy vehicle": {
        vkt: "heavy_vehicle_vkt",
        speed: "heavy_vehicle_speed_kmh",
    },
    "super heavy vehicle": {
        vkt: "super_heavy_vehicle_vkt",
        speed: "super_heavy_vehicle_speed_kmh",
    },
    "general fleet": {
        vkt: "general_fleet_vkt",
        speed: "general_fleet_speed_kmh",
    },
    "bus": {
        vkt: "bus_vkt",
        speed: "bus_speed_kmh",
    },
};
const RAIL_CALC_DEBOUNCE_MS = 800;

// type RailPersistMode = "small" | "large";

const mapRailCalcResponseToRow = (row: RailUserRow, res: any): RailUserRow => {
        return {
            ...row,
            dieselEmissionsTotalRefPeriod:
                res?.emissions_total_ref_period_tco2e != null
                    ? String(res.emissions_total_ref_period_tco2e)
                    : "",
        };
};

const UsersSubStage = ({ stageInstanceId, projectId, optionId, refreshKey, readOnly = false, projectClass, projectTypeName, jurisdiction, opsStartYear, activeLargeUsersYear,
    largeUsersYears = [], onActiveLargeUsersYearChange, onOpenAddLargeYear, onOpenCopyLargeYear, onOpenDeleteLargeYear,
    projectMitigationId = null,
    mitigationSubstitutionLeg = null,
     onTotalsUpdated,
}: Props) => {
    const isNZ = isNewZealandJurisdiction(jurisdiction);
    // const isLargeProject = projectClass === "LARGE";
    // const isLargeAU = isLargeProject && !isNZ;

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

    // const shouldUseLargeRailYears = isLargeAU && showRail && activeLargeUsersYear != null;
    // const shouldUseLargeRailYears = false;

   const roadVehicleTypes = useMemo(() => {
    return isNZ ? NZ_ROAD_VEHICLE_TYPES : VEHICLE_TYPES;
}, [isNZ]);


    const [roadExpanded, setRoadExpanded] = useState(true);
    const [railExpanded, setRailExpanded] = useState(true);
    const [railRows, setRailRows] = useState<RailUserRow[]>(INITIAL_RAIL_USERS);
    const [roadRows, setRoadRows] = useState<RoadUserRow[]>(() => emptyRows(roadVehicleTypes));
    const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
    const [railSaveState, setRailSaveState] = useState<"idle" | "saving" | "saved">("idle");
    const railSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    // const [largeRailYearData, setLargeRailYearData] = useState<Record<number, RailUserRow[]>>({});
    // const [largeRailSaveState, setLargeRailSaveState] = useState<"idle" | "saving" | "saved">("idle");
    // const largeRailSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [roadEmissionSummary, setRoadEmissionSummary] = useState<any>(emptySummary);
    const [roadEmissionLoading, setRoadEmissionLoading] = useState(false);
    const railCalcTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
    const railCalcRequestIds = useRef<Record<string, number>>({});

    const displayRailRows = railRows;

    const displayRailSaveState = railSaveState;

    const nzGeneralFleetHasData = isNZ && !!(roadRows.find(r => r.vehicleType === "General Fleet")?.vkt);
    const nzOthersHaveData = isNZ && roadRows.some(r => r.vehicleType !== "General Fleet" && !!r.vkt);


const buildRailPayload = useCallback(
    (
        rows: RailUserRow[],
        tableKey: "railUsers",
        modelledYear?: number
    ): ActivityDataCreate[] => {
        const sk = scopeUiTableKey(tableKey);
        return rows.map((r) => ({
            project_id: projectId,
            project_stage_instance_id: stageInstanceId,
            project_option_id: optionId ?? null,
            metric_id: null,
            quantity:
                r.freight !== "" && !isNaN(parseFloat(r.freight))
                    ? parseFloat(r.freight)
                    : 0,
            unit_id: null,
            ui_table_key: sk,
            extra_fields: {
                ...(modelledYear != null ? { modelled_year: modelledYear } : {}),
                vehicle_type: r.vehicleType,
                terrain: r.terrain,
                freight: r.freight || null,
                notes: r.notes || null,
                emissions_intensity_tco2e_kl: r.dieselEmissionsIntensity || null,
                emissions_annual_tco2e: r.dieselEmissions || null,
                emissions_total_ref_period_tco2e:
                    r.dieselEmissionsTotalRefPeriod || null,
            },
            ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
        }));
    },
    [projectId, stageInstanceId, optionId, scopeUiTableKey, projectMitigationId]
);


const persistRailUsers = useCallback(
    async (rows: RailUserRow[]) => {
        if (readOnly) return;

        setRailSaveState("saving");

        try {
            const payload = buildRailPayload(rows, "railUsers");

            if (payload.length > 0) {
                const sk = scopeUiTableKey("railUsers");
                const saved = await ActivityDataService.bulkUpsert(
                    stageInstanceId,
                    sk,
                    payload,
                    projectMitigationId ?? undefined,
                );

                setRailRows(prev =>
                    prev.map(r => {
                        const match = saved.find(
                            (s: any) => s.extra_fields?.vehicle_type === r.vehicleType
                        );
                        return match ? { ...r, id: match.id } : r;
                    })
                );
                await onTotalsUpdated?.();
            }

            setRailSaveState("saved");
            setTimeout(() => setRailSaveState("idle"), 2000);
        } catch (e) {
            console.error("Failed to save rail users data:", e);
            setRailSaveState("idle");
        }
    },
    [readOnly, stageInstanceId, buildRailPayload, scopeUiTableKey, projectMitigationId, onTotalsUpdated]
);

    const calculateAndPersistRailRow = useCallback(
        async (
            row: RailUserRow,
            allRows: RailUserRow[],
            opts?: { largeYear?: number | null }
        ) => {
            if (!isRailRowComplete(row)) return;

            const requestKey = opts?.largeYear != null
                ? `${opts.largeYear}-${row.vehicleType}`
                : row.vehicleType;

            railCalcRequestIds.current[requestKey] =
                (railCalcRequestIds.current[requestKey] ?? 0) + 1;
            const requestId = railCalcRequestIds.current[requestKey];
            try {
                const response = await EmissionCalculationsService.calculateRail({
                    project_id: projectId,
                    rail_type: row.vehicleType,
                    terrain: row.terrain,
                    freight_quantity_gtk_per_year: Number(row.freight),
                });

                if (railCalcRequestIds.current[requestKey] !== requestId) return;
                const calculatedRow = mapRailCalcResponseToRow(row, response);
                const updatedRows = allRows.map((r) =>
                    r.id === row.id ? calculatedRow : r
                );

                    setRailRows(updatedRows);
                    // Activity-data save AFTER calculation response
                    await persistRailUsers(updatedRows);
            } catch (e) {
                console.error("Failed to calculate rail emissions:", e);
            }
        },
        [projectId, persistRailUsers]
    );

    const scheduleRailRowCalculation = useCallback(
        (
            row: RailUserRow,
            allRows: RailUserRow[],
            opts?: { largeYear?: number | null }
        ) => {
            const requestKey = opts?.largeYear != null
                ? `${opts.largeYear}-${row.vehicleType}`
                : row.vehicleType;

            if (railCalcTimers.current[requestKey]) {
                clearTimeout(railCalcTimers.current[requestKey]);
            }
            railCalcTimers.current[requestKey] = setTimeout(() => {
                void calculateAndPersistRailRow(row, allRows);
            }, RAIL_CALC_DEBOUNCE_MS);
        },
        [calculateAndPersistRailRow]
    );


    useEffect(() => {
        if (!stageInstanceId) return;

        let cancelled = false;

        (async () => {
            try {
                const rows = await ActivityDataService.fetchRows(
                    stageInstanceId,
                    scopeUiTableKey("roadUsers"),
                    optionId ?? null,
                    undefined,
                    projectMitigationId ?? undefined,
                );

                if (cancelled) return;

                const firstExtra = rows.find((r: any) => r.extra_fields)?.extra_fields;
                setRoadEmissionSummary(normalizeCalculationSummary(firstExtra));
                const nextRows = roadVehicleTypes.map((vt, i) => {
                    const found = rows.find(
                        (r: any) => r.extra_fields?.vehicle_type === vt
                    );

                    return found
                        ? apiToRow(found, vt)
                        : {
                            id: `road-${i + 1}`,
                            vehicleType: vt,
                            vkt: "",
                            vht: "",
                            avgSpeed: "",
                            lastEdited: null,
                            notes: "",
                        };
                });

                setRoadRows(nextRows);

                // Important:
                // Do not calculate on page refresh.
            } catch (e) {
                console.error("Failed to load road users data:", e);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [stageInstanceId, optionId, refreshKey, roadVehicleTypes, scopeUiTableKey, projectMitigationId]);

    useEffect(() => {
        if (!stageInstanceId) return;
        let cancelled = false;
        (async () => {
            try {
                const rows = await ActivityDataService.fetchRows(
                    stageInstanceId,
                    scopeUiTableKey("railUsers"),
                    optionId ?? null,
                    undefined,
                    projectMitigationId ?? undefined,
                );
                if (cancelled) return;
                const nextRows = INITIAL_RAIL_USERS.map((defaultRow) => {
                    const found = rows.find(
                        (r: any) =>
                            r.extra_fields?.vehicle_type === defaultRow.vehicleType
                    );
                    return found ? apiToRailRow(found, defaultRow) : defaultRow;
                });
                setRailRows(nextRows);
            } catch (e) {
                console.error("Failed to load rail users data:", e);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [stageInstanceId, optionId, refreshKey, scopeUiTableKey, projectMitigationId]);


    useEffect(() => {
        return () => {
            Object.values(railCalcTimers.current).forEach(clearTimeout);

            if (railSaveTimer.current) {
                clearTimeout(railSaveTimer.current);
            }
        };
    }, []);


    const buildSmallRoadPayload = useCallback(
        (rows: RoadUserRow[]) => {
            const completedRows = rows.filter(isRoadRowComplete);

            if (!completedRows.length) return null;

            const payload: Record<string, any> = {
                project_id: projectId,
                project_option_id: optionId,
                project_stage_instance_id: stageInstanceId,
            };

            for (const row of completedRows) {
                const map = roadKeyMap[normalizeVehicleType(row.vehicleType)];
                if (!map) continue;

                const vkt = toNumberOrNull(row.vkt);
                const speed = getSpeed(row);

                if (vkt == null || speed == null) continue;

                payload[map.vkt] = vkt;
                payload[map.speed] = speed;
            }

            return payload;
        },
        [
            projectId,
            optionId,
            stageInstanceId,
        ]
    );



    const calculateRoadSummary = useCallback(
        async (rows: RoadUserRow[]): Promise<any | null> => {
            if (!showRoad || projectClass === "LARGE") return null;

            const payload = buildSmallRoadPayload(rows);

            if (!payload) {
                return null;
            }

            try {
                setRoadEmissionLoading(true);

                const summary = isNZ
                    ? await EmissionCalculationsService.calculateNzRoads(payload)
                    : await EmissionCalculationsService.calculateAusRoads(payload);

                const normalizedSummary = normalizeCalculationSummary(summary);

                setRoadEmissionSummary(normalizedSummary);

                return normalizedSummary;
            } catch (e) {
                console.error("Failed to calculate road user emissions:", e);
                return null;
            } finally {
                setRoadEmissionLoading(false);
            }
        },
        [
            showRoad,
            projectClass,
            isNZ,
            buildSmallRoadPayload,
        ]
    );

    const persistRows = useCallback(
        async (
            rows: RoadUserRow[],
            summary: any = roadEmissionSummary
        ) => {
            if (readOnly) return;

            const savable = rows.filter(
                (row) => row.vkt !== "" && !isNaN(parseFloat(row.vkt))
            );

            if (!savable.length) return;

            setSaveState("saving");

            try {
                const sk = scopeUiTableKey("roadUsers");
                const payload: ActivityDataCreate[] = savable.map((row) => ({
                    project_id: projectId,
                    project_stage_instance_id: stageInstanceId,
                    project_option_id: optionId ?? null,
                    metric_id: null,
                    quantity: parseFloat(row.vkt),
                    unit_id: null,
                    ui_table_key: sk,
                    extra_fields: {
                        vehicle_type: row.vehicleType,
                        vkt: row.vkt,
                        vht: row.vht || null,
                        avg_speed: row.avgSpeed || null,
                        last_edited: row.lastEdited,
                        notes: row.notes || null,

                        absoluteEmissions: summary?.absoluteEmissions ?? null,
                        baseCaseAbsoluteEmissions: summary?.baseCaseAbsoluteEmissions ?? null,
                        relativeUserEmissions: summary?.relativeUserEmissions ?? null,

                        absolute_emissions: summary?.absoluteEmissions ?? null,
                        base_case_absolute_emissions: summary?.baseCaseAbsoluteEmissions ?? null,
                        relative_user_emissions: summary?.relativeUserEmissions ?? null,
                    },
                    ...(projectMitigationId ? { project_mitigation_id: projectMitigationId } : {}),
                }));

                const saved = await ActivityDataService.bulkUpsert(
                    stageInstanceId,
                    sk,
                    payload,
                    projectMitigationId ?? undefined,
                );

                setRoadRows((prev) =>
                    prev.map((row) => {
                        const match = saved.find(
                            (s: any) =>
                                s.extra_fields?.vehicle_type === row.vehicleType
                        );

                        return match ? { ...row, id: match.id } : row;
                    })
                );
                await onTotalsUpdated?.();

                setSaveState("saved");
                setTimeout(() => setSaveState("idle"), 2000);
            } catch (e) {
                console.error("Failed to save road users data:", e);
                setSaveState("idle");
            }
        },
        [
            stageInstanceId,
            projectId,
            optionId,
            readOnly,
            roadEmissionSummary,
            scopeUiTableKey,
            projectMitigationId,
            onTotalsUpdated,
        ]
    );

    const updateRow = (id: string, changes: Partial<RoadUserRow>) => {
        if (readOnly) return;

        setRoadRows((prev) =>
            prev.map((row) =>
                row.id !== id
                    ? row
                    : computeDerived({
                        ...row,
                        ...changes,
                    })
            )
        );
    };

    const handleSaveRoadUsers = useCallback(async () => {
        if (readOnly) return;

        try {
            const payload = buildSmallRoadPayload(roadRows);

            if (payload) {
                const calculatedSummary = await calculateRoadSummary(roadRows);

                if (!calculatedSummary) {
                    return;
                }

                await persistRows(roadRows, calculatedSummary);
                return;
            }

            await persistRows(roadRows, roadEmissionSummary);
        } catch (e) {
            console.error("Failed to save road users data:", e);
        }
    }, [
        readOnly,
        roadRows,
        roadEmissionSummary,
        buildSmallRoadPayload,
        calculateRoadSummary,
        persistRows,
    ]);

    

   const scheduleRailSave = useCallback(
    (rows: RailUserRow[]) => {
        if (readOnly) return;

        if (railSaveTimer.current) {
            clearTimeout(railSaveTimer.current);
        }

        railSaveTimer.current = setTimeout(
            () => void persistRailUsers(rows),
            800
        );
    },
    [persistRailUsers, readOnly]
);



    const updateRailRow = (id: string, changes: Partial<RailUserRow>) => {
        if (readOnly) return;

        setRailRows((prev) => {
            const isTerrainChange =
                Object.prototype.hasOwnProperty.call(changes, "terrain");

            const isFreightChange =
                Object.prototype.hasOwnProperty.call(changes, "freight");

            const isCalcFieldChange = isTerrainChange || isFreightChange;

            const updated = prev.map((r) => {
                if (r.id !== id) return r;

                return {
                    ...r,
                    ...changes,
                    ...(isCalcFieldChange
                        ? {
                            dieselEmissionsIntensity: "",
                            dieselEmissions: "",
                            dieselEmissionsTotalRefPeriod: "",
                        }
                        : {}),
                };
            });

            const updatedRow = updated.find((r) => r.id === id);
            if (!updatedRow) return updated;

            /**
             * Debounced calculation:
             * - freight typing triggers calculation only after user stops typing
             * - terrain change also recalculates
             * - notes only saves activity data
             */
            if (isCalcFieldChange) {
                scheduleRailRowCalculation(updatedRow, updated);
            } else {
                scheduleRailSave(updated);
            }

            return updated;
        });
    };


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
                            {/* <span
                                className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-neutral-700 text-white text-xs ml-1 cursor-help"
                                title="Road user traffic data — VKT is required. Enter either VHT or Avg Speed; the other is computed automatically (VKT = Speed × VHT)."
                            >?</span> */}
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
                                                            onChange={(v: any) => updateRow(row.id, { vkt: v != null ? String(v) : "" })}
                                                            onCommit={() => { }}
                                                            allowDecimal
                                                            disabled={isDisabled}
                                                        />
                                                    </td>

                                                    <td className="px-4 py-2">
                                                        <div className="relative">
                                                            <NumericInput
                                                                value={row.vht}
                                                                onChange={(v: any) =>
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
                                                                onChange={(v: any) =>
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
                        {/* <span
                            className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-neutral-700 text-white text-xs ml-1 cursor-help"
                            title="Rail freight data for this project"
                        >?</span> */}
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
                                                    onChange={(v: any) =>
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
                                                {row.dieselEmissionsTotalRefPeriod || "—"}
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