import { useState, useEffect } from "react";
import Table from "@/components/common/Table";
import ActivityDataService from "@/services/ActivityData.service";


type ShortcutKey = "IS_MATERIALS" | "SAT_4P";

// type ShortcutToolsModalProps = {
//     open: boolean;
//     onClose: () => void;
//     columns: any[];
//     onCellChange?: any;
//     onRowPatch?: any;
//     readOnly?: boolean;
// };

const COMPONENT_TYPE_OPTIONS = [
    { label: "Road", value: "road" },
    { label: "Transport building", value: "transport_building" },
];

const SUB_COMPONENT_TYPE_OPTIONS = [
    { label: "Tunnel", value: "tunnel" },
    { label: "Parking facility", value: "parking_facility" },
];

const SAT4P_ROWS = [
    "Construction materials",
    "Construction processes/equipment",
    "Maintenance processes / equipment",
    "Disposal",
    "Transport (construction materials)",
    "Transport (maintenance materials)",
    "Transport off-site (waste)",
    "Use phase",
];


const SHORTCUT_TABLE_CONFIGS: Record<
    ShortcutKey,
    {
        title: string;
        tableKey: string;
        columns: () => any[];
    }
> = {
    IS_MATERIALS: {
        title: "IS Materials Calculator",
        tableKey: "isMaterials",
        columns: () => [
            {
                header: "Component type", 
                width: "22%", 
                key: "component_type", 
                editable: true,
                editorType: "select", getOptions: () => COMPONENT_TYPE_OPTIONS
            },
            {
                header: "Sub-component type", 
                width: "22%", 
                key: "sub_component_type", 
                editable: true,
                editorType: "select", getOptions: () => SUB_COMPONENT_TYPE_OPTIONS
            },
            { 
                header: "Base case GHG (tCO₂e)", 
                width: "28%", 
                key: "base_case", 
                editorType: "number", 
                editable: true 
            },
            { 
                header: "Actual case GHG (tCO₂e)", 
                width: "28%", 
                key: "actual_case", 
                editorType: "number", 
                editable: true 
            },
        ],
    },

    SAT_4P: {
        title: "SAT 4P",
        tableKey: "sat4p",
        columns: () => [
            { 
                header: "Emission source", 
                width: "40%", 
                key: "source", 
                editable: false },
            { 
                header: "Scope 1 emissions (tCO₂e)", 
                width: "30%", 
                key: "scope1", 
                editorType: "number", 
                editable: true 
            },
            { 
                header: "Scope 2 emissions (tCO₂e)", 
                width: "30%", 
                key: "scope2", 
                editorType: "number", 
                editable: true 
            },
        ],
    },
};



const ShortcutToolsModal = ({
    open,
    shortcutKey,
    onClose,
    stageInstanceId,
    projectId,
    projectOptionId,
    readOnly,
    onSaved,
}: {
    open: boolean;
    shortcutKey: ShortcutKey | null;
    onClose: () => void;
    stageInstanceId: string;
    projectId: string;
    projectOptionId: string | null;
    readOnly?: boolean;
    onSaved?: () => void;
}) => {
    const [rows, setRows] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    const [sat4pData, setSat4pData] = useState<
        Record<
            string,
            {
                base_scope1: number | "";
                base_scope2: number | "";
                actual_scope3: number | "";
                actual_scope4: number | "";
            }
        >
    >(() =>
        Object.fromEntries(
            SAT4P_ROWS.map((src) => [
                src,
                {
                    base_scope1: "",
                    base_scope2: "",
                    actual_scope3: "",
                    actual_scope4: "",
                },
            ])
        )
    );


    const [maintenanceUse, setMaintenanceUse] = useState<{
        base_case: number | "";
        actual_case: number | "";
    }>({
        base_case: "",
        actual_case: "",
    });

    useEffect(() => {
        if (!open || shortcutKey !== "IS_MATERIALS" || !stageInstanceId) return;
        setLoading(true);
        setRows([]);
        setMaintenanceUse({ base_case: "", actual_case: "" });
        ActivityDataService.fetchRows(stageInstanceId, "shortcutIsMaterials", projectOptionId)
            .then((data) => {
                const mainRow = data.find((r) => r.extra_fields?.row_type === "maintenance");
                if (mainRow) {
                    setMaintenanceUse({
                        base_case: mainRow.extra_fields?.base_case ?? "",
                        actual_case: mainRow.extra_fields?.actual_case ?? "",
                    });
                }
                const tableRows = data
                    .filter((r) => r.extra_fields?.row_type !== "maintenance")
                    .map((r) => ({
                        id: r.id,
                        component_type: r.extra_fields?.component_type ?? "",
                        sub_component_type: r.extra_fields?.sub_component_type ?? "",
                        base_case: r.extra_fields?.base_case ?? "",
                        actual_case: r.extra_fields?.actual_case ?? "",
                    }));
                setRows(tableRows);
            })
            .catch((e) => console.error("Failed to load IS Materials data", e))
            .finally(() => setLoading(false));
    }, [open, shortcutKey, stageInstanceId, projectOptionId]);

    useEffect(() => {
        if (!open || shortcutKey !== "SAT_4P" || !stageInstanceId) return;
        setLoading(true);
        setSat4pData(
            Object.fromEntries(
                SAT4P_ROWS.map((src) => [src, { base_scope1: "", base_scope2: "", actual_scope3: "", actual_scope4: "" }])
            )
        );
        ActivityDataService.fetchRows(stageInstanceId, "shortcutSat4p", projectOptionId)
            .then((data) => {
                setSat4pData((prev) => {
                    const updated = { ...prev };
                    for (const row of data) {
                        const src = row.extra_fields?.source;
                        if (src && SAT4P_ROWS.includes(src)) {
                            updated[src] = {
                                base_scope1: row.extra_fields?.base_scope1 ?? "",
                                base_scope2: row.extra_fields?.base_scope2 ?? "",
                                actual_scope3: row.extra_fields?.actual_scope3 ?? "",
                                actual_scope4: row.extra_fields?.actual_scope4 ?? "",
                            };
                        }
                    }
                    return updated;
                });
            })
            .catch((e) => console.error("Failed to load SAT 4P data", e))
            .finally(() => setLoading(false));
    }, [open, shortcutKey, stageInstanceId, projectOptionId]);

    if (!open || !shortcutKey) return null;

    const cfg = SHORTCUT_TABLE_CONFIGS[shortcutKey];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-[var(--radius-3)] shadow-xl w-[90%] max-w-6xl max-h-[85vh] flex flex-col">

                <div className="px-6 pt-6">
                    <div className="text-text-dark text-2xl">Shortcut from other tools</div>
                    <div className="text-text-base text-base">{cfg.title}</div>
                    {cfg.title === "SAT 4P" && (
                        <div className="text-text-base mt-6 mb-4">Enter results from the GHG Emissions report section</div>)}
                </div>

                <div className="px-6 pb-6 overflow-auto">
                    {shortcutKey === "IS_MATERIALS" ? (
                        <><Table
                            data={rows}
                            columns={cfg.columns()}
                            enableInlineNewRow
                            readOnly={!!readOnly}
                            hideToolbarActions
                            onNewRowSave={async (draft) => {
                                setRows((prev) => [{ id: crypto.randomUUID(), ...draft }, ...prev]);
                                return true;
                            }}
                            onCellChange={({ id, key, value }) => {
                                setRows((prev) =>
                                    prev.map((r) => (r.id === id ? { ...r, [key]: value } : r))
                                );
                            }}
                        />

                            <div className="border-b border-light-grey/65 border-t-0">
                                <div
                                    className="flex"
                                >
                                    <div className="px-4 py-2 font-medium text-text-base bg-neutral-95 w-130">
                                        Maintenance and use
                                    </div>

                                    <div className="px-2 py-1 w-65">
                                        <input
                                            type="number"
                                            className="w-full rounded-[var(--radius-3)] px-2 py-1 focus-visible:ring-0 text-right text-text-table-cell text-sm"
                                            disabled={!!readOnly}
                                            value={maintenanceUse.base_case}
                                            onChange={(e) =>
                                                setMaintenanceUse((prev) => ({
                                                    ...prev,
                                                    base_case:
                                                        e.target.value === "" ? "" : Number(e.target.value),
                                                }))
                                            }
                                        />
                                    </div>

                                    <div className="px-2 py-1 w-76">
                                        <input
                                            type="number"
                                            className="w-full rounded-[var(--radius-3)] px-2 py-1 focus-visible:ring-0 text-right text-text-table-cell text-sm"
                                            disabled={!!readOnly}
                                            value={maintenanceUse.actual_case}
                                            onChange={(e) =>
                                                setMaintenanceUse((prev) => ({
                                                    ...prev,
                                                    actual_case:
                                                        e.target.value === "" ? "" : Number(e.target.value),
                                                }))
                                            }
                                        />
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        <table className="w-full text-sm border-0 border-collapse">
                            <thead>
                                <tr className="bg-neutral-98 text-text-base">
                                    <th rowSpan={2} className="border border-light-grey/65 px-4 py-2 text-left  font-medium">
                                        Emissions source
                                    </th>
                                    <th colSpan={2} className="border border-light-grey/65 px-4 py-2 text-center font-medium">
                                        Base case
                                    </th>
                                    <th colSpan={2} className="border border-light-grey/65 px-4 py-2 text-center  font-medium">
                                        Actual case
                                    </th>
                                </tr>

                                <tr className="bg-neutral-98 text-text-base">
                                    <th className="border border-light-grey/65 px-2 py-2 text-left  font-medium">Scope 1 emissions (tCO₂e)</th>
                                    <th className="border border-light-grey/65 px-2 py-2 text-left  font-medium">Scope 3 emissions (tCO₂e)</th>
                                    <th className="border border-light-grey/65 px-2 py-2 text-left font-medium">Scope 1 emissions (tCO₂e)</th>
                                    <th className="border border-light-grey/65 px-2 py-2 text-left font-medium">Scope 3 emissions (tCO₂e)</th>
                                </tr>
                            </thead>

                            <tbody>
                                {SAT4P_ROWS.map((source) => (
                                    <tr key={source}>
                                        <td className="border border-light-grey/65 px-4 py-2 text-text-table-cell">
                                            {source}
                                        </td>

                                        <td className="border border-light-grey/65 px-2 py-1 text-right">
                                            <input
                                                type="number"
                                                className="w-full rounded-[var(--radius-3)] px-2 py-1 focus-visible:ring-0 focus-visible:ring-offset-0"
                                                disabled={!!readOnly}

                                                value={sat4pData[source].base_scope1}
                                                onChange={(e) =>
                                                    setSat4pData((prev) => ({
                                                        ...prev,
                                                        [source]: {
                                                            ...prev[source],
                                                            base_scope1:
                                                                e.target.value === "" ? "" : Number(e.target.value),
                                                        },
                                                    }))
                                                }
                                            />
                                        </td>

                                        <td className="border border-light-grey/65 px-2 py-1 text-right">
                                            <input
                                                type="number"
                                                className="w-full rounded-[var(--radius-3)] px-2 py-1"
                                                disabled={!!readOnly}

                                                value={sat4pData[source].base_scope2}
                                                onChange={(e) =>
                                                    setSat4pData((prev) => ({
                                                        ...prev,
                                                        [source]: {
                                                            ...prev[source],
                                                            base_scope2:
                                                                e.target.value === "" ? "" : Number(e.target.value),
                                                        },
                                                    }))
                                                }
                                            />
                                        </td>

                                        <td className="border border-light-grey/65 px-2 py-1 text-right">
                                            <input
                                                type="number"
                                                className="w-full rounded-[var(--radius-3)] px-2 py-1"
                                                disabled={!!readOnly}

                                                value={sat4pData[source].actual_scope3}
                                                onChange={(e) =>
                                                    setSat4pData((prev) => ({
                                                        ...prev,
                                                        [source]: {
                                                            ...prev[source],
                                                            actual_scope3:
                                                                e.target.value === "" ? "" : Number(e.target.value),
                                                        },
                                                    }))
                                                }
                                            />
                                        </td>

                                        <td className="border border-light-grey/65  px-2 py-1 text-right">
                                            <input
                                                type="number"
                                                className="w-full rounded-[var(--radius-3)] px-2 py-1"
                                                disabled={!!readOnly}

                                                value={sat4pData[source].actual_scope4}
                                                onChange={(e) =>
                                                    setSat4pData((prev) => ({
                                                        ...prev,
                                                        [source]: {
                                                            ...prev[source],
                                                            actual_scope4:
                                                                e.target.value === "" ? "" : Number(e.target.value),
                                                        },
                                                    }))
                                                }
                                            />
                                        </td>

                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                <div className="px-6 py-4 flex justify-end gap-3">
                    <button className="px-4 py-2 rounded-[var(--radius-3)] text-text-table-cell font-medium cursor-pointer" onClick={onClose}>
                        Cancel
                    </button>
                    <button
                        className="bg-primary text-white px-4 py-2 rounded-[var(--radius-3)] disabled:opacity-50 cursor-pointer"
                        disabled={readOnly || saving || loading}
                        onClick={async () => {
                            if (!stageInstanceId) return;
                            setSaving(true);
                            try {
                                if (shortcutKey === "IS_MATERIALS") {
                                    const base = { project_id: projectId, project_stage_instance_id: stageInstanceId, quantity: 0, ui_table_key: "shortcutIsMaterials", project_option_id: projectOptionId ?? null };
                                    const rowPayloads = rows.map((r) => ({
                                        ...base,
                                        extra_fields: {
                                            component_type: r.component_type,
                                            sub_component_type: r.sub_component_type,
                                            base_case: r.base_case,
                                            actual_case: r.actual_case,
                                        },
                                    }));
                                    const mainPayload = {
                                        ...base,
                                        extra_fields: {
                                            row_type: "maintenance",
                                            base_case: maintenanceUse.base_case,
                                            actual_case: maintenanceUse.actual_case,
                                        },
                                    };
                                    await ActivityDataService.bulkUpsert(stageInstanceId, "shortcutIsMaterials", [...rowPayloads, mainPayload]);
                                } else if (shortcutKey === "SAT_4P") {
                                    const base = { project_id: projectId, project_stage_instance_id: stageInstanceId, quantity: 0, ui_table_key: "shortcutSat4p", project_option_id: projectOptionId ?? null };
                                    const rowPayloads = SAT4P_ROWS.map((source) => ({
                                        ...base,
                                        extra_fields: {
                                            source,
                                            base_scope1: sat4pData[source].base_scope1,
                                            base_scope2: sat4pData[source].base_scope2,
                                            actual_scope3: sat4pData[source].actual_scope3,
                                            actual_scope4: sat4pData[source].actual_scope4,
                                        },
                                    }));
                                    await ActivityDataService.bulkUpsert(stageInstanceId, "shortcutSat4p", rowPayloads);
                                }
                                await onSaved?.();
                                onClose();
                            } catch (e) {
                                console.error("Failed to save shortcut data", e);
                            } finally {
                                setSaving(false);
                            }
                        }}
                    >
                        {saving ? "Saving..." : "Submit"}
                    </button>
                </div>
            </div>
        </div>
    );
};


type ShortcutProps = {
    stageInstanceId: string;
    projectId: string;
    projectOptionId: string | null;
    readOnly?: boolean;
    onSaved?: () => void;
};

export const ShortcutTools = ({ stageInstanceId, projectId, projectOptionId, readOnly, onSaved }: ShortcutProps) => {
    const [accordionState, setAccordionState] = useState(true);
    const [shortcutOpen, setShortcutOpen] = useState<ShortcutKey | null>(null);

    return (
        <>
            <div className="space-y-8 mx-12 mb-12 bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)]">

                <div className="flex items-center justify-between mb-4">
                    <div className="text-2xl font-light text-text-dark">
                        Shortcut from other tools (grade 3)
                    </div>

                    <button
                        type="button"
                        onClick={() => setAccordionState((v) => !v)}
                        className="w-5 h-5 inline-flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded cursor-pointer"
                    >
                        <span className="material-symbols-rounded">
                            {accordionState ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                        </span>
                    </button>
                </div>

                {accordionState && (
                    <div className="flex gap-3">
                        <button
                            type="button"
                            className="text-text-table-cell font-medium border border-text-table-cell rounded-[var(--radius-3)] px-4 py-2 cursor-pointer"
                            disabled={!!readOnly}
                            onClick={() => setShortcutOpen("IS_MATERIALS")}
                        >
                            IS Materials Calculator
                        </button>

                        <button
                            type="button"
                            className="text-text-table-cell font-medium border border-text-table-cell rounded-[var(--radius-3)] px-4 py-2 cursor-pointer"
                            disabled={!!readOnly}
                            onClick={() => setShortcutOpen("SAT_4P")}
                        >
                            SAT 4P
                        </button>
                    </div>
                )}
            </div>

            <ShortcutToolsModal
                open={shortcutOpen !== null}
                shortcutKey={shortcutOpen}
                onClose={() => setShortcutOpen(null)}
                stageInstanceId={stageInstanceId}
                projectId={projectId}
                projectOptionId={projectOptionId}
                onSaved={onSaved}
                readOnly={readOnly}
            />

        </>
    );
};

export default ShortcutTools;