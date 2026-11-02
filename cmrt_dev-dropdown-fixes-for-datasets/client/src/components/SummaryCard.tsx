import React, { useMemo } from "react";
import type { Project } from "../types/project";

interface Props {
  data: Project[];
}

const SummaryCard: React.FC<Props> = ({ data }) => {
 
  const summary = useMemo(() => {
    return {
      total: data.length,
      notStarted: data.filter((p) => p.status === "Not Started").length,
      inProgress: data.filter((p) => p.status === "In Progress").length,
      closed: data.filter((p) => p.status === "Closed").length,
    };
  }, [data]);

  return (
    <div className="w-59.75 bg-white rounded border border-[rgba(232,232,232,0.9)] shadow-[0_0_6px_0_rgba(19,19,19,0.04)] p-6 h-fit">
      <div className="text-sm uppercase text-text-base mb-1">Total Projects</div>
      <div className="text-2xl font-semibold text-[#3C3533] mb-4">{summary.total}</div>
      <div className="mb-4">
        <div className="h-px bg-gray-100"></div>
      </div>
      <div className="space-y-3 text-sm ">
        <div className="flex justify-between">
          <span className="text-text-base">Not started</span>
          <span className="text-[#3C3533]">{summary.notStarted}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-base">In progress</span>
          <span className="text-[#3C3533]">{summary.inProgress}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-base">Closed</span>
          <span className="text-[#3C3533]">{summary.closed}</span>
        </div>
      </div>
    </div>
  );
};

export default SummaryCard;