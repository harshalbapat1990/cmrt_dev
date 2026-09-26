"use client";

import { Bar } from "react-chartjs-2";
import ChartContainer from "./ChartContainer";
import type {
  AxisConfig,
  LegendConfig,
  RangeDatasetConfig,
} from "../../types/charts";
import { formatDisplayNumber } from "@/utils/utils";

interface RangeBarChartProps {
  title?: string;
  labels: string[];
  datasets: RangeDatasetConfig[];
  height?: number;
  yAxis?: AxisConfig;
  legend?: LegendConfig;
}

const RangeBarChart = ({
  title,
  labels,
  datasets,
  height = 380, // ✅ Figma-accurate plot height
  yAxis = {},
  legend = {},
}: RangeBarChartProps) => {
  return (
    <ChartContainer title={title} height={height}>
      <div className="h-full w-full">
        <Bar
          data={{
            labels,
            datasets: datasets.map((d) => ({
              label: d.label,
              data: d.ranges,
              backgroundColor: d.color,
              borderRadius: 2,
              borderSkipped: false,
              barThickness: 88,
              maxBarThickness: 100,
            })),
          }}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: legend.show ?? true,
                position: legend.position ?? "bottom",
                labels: {
                  usePointStyle: false, // ✅ square legend
                  boxWidth: 12,
                  boxHeight: 12,
                },
              },

              /* ✅ FULL TOOLTIP IMPLEMENTATION */
              tooltip: {
                displayColors: false, // ✅ cleaner tooltip
                callbacks: {
                  // ✅ Title = x-axis category label
                  title: (items) => {
                    if (!items.length) return "";
                    return items[0].label;
                  },

                  // ✅ Body = formatted range
                  label: (ctx) => {
                    const value = ctx.raw as [number, number];
                    if (!Array.isArray(value)) return "";

                    const [min, max] = value;
                    const unit = yAxis.title ? ` ${yAxis.title}` : "";

                    return `Range: ${formatDisplayNumber(min)} – ${formatDisplayNumber(max)}${unit}`;
                  },
                },
              },
            },
            scales: {
              x: {
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
                beginAtZero: true,
                title: {
                  display: !!yAxis.title,
                  text: yAxis.title,
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
              }
              },
            },
          }}
        />
      </div>
    </ChartContainer>
  );
};

export default RangeBarChart;
