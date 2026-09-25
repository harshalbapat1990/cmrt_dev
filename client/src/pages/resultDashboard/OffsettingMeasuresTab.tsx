import React, {useState, useEffect} from "react";
import BarChart from "../../components/charts/BarChart";
import ResultsDashboardService from "../../services/ResultsDashboard.service";

/* ================= TYPES ================= */

interface OffsettingMeasuresTabProps {
  projectId: string;
  stageInstanceId: string;
  projectOptionId?: string;
  submissionPeriodId?: string;
  submissionLabel?: string;
}

/* ================= COMPONENT ================= */

const OffsettingMeasuresTab: React.FC<OffsettingMeasuresTabProps> = ({
  projectId,
  stageInstanceId,
  submissionLabel,
  projectOptionId,
  submissionPeriodId,
}) => {
  const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(false);
  
    useEffect(() => {
      if (!projectId || !stageInstanceId || !submissionLabel ) return;
      if(["Business case", "Design"].includes(submissionLabel) && !projectOptionId) return;
      if(submissionLabel === "Construction" && !submissionPeriodId) return;
  
      let ignore = false;
  
      (async () => {
        try {
          setLoading(true);
  
          const res =await ResultsDashboardService.offsettingSummary( projectId,stageInstanceId,submissionLabel, projectOptionId, submissionPeriodId);
          if (ignore) return;
  
          setData(res);

        } catch (e) {
          console.error("Failed to load offsetting summary:", e);
        } finally {
          setLoading(false);
        }
      })();
  
      return () => {
        ignore = true;
      };
    }, [stageInstanceId, projectOptionId, submissionLabel, submissionPeriodId]);
  
    if (loading) {
      return (
        <div className="flex h-full items-center justify-center">
          Loading...
        </div>
      );
    }

  const unit = data?.unit ?? "tCO₂e";

  const categories =
    Array.isArray(data?.offset_categories)
      ? data!.offset_categories.map((c: any) => ({
          label: c.name ?? "Unknown",
          value: Number(c.quantity) || 0,
        }))
      : [];

  const standards =
    Array.isArray(data?.offset_standards)
      ? data!.offset_standards.map((s: any) => ({
          label: s.name ?? "Unknown",
          value: Number(s.quantity) || 0,
        }))
      : [];

  const hasCategoryData = categories.some((c: any) => c.value > 0);
  const hasStandardData = standards.some((s: any) => s.value > 0);

  // ✅ No usable data at all
  if (!hasCategoryData && !hasStandardData || !submissionLabel) {
    return (
      <div className="px-4">
        <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 text-sm text-[var(--color-text-faint)]">
          No offsetting summary data available
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 space-y-6">
      <div className="mx-auto max-w-[1400px]">

        {/* ================= GRID ================= */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* ================= OFFSET CATEGORIES ================= */}
          <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-4 sm:p-6 flex flex-col min-h-[360px]">
            <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
              Offset categories purchased
            </h3>

            <div className="flex-1 min-h-[260px]">
              {hasCategoryData ? (
                <BarChart
                  orientation="horizontal"
                  labels={categories.map((c: any) => c.label)}
                  datasets={[
                    {
                      label: `Offsets (${unit})`,
                      values:categories.map((c: any) => c.value),
                      color: "#E59D38",
                    },
                  ]}
                  xAxis={{ title: `Offsets (${unit})` }}
                  yAxis={{ grid: false }}
                  legend={{ show: false }}
                />
              ) : (
                <div className="text-sm text-[var(--color-text-faint)]">
                  No offset category data available
                </div>
              )}
            </div>
          </div>

          {/* ================= OFFSET STANDARDS ================= */}
          <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-4 sm:p-6 flex flex-col min-h-[360px]">
            <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
              Offset standards purchased
            </h3>

            <div className="flex-1 min-h-[260px]">
              {hasStandardData ? (
                <BarChart
                  orientation="horizontal"
                  labels={standards.map((s: any) => s.label)}
                  datasets={[
                    {
                        label: `Offsets (${unit})`,
                    values: standards.map((s: any) => s.value),
                   
                      color: "#E59D38",
                    },
                  ]}
                  xAxis={{ title: `Offsets (${unit})` }}
                  yAxis={{ grid: false }}
                  legend={{ show: false }}
                />
              ) : (
                <div className="text-sm text-[var(--color-text-faint)]">
                  No offset standards data available
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default OffsettingMeasuresTab;