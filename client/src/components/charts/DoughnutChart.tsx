"use client";

import { Doughnut } from "react-chartjs-2";
import ChartContainer from "./ChartContainer";
import { getDoughnutLayout } from "../../utils/chartLayout";
import type { LegendConfig } from "../../types/charts";

/* ================= TYPES ================= */

interface DoughnutChartProps {
  title?: string;
  footerTitle?: string;
  labels: string[];
  values: number[];
  colors: string[];
  responsive?: boolean;
  size?: number;         // optional max size
  thickness?: number;
  legend?: LegendConfig & {
    boxShape?: "circle" | "square";
  };
  tooltipFormatter?: (
    label: string,
    value: number,
    percent: number
  ) => string;
  caption?: string;
  footer:boolean;
}

/* ================= CENTER VALUE PLUGIN ================= */

const centerValuePlugin = {
  id: "centerValue",
  afterDraw(chart: any) {
    const { ctx, chartArea } = chart;
    if (!chartArea) return;

    const centerValue = chart.options.plugins?.centerValue;
    if (!centerValue) return;

    const width = chartArea.right - chartArea.left;
    const cx = (chartArea.left + chartArea.right) / 2;
    const cy = (chartArea.top + chartArea.bottom) / 2;

    //  Scale font with chart width
    const fontSize = Math.max(14, Math.min(32, width * 0.12));

    ctx.save();
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
    ctx.fillStyle = "#4A4643";
    ctx.fillText(centerValue, cx, cy);
    ctx.restore();
  },
};

/* ================= COMPONENT ================= */

const DoughnutChart = ({
  title,
  footerTitle,
  labels,
  values,
  colors,
  responsive = true,
  size,
  thickness,
  legend = { show: true },
  tooltipFormatter,
  caption,
  footer = false,
  
}: DoughnutChartProps) => {
  const autoLayout = getDoughnutLayout({ values });

  const finalCutout = thickness ?? autoLayout.cutout;

  return (
    <ChartContainer
      title={title}
      footerTitle={footer? footerTitle : undefined}
      fullHeight
      fullWidth
      height={responsive ? undefined : size}
      width={responsive ? undefined : size}
    >
      <div className="flex flex-col items-center w-full">
        {/* ================= Donut ================= */}
        <div
          className="
            relative
            w-full
            aspect-square
          "
          style={
            size
              ? { maxWidth: size, maxHeight: size }
              : undefined
          }
        >
          <Doughnut
            data={{
              labels,
              datasets: [
                {
                  data: values,
                  backgroundColor: colors,
                  borderWidth: 0,
                },
              ],
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              cutout: `${finalCutout}%`,
              plugins: {
               
                legend: {
                  display: legend.show ?? false,
                  position: legend.position ?? "bottom",
                  labels: {
                    usePointStyle: legend.boxShape === "circle",
                    boxWidth: 12,
                    padding: 12,
                  },
                },
                tooltip: {
                  callbacks: {
                    label: (ctx) => {
                      const value = ctx.parsed as number;
                      const percent =
                        autoLayout.total > 0
                          ? (value / autoLayout.total) * 100
                          : 0;

                      return tooltipFormatter
                        ? tooltipFormatter(ctx.label!, value, percent)
                        : `${ctx.label}: ${value} (${percent.toFixed(1)}%)`;
                    },
                  },
                },
              },
            }}
            plugins={[centerValuePlugin]}
          />
        </div>

        {/* ================= Caption ================= */}
        {caption && (
          <div className="mt-3 text-sm text-[#6B6E6D] text-center max-w-[90%]">
            {caption}
          </div>
        )}
      </div>
    </ChartContainer>
  );
};

export default DoughnutChart;