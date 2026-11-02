import React, { type RefObject, useState, useMemo,useEffect } from "react";
import { DatePicker2 } from "./common/DatePicker2";
import { NumericInput } from "./common/NumericInput";
import FieldError from "./common/FieldError";
import { SelectListbox } from "./common/Select";

type CostAndScheduleProps = {
  startDateRef: RefObject<HTMLInputElement | null>;
  endDateRef: RefObject<HTMLInputElement | null>;
  commenceDateRef: RefObject<HTMLInputElement | null>;
  operationalLife?: string;
  setOperationalLife?: (v: string) => void;
  capex?: string;
  setCapex?: (v: string) => void;
  opex?: string;
  setOpex?: (v: string) => void;
  commenceDateValue?: Date | null;
  setCommenceDateValue?: (d: Date | null) => void;
  constructionStartDate?: Date | null;
  setConstructionStartDate?: (d: Date | null) => void;
  constructionEndDate?: Date | null;
  setConstructionEndDate?: (d: Date | null) => void;
  errors?: {
    commenceDate?: string | null;
    operationalLifeYears?: string | null;
    projectCapexM?: string | null;
  };
  onFieldValid?: (field: "commenceDate" | "operationalLifeYears" | "projectCapexM") => void;
  declaredUnitValue?: string;
  setDeclaredUnitValue?: (v: string) => void;
  declaredUnitType?: string;
  setDeclaredUnitType?: (v: string) => void;
  declaredUnitOptions?: string[];
};

// Simple dd/MM/yyyy formatter & parser
const formatDDMMYYYY = (d: Date) => {
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
};
const parseDDMMYYYY = (s: string) => {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(s.trim());
  if (!m) return null;
  const dd = Number(m[1]);
  const mm = Number(m[2]);
  const yyyy = Number(m[3]);
  const d = new Date(yyyy, mm - 1, dd);
  return d.getFullYear() === yyyy && d.getMonth() === mm - 1 && d.getDate() === dd ? d : null;
};

const atMidnight = (d: Date) => {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
};
const addDays = (d: Date, days: number) => {
  const x = new Date(d);
  x.setDate(x.getDate() + days);
  return x;
};
const isBefore = (a: Date, b: Date) => a.getTime() < b.getTime();


const toNumberOrNull = (val: string | number | null | undefined): number | null => {
  if (val === null || val === undefined) return null;
  if (typeof val === "number") return isNaN(val) ? null : val;
  const trimmed = String(val).trim();
  if (trimmed === "") return null;
  const num = Number(trimmed);
  return isNaN(num) ? null : num;
};

const CostAndSchedule: React.FC<CostAndScheduleProps> = ({
  startDateRef,
  endDateRef,
  commenceDateRef,
  operationalLife,
  setOperationalLife,
  capex,
  setCapex,
  opex,
  setOpex,
  errors,
  onFieldValid,
  commenceDateValue,
  setCommenceDateValue,
  constructionStartDate: _constructionStartDate,
  setConstructionStartDate,
  constructionEndDate: _constructionEndDate,
  setConstructionEndDate,
  declaredUnitValue,
  setDeclaredUnitValue,
  declaredUnitType,
  setDeclaredUnitType,
  declaredUnitOptions = [],
}) => {
  const commenceDate = commenceDateValue ?? null;
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    if (errors && Object.keys(errors).length > 0) {
      setExpanded(true);
    }
  }, [errors]);

  // Numeric states as numbers (null if empty)
  const operationalLifeYears = toNumberOrNull(operationalLife);
  const projectCapexM = toNumberOrNull(capex);
  const projectOpexMPerYear = toNumberOrNull(opex);


  const handleAccordion = () => setExpanded((v) => !v);

  // Today normalized to midnight
  const today = useMemo(() => atMidnight(new Date()), []);

  // --- Dynamic constraints:
  // Strict rule: start < end
  // So end.minDate = start + 1 day; start.maxDate = end - 1 day
  const startMaxDate = useMemo(() => (_constructionEndDate ? atMidnight(addDays(_constructionEndDate, -1)) : undefined), [_constructionEndDate]);
  const endMinDate = useMemo(() => (_constructionStartDate ? atMidnight(addDays(_constructionStartDate, +1)) : undefined), [_constructionStartDate]);

  // Commencement must be today or future
  const commenceMinDate = today;

  // --- Derived validation messages (for extra UX clarity)
  const startEndError =
    _constructionStartDate && _constructionEndDate && !isBefore(atMidnight(_constructionStartDate), atMidnight(_constructionEndDate))
      ? "Construction start must be earlier than construction end."
      : "";

  const commenceError =
    commenceDate && isBefore(atMidnight(commenceDate), today)
      ? "Commencement of operations cannot be in the past."
      : "";

  // Live validity flags (based on current values in this component)
  const isOperationalLifeValid =
    operationalLifeYears !== null && operationalLifeYears >= 0;
  const isCapexValid = projectCapexM !== null && projectCapexM >= 0;
  const isCommenceValid = !!commenceDate && !commenceError;

  // Only show error if parent has error AND current value is still invalid
  const showOperationalLifeError =
    !!errors?.operationalLifeYears && !isOperationalLifeValid;
  const showCapexError = !!errors?.projectCapexM && !isCapexValid;
  const showCommenceError = !!errors?.commenceDate && !isCommenceValid;


  // --- Completion rule (tweak as you like):
  // complete when all 3 dates + operational life + capex present; opex optional
  const isComplete =
    !!_constructionStartDate &&
    !!_constructionEndDate &&
    !!commenceDate &&
    !startEndError &&
    !commenceError &&
    operationalLifeYears !== null &&
    operationalLifeYears >= 0 &&
    projectCapexM !== null &&
    projectCapexM >= 0;

  // --- Icon selection (all in grey)
  const getStatusIcon = () => {
    if (isComplete) return "check_circle";
    if (expanded) return "radio_button_partial"; // fallback: "adjust" if not present in your icon set
    return "radio_button_unchecked";
  };

  return (
    <div className="border-t border-light-grey p-4">
      <div className="flex items-center justify-between gap-2">

        <button
          type="button"
          onClick={handleAccordion}
          className="w-full flex items-center justify-between gap-2 text-left cursor-pointer"
          aria-expanded={expanded}
          aria-controls="cost-schedule-panel"
          title={expanded ? "Collapse" : "Expand"}>
        <div className="flex items-center min-w-0 text-text-dark">
          <span
            className="material-symbols-rounded mr-2 shrink-0 text-lg text-gray-600"
            aria-hidden="true"
          >
            {getStatusIcon()}
          </span>
          <span className="truncate">Cost and schedule</span>
        </div>

  <span className="material-symbols-rounded shrink-0">
    {expanded ? "keyboard_arrow_up" : "keyboard_arrow_down"}
  </span>
</button>

      </div>

      {expanded && (
        <div id="cost-schedule-panel" className="space-y-4 pt-8">
          {/* Row 1 */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 mb-8">
            <div className="flex flex-col">
              <label className="mb-1 text-sm text-text-base">
                Construction start date (optional)
              </label>
              <div className="w-full">
                <DatePicker2
                  ref={startDateRef as any}
                  value={_constructionStartDate}
                  onChange={(d) => {
                    setConstructionStartDate?.(d);
                  }}
                  placeholder="dd/mm/yyyy"
                  formatFn={formatDDMMYYYY}
                  parseFn={parseDDMMYYYY}
                  firstDayOfWeek={0}
                  closeOnSelect
                  maxDate={startMaxDate}
                />
              </div>
            </div>

            <div className="flex flex-col">
              <label className="mb-1 text-sm text-text-base">
                Construction end date (optional)
              </label>
              <div className="w-full">
                <DatePicker2
                  ref={endDateRef as any}
                  value={_constructionEndDate}
                  onChange={(d) => {
                    setConstructionEndDate?.(d);
                  }}
                  placeholder="dd/mm/yyyy"
                  formatFn={formatDDMMYYYY}
                  parseFn={parseDDMMYYYY}
                  firstDayOfWeek={0}
                  closeOnSelect
                  minDate={endMinDate}
                />
              </div>
            </div>
          </div>

          {startEndError && (
            <p className="text-xs text-danger" role="alert" aria-live="polite">
              {startEndError}
            </p>
          )}


          {/* Row 2 */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 mb-8">
            <div className="flex flex-col">
              <label className="mb-1 text-sm text-text-base">Commencement of operations</label>
              <div className="w-full">
                <DatePicker2
                  ref={commenceDateRef as any}
                  value={commenceDate}
                  onChange={(d) => {
                    setCommenceDateValue?.(d);
                    if (d && !isBefore(atMidnight(d), today)) {
                      onFieldValid?.("commenceDate");
                    }
                  }}
                  placeholder="dd/mm/yyyy"
                  formatFn={formatDDMMYYYY}
                  parseFn={parseDDMMYYYY}
                  firstDayOfWeek={0}
                  closeOnSelect
                  minDate={commenceMinDate}
                />
                {showCommenceError && (
                  <FieldError message={errors!.commenceDate!} />
                )}
              </div>
              {commenceError && (
                <p className="mt-1 text-xs text-danger" role="alert" aria-live="polite">
                  {commenceError}
                </p>
              )}

            </div>

            <div className="flex flex-col">
              <NumericInput
                label="Operational life (years)"
                placeholder="Years"
                value={operationalLifeYears}
                onChange={(v) => {
                  const n = toNumberOrNull(v);
                  // update parent string state
                  setOperationalLife?.(n === null ? "" : String(n));
                  // clear error when valid
                  if (n !== null && n >= 0) onFieldValid?.("operationalLifeYears");
                }}
                allowDecimal={false}
                min={0}
                ariaLabel="Operational life in years"
                className={errors?.operationalLifeYears ? "border-danger" : ""}
              />
              {showOperationalLifeError && (
                <FieldError message={errors!.operationalLifeYears!} />
              )}
            </div>

          </div>

          {/* Row 3 */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 mb-8">
            <div className="flex flex-col">
              <NumericInput
                label="Project CAPEX"
                placeholder="$M"
                value={projectCapexM}
                onChange={(v) => {
                  const n = toNumberOrNull(v);
                  setCapex?.(n === null ? "" : String(n));
                  if (n !== null && n >= 0) onFieldValid?.("projectCapexM");
                }}
                allowDecimal
                min={0}
                prefix="$"
                ariaLabel="Project CAPEX in million dollars"
                className={errors?.projectCapexM ? "border-danger" : ""}
              />
              {showCapexError && <FieldError message={errors!.projectCapexM!} />}
            </div>

            <NumericInput
              label="Project OPEX (optional)"
              placeholder="$M/year"
              value={projectOpexMPerYear}
              onChange={(v) => {
                const n = toNumberOrNull(v);
                setOpex?.(n === null ? "" : String(n));
              }}
              allowDecimal
              min={0}
              prefix="$"
              ariaLabel="Project OPEX in million dollars per year"
            />
          </div>

          {/* Row 4 — Declared unit */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 mb-8">
            <div className="flex flex-col">
              <NumericInput
                label="Declared unit (quantity)"
                placeholder="Enter value"
                value={toNumberOrNull(declaredUnitValue)}
                onChange={(v) => {
                  const n = toNumberOrNull(v);
                  setDeclaredUnitValue?.(n === null ? "" : String(n));
                }}
                allowDecimal
                min={0}
                ariaLabel="Declared unit value"
              />
            </div>

            <div className="flex flex-col">
              <label className="mb-1 text-sm text-text-base">Declared unit type</label>
              <SelectListbox
                value={declaredUnitType ?? ""}
                onChange={(v) => setDeclaredUnitType?.(v)}
                options={declaredUnitOptions.map((opt) => ({ label: opt, value: opt }))}
                placeholder={declaredUnitOptions.length === 0 ? "Select a project typecast first" : "Select unit"}
                disabled={declaredUnitOptions.length === 0}
                noOptionsLabel="No units available for the selected typecast"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CostAndSchedule;