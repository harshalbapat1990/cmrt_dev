import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RecurringStageContent } from "./RecurringStageContent";

vi.mock("@/components/common/TableWrapper", () => ({
    default: ({ title, columns, children, collapsible = true }: { title: string; columns: Array<{ header?: string }>; children?: React.ReactNode; collapsible?: boolean }) => (
        <div data-testid="table-wrapper" data-title={title} data-collapsible={collapsible}>
            <h3>{title}</h3>
            {children}
            {columns.map((column) => <span key={column.header}>{column.header}</span>)}
        </div>
    ),
}));
vi.mock("./PeriodEmissionSummary", () => ({ PeriodEmissionSummary: () => <div /> }));

describe("RecurringStageContent electricity groups", () => {
    it("renders each electricity table before its other-sources table and omits the year column", () => {
        const activities = [
            "Construction plant/equipment",
            "Permanent depots / facilities",
            "Temporary sites / camps",
            "Vehicle fleet",
        ];
        render(<RecurringStageContent
            period={{ id: "period-1" } as never}
            activities={activities}
            rowsByActivity={Object.fromEntries(activities.map((activity) => [activity, []]))}
            electricityRowsByActivity={Object.fromEntries(activities.map((activity, index) => [activity, index === 0 ? [] : [{ id: activity }]]))}
            columnsForActivity={() => [{ header: "Source" }] as never}
            electricityColumns={[{ header: "Emission source" }, { header: "Quantity" }] as never}
            onActivityRowsChange={vi.fn()}
            onElectricityRowsChange={vi.fn()}
            onRequestUpload={vi.fn()}
            saveNewRow={vi.fn(async () => true)}
            accordionState={{}}
            setAccordionState={vi.fn()}
        />);

        const wrappers = screen.getAllByTestId("table-wrapper");
        expect(wrappers).toHaveLength(activities.length * 2);
        for (let i = 0; i < activities.length; i += 1) {
            const activityWrapper = wrappers.find((wrapper) => wrapper.getAttribute("data-title") === activities[i]);
            expect(activityWrapper).toBeInTheDocument();
            expect(within(activityWrapper!).getByText("Electricity")).toBeInTheDocument();
            expect(within(activityWrapper!).getByText("All other sources")).toBeInTheDocument();
            const electricityWrapper = within(activityWrapper!).getByTestId("table-wrapper");
            expect(electricityWrapper).toHaveAttribute("data-title", "Electricity");
            expect(electricityWrapper).toHaveAttribute("data-collapsible", "false");
            expect(within(electricityWrapper).queryByText("Year")).not.toBeInTheDocument();
        }
    });
});
