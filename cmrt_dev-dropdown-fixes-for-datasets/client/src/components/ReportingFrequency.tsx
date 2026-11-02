// components/ReportingFrequency.tsx
import { SelectListbox } from "./common/Select";
import { DatePicker } from "./common/DatePicker";
import type { YearMonth } from "./common/DatePicker";
import FieldError from "./common/FieldError";

const frequencyOptions = [
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "annually", label: "Annually" },
];

type Props = {
  frequency: string;
  setFrequency: (v: string) => void;
  period: YearMonth | null;
  setPeriod: (v: YearMonth | null) => void;
  frequencyError?: string | null;
  periodError?: string | null;
  disabled?: boolean;
};

export default function ReportingFrequency({
  frequency,
  setFrequency,
  period,
  setPeriod,
  frequencyError,
  periodError,
  disabled = false,
}: Props) {
  return (
    <div className="w-full max-w-full sm:max-w-160 lg:max-w-176 xl:max-w-240 rounded-[var(--radius-3)]">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4">
        <div className="w-full">
          <SelectListbox
            value={frequency}
            label="Reporting frequency"
            onChange={(v) => {
              setFrequency(v);
            }}
            options={frequencyOptions}
            placeholder=""
            className="mb-2"
            disabled={disabled}
          />
          {frequencyError && <FieldError message={frequencyError} />}
        </div>

        {/* First reporting period */}
        <div className="w-full">
          <label className="mb-2 block text-sm text-text-base">
            First reporting period
          </label>
          <DatePicker
            min={{ year: 1900, month: 1 }}
            value={period ?? undefined}
            onChange={setPeriod}
            disabled={disabled}
          />
          {periodError && <FieldError message={periodError} />}
        </div>
      </div>
    </div>
  );
}