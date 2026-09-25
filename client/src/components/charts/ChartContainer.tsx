"use client";

import React from "react";

interface ChartContainerProps {
  title?: string;
  footerTitle?: string; 
  height?: number | string;    
  width?: number | string;
  fullHeight?: boolean;         
  fullWidth?: boolean;          
  children: React.ReactNode;
}


const ChartContainer = ({
  title,
  footerTitle,
  height = 300,
  width = "100%",
  fullHeight = false,
  fullWidth = false,
  children,
}: ChartContainerProps) => {
  return (
    <div
      className="rounded bg-white p-4 flex flex-col"
      style={{
        height: fullHeight ? "100%" : height,
        width: fullWidth ? "100%" : width,
      }}
    >
      {/* ================= HEADER ================= */}
      {title && (
        <h3 className="mb-3 font-medium text-center">
          {title}
        </h3>
      )}

      {/* ================= CONTENT ================= */}
      <div className="flex-1 relative min-h-0">
        {children}
      </div>

      {/* ================= FOOTER TITLE ================= */}
      {footerTitle && (
        <div className="mt-3 text-sm font-medium text-center text-[#3F3A38]">
          {footerTitle}
        </div>
      )}
    </div>
  );
};



export default ChartContainer;