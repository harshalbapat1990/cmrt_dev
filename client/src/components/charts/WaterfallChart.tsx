"use client";

import { Bar } from "react-chartjs-2";
import ChartContainer from "@/components/charts/ChartContainer";
import { Chart as ChartJS } from "chart.js";
import { ChartColors } from "@/styles/colors";
import { formatDisplayNumber } from "@/utils/utils";

export interface WaterfallItem {
  label: string;
  value: number;
  type: "total" | "step";
}

interface WaterfallChartProps {
  title?: string;
  unit: string;
  items: WaterfallItem[];
  height?: number;
}

/* =========================
   ✅ Inline value-label plugin
   (NO external dependency)
========================= */
const valueLabelPlugin = {
  id: "valueLabelPlugin",
  afterDatasetsDraw(chart: ChartJS) {
    const { ctx } = chart;

    ctx.save();
    ctx.fillStyle = ChartColors.valueLabelText;
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";

    chart.getDatasetMeta(0).data.forEach((bar: any, index: number) => {
      const raw = chart.data.datasets[0].data[index] as number[];
      if (!Array.isArray(raw)) return;

      const value = raw[1] - raw[0];
      const { x, y } = bar.tooltipPosition();

      ctx.fillText(
        formatDisplayNumber(value),
        x,
        y - 6
      );
    });

    ctx.restore();
  },
};

const WaterfallChart = ({
  title,
  unit,
  items,
  height = 520,
}: WaterfallChartProps) => {
  let runningTotal = 0;

  const data = items.map((item) => {
    if (item.type === "total") {
      runningTotal = item.value;
      return [0, item.value];
    }

    const start = runningTotal;
    const end = runningTotal + item.value;
    runningTotal = end;
    return [start, end];
  });

  const colors = items.map((i) =>
    i.type === "total" ? ChartColors.totalBar : ChartColors.stepBar
  );

  return (
    <ChartContainer title={title} height={height}>
      <Bar
        data={{
          labels: items.map((i) => i.label),
          datasets: [
            {
              data,
              backgroundColor: colors,
              borderRadius: 2,
              barPercentage: 0.7,
            },
          ],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const raw = ctx.raw as number[];
                  const diff = raw[1] - raw[0];
                  return `${formatDisplayNumber(diff)} ${unit}`;
                },
              },
            },
          },
          scales: {
            x: {
              grid: {
                display: true,
                color: "rgba(0,0,0,0.10)",
                //borderDash: [2,4],
                tickBorderDash: [2,4],
                lineWidth:1,
                drawTicks:false,
              },
              border:{
                display:true,
                dash: [2,4],
              }
            },
            y: {

              grid:{
                 display: true,
                color: "rgba(0,0,0,0.10)",
                //borderDash: [2,4],
                tickBorderDash: [2,4],
                lineWidth:1,
                drawTicks:false,

              },
              border:{
                 display:true,
                dash: [2,4],

              },
              title: {
                display: true,
                text: unit,
              },
              ticks: {
                callback: (v) =>
                  formatDisplayNumber(Number(v)),
              },
            },
          },
        }}
        plugins={[valueLabelPlugin]}
      />
    </ChartContainer>
  );
};

export default WaterfallChart;
