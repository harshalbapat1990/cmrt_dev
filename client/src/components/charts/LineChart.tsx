"use client";

import { Line } from "react-chartjs-2";
import ChartContainer from "./ChartContainer";
import { ChartColors } from "@/styles/colors";
import type { AxisConfig, LegendConfig } from "../../types/charts";

/* ================= HELPERS ================= */

const getNiceScale = (values: number[]) => {
  const max = Math.max(...values, 0);
  const paddedMax = max * 1.1;

  const niceMax =
    paddedMax <= 50
      ? 50
      : paddedMax <= 100
      ? 100
      : paddedMax <= 200
      ? 200
      : Math.ceil(paddedMax / 100) * 100;

  const stepSize =
    niceMax <= 50
      ? 10
      : niceMax <= 100
      ? 20
      : niceMax <= 200
      ? 40
      : niceMax / 5;

  return { min: 0, max: niceMax, stepSize };
};

const createGradient = (
  ctx: CanvasRenderingContext2D,
  area: { top: number; bottom: number },
  color: string
) => {
  const gradient = ctx.createLinearGradient(0, area.top, 0, area.bottom);
  gradient.addColorStop(0, `${color}55`);
  gradient.addColorStop(1, `${color}00`);
  return gradient;
};

/* ================= PROPS ================= */

interface LineChartProps {
  title?: string;
  labels: string[];
  values: number[];
  color?: string;
  height?: number;
  width?: string | number;
  xAxis?: AxisConfig;
  yAxis?: AxisConfig;
  legend?: LegendConfig;
}

/* ================= COMPONENT ================= */

const LineChart = ({
  title,
  labels,
  values,
  color = "#F2993A",
  height = 320,
  width = "100%",
  xAxis = {},
  yAxis = {},
  legend = {},
}: LineChartProps) => {
  const autoScale = getNiceScale(values);

  const pointSize =
    labels.length > 15 ? 2 : labels.length > 10 ? 3 : 4;

  return (
    <ChartContainer title={title} height={height} width={width}>
      <Line
        data={{
          labels,
          datasets: [
            {
              data: values,
              borderColor: color,
              borderWidth: 2,
              tension: 0,

              /*  Gradient fill (Figma‑accurate) */
              backgroundColor: (ctx) => {
                const chart = ctx.chart;
                if (!chart.chartArea) return `${color}22`;
                return createGradient(
                  chart.ctx,
                  chart.chartArea,
                  color
                );
              },
              fill: true,

              /*  Points match Figma */
              pointRadius: pointSize,
              pointHoverRadius: pointSize + 1,
              pointBackgroundColor: ChartColors.pointBackground,
              pointBorderColor: color,
              pointBorderWidth: 2,
            },
          ],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: legend.show ?? false,
            },
          },
          scales: {
            x: {
            offset: labels.length===1, // Center single label
            grid: {
                display:  true,
                color: "rgba(0,0,0,0.10)",
                // borderDash:[2,4],
                tickBorderDash:[2,4],
                lineWidth:1,
                drawTicks:false,
              },
              border:{
                display:true,
                dash:[2,4]
              },
              ticks: {
                minRotation: 45,
                maxRotation: 45,
              },
              title: {
                display: !!xAxis.title,
                text: xAxis.title,
              },
            },
            y: {
              min: yAxis.min ?? autoScale.min,
              max: yAxis.max ?? autoScale.max,
              ticks: {
                stepSize: yAxis.stepSize ?? autoScale.stepSize,
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

export default LineChart;