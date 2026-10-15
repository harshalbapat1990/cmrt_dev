import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Mitigation } from "../mitigationTypes";
import { MitigationSummaryView, MitigationsList } from "./MitigationOverview";

const mitigation: Mitigation = {
    id: "mitigation-1",
    name: "Use recycled aggregate",
    type: "reduction",
    group: "Materials",
    estimatedSavingTco2e: 25,
    lifecyclePhase: "construction",
    lifecyclePhaseLabel: "Construction",
};

describe("MitigationOverview", () => {
    it("renders the empty summary and empty list states", () => {
        const { container } = render(<>
            <MitigationSummaryView mitigations={[]} />
            <MitigationsList mitigations={[]} />
        </>);

        expect(screen.getByText("No mitigations to summarize yet.")).toBeInTheDocument();
        expect(screen.getByText("No mitigations yet")).toBeInTheDocument();
        expect(container.querySelector("tbody td")?.getAttribute("colspan")).toBe("7");
    });

    it("shows mitigation totals and routes edit and delete actions to their callbacks", () => {
        const onEdit = vi.fn();
        const onDelete = vi.fn();
        render(<>
            <MitigationSummaryView mitigations={[mitigation]} />
            <MitigationsList mitigations={[mitigation]} onEdit={onEdit} onDelete={onDelete} />
        </>);

        expect(screen.getAllByText("Use recycled aggregate")).toHaveLength(2);
        expect(screen.getByText("Construction")).toBeInTheDocument();
        fireEvent.click(screen.getByRole("button", { name: "Edit Use recycled aggregate" }));
        fireEvent.click(screen.getByRole("button", { name: "Delete Use recycled aggregate" }));
        expect(onEdit).toHaveBeenCalledWith(mitigation);
        expect(onDelete).toHaveBeenCalledWith("mitigation-1");
    });

    it("opens a mitigation row in view-only mode without showing mutation actions", () => {
        const onOpenRow = vi.fn();
        render(<MitigationsList
            mitigations={[mitigation]}
            allowMutations={false}
            viewOnlyInteraction
            onOpenRow={onOpenRow}
        />);

        fireEvent.click(screen.getByText("Use recycled aggregate"));
        expect(onOpenRow).toHaveBeenCalledWith(mitigation);
        expect(screen.queryByRole("button", { name: "Edit Use recycled aggregate" })).not.toBeInTheDocument();
    });
});
