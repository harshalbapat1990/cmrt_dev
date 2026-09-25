
import React from "react";
import InfoTooltip from "../common/InfoTooltip";

type CardOption = {
  label: string;
  description?: string;
  value: string;
  tooltip?: string;
};

type CardSelectorProps = {
  options: CardOption[];
  selected: string;
  onSelect: (value: string) => void;
  name?: string;
  className?: string;
};

const CardSelector: React.FC<CardSelectorProps> = ({
  options,
  selected,
  onSelect,
  name = "card-selector",
  className = "",
}) => {
  return (
    <div className={`mb-12 flex flex-col gap-4 ${className}`}>
      {options.map((opt) => {
        const isSelected = selected === opt.value;

        return (
          <label
            key={opt.value}
            className={[
              "group relative flex items-start gap-4 rounded-[var(--radius-3)] py-4.5 pl-4 pr-6 cursor-pointer",
              "transition-colors duration-200",
              isSelected
                ? "bg-primary-weak border-2 border-primary ring-0.5 ring-primary"
                : "bg-white border border-border hover:bg-neutral-90",
            ].join(" ")}
            onClick={() => onSelect(opt.value)}
          >
            {/* Left radio glyph */}
            <span
              className={[
                "material-symbols-rounded",
                "text-2xl mt-0.5 shrink-0",
                "text-border-neutral",
              ].join(" ")}
              aria-hidden="true"
            >
              {isSelected ? "radio_button_checked" : "radio_button_unchecked"}
            </span>

            {/* Text block */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <div
                  className={[
                    "font-bold text-sm",
                    "text-text-base",
                    "truncate min-w-0",
                  ].join(" ")}
                  title={opt.label}
                >
                  {opt.label}
                </div>

                {/* Tooltip with bolded terms where needed */}
                {opt.tooltip && (
                  <InfoTooltip
                    content={
                      opt.value === "large" ? (
                        <>
                          The allocation of a project as a <strong>"Large Project"</strong> is at the discretion
                          of your organisation and is subject to any internal policies and thresholds on the use
                          of large vs small project reporting pathways.
                        </>
                      ) : opt.value === "small" ? (
                        <>
                          The allocation of a project as a <strong>"Small Project"</strong> is at the discretion
                          of your organisation and is subject to any internal policies and thresholds on the use
                          of large vs small project reporting pathways.
                        </>
                      ) : (
                        <>{opt.tooltip}</>
                      )
                    }
                    
                  iconSize={14}
                  trigger="auto"
                  placement="top"
                  arrowOffset={24}
                  shiftX={90}
                  offset={10}         
                  

                  />
                )}
              </div>

              {opt.description && (
                <div className="mt-2 text-sm text-text-faint">
                  {opt.description}
                </div>
              )}
            </div>

            {/* Hidden radio input for semantics */}
            <input
              type="radio"
              name={name}
              value={opt.value}
              checked={isSelected}
              onChange={() => onSelect(opt.value)}
              className="sr-only"
            />
          </label>
        );
      })}
    </div>
  );
};

export default CardSelector;
