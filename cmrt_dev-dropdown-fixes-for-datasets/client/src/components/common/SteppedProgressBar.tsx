
import React from "react";

type SteppedProgressBarProps = {
  steps: string[];
  currentStep: number; // 1-based index
  className?: string;
};

const getStepIcon = (stepIndex: number, currentStep: number) => {
  if (stepIndex < currentStep - 1) return "check_circle";
  if (stepIndex === currentStep - 1) return "radio_button_partial";
  return "radio_button_unchecked";
};

const getIconClasses = (stepIndex: number, currentStep: number) => {
  if (stepIndex === currentStep - 1) return "text-[var(--color-primary)]";
  if (stepIndex < currentStep - 1) return "text-[var(--color-border-neutral)]";
  return "text-[var(--color-text-faint)]";
};

const getFontClasses = (stepIndex: number, currentStep: number) => {
  if (stepIndex === currentStep - 1) return "text-[var(--color-primary)] font-medium";
  if (stepIndex < currentStep - 1) return "text-[var(--color-border-neutral)] font-medium";
  return "text-[var(--color-text-faint)] font-medium";
};

const SteppedProgressBar: React.FC<SteppedProgressBarProps> = ({
  steps,
  currentStep,
  className = "",
}) => {
  const progressPercent = steps.length > 1 ? (currentStep / steps.length) * 100 : 0;

  return (
    <div className={`w-full ${className}`}>
      {/* Progress bar */}
      <div className="relative w-full h-2 mb-[12px] rounded bg-[var(--color-neutral-90)]">
        <div
          className="absolute top-0 left-0 h-2 rounded bg-[var(--color-primary)] transition-[width] duration-300"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Step icons and labels */}
      <div className="flex justify-between w-full">
        {steps.map((label, idx) => {
          const words = label.split(" ");
          const formattedLabel =
            words.length === 3 ? `${words.slice(0, 2).join(" ")}\n${words[2]}` : label;

          return (
            <div key={label} className="flex flex-row items-start gap-2 flex-1 min-w-0">
              <span
                className={[
                  "material-symbols-rounded",
                  "text-[24px]",
                  "-translate-y-[2px]",
                  getIconClasses(idx, currentStep),
                ].join(" ")}
              >
                {getStepIcon(idx, currentStep)}
              </span>

              <span
                className={[
                  "text-sm",
                  "text-left",
                  "break-words",
                  "whitespace-pre-line",
                  "-translate-y-[2.5px]",
                  getFontClasses(idx, currentStep),
                ].join(" ")}
              >
                {formattedLabel}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SteppedProgressBar;
