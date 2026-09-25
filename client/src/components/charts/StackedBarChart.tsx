"use client";

import { Bar } from "react-chartjs-2";
import ChartContainer from "./ChartContainer";
import type {
  AxisConfig,
  DatasetConfig,
  LegendConfig,
} from "../../types/charts";

/* ================= HELPERS ================= */

/**
 * Existing auto scaling (unchanged)
 */
const getAutoStackedScale = (
  labels: string[],
  datasets: DatasetConfig[]
) => {
  const totals = labels.map((_, i) =>
    datasets.reduce((sum, d) => sum + (d.values[i] ?? 0), 0)
  );

  const maxValue = Math.max(...totals, 0);

  return {
    min: 0,
    max: maxValue,
  };
};

/**
 *  NEW: dynamic 40‑based scaling
 */
const getStacked40Scale = (
  labels: string[],
  datasets: DatasetConfig[]
) => {
  const totals = labels.map((_, i) =>
    datasets.reduce((sum, d) => sum + (d.values[i] ?? 0), 0)
  );

  const maxValue = Math.max(...totals, 0);

  const BASE_STEP = 40;
  const TARGET_TICKS = 5;

  let stepSize = BASE_STEP;

  // Increase step if data grows
  if (maxValue > 200) {
    const roughStep = maxValue / TARGET_TICKS;
    stepSize =
      Math.ceil(roughStep / BASE_STEP) * BASE_STEP;
  }

  const niceMax =
    Math.ceil(maxValue / stepSize) * stepSize;

  return {
    min: 0,
    max: niceMax,
    stepSize,
  };
};

/* ================= PROPS ================= */

interface StackedBarChartProps {
  title?: string;
  labels: string[];
  datasets: DatasetConfig[];
  orientation?: "vertical" | "horizontal";
  height?: number;
  width?: string | number;
  xAxis?: AxisConfig;
  yAxis?: AxisConfig;
  legend?: LegendConfig;

  /**  Opt‑in scaling mode */
  scaleMode?: "auto" | "stacked-40";
}

/* ================= COMPONENT ================= */

const StackedBarChart = ({
  title,
  labels,
  datasets,
  orientation = "vertical",
  height = 400,
  width = "100%",
  // xAxis = {},
  yAxis = {},
  legend = {},
  scaleMode = "auto",
}: StackedBarChartProps) => {
  const scale =
    scaleMode === "stacked-40"
      ? getStacked40Scale(labels, datasets)
      : getAutoStackedScale(labels, datasets);

  return (
    <ChartContainer title={title} height={height} width={width}>
      <Bar
        data={{
          labels,
          datasets: datasets.map((d) => ({
            label: d.label,
            data: d.values,
            backgroundColor: d.color,
          })),
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: orientation === "horizontal" ? "y" : "x",
          plugins: {
           legend: {
            display: legend.show ?? true,
            position: legend.position ?? "bottom",
            labels: {
              usePointStyle: legend.boxShape === "circle",
              boxWidth: 12,
              boxHeight: 12,        //  force square height
            },
          },
          },
          scales: {
            x: {
              stacked: true,
              grid: {
                display:  true,
                color: "rgba(0,0,0,0.10)",
                //borderDash:[2,4],
                tickBorderDash:[2,4],
                lineWidth:1,
                drawTicks:false,
              },
              border:{
                display:true,
                dash:[2,4]
              }
            },
            y: {
              stacked: true,
              min: yAxis.min ?? scale.min,
              max: yAxis.max ?? scale.max,
              ticks: {
                stepSize:
                  yAxis.stepSize ??
                  (scale as any).stepSize,
              },
               grid: {
                display:  true,
                color: "rgba(0,0,0,0.10)",
                //borderDash:[2,4],
                tickBorderDash:[2,4],
                lineWidth:1,
                drawTicks:false,
              },
              border:{
                display:true,
                dash:[2,4]
              },
              title: {
                display: !!yAxis.title,
                text: yAxis.title,
              },
            },
          },
        }}
      />
    </ChartContainer>
  );
};

export default StackedBarChart;