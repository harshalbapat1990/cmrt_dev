interface DatasetInput {
  values: number[];
}

interface UseChartLayoutProps {
  labels: string[];
  datasets: DatasetInput[];
  orientation?: "horizontal" | "vertical";
  stacked?: boolean;
}

export const useChartLayout = ({
  labels,
  datasets,
  orientation = "vertical",
  stacked = false,
}: UseChartLayoutProps) => {
  // ✅ IMPORTANT: use stacked totals when stacked=true
  const computedValues = stacked
    ? labels.map((_, index) =>
        datasets.reduce(
          (sum, dataset) => sum + (dataset.values[index] ?? 0),
          0
        )
      )
    : datasets.flatMap((d) => d.values);

  const maxValue = Math.max(...computedValues, 0);

  // ✅ Add headroom so bars never touch the edge
  const paddedMax = maxValue * 1.1;

  const niceMax =
    paddedMax === 0 ? 10 : Math.ceil(paddedMax / 10) * 10;

  const stepSize =
    niceMax <= 50
      ? 5
      : niceMax <= 200
      ? 20
      : niceMax <= 500
      ? 50
      : niceMax <= 1000
      ? 100
      : Math.ceil(niceMax / 8);

  const height =
    orientation === "horizontal"
      ? Math.min(Math.max(labels.length * 48, 260), 800)
      : 400;

  return {
    height,
    xAxis: {
      min: 0,
      max: niceMax,
      stepSize,
    },
  };
};
