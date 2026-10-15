import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import { formatEmissionsOrQuantity } from "@/utils/utils";

export function PeriodEmissionSummary({ period }: { period: ConstructionPeriod | null }) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white p-5 mb-6 mx-12 rounded-[var(--radius-3)] shadow-sm">
            <SummaryItem label="Total emissions reported" value={period?.all_periods_emissions_tco2e} />
            <SummaryItem label="Emissions this period" value={period?.period_emissions_tco2e} />
            <SummaryItem
                className="pb-6 md:border-x md:border-neutral-90 md:px-6"
                label="Emissions last period"
                value={period?.previous_period_emissions_tco2e}
            />
        </div>
    );
}

function SummaryItem({
    label,
    value,
    className = "pb-6",
}: {
    label: string;
    value?: string | number | null;
    className?: string;
}) {
    return (
        <div className={className}>
            <div className="text-sm text-text-faint mb-1">{label}</div>
            <div className="text-[28px] font-bold text-text-dark">
                {value != null ? formatEmissionsOrQuantity(parseFloat(String(value))) : "—"}{" "}
                <span className="text-[28px] font-light text-text-dark">tCO<sub>2</sub>e</span>
            </div>
        </div>
    );
}
