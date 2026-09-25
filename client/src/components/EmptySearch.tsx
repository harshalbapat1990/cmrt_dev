import React from "react";

interface EmptyStateProps {
  title?: string;
  subtitle?: string;
  className?: string;
  iconName?: string; // material symbol name
}

const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No results found",
  subtitle = "Try adjusting your search or filters.",
  className,
  // iconName = "search_off",
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center rounded-[var(--radius-3)] bg-white p-10 min-h-[180px] ${className ?? ""}`}
      role="status"
      aria-live="polite"
    >
      <h3 className="text-gray-700 font-medium">{title}</h3>
      {subtitle && <p className="text-gray-500 text-sm mt-1 w-100">{subtitle}</p>}
    </div>
  );
};

export default EmptyState;
