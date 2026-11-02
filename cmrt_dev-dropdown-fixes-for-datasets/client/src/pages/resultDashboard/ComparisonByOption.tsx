import React, {useState, useEffect} from "react";
import RangeBarChart from "../../components/charts/RangeBarChart";
import ResultsDashboardService from "@/services/ResultsDashboard.service";
import { formatDisplayNumber } from "@/utils/utils";

/* ================= TYPES ================= */

interface ProjectOption {
  label: string;
  emissions: {
    min: number;
    medium: number;
    max: number;
  };
  carbonValue: {
    min: number;
    medium: number;
    max: number;
  };
}

interface ComparisonByOptionResponse {
  projectOptions: ProjectOption[];
  unit?: {
    emissions?: string;
    carbonValue?: string;
  };
}


interface ComparisonByOptionProps {
  projectId: string;
  accountingMethod: string;
}

/* ================= COMPONENT ================= */

const ComparisonByOption: React.FC<ComparisonByOptionProps> = ({ projectId, accountingMethod }) => {

const [data, setData] = useState<ComparisonByOptionResponse  | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!projectId || !accountingMethod ) return;
    let ignore = false;
    (async () => {
      try {
        setLoading(true);
        const res =await ResultsDashboardService.optionsComparisonSummary( projectId,accountingMethod);
        if (ignore) return;

        setData(res);
      } catch (e) {
        console.error("Failed to load material hotspots:", e);
      } finally {
        setLoading(false);
      }
    })();

    return () => {
      ignore = true;
    };
  }, [projectId, accountingMethod]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        Loading...
      </div>
    );
  }

  const projectOptions: ProjectOption[] = Array.isArray(
    data?.projectOptions
  )
    ? data!.projectOptions
    : [];

  const unit = {
    emissions: data?.unit?.emissions ?? "",
    carbonValue: data?.unit?.carbonValue ?? "",
  };

  const ranges: Array<"min" | "medium" | "max"> = [
    "min",
    "medium",
    "max",
  ];

  // No usable data
  if (projectOptions.length === 0 || !accountingMethod) {
    return (
      <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 text-sm text-[var(--color-text-faint)]">
        No comparison data available
      </div>
    );
  }

  return (
    <div className="px-4 space-y-6">
      {/* ================= TOTAL EMISSIONS TABLE ================= */}
      <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6">
        <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
          Total emissions (A1–B8) by project option
        </h3>

        <div className="overflow-x-auto">
          <table className="min-w-[900px] w-full text-sm">
            <thead className="border-b border-[var(--color-neutral-90)] text-xs text-text-base font-medium">
              <tr>
                <th className="py-2 text-left">
                  Range ({unit.emissions})
                </th>
                {projectOptions.map((opt) => (
                  <th
                    key={opt.label}
                    className="py-2 text-right whitespace-nowrap"
                  >
                    {opt.label}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {ranges.map((key) => (
                <tr
                  key={`emissions-${key}`}
                  className="border-b border-[var(--color-neutral-95)]"
                >
                  <td className="py-3 capitalize">
                    {key === "min"
                      ? "Minimum"
                      : key === "medium"
                      ? "Medium"
                      : "Maximum"}
                  </td>

                  {projectOptions.map((opt) => (
                    <td
                      key={`${opt.label}-${key}-e`}
                      className="py-3 text-right tabular-nums"
                    >
                      {formatDisplayNumber(opt.emissions?.[key] ?? 0)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ================= TOTAL CARBON VALUE TABLE ================= */}
      <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6">
        <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
          Total carbon value ($) by project option (A1–B8)
        </h3>

        <div className="overflow-x-auto">
          <table className="min-w-[900px] w-full text-sm">
            <thead className="border-b border-[var(--color-neutral-90)] text-xs text-text-base font-medium">
              <tr>
                <th className="py-2 text-left">
                  Carbon value ({unit.carbonValue})
                </th>
                {projectOptions.map((opt) => (
                  <th
                    key={opt.label}
                    className="py-2 text-right whitespace-nowrap"
                  >
                    {opt.label}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {ranges.map((key) => (
                <tr
                  key={`carbon-${key}`}
                  className="border-b border-[var(--color-neutral-95)]"
                >
                  <td className="py-3 capitalize">
                    {key === "min"
                      ? "Minimum"
                      : key === "medium"
                      ? "Medium"
                      : "Maximum"}
                  </td>

                  {projectOptions.map((opt) => (
                    <td
                      key={`${opt.label}-${key}-c`}
                      className="py-3 text-right tabular-nums"
                    >
                      {formatDisplayNumber(opt.carbonValue?.[key] ?? 0)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ================= RANGE BAR CHART ================= */}
      <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 flex flex-col">
        <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
          Total construction, operations and maintenance carbon (A1–B8)
        </h3>

        <div className="flex-1">
          <RangeBarChart
            labels={projectOptions.map((o) => o.label)}
            datasets={[
              {
                label: "Max / Min range",
                ranges: projectOptions.map((o) => [
                  Number(o.emissions?.min ?? 0),
                  Number(o.emissions?.max ?? 0),
                ]),
                color: "#E59D38",
              },
            ]}
            yAxis={{ title: unit.emissions }}
            legend={{
              show: true,
              position: "bottom",
              boxShape: "square",
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default ComparisonByOption;