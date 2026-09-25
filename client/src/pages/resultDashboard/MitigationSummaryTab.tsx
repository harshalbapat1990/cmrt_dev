import React, {useState, useEffect} from "react";
import WaterfallChart from "../../components/charts/WaterfallChart";
import type { WaterfallItem } from "../../components/charts/WaterfallChart";
import ResultsDashboardService from "../../services/ResultsDashboard.service";

/* ================= TYPES ================= */

interface MitigationSummaryData {
  unit?: string;
  chart?: WaterfallItem[];
}

interface MitigationSummaryTabProps {
  // data?: MitigationSummaryData;
  projectId: string;
  stageInstanceId: string;
  accountingMethod: string;
  submissionLabel: string;
  projectOptionId?: string;
  submissionPeriodId?: string;  
}

/* ================= COMPONENT ================= */

const MitigationSummaryTab: React.FC<MitigationSummaryTabProps> = ({
  // data,
  projectId,
  stageInstanceId,
  accountingMethod,
  submissionLabel,
  projectOptionId,
  submissionPeriodId,
}) => {
  const [data, setData] = useState<MitigationSummaryData | null>(null);
    const [loading, setLoading] = useState(false);
  
    useEffect(() => {
      if (!projectId || !stageInstanceId || !submissionLabel || !accountingMethod ) return;
      if(["Business case", "Design"].includes(submissionLabel) && !projectOptionId) return;
      if(submissionLabel === "Construction" && !submissionPeriodId) return;
  
      let ignore = false;
  
      (async () => {
        try {
          setLoading(true);
  
          const res =await ResultsDashboardService.mitigationSummary( projectId,stageInstanceId,accountingMethod,submissionLabel, projectOptionId, submissionPeriodId);
          if (ignore) return;
  
         setData(res);
        } catch (e) {
          console.error("Failed to load mitigation summary:", e);
        } finally {
          setLoading(false);
        }
      })();
  
      return () => {
        ignore = true;
      };
    }, [accountingMethod, stageInstanceId, projectOptionId, submissionLabel, submissionPeriodId]);
  
    if (loading) {
      return (
        <div className="flex h-full items-center justify-center">
          Loading...
        </div>
      );
    }
  

  //  Safely normalise inputs
  const unit = data?.unit ?? "";
  const items: WaterfallItem[] = Array.isArray(data?.chart)
    ? data!.chart.map((i: any) => ({
        ...i,
        value: Number(i.value) || 0,
      }))
    : [];

  //  No usable data
  if (!items.length || !submissionLabel || !accountingMethod) {
    return (
       <div className="flex h-full flex-col items-center justify-center gap-2">
      <h3 className="text-gray-500">No data</h3>
     
    </div>
    );
  }

  /* ================= ORDER ITEMS ================= */

  //  Base case (initial absolute)
  const baseCase = items.find(
    (item) => item.type === "total" && item.value > 0
  );

  //  Mitigation deltas
  const deltas = items.filter(
    (item) => item.type === "step" && item.value !== 0
  );

  //  Final actual case (prefer explicit "actual")
  const actualCase =
    items.find(
      (item) =>
        item.type === "total" &&
        item !== baseCase &&
        item.label?.toLowerCase().includes("actual")
    ) ||
    items.find(
      (item) =>
        item.type === "total" && item !== baseCase
    );

  const orderedItems: WaterfallItem[] = [
    ...(baseCase ? [baseCase] : []),
    ...deltas,
    ...(actualCase ? [actualCase] : []),
  ];

  //  Still nothing to render safely
  if (orderedItems.length === 0) {
    return (
      <div className="rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-6 text-sm text-gray-500">
        No mitigation summary data available
      </div>
    );
  }

  /* ================= RENDER ================= */

  return (
    <div className="px-4">
      <div className="w-full rounded-[var(--radius-3)] border border-[#E8E8E8] bg-white p-6 flex flex-col">
        <h3 className="mb-4 text-xl font-light text-[#3F3A38]">
          GHG mitigation breakdown by source category
        </h3>

        <div className="flex-1">
          <WaterfallChart
            unit={unit}
            items={orderedItems}
          />
        </div>
      </div>
    </div>
  );
};

export default MitigationSummaryTab;