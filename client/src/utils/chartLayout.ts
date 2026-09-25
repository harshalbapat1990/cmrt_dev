/* ======================================================
   CHART AUTO‑LAYOUT ENGINE
   Single source of truth for ALL charts
   ====================================================== */

export type ChartOrientation = "horizontal" | "vertical";

/* ---------- BAR / LINE / STACKED ---------- */

export interface BarLikeLayoutInput {
  labels: string[];
  datasets: { values: number[] }[];
  orientation?: ChartOrientation;
  stacked?: boolean;
}

export const getBarLikeLayout = ({
  labels,
  datasets,
  orientation = "vertical",
  stacked = false,
}: BarLikeLayoutInput) => {
  // ✅ Correct max calculation for stacked charts
  const values = stacked
    ? labels.map((_, i) =>
        datasets.reduce(
          (sum, d) => sum + (d.values[i] ?? 0),
          0
        )
      )
    : datasets.flatMap((d) => d.values);

  const maxValue = Math.max(...values, 0);

  // ✅ Add headroom so bars never touch edge
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

  // ✅ Dynamic height (important for horizontal bars)
  const height =
    orientation === "horizontal"
      ? Math.min(Math.max(labels.length * 48, 260), 800)
      : 400;

  return {
    height,
    axis: {
      min: 0,
      max: niceMax,
      stepSize,
    },
  };
};

/* ---------- DOUGHNUT / PIE ---------- */

export interface DoughnutLayoutInput {
  values: number[];
}

export const getDoughnutLayout = ({ values }: DoughnutLayoutInput) => {
  const total = values.reduce((a, b) => a + b, 0);

  // ✅ Size adapts by data density
  const size =
    values.length <= 3
      ? 320
      : values.length <= 6
      ? 420
      : 520;

  const cutout =
    values.length <= 3 ? 60 :
    values.length <= 6 ? 55 :
    50;

  return {
    size,
    cutout,
    total,
  };
};
