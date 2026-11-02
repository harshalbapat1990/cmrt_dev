// components/ReportingStage.tsx
import React, { useRef, useState, useEffect } from "react";
import InfoTooltip from "./common/InfoTooltip";
import checkCircleUrl from "../assets/icons/check_circle.svg";
import FieldError from "./common/FieldError";
import ReportingFrequency from "./ReportingFrequency";
import type { YearMonth } from "./common/DatePicker";
import type { StageValue} from "../types/addnewproject";

const stageLabels: Record<StageValue, string> = {
  business: "Business case",
  design: "Design",
  construction: "Construction",
};

const reportingStages: { label: string; value: StageValue }[] = [
  { label: stageLabels.business, value: "business" },
  { label: stageLabels.design, value: "design" },
  { label: stageLabels.construction, value: "construction" },
];

export type SubmissionMap = Record<StageValue, string>;

type ReportingStageProps = {
  selectedStage: StageValue | "";
  onSelectStage: (stage: StageValue) => void;
  submissions: SubmissionMap;
  onChangeSubmissions: (next: SubmissionMap) => void;
  stageError?: string | null;
  submissionsError?: string | null;
  rfFrequency?: string;
  onRfFrequencyChange?: (value: string) => void;
  rfPeriod?: YearMonth | null;
  onRfPeriodChange?: (value: YearMonth | null) => void;
  rfFrequencyError?: string | null;
  rfPeriodError?: string | null;
  readOnly?: boolean;
};

const submissionSetupTooltip = "This can't be edited later in the project once created.";

const ReportingStage: React.FC<ReportingStageProps> = ({
  selectedStage,
  onSelectStage,
  stageError,
  submissionsError,
  submissions,
  onChangeSubmissions,
  rfFrequency,
  onRfFrequencyChange,
  rfPeriod,
  onRfPeriodChange,
  rfFrequencyError,
  rfPeriodError,
  readOnly = false,
}) => {
  const [expanded, setExpanded] = useState<{
    business: boolean;
    design: boolean;
    construction: boolean;
  }>({
    business: false,
    design: false,
    construction: false,
  });

  
  //Which submissions are editable based on the selected reporting stage
const getVisibleStages = (): StageValue[] => {
  if (!selectedStage) return [];
  if (selectedStage === "business") return ["business", "design", "construction"];
  if (selectedStage === "design") return ["design", "construction"];
  if (selectedStage === "construction") return ["construction"];
  return [];
};

const visibleStages = getVisibleStages();
const isVisible = (stage: StageValue) => visibleStages.includes(stage);

  
// When selectedStage changes, collapse any expanded blocks that are no longer editable
  useEffect(() => {
    setExpanded((prev) => {
      const next = { ...prev };
      (Object.keys(next) as StageValue[]).forEach((st) => {
        if (!isVisible(st)) next[st] = false;
      });
      return next;
    });
  }, [selectedStage]);

  // refs to autofocus number inputs on expand
  const inputRefs: Record<StageValue, React.RefObject<HTMLInputElement | null>> =
    {
      business: useRef<HTMLInputElement | null>(null),
      design: useRef<HTMLInputElement | null>(null),
      construction: useRef<HTMLInputElement | null>(null),
    };

  useEffect(() => {
    if (readOnly) return;
    (Object.keys(expanded) as StageValue[]).forEach((stage) => {
      if (expanded[stage]) {
        inputRefs[stage].current?.focus();
      }
    });
 }, [expanded, readOnly]);

  // ===== Helpers =====
  const isStageCompleted = (stage: StageValue) => {
    if (stage === "construction") {
      return Boolean(rfFrequency && rfPeriod);
    }
    const n = Number(String(submissions[stage]).trim());
    return Number.isFinite(n) && n > 0;
  };

  const updateCount = (stage: StageValue, value: string) => {
    if (readOnly) return;
    onChangeSubmissions({ ...submissions, [stage]: value });
  };

  
  const TickIcon: React.FC<{ active: boolean; alt?: string }> = ({
    active,
    alt,
  }) => {
    if (!active) return null;
    return (
      <img
        src={checkCircleUrl}
        alt={alt ?? "Selected"}
        width={20}
        height={20}
        className="opacity-100"
      />
    );
  };

  // ===== Collapsed Row =====
  const CollapsedRow: React.FC<{
    stage: StageValue;
    tooltip?: string;
  }> = ({ stage, tooltip }) => {
    if (!isVisible(stage)) return null; 
    return (
      <div
        role="button"
        onClick={() => setExpanded((prev) => ({ ...prev, [stage]: true }))}
        className="
          w-full cursor-pointer rounded-[var(--radius-3)] border border-border bg-white
          p-4 text-text-base outline-none text-sm
          flex items-center gap-2
        "
      >
        <span className="inline-flex items-center gap-2">
          {stageLabels[stage]}
          {tooltip && (
            <InfoTooltip
              text={tooltip}
              iconSize={18}
              trigger="hover"
              placement="top"
              arrowOffset={20}
              offset={10}
            />
          )}
        </span>

        <span className="ml-auto" />
        <TickIcon active={isStageCompleted(stage)} />
      </div>
    );
  };

  
  type SubmissionCountInputProps = {
    id: string;
    value: string;
    onChange: (v: string) => void;
    placeholder?: string;
    inputRef?: React.RefObject<HTMLInputElement | null>;
    min?: number;
    autoFocus?: boolean;
    selectOnFocus?: boolean; // optional: select text when input receives focus
    ariaLabel?: string;
    className?: string;
    disabled?: boolean;
  };

  const SubmissionCountInput: React.FC<SubmissionCountInputProps> = ({
    id,
    value,
    onChange,
    placeholder,
    inputRef,
    min = 1,
    autoFocus = false,
    selectOnFocus = false,
    ariaLabel = "Number of submissions",
    className,
    disabled = false,
  }) => {
    return (
      <input
        id={id}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        autoFocus={autoFocus}
        aria-label={ariaLabel}
        placeholder={placeholder}
        ref={inputRef}
        value={value}
        disabled={disabled}
        onFocus={(e) => {
          if (disabled) return;
          if (selectOnFocus) {
            // Select the full value for quick overwrite
            requestAnimationFrame(() => e.currentTarget.select());
          }
        }}
        onChange={(e) => {
          if (disabled) return;
          // keep only digits; avoid spinners
          const next = e.target.value.replace(/[^\d]/g, "");
          // Let user type freely; we don't hard-block mid-typing
          onChange(next);
        }}
        onBlur={(e) => {
          if (disabled) return;
          // Enforce min on blur if value present
          const raw = e.target.value;
          if (raw === "") return;
          const n = Number(raw);
          if (!Number.isFinite(n) || (typeof min === "number" && n < min)) {
            onChange(String(min));
          }
        }}
        className={
          className ??
           `w-full rounded-[var(--radius-3)] border-2 border-border-input bg-white px-4 py-3 text-base text-text-base outline-none disabled:opacity-60 disabled:cursor-not-allowed disabled:bg-gray-50`
        }
      />
    );
  };

    // ===== Expanded Block =====
    const ExpandedStageBlock: React.FC<{
      stage: { label: string; value: StageValue };
      tooltip?: string;
      onCollapse?: () => void;
      inputRef?: React.RefObject<HTMLInputElement | null>;
    }> = ({ stage, tooltip, onCollapse, inputRef }) => {
      if (!isVisible(stage.value)) return null;
      const value = submissions[stage.value] ?? "";
      return (
        <div>
          {/* Header strip */}
          <div className="relative mb-3">
            <div
              aria-label={`${stage.label} (collapse)`}
              onClick={onCollapse}
              className="
                flex w-full cursor-pointer items-center gap-2 rounded-[var(--radius-3)]
                bg-white p-4 text-sm text--text-base outline-none
                border-primary border-2 ring-1 ring-primary
              "
            >
              <span className="inline-flex items-center gap-2">
                {stage.label}
                {tooltip && (
                  <InfoTooltip
                    text={tooltip}
                    iconSize={18}
                    trigger="hover"
                    placement="top"
                    arrowOffset={10}
                    offset={6}
                  />
                )}
              </span>
              <span className="ml-auto" />
              <TickIcon active={isStageCompleted(stage.value)} />
            </div>
          </div>

          {/* Content panel */}
          <div className="rounded-[var(--radius-3)] border border-dashed border-border bg-[#FAFAFA] p-4">
            <label
              htmlFor={`count-${stage.value}`}
              className="mb-2 block text-sm text-text-base"
            >
              Number of submissions
            </label>
            <SubmissionCountInput
              id={`count-${stage.value}`}
              value={value}
              onChange={(v) => updateCount(stage.value, v)}
              placeholder="Enter number of submissions"
              inputRef={inputRef}
              min={1}
              autoFocus={!readOnly}
              disabled={readOnly}
            />
          </div>
        </div>
      );
    };

  return (
    <div className="w-full">
      {readOnly && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-[var(--radius-3)] mb-4 text-sm text-blue-700">
          <strong>Note:</strong> Project Stages and corresponding submissions cannot be changed. They are shown here for reference only.
        </div>
      )}

      {/* Heading */}
      <div className="mb-6 text-2xl text-text-base">
        What stage is the project currently in?
      </div>

      {stageError && (
        <div className="mb-3">
          <FieldError message={stageError} />
        </div>
      )}

      {/* Stage selector */}
      <div className="mb-10 grid grid-cols-1 gap-4">
        {reportingStages.map((stage) => {
          const isSelected = selectedStage === stage.value;
          return (
            <label
              key={stage.value}
              className={`
                flex items-center rounded-[var(--radius-3)] px-4 text-text-base
                ${readOnly ? "cursor-default opacity-60" : "cursor-pointer"}
                ${isSelected
                  ? "border-2 border-primary bg-primary-weak ring-1 ring-primary"
                   : readOnly
                    ? "border border-border bg-gray-50"
                    : "border border-border bg-white"}
              `}
            >
              <span
                className="material-symbols-rounded w-5 h-5 mr-2.5 text-border-neutral"
                aria-hidden="true"
              >
                {isSelected ? "radio_button_checked" : "radio_button_unchecked"}
              </span>
              <input
                type="radio"
                name="reporting-stage"
                value={stage.value}
                checked={isSelected}
                disabled={readOnly}
                onChange={() => {
                  if (!readOnly) onSelectStage(stage.value);
                }}
                className="hidden"
              />
              <span className="text-sm py-5.25">{stage.label}</span>
            </label>
          );
        })}
      </div>

      {/* Reporting section — only show AFTER a stage is selected */}
      {selectedStage && (
        <div className="mb-12">
          <h2 className="mb-2 text-2xl text-text-base">
            Reporting submissions for this project
          </h2>
          <div className="mb-6 text-text-faint text-sm">
            {readOnly
              ? "Submissions are shown for reference only."
              : "Check applicable submissions and enter how many are expected at each stage."}
          </div>
          {submissionsError && <FieldError message={submissionsError} />}

          <div className="flex flex-col gap-4">
            {/* BUSINESS */}
            {isVisible("business") && (
              expanded.business ? (
              <ExpandedStageBlock
                stage={{ label: stageLabels.business, value: "business" }}
                onCollapse={() =>
                  setExpanded((s) => ({ ...s, business: false }))
                }
                inputRef={inputRefs.business}
              />
            ) : (
              <CollapsedRow
                stage="business"
              />
            ))}

            {/* DESIGN */}
            {isVisible("design") && (
              expanded.design ? (
              <ExpandedStageBlock
                stage={{ label: stageLabels.design, value: "design" }}
                tooltip={readOnly ? undefined : submissionSetupTooltip}
                onCollapse={() => setExpanded((s) => ({ ...s, design: false }))}
                inputRef={inputRefs.design}
              />
            ) : (
              <CollapsedRow
                stage="design"
                tooltip={readOnly ? undefined : submissionSetupTooltip}
              />
            ))}

            {/* CONSTRUCTION */}
            {isVisible("construction") && (
            expanded.construction ? (
              <div>
                {/* Header strip */}
                <div className="relative mb-4">
                  <div
                    aria-label={`${stageLabels.construction} (collapse)`}
                    onClick={() =>
                      setExpanded((s) => ({ ...s, construction: false }))
                    }
                    className="
                      flex w-full cursor-pointer items-center gap-2 rounded-[var(--radius-3)]
                      bg-white p-4 text-sm text-text-base outline-none
                      border-primary border-2 ring-1 ring-primary
                    "
                  >
                    <span className="inline-flex items-center gap-2">
                      {stageLabels.construction}
                      {!readOnly && (
                        <InfoTooltip
                          text={submissionSetupTooltip}
                          iconSize={18}
                          trigger="hover"
                          placement="top"
                          arrowOffset={10}
                          offset={6}
                        />
                      )}
                    </span>
                    <span className="ml-auto" />
                    <TickIcon active={isStageCompleted("construction")} />
                  </div>
                </div>

                {/* Content */}
                <div className="rounded-[var(--radius-3)] bg-white border border-border">
                  <ReportingFrequency
                    frequency={rfFrequency ?? ""}
                    setFrequency={onRfFrequencyChange ?? (() => {})}
                    period={rfPeriod ?? null}
                    setPeriod={(v) => onRfPeriodChange?.(v)}
                    frequencyError={rfFrequencyError}
                    periodError={rfPeriodError}
                    disabled={readOnly}
                  />
                </div>
              </div>
            ) : (
              <CollapsedRow
                stage="construction"
                 tooltip={readOnly ? undefined : submissionSetupTooltip}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportingStage;