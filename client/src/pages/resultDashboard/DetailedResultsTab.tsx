import { useEffect, useState } from "react";
import DataTable from "./DataTable";
import type { ColumnConfig } from "./DataTable";
import ResultsDashboardService from "@/services/ResultsDashboard.service";
import ScopeBreakdownTable from "./ScopeBreakdownTable";


export type DetailTab =
    | "Energy Consumption"
    | "Recycled Materials"
    | "User Emissions"
    | "Waste"
    | "Carbon Valuation"
    | "Carbon Storage"
    | "Emissions Scopes";

const DETAIL_TABS: DetailTab[] = [
    "Energy Consumption",
    "Recycled Materials",
    "User Emissions",
    "Waste",
    "Carbon Valuation",
    "Carbon Storage",
    "Emissions Scopes",
];

interface DetailedResultsTabProps {
    projectId?: string;
    stageInstanceId?: string;
    submissionLabel?: string;
    projectOptionId?: string;
    submissionPeriodId?: string;
    accountingMethod?: string;
     orgId?: string | null;
  mode?: "project" | "org";
  projectCategory?: string;
  programName?: string;
  projectTypecast?: string;
}

function normalizeScopeAccountingMethod(value?: string): "market" | "location" {
  if (!value) return "market";
  const v = value.toLowerCase();
  if (v.includes("location")) return "location";
  return "market";
}

function humaniseKey(key: string): string {
    return key
        .replace(/_/g, " ")
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function deriveColumns(rows: Record<string, any>[]): ColumnConfig<Record<string, any>>[] {
    if (!rows.length) return [];
    return Object.keys(rows[0]).map((key) => ({
        key,
        label: humaniseKey(key),
        align: typeof rows[0][key] === "number" ? "right" : "left",
    }));
}

function extractRows(data: any): Record<string, any>[] {
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.rows)) return data.rows;
    if (Array.isArray(data.data)) return data.data;
    return [];
}

const SCOPE_LABELS: Record<string, string> = {
  "1": "Scope 1",
  "2": "Scope 2",
  "3": "Scope 3",
  upscaling: "Upscaling",
  total: "Total",
};

const EMISSIONS_SCOPE_CSV_COLUMNS: ColumnConfig<Record<string, any>>[] = [
  { key: "scope", label: "GHG Scope" },
  { key: "baseline_construction", label: "Baseline Construction (tCO2e)", align: "right" },
  { key: "baseline_operations", label: "Baseline Operations (tCO2e)", align: "right" },
  { key: "baseline_lifecycle", label: "Baseline Lifecycle (tCO2e)", align: "right" },
  { key: "actual_construction", label: "Actual Construction (tCO2e)", align: "right" },
  { key: "actual_operations", label: "Actual Operations (tCO2e)", align: "right" },
  { key: "actual_lifecycle", label: "Actual Lifecycle (tCO2e)", align: "right" },
];

function transformScopeRowsForCsv(data: any): Record<string, any>[] {
  const rows = Array.isArray(data?.rows) ? data.rows : [];
  return rows.map((row: any) => ({
    ...row,
    scope: SCOPE_LABELS[row.scope] ?? row.scope,
  }));
}

function downloadCsv(
  rows: Record<string, any>[],
  columns: ColumnConfig<Record<string, any>>[],
  fileName: string
) {
  if (!rows.length) return;

  const headers = columns.map((c) => c.label);

  const csvRows = [
    headers.join(","),
    ...rows.map((row) =>
      columns
        .map((col) => {
          const value = row[col.key];

          if (value == null) return "";

          const str = String(value).replace(/"/g, '""');

          return `"${str}"`;
        })
        .join(",")
    ),
  ];

  const blob = new Blob([csvRows.join("\n")], {
    type: "text/csv;charset=utf-8;",
  });

  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = `${fileName}.csv`;

  document.body.appendChild(link);
  link.click();

  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function transformUserEmissions(data: any): Record<string, any>[] {
  if (!data?.options?.length) return [];

  const result: Record<string, any>[] = [];

  data.options.forEach((option: any) => {
    const optionLabel = option.option_label;

    const processSection = (section: any) => {
      if (!section?.years || !section?.rows) return;

      const years = section.years;

      section.rows.forEach((row: any) => {

        const rowObj: Record<string, any> = {
          option: optionLabel,
          vehicle: row.label,
        };

        years.forEach((year: number, i: number) => {
          rowObj[year] = Number(row.values?.[i]) || 0;
        });

        result.push(rowObj);
      });
    };

    processSection(option.road_section);

    processSection(option.rail_section);
  });

  return result;
}

const COLUMN_CONFIGS: Partial<Record<DetailTab, ColumnConfig<Record<string, any>>[]>> = {
    "Energy Consumption": [
        { key: "lifecycle_stage",           label: "Lifecycle Stage" },
        { key: "input_table",               label: "Input Table" },
        { key: "sub_category",              label: "Sub-category" },
        { key: "emissions_source",          label: "Emissions Source" },
        { key: "unit",                      label: "Unit" },
        { key: "quantity",                  label: "Quantity",                      align: "right" },
        { key: "conversion_factor",         label: "Conversion Factor (GJ/unit)",   align: "right" },
        { key: "energy_gj",                 label: "Energy Use (GJ)",               align: "right" },
        { key: "renewable_status",          label: "Renewable Status" },
    ],
    "Recycled Materials": [
        { key: "input_table",               label: "Input Table" },
        { key: "sub_category",              label: "Sub-Category" },
        { key: "emissions_source",          label: "Emissions Source" },
        { key: "unit",                      label: "Unit" },
        { key: "quantity",                  label: "Quantity",                  align: "right" },
        { key: "density",                   label: "Density",                   align: "right" },
        { key: "mass_t",                    label: "Mass (tonnes)",             align: "right" },
        { key: "recycled_pct",              label: "Recycled Content (%)",      align: "right" },
        { key: "recycled_t",                label: "Recycled Content (tonnes)", align: "right" },
        { key: "reused_pct",                label: "Reused Content (%)",        align: "right" },
        { key: "reused_t",                  label: "Reused Content (tonnes)",   align: "right" },
        { key: "virgin_t",                  label: "Virgin Material (tonnes)",  align: "right" },
    ],
    "Waste": [
        { key: "waste_treatment",  label: "Waste Treatment" },
        { key: "waste_type",       label: "Waste Type" },
        { key: "quantity_t",       label: "Quantity (t)", align: "right" },
    ],
    "Carbon Storage": [
        { key: "input_table",               label: "Input Table" },
        { key: "category",                  label: "Category" },
        { key: "sub_category",              label: "Sub-Category" },
        { key: "emissions_source",          label: "Emissions Source" },
        { key: "unit",                      label: "Unit" },
        { key: "quantity",                  label: "Quantity",                              align: "right" },
        { key: "carbon_storage_ef",         label: "Carbon Storage Emission Factor (tCO₂e/UoM)", align: "right" },
        { key: "carbon_storage_tco2e",      label: "Carbon Storage (tCO₂e)",                align: "right" },
    ],
    "Carbon Valuation": [
        { key: "year",                                          label: "Year" },
        { key: "upfrontA1A5",                                 label: "Upfront (A1-A5)",                                          align: "right" },
        { key: "useB1",                                        label: "Use (B1)",                                                 align: "right" },
        { key: "maintenanceRepairReplacementRefurbishmentB2B5",          label: "Maintenance, Repair, Replacement & Refurbishment (B2-B5)", align: "right" },
        { key: "operationalEnergyWaterB6B7",                label: "Operational Energy & Water (B6-B7)",                      align: "right" },
        { key: "usersB8",                                      label: "Users (B8)",                                              align: "right" },
        { key: "totalEmissionsA1B8",                         label: "Total Emissions (A1 - B8)",                               align: "right" },
        { key: "centralCarbonValuePerTco2e",                label: "Central Carbon Value ($/tCO₂e)",                          align: "right" },
        { key: "centralCarbonValue",                          label: "Central Carbon Value ($)",                                align: "right" },
        { key: "lowCarbonValuePerTco2e",                    label: "Low Carbon Value ($/tCO₂e)",                              align: "right" },
        { key: "lowCarbonValue",                              label: "Low Carbon Value ($)",                                    align: "right" },
        { key: "highCarbonValuePerTco2e",                   label: "High Carbon Value ($/tCO₂e)",                             align: "right" },
        { key: "highCarbonValue",                             label: "High Carbon Value ($)",                                   align: "right" },
    ],
"User Emissions": [
  { key: "option", label: "Option" },
  { key: "vehicle", label: "Vehicle" },
],
};

function resolveColumns(tab: DetailTab, rows: Record<string, any>[]) {
  if (tab === "User Emissions" && rows.length) {
    const baseCols = [
      { key: "option", label: "Option" },
      { key: "vehicle", label: "Vehicle" },
    ];

    const yearKeys = Object.keys(rows[0]).filter((k) =>
      /^\d{4}$/.test(k)
    );

    const yearCols = yearKeys.map((year) => ({
      key: year,
      label: year,
      align: "right" as const,
    }));

    return [...baseCols, ...yearCols];
  }

  return COLUMN_CONFIGS[tab] ?? deriveColumns(rows);
}

async function fetchDetail(
    tab: DetailTab,
    projectId: string,
    stageInstanceId: string,
    submissionLabel: string,
    projectOptionId?: string,
    submissionPeriodId?: string,
    accountingMethod?: string,
): Promise<any> {
    const args: [string, string, string, string?, string?] = [
        projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId,
    ];
    switch (tab) {
        case "Energy Consumption":    return ResultsDashboardService.energyDetail(...args);
        case "Recycled Materials":    return ResultsDashboardService.materialsDetail(...args);
        case "User Emissions":        return ResultsDashboardService.userEmissions(projectId, stageInstanceId);
        case "Waste":                 return ResultsDashboardService.wasteDetail(...args);
        case "Carbon Valuation":      return ResultsDashboardService.carbonValuationDetails(...args);
        case "Carbon Storage":        return ResultsDashboardService.carbonStorageDetail(...args);
        case "Emissions Scopes":       return ResultsDashboardService.scopeBreakdown(projectId, stageInstanceId, accountingMethod || "location", submissionLabel, projectOptionId, submissionPeriodId);
    }
}


async function fetchOrgDetail(
  tab: DetailTab,
  orgId: string,
  projectCategory?: string,
  programName?: string,
  submissionLabel?: string,
  projectTypecast?: string,
  accountingMethod?: string,
): Promise<any> {

  const safeCategory = projectCategory ?? "";
  const safeProgram = programName ?? "";
  const safeSubmission = submissionLabel ?? "";
  const safeTypecast = projectTypecast ?? "";
  const safeMethod = accountingMethod ?? "";

  switch (tab) {

    case "Energy Consumption":
      return ResultsDashboardService.orgEnergyDetail(
        orgId,
        safeMethod,
        safeCategory,
        safeProgram,
        safeTypecast,
        safeSubmission
      );

    case "Recycled Materials":
      return ResultsDashboardService.orgMaterialsDetail(
        orgId,
        safeCategory,
        safeProgram,
        safeTypecast,
        safeSubmission,
        safeMethod,
      );

case "User Emissions":
  return ResultsDashboardService.orgUserEmissions(
    orgId,
    safeCategory,
    safeProgram,
    safeTypecast,
    safeSubmission,
    safeMethod
  );

    case "Waste":
      return ResultsDashboardService.orgWasteDetail(
        orgId,
        safeCategory,
        safeProgram,
        safeTypecast,
        safeSubmission,
        safeMethod
      );

    case "Carbon Valuation":
      return ResultsDashboardService.orgCarbonValuationDetails(
        orgId,
        safeCategory,
        safeProgram,
        safeTypecast,
        safeSubmission,
        safeMethod
      );

    case "Carbon Storage":
      return ResultsDashboardService.orgCarbonStorageDetail(
        orgId,
        safeCategory,
        safeProgram,
        safeTypecast,
        safeSubmission,
        safeMethod
      );

    case "Emissions Scopes":
return ResultsDashboardService.orgScopeBreakdown(
  orgId,
  safeCategory,
  safeMethod,
  safeSubmission,
  safeProgram,
  safeTypecast
);

  }
}
export default function DetailedResultsTab({
    projectId,
    stageInstanceId,
    submissionLabel,
    projectOptionId,
    submissionPeriodId,
    accountingMethod,
      orgId,
  mode,
  projectCategory,
  programName,
  projectTypecast,
}: DetailedResultsTabProps) {
    const [activeTab, setActiveTab] = useState<DetailTab>("Energy Consumption");
    const [rows, setRows] = useState<Record<string, any>[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [scopeData, setScopeData] = useState<any | null>(null);
    const [scopeLoading, setScopeLoading] = useState(false);
    const [scopeError, setScopeError] = useState<string | null>(null);
    const scopeAccountingMethod = normalizeScopeAccountingMethod(accountingMethod);

    useEffect(() => {
        
if (mode === "project") {
  if (!projectId || !stageInstanceId || !submissionLabel) return;
}else if (mode === "org") {
  if (!orgId) return; // only orgId required
}else {
    return;
}
let cancelled = false;

        
  if (activeTab === "Emissions Scopes") {
    setScopeLoading(true);
    setScopeError(null);
    setScopeData(null);

    const fetchScopes = mode === "project"
      ? fetchDetail(activeTab, projectId!, stageInstanceId!, submissionLabel ?? "", projectOptionId, submissionPeriodId, scopeAccountingMethod)
      : fetchOrgDetail(activeTab, orgId ?? "", projectCategory ?? "", programName ?? "", submissionLabel ?? "", projectTypecast ?? "", scopeAccountingMethod);

    fetchScopes
      .then((data) => {
        if (!cancelled) setScopeData(data);
      })
      .catch(() => {
        if (!cancelled) setScopeError("Failed to load scope data. Please try again.");
      })
      .finally(() => {
        if (!cancelled) setScopeLoading(false);
      });

    return () => { cancelled = true; };
  }

        setLoading(true);
        setError(null);
        setRows([]);

        
const fetchData = mode === "project"
    ? fetchDetail(activeTab, projectId!, stageInstanceId!, submissionLabel ?? "", projectOptionId, submissionPeriodId)
    : fetchOrgDetail(activeTab, orgId ?? "", projectCategory ?? "", programName ?? "", submissionLabel ?? "", projectTypecast ?? "", accountingMethod);
      fetchData
        .then((data) => {
          if (cancelled) return;

          if (activeTab === "User Emissions") {
            const transformed = transformUserEmissions(data);

            setRows(transformed);
          } else {
            setRows(extractRows(data));
          }
        })
    .catch(() => {
      if (!cancelled)
        setError(
          mode === "project"
            ? "Failed to load project detail data. Please try again."
            : "Failed to load org detail data. Please try again."
        );
    })
    .finally(() => {
      if (!cancelled) setLoading(false);
    });

  return () => { cancelled = true; };

    }, [activeTab, projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId, accountingMethod, orgId, 
      projectCategory, projectTypecast, programName, mode, scopeAccountingMethod
    ]);

    const columns = resolveColumns(activeTab, rows);
    const scopeCsvRows = transformScopeRowsForCsv(scopeData);

    return (
        <div className="flex flex-col h-full overflow-hidden">
            <div className="flex items-center gap-1 px-6 pt-4 pb-0 border-b border-[#E8E8E8] bg-white flex-shrink-0 flex-wrap">
                {DETAIL_TABS.map((tab) => {
                    const isActive = tab === activeTab;
                    return (
                        <button
                            key={tab}
                            type="button"
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2 text-sm whitespace-nowrap cursor-pointer transition-colors border-b-2 -mb-px ${
                                isActive
                                    ? "border-primary text-primary font-medium"
                                    : "border-transparent text-[#6C6C6C] hover:text-[#3F3A38] hover:border-[#D0D0D0]"
                            }`}
                        >
                            {tab}
                        </button>
                    );
                })}
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-6">
                <div className="flex justify-end mb-4">
                  {activeTab === "Emissions Scopes" && scopeCsvRows.length > 0 && (
                    <button
                      type="button"
                      onClick={() =>
                        downloadCsv(
                          scopeCsvRows,
                          EMISSIONS_SCOPE_CSV_COLUMNS,
                          "Emissions_Scopes"
                        )
                      }
                      className="px-3 py-2 text-sm border rounded-md bg-white hover:bg-gray-50"
                    >
                      Download CSV
                    </button>
                  )}
                  {activeTab !== "Emissions Scopes" && rows.length > 0 && (
                    <button
                      type="button"
                      onClick={() =>
                        downloadCsv(
                          rows,
                          columns,
                          activeTab.replace(/\s+/g, "_")
                        )
                      }
                      className="px-3 py-2 text-sm border rounded-md bg-white hover:bg-gray-50"
                    >
                      Download CSV
                    </button>
                  )}
                </div>
                {activeTab === "Emissions Scopes" && (
                    <ScopeBreakdownTable
                        data={scopeData}
                        loading={scopeLoading}
                        error={scopeError}
                    />
                )}

                {activeTab !== "Emissions Scopes" && (mode === "project" && (!projectId || !stageInstanceId)) && (
                    <div className="flex flex-col items-center justify-center h-full text-[#6C6C6C] gap-2">
                        <span className="material-symbols-rounded text-4xl text-[#D0D0D0]">
                            table_chart
                        </span>
                        <p className="text-sm">Select a submission on the dashboard to view detailed data.</p>
                    </div>
                )}

                {activeTab !== "Emissions Scopes" && (mode === "project" ? (projectId && stageInstanceId) : true) && loading && (
                    <div className="flex items-center justify-center h-full text-[#6C6C6C] text-sm">
                        Loading…
                    </div>
                )}

                {activeTab !== "Emissions Scopes" && !loading && error && (
                    <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                        {error}
                    </div>
                )}

                {activeTab !== "Emissions Scopes" && !loading && !error && 
rows.length === 0 &&
(mode === "project" ? (projectId && stageInstanceId) : true) && (
                    <div className="flex flex-col items-center justify-center h-full text-[#6C6C6C] gap-2">
                        <span className="material-symbols-rounded text-4xl text-[#D0D0D0]">
                            inbox
                        </span>
                        <p className="text-sm">No data available for {activeTab}.</p>
                    </div>
                )}

                {activeTab !== "Emissions Scopes" && !loading && !error && rows.length > 0 && (
                    <DataTable
                        title={activeTab}
                        columns={columns}
                        rows={rows}
                    />
                )}
            </div>
        </div>
    );
}
