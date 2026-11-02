import React, {useState, useEffect} from "react";
import ResultsDashboardService from "@/services/ResultsDashboard.service";
import { formatDisplayNumber } from "@/utils/utils";

/* ================= TYPES ================= */

interface LcaModuleBreakdownTabProps {
  typeOfProject?: string;
   projectId?: string;
  stageInstanceId?: string;
  projectOptionId?: string;
  accountingMethod?: string;
  submissionPeriodId?: string;
  submissionLabel?: string;
}

/* ================= HELPERS ================= */

const isTotalRow = (label: string) =>
  label?.includes("total");

/* ================= COMPONENT ================= */

const LcaModuleBreakdownTab: React.FC<LcaModuleBreakdownTabProps> = ({
  typeOfProject,
    projectId,
  stageInstanceId,
  projectOptionId,
  accountingMethod,
  submissionPeriodId,
  submissionLabel,
}) => {

  const [data, setData] = useState<any | null>(null);
      const [loading, setLoading] = useState(false);
    
      useEffect(() => {
        if (!projectId || !stageInstanceId || !submissionLabel || !accountingMethod ) return;
        if(["Business case", "Design"].includes(submissionLabel) && !projectOptionId) return;
        if(submissionLabel === "Construction" && !submissionPeriodId) return;
        let ignore = false;
    
        (async () => {
          try {
            setLoading(true);
            const res =await ResultsDashboardService.itmmReportingSummary( projectId,stageInstanceId,accountingMethod,submissionLabel, projectOptionId, submissionPeriodId);
            if (ignore) return;
    
           setData(res);
          } catch (e) {
            console.error("Failed to load ITMM rating summary:", e);
          } finally {
            setLoading(false);
          }
        })();
    
        return () => {
          ignore = true;
        };
      }, [projectId, accountingMethod, stageInstanceId, projectOptionId, submissionLabel, submissionPeriodId]);
    
      if (loading) {
        return (
          <div className="flex h-full items-center justify-center">
            Loading...
          </div>
        );
      }
    
  
  const rows = Array.isArray(data?.rows) ? data!.rows : [];

  
  const isSmallProject = typeOfProject === "small";

  if (rows.length === 0 || !submissionLabel || !accountingMethod) {
    return (
      <div className="px-4">
        <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 text-sm text-[var(--color-text-faint)]">
          No LCA module breakdown data available
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 space-y-6">
      <h2 className="text-xl font-light text-[var(--color-heading)]">
        LCA module breakdown
      </h2>

      <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 overflow-x-auto">
        <table className="w-full border-collapse text-sm">

          {/* ================= HEADER ================= */}
          <thead className="border-b border-[var(--color-neutral-90)] text-xs text-[var(--color-text-faint)]">
            <tr>
              <th className="py-3 pr-4 text-left font-medium">
                Lifecycle module
              </th>

              {!isSmallProject && (
                <>
                  <th className="py-3 pr-4 text-right font-medium">
                    Baseline - absolute (tCO₂e)
                  </th>
                  <th className="py-3 pr-4 text-right font-medium">
                    Baseline - per declared unit (tCO₂e)
                  </th>
                </>
              )}

              <th className="py-3 pr-4 text-right font-medium">
               Actual (as built): difference compared to baseline (tCO₂e/unit)
              </th>
              <th className="py-3 pr-4 text-right font-medium">
                Actual (as built): per declared unit difference compared to baseline (tCO₂e/unit)
              </th>

              {!isSmallProject && (
                <>
                  <th className="py-3 pr-4 text-right font-medium">
                    Reduction % change on Absolute (tCO₂e)
                  </th>
                  <th className="py-3 text-right font-medium">
                    Reduction % change on per declared unit (tCO₂e/unit)
                  </th>
                </>
              )}
            </tr>
          </thead>

          {/* ================= BODY ================= */}
          <tbody>
            {rows.map((row: any, idx: any) => {
              const total = isTotalRow(row.module);

              return (
                <tr
                  key={idx}
                  className={`border-b border-[var(--color-neutral-95)] last:border-b-0 ${
                    total
                      ? "bg-[var(--color-neutral-98)] font-semibold"
                      : ""
                  }`}
                >
                  <td className="py-4 pr-4 text-[var(--color-text-table-cell)]">
                    {row.module_label}
                  </td>

                  {!isSmallProject && (
                    <>
                      <td className="py-4 pr-4 text-right tabular-nums">
                        {formatDisplayNumber(row.baseline_absolute ?? 0)}
                      </td>

                      <td className="py-4 pr-4 text-right tabular-nums">
                        {formatDisplayNumber(row.baseline_per_unit ?? 0)}
                      </td>
                    </>
                  )}

                  <td className="py-4 pr-4 text-right tabular-nums">
                    {formatDisplayNumber(row.actual_absolute ?? 0)}
                  </td>

                  <td className="py-4 pr-4 text-right tabular-nums">
                    {formatDisplayNumber(row.actual_per_unit ?? 0)}
                  </td>

                  {!isSmallProject && (
                    <>
                      <td className="py-4 pr-4 text-right tabular-nums">
                        {formatDisplayNumber(
                          row.reduction_pct_absolute ?? 0
                        )}
                        %
                      </td>

                      <td className="py-4 text-right tabular-nums">
                        {formatDisplayNumber(
                          row.reduction_pct_per_unit ?? 0
                        )}
                        %
                      </td>
                    </>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LcaModuleBreakdownTab;