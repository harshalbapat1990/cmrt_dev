import React, { useState, useEffect } from "react";
import DoughnutChart from "../../components/charts/DoughnutChart";
import TreemapChart from "../../components/charts/TreemapChart";
import ResultsDashboardService from "../../services/ResultsDashboard.service";
import { formatDisplayNumber } from "@/utils/utils";

/* ================= TYPES ================= */

interface SummaryIndicator {
  value: number;
  unit?: string;
}

interface SummaryIndicators {
  primaryIndicator?: SummaryIndicator;
  secondaryIndicator?: SummaryIndicator;
}

interface Module {
  code: string;
  label: string;
  value: number;
}

interface SourceCategory {
  category: string;
  value: number;
}

// interface EmissionsBreakdownData {
//   summaryIndicators?: SummaryIndicators;
//   modules?: Module[];
//   sourceCategories?: SourceCategory[];
// }

interface EmissionsBreakdownTabProps {
  // data?: EmissionsBreakdownData;
  projectId?: string;
  stageInstanceId?: string;
  projectOptionId?: string;
  accountingMethod?: string;
  submissionPeriodId?: string;
  submissionLabel?: string;
  orgId?: string | null;
  mode?: "project" | "org";
  projectCategory?: string;
  programName?: string;
  projectTypecast?: string;
}

/* ================= HELPERS ================= */

const sumByCodes = (modules: Module[], codes: string[]) =>
  modules
    .filter((m) => codes.includes(m.code))
    .reduce((s, m) => s + (Number(m.value) || 0), 0);

const getValueForCode = (modules: Module[], code: string): number =>
  Number(modules.find((m) => m.code === code)?.value ?? 0);

/* ================= TREEMAP COLORS ================= */

const TREEMAP_COLORS = [
  "#B06443",
  "#B04359",
  "#B59F4A",
  "#439887",
  "#4557A1",
  "#94477D",
  "#5B4294",
  "#4586A1",
  "#4DA869",
  "#505050",
];

const getColorForCategory = (key: string) =>
  TREEMAP_COLORS[
  [...key].reduce((sum, c) => sum + c.charCodeAt(0), 0) %
  TREEMAP_COLORS.length
  ];

/* ================= COMPONENT ================= */

const EmissionsBreakdownTab: React.FC<EmissionsBreakdownTabProps> = ({
  // data,
  projectId,
  stageInstanceId,
  projectOptionId,
  accountingMethod,
  submissionPeriodId,
  submissionLabel,
  orgId,
  mode,
  projectCategory,
  programName,
  projectTypecast,
}) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let ignore = false;
    const loadData = async () => {
      try {
        setLoading(true);
        setData(null);

        if (mode === "org") {
          if (!orgId) return;
          const normalizedProgramName =
            programName === "__NONE__" ? "" : programName ?? "";
          const res =
            await ResultsDashboardService.orgEmissionsBreakdownSummary(
              orgId,
              accountingMethod ?? "location",
              projectCategory ?? "",
              normalizedProgramName,
              projectTypecast ?? "",
              submissionLabel ?? "",
            );
          if (!ignore) {
            setData(res);
          }
          return;
        } else {
          if (!projectId || !stageInstanceId || !submissionLabel) return;
          if (
            ["Business case", "Design"].includes(submissionLabel) &&
            !projectOptionId
          ) {
            return;
          }
          if (submissionLabel === "Construction" && !submissionPeriodId) {
            return;
          }
          const res = await ResultsDashboardService.emissionsBrkdownSummary(
            projectId,
            stageInstanceId,
            accountingMethod ?? "location",
            submissionLabel,
            projectOptionId,
            submissionPeriodId
          );
          if (!ignore) {
            setData(res);
          }
        }
      } catch (e) {
        console.error("Failed to load emissions breakdown:", e);
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    loadData();
    return () => {
      ignore = true;
    };
  }, [
    mode,
    orgId,
    accountingMethod,
    projectCategory,
    programName,
    projectTypecast,
    projectId,
    stageInstanceId,
    projectOptionId,
    submissionLabel,
    submissionPeriodId,
  ]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        Loading...
      </div>
    );
  }


  if (!data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2">
        <h3 className="text-gray-500">No data exists for Emission Breakdown</h3>
      </div>
    );
  }

  const modules: Module[] = data.modules ?? [];
  const sourceCategories: SourceCategory[] = data.sourceCategories ?? [];

  if (!modules.length && !sourceCategories.length) {
    return (
      <div className="rounded bg-white p-6 text-sm text-gray-500">
        No data available
      </div>
    );
  }

  /* ================= CALCULATIONS ================= */

  const totalA1B8 =
    sumByCodes(modules, ["A1", "A2", "A3"]) +
    getValueForCode(modules, "A4") +
    getValueForCode(modules, "A5") +
    getValueForCode(modules, "B1") +
    sumByCodes(modules, ["B2", "B3", "B4", "B5"]) +
    getValueForCode(modules, "B6") +
    getValueForCode(modules, "B7") +
    getValueForCode(modules, "B8");

  const offsets = getValueForCode(modules, "Offsets");
  const storedCarbon = getValueForCode(modules, "Stored carbon");
  const totalNet = totalA1B8 - offsets - storedCarbon;

  const doughnutData = [
    {
      label: "Upfront (A1-A5)",
      value: sumByCodes(modules, ["A1", "A2", "A3", "A4", "A5"]),
      color: "#E7A33E",
    },
    {
      label: "In-use & operations (B1-B5)",
      value: sumByCodes(modules, ["B1", "B2", "B3", "B4", "B5"]),
      color: "#616361",
    },

    {
      label: "Operational energy (B6)",
      value: getValueForCode(modules, "B6"),
      color: "#3B82F6",
    },
    {
      label: "Water (B7)",
      value: getValueForCode(modules, "B7"),
      color: "#06B6D4",
    },

    {
      label: "User (B8)",
      value: getValueForCode(modules, "B8"),
      color: "#BDBDBD",
    },
  ].filter((d) => d.value > 0);

  const treemapColors: Record<string, string> = Object.fromEntries(
    sourceCategories.map((s) => [
      s.category,
      getColorForCategory(s.category),
    ])
  );



  const totalSource =
    sourceCategories.reduce((s, c) => s + (Number(c.value) || 0), 0) || 0;

  /* ================= UI ================= */

  return (
    <div className="grid md:px-4">
      {/* ================= TOP ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-6">

        {/* MODULE TABLE */}
        <div className="rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-6">
          <h3 className="mb-4 text-xl font-light text-[#3F3A38]">
            Emissions breakdown by module
          </h3>

          <div className="grid grid-cols-[1fr_auto] pb-2 text-xs text-text-base font-medium border-b border-[#E8E8E8]">
            <div >Module</div>
            <div className="text-right">Emissions (tCO₂e)</div>
          </div>

          <div className="divide-y divide-[#EFEFEF] text-sm text-[#3F3A38]">
            <SingleRow
              label={
                <div className="leading-6">
                  Raw material supply (A1)<br />
                  Transport (A2)<br />
                  Manufacturing (A3)
                </div>
              }
              value={sumByCodes(modules, ["A1", "A2", "A3"])}
            />

            <SingleRow
              label="Transport to site (A4)"
              value={getValueForCode(modules, "A4")}
            />

            <SingleRow
              label="Construction installation process (A5)"
              value={getValueForCode(modules, "A5")}
            />

            <SingleRow
              label="Use (B1)"
              value={getValueForCode(modules, "B1")}
            />

            <SingleRow
              label={
                <div className="leading-6">
                  Maintenance (B2)<br />
                  Repair (B3)<br />
                  Replacement (B4)<br />
                  Refurbishment (B5)
                </div>
              }
              value={sumByCodes(modules, ["B2", "B3", "B4", "B5"])}
            />

            <SingleRow
              label="Operational energy (B6)"
              value={getValueForCode(modules, "B6")}
            />

            <SingleRow
              label="Water (B7)"
              value={getValueForCode(modules, "B7")}
            />

            <SingleRow
              label="User (B8)"
              value={getValueForCode(modules, "B8")}
            />

            <TotalRow label="Total (A1–B8)" value={totalA1B8} bold />
            <SingleRow label="Offsets" value={offsets} />
            <SingleRow label="Stored carbon" value={storedCarbon} />
            <TotalRow label="Total net" value={totalNet} bold />
          </div>
        </div>

        {/* DOUGHNUT */}
        <div className="rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-6 flex flex-col">
          <h3 className="text-xl font-light text-[#3F3A38]">
            Total emissions by module
          </h3>

          <div className="flex-1 mt-4">
            {doughnutData.length > 0 ? (
              <DoughnutChart
                footer={false}
                labels={doughnutData.map((d) => d.label)}
                values={doughnutData.map((d) => d.value)}
                colors={doughnutData.map((d) => d.color)}
                thickness={50}
                responsive
              />
            ) : (
              <div className="text-sm text-gray-500">
                No data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ================= BOTTOM ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-6">
        <div className="flex flex-col gap-3">
          {/* INDICATORS */}
          <Indicators summaryIndicators={data.summaryIndicators} />

          {/* SOURCE CATEGORY TABLE */}
          <div className="rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-6">
            <h3 className="mb-4 text-xl font-light text-[#3F3A38]">
              Emissions breakdown by source category
            </h3>

            <div className="grid grid-cols-3 pb-2 text-xs text-text-base font-medium border-b border-[#E8E8E8]">
              <div>Source</div>
              <div className="text-center">Emissions (tCO₂e)</div>
              <div className="text-right">Proportion of total (%)</div>
            </div>

            <div className="divide-y divide-[#EFEFEF] text-sm text-[#3F3A38]">
              {sourceCategories.map((s) => {
                const percentage =
                  totalSource > 0 ? (Number(s.value) / totalSource) * 100 : 0;

                return (
                  <div key={s.category} className="grid grid-cols-3 py-4">
                    <div>{s.category}</div>
                    <div className="text-center tabular-nums">
                      {formatDisplayNumber(s.value)}
                    </div>
                    <div className="text-right tabular-nums">
                      {formatDisplayNumber(percentage)}%
                    </div>
                  </div>
                );
              })}

              <div className="grid grid-cols-3 py-4 bg-[#F7F7F7] font-semibold">
                <div>Total</div>
                <div className="text-center tabular-nums">{formatDisplayNumber(totalSource)}</div>
                <div className="text-right tabular-nums">100%</div>
              </div>
            </div>
          </div>
        </div>

        {/* TREEMAP */}
        <div className="rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-6 mt-5">
          <h3 className="mb-4 text-xl font-light text-[#3F3A38]">
            Emissions by source category
          </h3>

          <div className="w-full h-[420px]">
            {sourceCategories.length > 0 ? (
              <TreemapChart
                data={sourceCategories
                  .filter((s) => Number(s.value) > 0)
                  .map((s) => ({
                    category: s.category,
                    value: Number(s.value),
                    color: treemapColors[s.category],
                  }))}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-gray-500">
                No source category data
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};


const SingleRow = ({
  label,
  value,
}: {
  label: React.ReactNode;
  value: number;
}) => (
  <div className="grid grid-cols-[1fr_auto] py-4">
    <div>{label}</div>
    <div className="text-right tabular-nums">{formatDisplayNumber(value)}</div>
  </div>
);

const TotalRow = ({
  label,
  value,
  bold,
}: {
  label: string;
  value: number;
  bold?: boolean;
}) => (
  <div
    className={`grid grid-cols-[1fr_auto] py-4 bg-[#F7F7F7] ${bold ? "font-semibold" : ""
      }`}
  >
    <div>{label}</div>
    <div className="text-right tabular-nums">{formatDisplayNumber(value)}</div>
  </div>
);

const Indicators = ({
  summaryIndicators,
}: {
  summaryIndicators?: SummaryIndicators;
}) => {
  if (!summaryIndicators) return null;

  const { primaryIndicator, secondaryIndicator } = summaryIndicators;

  return (
    <div className="grid grid-cols-2 gap-4 mb-4 mt-5 w-fit">
      {/* {primaryIndicator && ( */}
        <div className="rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-4">
          <div className="text-xs text-[#7A7A7A] mb-1">
            Primary Indicator
          </div>
          <div className="text-2xl font-semibold tabular-nums">
            {formatDisplayNumber(primaryIndicator?.value)}
            {primaryIndicator?.unit && (
              <span className="ml-1 text-sm font-normal text-[#6C6C6C]">
                {primaryIndicator?.unit}
              </span>
            )}
          </div>
        </div>
      {/* )} */}

      {/* {secondaryIndicator && ( */}
        <div className="rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-4">
          <div className="text-xs text-[#7A7A7A] mb-1">
            Secondary Indicator
          </div>
          <div className="text-2xl font-semibold tabular-nums">
            {formatDisplayNumber(secondaryIndicator?.value)}
            <span className="ml-1 text-sm font-normal text-[#6C6C6C]">
             {secondaryIndicator?.unit}
            </span>
          </div>
        </div>
      {/* )} */}
    </div>
  );
};


export default EmissionsBreakdownTab;
