import React, {useState, useEffect} from "react";
import BarChart from "../../components/charts/BarChart";
import ResultsDashboardService from "../../services/ResultsDashboard.service";
import { formatDisplayNumber } from "@/utils/utils";

/* ================= TYPES ================= */

interface RenewableEnergySummaryProps {
  projectId?: string;
  stageInstanceId?: string;
  projectOptionId?: string;
  submissionPeriodId?: string;
  submissionLabel?: string;
   orgId?: string | null;
  mode?: "project" | "org";
  projectCategory?: string;
  programName?: string;
  projectTypecast?: string;
}


const PREFERRED_STAGES = [
  "Lifecycle",
  "Construction",
  "In-use / Operations",
];
/* ================= HELPERS ================= */

const format = formatDisplayNumber;


/* ================= COMPONENT ================= */

const RenewableEnergySummary: React.FC<RenewableEnergySummaryProps> = ({
  projectId,
  stageInstanceId,
  projectOptionId,
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
              await ResultsDashboardService.orgRenewableEnergySummary(
                orgId,
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
  
            const res = await ResultsDashboardService.renewableEnergySummary(
              projectId,
              stageInstanceId,
              submissionLabel,
              projectOptionId,
              submissionPeriodId
            );
            if (!ignore) {
              setData(res);
            }
          }
        } catch (e) {
          console.error("Failed to load renewable energy summary:", e);
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

  const unit = data?.unit ?? "GJ";
  const stages = Array.isArray(data?.stages) ? data!.stages : [];

  const absoluteNR = data?.absolute?.nonRenewable ?? {};
  const absoluteR = data?.absolute?.renewable ?? {};
  const percentNR = data?.percentage?.nonRenewable ?? {};
  const percentR = data?.percentage?.renewable ?? {};

  //  Determine which stages to show in the BAR CHART
const stagesWithData = stages.filter(
  (s: any) => (percentNR[s] ?? 0) > 0 || (percentR[s] ?? 0) > 0
);

const preferredStagesWithData = PREFERRED_STAGES.filter((s) =>
  stagesWithData.includes(s)
);

//  Final stages for chart
const chartStages =
  preferredStagesWithData.length > 0
    ? preferredStagesWithData
    : stagesWithData.includes("Recurring project")
    ? ["Recurring project"]
    : [];

  const hasData =
    stages.length > 0 &&
    stages.some(
      (s: any) =>
        (absoluteNR[s] ?? 0) > 0 || (absoluteR[s] ?? 0) > 0
    );

  if (!hasData) {
    return (
      <div className="px-4">
        <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 text-sm text-[var(--color-text-faint)]">
          No renewable energy summary data available
        </div>
      </div>
    );
  }

  return (
    <div className="px-2 md:px-4 xl:px-4 space-y-6">
      <div className="mx-auto max-w-350 space-y-6">

        {/* ================= TABLE ================= */}
        <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-4 sm:p-6">
          <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
            Renewable energy consumption by source
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-sm">

              {/* ===== HEADER ===== */}
              <thead className="bg-[var(--color-neutral-98)] text-xs text-text-base font-medium">
                <tr>
                  <th
                    rowSpan={2}
                    className="border border-[var(--color-neutral-95)] px-4 py-3 text-left font-medium"
                  >
                    Energy type
                  </th>

                  {stages.map((stage: any) => (
                    <th
                      key={stage}
                      colSpan={2}
                      className="border border-[var(--color-neutral-95)] px-4 py-3 text-center font-medium"
                    >
                      {stage}
                    </th>
                  ))}
                </tr>

                <tr>
                  {stages.map((stage: any) => (
                    <React.Fragment key={`${stage}-sub`}>
                      <th className="border border-[var(--color-neutral-95)] px-4 py-3 text-right font-normal">
                        {unit}
                      </th>
                      <th className="border border-[var(--color-neutral-95)] px-4 py-3 text-right font-normal">
                        %
                      </th>
                    </React.Fragment>
                  ))}
                </tr>
              </thead>

              {/* ===== BODY ===== */}
              <tbody>
                {/* NON‑RENEWABLE */}
                <tr>
                  <td className="border border-[var(--color-neutral-95)] px-4 py-4 font-normal">
                    Non‑renewable
                  </td>

                  {stages.map((stage: any) => (
                    <React.Fragment key={`nr-${stage}`}>
                      <td className="border border-[var(--color-neutral-95)] px-4 py-4 text-right tabular-nums">
                        {format(absoluteNR[stage] ?? 0)}
                      </td>
                      <td className="border border-[var(--color-neutral-95)] px-4 py-4 text-right tabular-nums">
                        {(percentNR[stage] ?? 0).toFixed(1)}
                      </td>
                    </React.Fragment>
                  ))}
                </tr>

                {/* RENEWABLE */}
                <tr>
                  <td className="border border-[var(--color-neutral-95)] px-4 py-4 font-normal">
                    Renewable
                  </td>

                  {stages.map((stage: any) => (
                    <React.Fragment key={`r-${stage}`}>
                      <td className="border border-[var(--color-neutral-95)] px-4 py-4 text-right tabular-nums">
                        {format(absoluteR[stage] ?? 0)}
                      </td>
                      <td className="border border-[var(--color-neutral-95)] px-4 py-4 text-right tabular-nums">
                        {(percentR[stage] ?? 0).toFixed(1)}
                      </td>
                    </React.Fragment>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* ================= CHART ================= */}
        <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-4 sm:p-6 flex flex-col min-h-[360px]">
          <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
            Renewable energy usage by stage (%)
          </h3>
          
          <div className="flex-1 min-h-[260px]">
           {chartStages.length > 0 ? (
            <BarChart
              labels={chartStages}
              datasets={[
                {
                  label: "Non‑renewable",
                  values: chartStages.map((s) => percentNR[s] ?? 0),
                  color: "#E59D38",
                },
                {
                  label: "Renewable",
                  values: chartStages.map((s) => percentR[s] ?? 0),
                  color: "#646665",
                },
              ]}
              stacked={false}
              
                              
                  xAxis={{
                      min: 0,
                      max: 100,
                      tickFormatter: (v) => `${v}%`, 
                    }}

              legend={{
                show: true,
                position: "bottom",
                boxShape: "square",
              }}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-[var(--color-text-faint)]">
              No chart data available
            </div>
          )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RenewableEnergySummary;