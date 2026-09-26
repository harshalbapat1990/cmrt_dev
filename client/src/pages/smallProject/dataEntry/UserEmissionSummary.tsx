import { formatDisplayNumber } from "@/utils/utils";

type EmissionsSummaryState = {
  absoluteEmissions: number;
  baseCaseAbsoluteEmissions: number;
  relativeUserEmissions: number;
};

export const emptySummary: EmissionsSummaryState = {
  absoluteEmissions: 0,
  baseCaseAbsoluteEmissions: 0,
  relativeUserEmissions: 0,
};

const formatEmission = formatDisplayNumber;

export const UserEmissionsSummary = ({
  summary,
  loading,
}: {
  summary: EmissionsSummaryState;
  loading?: boolean;
}) => {
  const items = [
    {
      label: "Absolute emissions",
      value: summary.absoluteEmissions,
    },
    {
      label: "Base case absolute emissions",
      value: summary.baseCaseAbsoluteEmissions,
    },
    {
      label: "Relative user emissions (B8)",
      value: summary.relativeUserEmissions,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border-b border-neutral-90 pb-6 mb-6">
      {items.map((item, index) => (
        <div
          key={item.label}
          className={`px-6 first:pl-0 ${index > 0 ? "md:border-l md:border-neutral-90" : ""}`}
        >
          <div className="text-sm text-text-faint mb-1">{item.label}</div>
          <div className="text-[22px] font-bold text-text-dark leading-tight">
            {loading ? "..." : formatEmission(item.value)}{" "}
            {!loading && (
              <span className="font-light">
                tCO<sub>2</sub>e
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
