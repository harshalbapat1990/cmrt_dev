interface ScopeBreakdownRow {
    scope: string;
    baseline_construction: number;
    baseline_operations: number;
    baseline_lifecycle: number;
    actual_construction: number;
    actual_operations: number;
    actual_lifecycle: number;
}

interface ScopeBreakdownData {
    rows: ScopeBreakdownRow[];
}

interface ScopeBreakdownTableProps {
    data: ScopeBreakdownData | null;
    loading: boolean;
    error: string | null;
}

function fmt(val: number | null | undefined): string {
    if (val == null) return "—";
    if (Math.abs(val) >= 1000) {
        return Math.round(val).toLocaleString("en-AU", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }
    const rounded = Math.round(val * 10) / 10;
    return rounded.toLocaleString("en-AU", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

const SCOPE_LABELS: Record<string, string> = {
    "1": "Scope 1",
    "2": "Scope 2",
    "3": "Scope 3",
    "upscaling": "Upscaling",
    "total": "Total",
};

export default function ScopeBreakdownTable({ data, loading, error }: ScopeBreakdownTableProps) {
    if (loading) {
        return (
            <div className="flex items-center justify-center h-full text-[#6C6C6C] text-sm">
                Loading…
            </div>
        );
    }

    if (error) {
        return (
            <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {error}
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                    <thead>
                        <tr className="bg-[#F5F5F5]">
                            <th
                                rowSpan={2}
                                className="px-4 py-2 text-left font-semibold text-[#3F3A38] border border-[#E8E8E8] align-bottom whitespace-nowrap"
                            >
                                GHG Scope
                            </th>
                            <th
                                colSpan={3}
                                className="px-4 py-2 text-center font-semibold text-[#3F3A38] border border-[#E8E8E8]"
                            >
                                Baseline
                            </th>
                            <th
                                colSpan={3}
                                className="px-4 py-2 text-center font-semibold text-[#3F3A38] border border-[#E8E8E8]"
                            >
                                Actual
                            </th>
                        </tr>
                        <tr className="bg-[#F5F5F5]">
                            {(["Construction", "Operations", "Lifecycle"] as const).map((col) => (
                                <th
                                    key={`bl-${col}`}
                                    className="px-4 py-2 text-right font-medium text-[#6C6C6C] border border-[#E8E8E8] whitespace-nowrap"
                                >
                                    <div>{col}</div>
                                    <div className="text-xs font-normal text-[#9C9C9C]">tCO₂e</div>
                                </th>
                            ))}
                            {(["Construction", "Operations", "Lifecycle"] as const).map((col) => (
                                <th
                                    key={`ac-${col}`}
                                    className="px-4 py-2 text-right font-medium text-[#6C6C6C] border border-[#E8E8E8] whitespace-nowrap"
                                >
                                    <div>{col}</div>
                                    <div className="text-xs font-normal text-[#9C9C9C]">tCO₂e</div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data?.rows.map((row) => {
                            const isTotal = row.scope === "total";
                            const rowClass = isTotal
                                ? "bg-[#F0F0F0] font-semibold"
                                : "bg-white hover:bg-[#FAFAFA]";
                            return (
                                <tr key={row.scope} className={rowClass}>
                                    <td className="px-4 py-2 text-left text-[#3F3A38] border border-[#E8E8E8] whitespace-nowrap">
                                        {SCOPE_LABELS[row.scope] ?? row.scope}
                                    </td>
                                    <td className="px-4 py-2 text-right text-[#3F3A38] border border-[#E8E8E8] tabular-nums">
                                        {fmt(row.baseline_construction)}
                                    </td>
                                    <td className="px-4 py-2 text-right text-[#3F3A38] border border-[#E8E8E8] tabular-nums">
                                        {fmt(row.baseline_operations)}
                                    </td>
                                    <td className="px-4 py-2 text-right text-[#3F3A38] border border-[#E8E8E8] tabular-nums font-medium">
                                        {fmt(row.baseline_lifecycle)}
                                    </td>
                                    <td className="px-4 py-2 text-right text-[#3F3A38] border border-[#E8E8E8] tabular-nums">
                                        {fmt(row.actual_construction)}
                                    </td>
                                    <td className="px-4 py-2 text-right text-[#3F3A38] border border-[#E8E8E8] tabular-nums">
                                        {fmt(row.actual_operations)}
                                    </td>
                                    <td className="px-4 py-2 text-right text-[#3F3A38] border border-[#E8E8E8] tabular-nums font-medium">
                                        {fmt(row.actual_lifecycle)}
                                    </td>
                                </tr>
                            );
                        })}

                        {(!data || data.rows.length === 0) && (
                            <tr>
                                <td colSpan={7} className="px-4 py-8 text-center text-[#9C9C9C] text-sm border border-[#E8E8E8]">
                                    No emissions data available for this stage.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
