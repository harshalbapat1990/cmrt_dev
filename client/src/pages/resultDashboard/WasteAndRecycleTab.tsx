
import DoughnutChart from "../../components/charts/DoughnutChart";
import ResultsDashboardService from "../../services/ResultsDashboard.service";
import { useEffect, useState } from "react";
import { formatDisplayNumber } from "@/utils/utils";

/* ================= TYPES ================= */

interface WasteAndRecycleTabProps {
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

/* ================= COMPONENT ================= */

const WasteAndRecycleTab = ({
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
}: WasteAndRecycleTabProps) => {

  const [materialData, setMaterialData] = useState<any>(null);
  const [wasteData, setWasteData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let ignore = false;

    const loadData = async () => {
      try {
        setLoading(true);
        setMaterialData(null);
        setWasteData(null);

        if (mode === "org") {
          if (!orgId) return;

          const normalizedProgramName =
            programName === "__NONE__" ? "" : programName ?? "";
          const [materialRes, wasteRes] = await Promise.all([
            ResultsDashboardService.orgMaterialsSummary(orgId, projectCategory ?? "", normalizedProgramName, projectTypecast ?? "", submissionLabel ?? ""),
            ResultsDashboardService.orgWasteSummary(orgId, projectCategory ?? "", normalizedProgramName, projectTypecast ?? "", submissionLabel ?? "")
          ]);

          if (!ignore) {
            setMaterialData(materialRes);
            setWasteData(wasteRes);
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
          const [materialRes, wasteRes] = await Promise.all([
            ResultsDashboardService.materialsSummary(projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId),
            ResultsDashboardService.wasteSummary(projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId)
          ]);
          if (!ignore) {
            setMaterialData(materialRes);
            setWasteData(wasteRes);
          }
        }
      } catch (e) {
        console.error("Failed to load materials and waste summary:", e);
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

  const materialTotals = materialData?.totals;

  const materialSegments = [
    {
      label: "Reused",
      value: Number(materialTotals?.reused_t) || 0,
    },
    {
      label: "Recycled",
      value: Number(materialTotals?.recycled_t) || 0,
    },
    {
      label: "Virgin material",
      value: Number(materialTotals?.virgin_t) || 0,
    },
  ];

  const hasMaterialData = materialSegments.some((s) => s.value > 0);

  const wasteSegments = wasteData?.waste_by_treatment ?? [];
  const wasteBreakdown = wasteData?.waste_table ?? [];
  const hasWasteData = wasteSegments.some((s: any) => s.quantity_t > 0);
  const hasBreakdownData = wasteBreakdown.length > 0;

  // No usable data
  if (!materialData && !hasWasteData && !hasBreakdownData) {
    return (
      <div className="px-4">
        <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-6 text-sm text-[var(--color-text-faint)]">
          No waste and recycling data available
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 space-y-6">
      <div className="mx-auto max-w-[1400px] space-y-6">

        {/* ================= TOP ROW ================= */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* ================= MATERIALS ================= */}
          <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-4 sm:p-6 flex flex-col min-h-[420px]">
            <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
              Materials use and composition
            </h3>

            <div className="flex flex-col md:flex-row items-center justify-between gap-6 flex-1 min-w-0">
              <div className="text-center sm:text-left">
                <div className="text-3xl font-semibold text-[var(--color-text-dark)]">
                  {formatDisplayNumber(materialData?.totals?.total_materials_t)}
                  <span className="ml-1">t</span>
                </div>
                <div className="text-sm text-[var(--color-text-faint)]">
                  Total materials
                </div>
              </div>

              <div className="w-full max-w-[320px] sm:max-w-[360px] mx-auto aspect-square">
                {hasMaterialData && (
                  <DoughnutChart
                    responsive
                    footerTitle="Reused material"
                    // footer={true}
                    labels={materialSegments.map((s) => s.label)}
                    values={materialSegments.map((s) => s.value)}
                    colors={["#E59D38", "#000000", "#646665"]}
                    legend={{ show: true, position: "bottom", boxShape: "square" }}
                    footer={false}
                    tooltipFormatter={(label, value, percent) =>
                      `${label}: ${formatDisplayNumber(value)} ${materialData?.materials_table?.unit ?? ""} (${formatDisplayNumber(percent)}%)`
                    }
                  />
                )}
              </div>
            </div>
          </div>

          {/* ================= WASTE ================= */}
          <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-4 sm:p-6 flex flex-col min-h-[420px]">
            <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
              Total waste and treatment type
            </h3>

            <div className="flex flex-col md:flex-row items-center justify-between gap-6 flex-1 min-w-0">
              <div className="text-center sm:text-left">
                <div className="text-3xl font-semibold text-[var(--color-text-dark)]">
                  {formatDisplayNumber(wasteData?.totals?.total_waste_t)}

                  <span className="ml-1">t</span>
                </div>
                <div className="text-sm text-[var(--color-text-faint)]">
                  {`${formatDisplayNumber(wasteData?.totals?.total_spoil_t)} (${formatDisplayNumber(
                    wasteData?.totals?.total_waste_excl_spoil_t
                  )} t ex. spoil)`}
                </div>
              </div>

              <div className="w-full max-w-[320px] sm:max-w-[360px] mx-auto aspect-square">
                {hasWasteData && (
                  <DoughnutChart
                    responsive
                    labels={wasteSegments.map((s: any) => s.name)}
                    values={wasteSegments.map((s: any) => s.quantity_t)}
                    colors={[
                      "#E59D38",
                      "#000000",
                      "#646665",
                      "#A7A7A7",
                      "#C8CCCD",
                    ]}
                    legend={{ show: true, position: "bottom", boxShape: "square" }}
                    footer={false}
                    tooltipFormatter={(label, value, percent) =>
                      `${label}: ${formatDisplayNumber(value)} t (${formatDisplayNumber(percent)}%)`
                    }
                  />
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ================= BREAKDOWN ================= */}
        {hasBreakdownData && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-[var(--radius-3)] border border-[var(--color-neutral-90)] bg-white p-4 sm:p-6">
              <h3 className="mb-4 text-xl font-light text-[var(--color-heading)]">
                Waste breakdown
              </h3>

              <div className="text-sm">
                <div className="flex justify-between border-b border-[var(--color-neutral-90)] pb-2 text-xs text-text-base font-medium">
                  <span>Waste Breakdown</span>
                  <span>Tonnes</span>
                </div>

                {wasteBreakdown.map((item: any, idx: any) => (
                  <div
                    key={idx}
                    className="flex justify-between border-b border-[var(--color-neutral-95)] py-3"
                  >
                    <span>{item.waste_type}</span>
                    <span className="tabular-nums">
                      {`${formatDisplayNumber(item.quantity_t)} t`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default WasteAndRecycleTab;
