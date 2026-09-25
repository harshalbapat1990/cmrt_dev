"use client";

import { Bar } from "react-chartjs-2";
import ChartContainer from "./ChartContainer";
import { ChartColors } from "@/styles/colors";
import type {
  AxisConfig,
  DatasetConfig,
  LegendConfig,
} from "../../types/charts";

/* =========================================================
   SMART AXIS SCALING (BUSINESS FRIENDLY)
========================================================= */
const getSmartAxisScale = (maxValue: number) => {
  if (maxValue <= 0) {
    return { min: 0, max: 10, stepSize: 2 };
  }

  const targetTicks = 5;

  // Raw step
  const rawStep = maxValue / targetTicks;

  // "Nice" step candidates
  const niceSteps = [1, 2, 5, 10];
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));

  let stepSize = niceSteps.find(
    step => rawStep <= step * magnitude
  )! * magnitude;

  // Compute axis max from step
  const max = Math.ceil(maxValue / stepSize) * stepSize;

  return {
    min: 0,
    max,
    stepSize,
  };
};
/* ========================================================= */

interface BarChartProps {
  title?: string;
  labels: string[];
  datasets?: DatasetConfig[];
  orientation?: "vertical" | "horizontal";
  stacked?: boolean;
  width?: string | number;

  xAxis?: AxisConfig & {
    valuesForScaling?: number[];
  };

  yAxis?: AxisConfig;

  legend?: LegendConfig;

  tooltipFormatter?: (ctx: any) => string[] | string;
}

const BarChart = ({
  title,
  labels,
  datasets = [],
  orientation = "vertical",
  stacked = false,
  width = "100%",
  xAxis = {},
  yAxis = {},
  legend = {},
  tooltipFormatter,
}: BarChartProps) => {

  /* =========================================================
     SCALE VALUES
  ========================================================= */
  const scaleValues =
    xAxis.valuesForScaling ??
    datasets.reduce<number[]>((acc, d) => {
      if (Array.isArray(d.values)) {
        acc.push(...d.values);
      }
      return acc;
    }, []);

  const maxValue = scaleValues.length
    ? Math.max(...scaleValues)
    : 0;

  const axis = getSmartAxisScale(maxValue);

  /* =========================================================
     DYNAMIC AXIS CONFIG
  ========================================================= */
  const valueAxis =
    orientation === "horizontal" ? "x" : "y";

  const categoryAxis =
    orientation === "horizontal" ? "y" : "x";

  return (
    <ChartContainer title={title} height={420} width={width}>
      <Bar
        data={{
          labels,

          datasets: datasets.map((d) => ({
            label: d.label,
            data: d.values,
            backgroundColor: d.color,

            barThickness: "flex",
            categoryPercentage: 0.75,
            barPercentage: 0.95,
            borderRadius:0,
          })),
        }}
       options={{
          responsive: true,
          maintainAspectRatio: false,

          indexAxis:
            orientation === "horizontal"
              ? "y"
              : "x",

          layout: {
            padding: {
              top: 10,
              right: 10,
              left: 10,
              bottom: 0,
            },
          },

        plugins: {
          legend: {
            display:
              legend.show ?? datasets.length > 1,

            position:
              legend.position ?? "bottom",

            labels: {
              boxWidth: 14,
              boxHeight: 14,
              padding: 24,
              color: ChartColors.textMuted,
              font: {
                size: 13,
                weight: 400,
              },
            },
          },

          tooltip: {
            callbacks: {
              label: (ctx) =>
                tooltipFormatter
                  ? tooltipFormatter(ctx)
                  : `${ctx.dataset.label}: ${
                      orientation === "horizontal"
                        ? ctx.parsed.x
                        : ctx.parsed.y
                    }`,
            },
          },
        },

        scales: {
          /* =====================================================
            VALUE AXIS
          ===================================================== */
          [valueAxis]: {
            type: "linear",

            stacked,

            min: axis.min,
            max: axis.max,

            position:
              orientation === "horizontal"
                ? "top"
                : "left",

           ticks: {
  stepSize: axis.stepSize,
  precision: 0,
  color: ChartColors.axisLabel,
  font: {
    size: 12,
    weight: 400,
  },
  callback: (v: any) =>
    xAxis.tickFormatter
      ? xAxis.tickFormatter(Number(v))
      : Number(v).toLocaleString(),
},

            grid: {
              display: true,

              color: "rgba(0,0,0,0.10)",
              tickBorderDash: [2,4],
              // borderDash: [2, 4],

              lineWidth: 1,

              // drawBorder: false,

              drawTicks: false,
            },

            border: {
              display: false,
              dash:[2,4],

            },

            title: {
              display: !!xAxis.title,

              text: xAxis.title,

              color: ChartColors.axisLabel,

              font: {
                size: 13,
                weight: 400,
              },
            },
          },

          /* =====================================================
            CATEGORY AXIS
          ===================================================== */
          [categoryAxis]: {
            stacked,

            ticks: {
              color: ChartColors.axisLabelDark,

              padding: 10,

              font: {
                size: 13,
                weight: 400,
              },
            },

            grid: {
              display: true,

              color: "rgba(0,0,0,0.08)",

              //borderDash: [2, 4],
              tickBorderDash: [2,4],
              lineWidth: 1,

              //drawBorder: false,

              drawTicks: false,
            },

            border: {
              display: true,
              color: ChartColors.axisBorder,      
              dash: [2,4],
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

export default BarChart;