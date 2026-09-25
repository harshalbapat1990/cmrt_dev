import React, {useState, useEffect} from "react";
import ResultsDashboardService from "@/services/ResultsDashboard.service";
import { formatDisplayNumber } from "@/utils/utils";

/* ================= CONSTANTS ================= */

const INFO_MESSAGE =
  "Credit levels shown are not guaranteed, projects will need to meet all the applicable IS criteria (and must statements) in the IS Technical Manual and guidelines to achieve the relevant IS credit(s)";

/* ================= TYPES ================= */

interface RatingPerformanceProps {
 projectId?: string;
  stageInstanceId?: string;
  projectOptionId?: string;
  accountingMethod?: string;
  submissionPeriodId?: string;
  submissionLabel?: string;
}

/* ================= HELPERS ================= */

const format = formatDisplayNumber;

/* ================= COMPONENT ================= */

const RatingPerformance: React.FC<RatingPerformanceProps> = ({  
  projectId,
  stageInstanceId,
  projectOptionId,
  accountingMethod,
  submissionPeriodId,
  submissionLabel, }) => {
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
                const res =await ResultsDashboardService.ratingScoresSummary( projectId,stageInstanceId,accountingMethod,submissionLabel, projectOptionId, submissionPeriodId);
                if (ignore) return;
        
               setData(res);
              } catch (e) {
                console.error("Failed to load Rating performance summary:", e);
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

  //  No usable data
  if (!data || !submissionLabel || !accountingMethod) {
    return (
      <div className="px-4">
        <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 text-sm text-[var(--color-text-faint)]">
          No rating performance data available
        </div>
      </div>
    );
  }
  return (
    <div className="px-4 space-y-6">
      <div className="mx-auto max-w-[1600px] space-y-6">

        {/* ================= INFO BANNER ================= */}
       <div className="rounded-[var(--radius-3)] border border-[var(--color-info-border)] bg-[var(--color-info-bg)] p-4 text-sm text-[var(--color-info-text)] flex items-start gap-2">
        <span className="material-symbols-rounded info-icon">
          info
        </span>
        {INFO_MESSAGE}
      </div>

        {/* ================= CREDIT CARDS ================= */}
        {data && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* {credits.map((credit: any) => ( */}
              <div
                // key={credit.code}
                className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6"
              >
                <div className="text-sm text-[var(--color-text-faint)]">
                  Ene-1
                </div>
                <div className="mt-2 text-3xl font-semibold tabular-nums text-[var(--color-text-dark)]">
                  {Number(data.ene1_score).toFixed(1)}
                </div>
              </div>
               <div
                // key={credit.code}
                className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6"
              >
                <div className="text-sm text-[var(--color-text-faint)]">
                  Ene-2
                </div>
                <div className="mt-2 text-3xl font-semibold tabular-nums text-[var(--color-text-dark)]">
                  {Number(data.ene2_score).toFixed(1)}
                </div>
              </div>
               <div
                // key={credit.code}
                className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6"
              >
                <div className="text-sm text-[var(--color-text-faint)]">
                  Ene-3
                </div>
                <div className="mt-2 text-3xl font-semibold tabular-nums text-[var(--color-text-dark)]">
                  {Number(data.ene3_score).toFixed(1)}
                </div>
              </div>
            {/* ))} */}
          </div>
        )}

        {/* ================= ENE‑1 REPORTING TABLE ================= */}
        {data.ene1_energy_gj && data.ene1_emissions_tco2e && (
          <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-4 sm:p-6">
            <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
              Ene-1 reporting
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] border-collapse text-sm">

                {/* HEADER */}
                <thead className="bg-[var(--color-neutral-98)] text-xs text-[var(--color-text-faint)]">
                  <tr>
                    <th rowSpan={2} className="border border-[var(--color-neutral-95)] px-4 py-3 text-left font-medium" />
                    <th colSpan={3} className="border border-[var(--color-neutral-95)] px-4 py-3 text-center font-medium">
                      Base Case
                    </th>
                    <th colSpan={3} className="border border-[var(--color-neutral-95)] px-4 py-3 text-center font-medium">
                      Actual Case
                    </th>
                  </tr>
                  <tr>
                    {[
                      "Construction",
                      "In-use / Operations",
                      "Lifecycle",
                      "Construction",
                      "In-use / Operations",
                      "Lifecycle",
                    ].map((label) => (
                      <th
                        key={label}
                        className="border border-[var(--color-neutral-95)] px-4 py-3 text-center font-medium whitespace-nowrap"
                      >
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>

                {/* BODY */}
                <tbody>
                  {/* Energy */}
                  <tr>
                    <td className="border border-[var(--color-neutral-95)] px-4 py-4 font-medium whitespace-nowrap">
                      Energy Use (GJ)
                    </td>
                    {[
                      data.ene1_energy_gj?.baseline_construction,
                      data.ene1_energy_gj?.baseline_inuse,
                      data.ene1_energy_gj?.baseline_lifecycle,
                      data.ene1_energy_gj?.actual_construction,
                      data.ene1_energy_gj?.actual_inuse,
                      data.ene1_energy_gj?.actual_lifecycle,
                    ].map((v, i) => (
                      <td key={i} className="border border-[var(--color-neutral-95)] px-4 py-4 text-right tabular-nums">
                        {format(v ?? 0)}
                      </td>
                    ))}
                  </tr>

                  {/* Emissions */}
                  <tr>
                    <td className="border border-[var(--color-neutral-95)] px-4 py-4 font-medium whitespace-nowrap">
                      Emissions (tCO₂e)
                    </td>
                    {[
                      data.ene1_emissions_tco2e?.baseline_construction,
                      data.ene1_emissions_tco2e?.baseline_inuse,
                      data.ene1_emissions_tco2e?.baseline_lifecycle,
                      data.ene1_emissions_tco2e?.actual_construction,
                      data.ene1_emissions_tco2e?.actual_inuse,
                      data.ene1_emissions_tco2e?.actual_lifecycle,
                    ].map((v, i) => (
                      <td key={i} className="border border-[var(--color-neutral-95)] px-4 py-4 text-right tabular-nums">
                        {format(v ?? 0)}
                      </td>
                    ))}
                  </tr>
                </tbody>

              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RatingPerformance;