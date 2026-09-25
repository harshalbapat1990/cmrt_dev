import React, { useState, useEffect } from "react";
import StackedBarChart from "../../components/charts/StackedBarChart";
import LineChart from "../../components/charts/LineChart";
import ResultsDashboardService from "../../services/ResultsDashboard.service";

/* ================= TYPES ================= */

// interface SubmissionEmissions {
//   label: string;
//   grades: Record<
//     "Grade 1" | "Grade 2" | "Grade 3" | "Grade 4",
//     number
//   >;
// }

// interface ConstructionPeriod {
//   period: string;
//   value: number;
// }

interface ComparisonProps {
  projectId: string;
  accountingMethod: string;
}

const toNumber = (value: unknown): number => {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
};

/* ================= COMPONENT ================= */

const ConstructionOperationsComparisonTab: React.FC<ComparisonProps> = ({
  projectId,
  accountingMethod
}) => {
  const [totalEmissionsBySubmission, setTotalEmissionsBySubmission] = useState<any>(null);
  const [totalEmissionsByConstructionPeriod, setTotalEmissionsByConstructionPeriod] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!projectId || !accountingMethod) {
      setTotalEmissionsBySubmission(null);
      setTotalEmissionsByConstructionPeriod(null);
      return;
    }
    let ignore = false;
    setTotalEmissionsBySubmission(null);
    setTotalEmissionsByConstructionPeriod(null);
    (async () => {
      try {
        setLoading(true);
        const [submissionData, periodData] = await Promise.all([
          ResultsDashboardService.comparisonByStageSummary(projectId, accountingMethod),
          ResultsDashboardService.comparisonByPeriodSummary(projectId, accountingMethod)
        ]);
        if (ignore) return;

        setTotalEmissionsBySubmission(submissionData);
        setTotalEmissionsByConstructionPeriod(periodData);

      } catch (e) {
        console.error("Failed to load comparison dashboard summary:", e);
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

  const submissions = Array.isArray(
    totalEmissionsBySubmission?.submissions
  )
    ? totalEmissionsBySubmission!.submissions
    : [];

  const periods = Array.isArray(
    totalEmissionsByConstructionPeriod?.periods
  )
    ? totalEmissionsByConstructionPeriod!.periods
    : [];

    const getGradeValue = (submission: any, gradeKey: string): number => {
  return toNumber(submission?.grades?.[gradeKey]);
};

  //  No usable data
  if (submissions.length === 0 && periods.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2">
        <h3 className="text-gray-500">No data</h3>
      </div>
    );
  }

  return (
    /*  CENTERED CONTENT */
    <div className="px-4 py-3">
      <div className="mx-auto max-w-[1280px] space-y-6">

        {/* ================= CARDS ROW ================= */}
        <div className="grid grid-cols-1 lg:grid-cols-[3fr_4fr] gap-6">

          {/* ===== LEFT CARD ===== */}
          <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 flex flex-col">
            <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
              Total emissions and data quality by submission
            </h3>

            <div className="flex-1 min-h-[360px]">
              {submissions.length > 0 ? (
                <StackedBarChart
                  labels={submissions.map((s: any) => s.label)}
                  datasets={[
                    {
                      label: "Grade 1",
                      values: submissions.map((s: any) =>
                        getGradeValue(s, "grade1")
                      ),
                      color: "#E88700",
                    },
                    {
                      label: "Grade 2",
                      values: submissions.map((s: any) =>
                        getGradeValue(s, "grade2")
                      ),
                      color: "#646665",
                    },
                    {
                      label: "Grade 3",
                      values: submissions.map((s: any) =>
                        getGradeValue(s, "grade3")
                      ),
                      color: "#A7A7A7",
                    },
                    {
                      label: "Grade 4",
                      values: submissions.map((s: any) =>
                        getGradeValue(s, "grade4")
                      ),
                      color: "#C8CCCD",
                    },
                  ]}
                  // scaleMode="stacked-40"
                  yAxis={{ title: `GHG emissions (${totalEmissionsBySubmission?.unit ?? "tCO₂e"})` }}
                  xAxis={{ grid: false }}
                  legend={{
                    show: true,
                    position: "bottom",
                    boxShape: "square",
                  }}
                />
              ) : (
                <div className="text-sm text-[var(--color-text-faint)]">
                  No submission data available
                </div>
              )}
            </div>
          </div>

          {/* ===== RIGHT CARD ===== */}
          <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 flex flex-col">
            <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
              Total emissions by construction period
            </h3>

            <div className="flex-1 min-h-[360px]">
              {periods.length > 0 ? (
                <LineChart
                  labels={periods.map((p: any) => p.period_label)}
                  values={periods.map((p: any) => toNumber(p.total_tco2e) || 0)}
                  yAxis={{
                    title: `GHG emissions (${totalEmissionsByConstructionPeriod?.unit ?? "tCO₂e"})`,
                  }}
                  xAxis={{ grid: false }}
                  legend={{ show: false }}
                />
              ) : (
                <div className="text-sm text-[var(--color-text-faint)]">
                  No construction period data available
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default ConstructionOperationsComparisonTab;