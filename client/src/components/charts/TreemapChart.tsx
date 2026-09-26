"use client";

import React, { useMemo, useState } from "react";
import { formatDisplayNumber } from "@/utils/utils";

/* ================= TYPES ================= */

export type TreemapNode = {
  category: string;
  value: number;
  color: string;
};

interface Rect extends TreemapNode {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface TreemapProps {
  data: TreemapNode[];
}

/* ================= UTILS ================= */

const sum = (arr: TreemapNode[]) =>
  arr.reduce((s, d) => s + d.value, 0);

/* ================= SIMPLE AREA LAYOUT ================= */

/**
 * Slice-and-dice treemap (clean + accurate)
 * Alternates horizontal & vertical splits
 */
const layoutCompact = (data: TreemapNode[]): Rect[] => {
  if (!data.length) return [];

  const sorted = [...data].sort((a, b) => b.value - a.value);
  const total = sum(sorted);

  const [largest, ...rest] = sorted;

  // ✅ LEFT BLOCK
  const leftWidth = (largest.value / total) * 100;

  const rects: Rect[] = [
    {
      ...largest,
      x: 0,
      y: 0,
      w: leftWidth,
      h: 100,
    },
  ];

  if (!rest.length) return rects;

  const rightX = leftWidth;
  const rightWidth = 100 - leftWidth;

  const restTotal = sum(rest);

  // ✅ FIXED ROW COUNT (IMPORTANT)
  const MAX_ROWS = 3;

  const rows: TreemapNode[][] = Array.from(
    { length: MAX_ROWS },
    () => []
  );

  // ✅ distribute items evenly across rows
  rest.forEach((item, index) => {
    rows[index % MAX_ROWS].push(item);
  });

  let currentY = 0;

  rows.forEach((row) => {
    if (!row.length) return;

    const rowSum = sum(row);
    const rowHeight = (rowSum / restTotal) * 100;

    let xOffset = rightX;

    row.forEach((item) => {
      const width = (item.value / rowSum) * rightWidth;

      rects.push({
        ...item,
        x: xOffset,
        y: currentY,
        w: width,
        h: rowHeight,
      });

      xOffset += width;
    });

    currentY += rowHeight;
  });

  return rects;
};


/* ================= COMPONENT ================= */

const TreemapChart: React.FC<TreemapProps> = ({ data }) => {
  const [hover, setHover] = useState<any>(null);

  const sorted = useMemo(
    () => [...data].sort((a, b) => b.value - a.value),
    [data]
  );

  const rects = layoutCompact(sorted);

  if (!data.length) return null;

  return (
    <>
      {/* TREEMAP */}
      <div className="relative w-full h-[550px]">
        {rects.map((r) => (
          <div
            key={r.category}
            onMouseMove={(e) =>
              setHover({
                ...r,
                x: e.clientX,
                y: e.clientY,
              })
            }
            onMouseLeave={() => setHover(null)}
            className="absolute overflow-hidden cursor-pointer"
            style={{
              left: `calc(${r.x}% + 4px)`,
              top: `calc(${r.y}% + 4px)`,
              width: `calc(${r.w}% - 8px)`,
              height: `calc(${r.h}% - 8px)`,
              backgroundColor: r.color,
            }}
          >
            {/* LABEL */}
            {r.w > 10 && (
              <div className="absolute top-2 left-3 right-3 text-white text-sm font-medium truncate">
                {r.category}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* TOOLTIP */}
      {hover && (
  <div
    className="
      fixed z-50
      rounded-md
      
      bg-[#393939]
      shadow-lg
      px-3 py-2
      text-sm
      pointer-events-none
      min-w-[140px]
    "
    style={{
      left: Math.min(hover.x + 12, window.innerWidth - 160),
      top: Math.min(hover.y + 12, window.innerHeight - 80),
    }}
  >
    {/* CATEGORY */}
   
<div className="flex items-center gap-2">
      <span
        className="h-3 w-3"
        style={{ backgroundColor: hover.color }}
      />
      <span className="text-white font-medium">
        {hover.category}
      </span>
    </div>


    {/* VALUE */}
    <div className="mt-1 text-white text-xs">
      Emissions:{" "}
      <span className="text-white font-medium">
        {formatDisplayNumber(hover.value)} tCO₂e
        
      </span>
    </div>
  </div>
)}


        {/* ================= LEGEND ================= */}
      <div className="mt-4 flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm">
        {data.map((d) => (
          <div key={d.category} className="flex items-center gap-2">
            <span
              className="h-3 w-3"
              style={{ backgroundColor: d.color }}
            />
            <span className="text-[#61605F]">{d.category}</span>
          </div>
        ))}
      </div>
    </>
  );
};

export default TreemapChart;
