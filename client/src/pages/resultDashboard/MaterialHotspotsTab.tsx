import React, { useState, useEffect } from "react";
import BarChart from "../../components/charts/BarChart";
import ResultsDashboardService from "../../services/ResultsDashboard.service";

/* =============== TYPES =============== */

interface MaterialHotspotItem {
  material: string;
  actual: number;
  mitigation: number;
}

interface MaterialHotspotsData {
  items?: MaterialHotspotItem[];
}

interface MaterialHotspotsTabProps {
  // data?: MaterialHotspotsData;
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

/* =============== COMPONENT =============== */

const MaterialHotspotsTab: React.FC<MaterialHotspotsTabProps> = ({ projectId,
  stageInstanceId, projectOptionId, submissionPeriodId, submissionLabel, orgId,
  mode,
  projectCategory,
  programName,
  projectTypecast, }) => {
  const [data, setData] = useState<MaterialHotspotsData | null>(null);
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
            await ResultsDashboardService.orgMaterialHotspotsSummary(
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

          const res = await ResultsDashboardService.materialHotspotsSummary(
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

  const rawItems =
    Array.isArray(data)
      ? data
      : Array.isArray((data as any)?.items)
        ? (data as any).items
        : Array.isArray((data as any)?.data?.items)
          ? (data as any).data.items
          : Array.isArray((data as any)?.rows)
            ? (data as any).rows
            : Array.isArray((data as any)?.data?.rows)
              ? (data as any).data.rows
              : [];


  const items: MaterialHotspotItem[] = rawItems.map((item: any) => ({
    material:
      item.material ??
      item.sub_category ??
      item.category ??
      item.name ??
      "Unknown",

    actual:
      Number(
        item.actual ??
        item.actual_tco2e ??
        item.emissions ??
        item.value ??
        0
      ),

    mitigation:
      Number(
        item.mitigation ??
        item.mitigation_tco2e ??
        item.mitigation_emissions ??
        0
      ),
  }));

  //  Sort by base emissions & filter invalid rows
  const sortedItems = items
    .map((i) => ({
      material: i.material ?? "Unknown",
      actual: Number(i.actual) || 0,
      mitigation: Number(i.mitigation) || 0,
    }))
    .filter((i) => i.actual > 0 || i.mitigation > 0)
    .sort(
      (a, b) =>
        b.actual + b.mitigation - (a.actual + a.mitigation)
    );

  // Handle no usable data
  if (sortedItems.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2">
        <h3 className="text-gray-500">No data</h3>

      </div>
    );
  }

  const labels = sortedItems.map((i) => i.material);
  const actualValues = sortedItems.map((i) => i.actual);
  const mitigationValues = sortedItems.map((i) => i.mitigation);
  const baseValues = sortedItems.map(
    (i) => i.actual + i.mitigation
  );

  return (
    <div
      className="grid gap-6 px-4 md:px-8"
      style={{ gridTemplateColumns: "1.5fr 2fr" }}
    >
      {/* ================= LEFT: TABLE ================= */}
      <div className="rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-6">
        <h3 className="mb-4 text-xl font-light text-[#3F3A38]">
          Emissions from materials
        </h3>

        {/* Header */}
        <div className="grid grid-cols-[1fr_auto] pb-2 text-xs text-text-base font-medium border-b border-[#E8E8E8]">
          <div>Material</div>
          <div className="text-right">Emissions (tCO₂e)</div>
        </div>

        {/* Rows */}
        <div className="divide-y divide-[#EFEFEF] text-sm">
          {sortedItems.map((row) => (
            <div
              key={row.material}
              className="grid grid-cols-[1fr_auto] py-4"
            >
              <div>{row.material}</div>
              <div className="text-right tabular-nums">
                {row.actual}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ================= RIGHT: CHART ================= */}
      <div className="rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-6">
        <h3 className="mb-4 text-xl font-light text-[#3F3A38]">
          Materials emissions by type
        </h3>

        {labels.length > 0 ? (
          <BarChart
            orientation="horizontal"
            stacked
            labels={labels}
            datasets={[
              {
                label: "Actual emissions",
                values: actualValues,
                color: "#E7A33E",
              },
              {
                label: "Mitigation",
                values: mitigationValues,
                color: "#616361",
              },
            ]}
            xAxis={{
              title: "tCO₂e",
              valuesForScaling: baseValues,
            }}
            tooltipFormatter={(ctx) => {
              const i = ctx.dataIndex;
              return [
                `Actual emissions: ${actualValues[i]} tCO₂e`,
                `Mitigation: ${mitigationValues[i]} tCO₂e`,
                `Base emissions: ${baseValues[i]} tCO₂e`,
              ];
            }}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2">
            <h3 className="text-gray-500">No data</h3>
          </div>
        )}
      </div>
    </div>
  );
};

export default MaterialHotspotsTab;