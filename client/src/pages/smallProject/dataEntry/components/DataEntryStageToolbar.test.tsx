import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DataEntryStageToolbar } from "./DataEntryStageToolbar";

const baseProps = {
    isConstructionStage: false,
    isRecurringStage: false,
    isLargeProject: false,
    isBusinessCaseStage: true,
    isReadOnly: false,
    totalEmissions: 1250,
    operationalLifeYears: 40,
    designReportNumbers: [1, 2],
    designReportNumber: 1,
    onRequestDesignReportChange: vi.fn(),
    activeOptionId: "option-1",
    options: [{ label: "Option 1", value: "option-1" }],
    onOptionChange: vi.fn(),
    onOpenCopyData: vi.fn(),
    onOpenManageOptions: vi.fn(),
};

describe("DataEntryStageToolbar", () => {
    it("opens the Business Case menu and invokes its actions", () => {
        render(<DataEntryStageToolbar {...baseProps} />);

        fireEvent.click(screen.getByRole("button", { name: "More options" }));
        fireEvent.click(screen.getByRole("button", { name: "Copy data" }));
        expect(baseProps.onOpenCopyData).toHaveBeenCalledOnce();

        fireEvent.click(screen.getByRole("button", { name: "More options" }));
        fireEvent.click(screen.getByRole("button", { name: "Manage options" }));
        expect(baseProps.onOpenManageOptions).toHaveBeenCalledOnce();
    });

    it("allows a different Design report to be requested for confirmation", () => {
        render(<DataEntryStageToolbar
            {...baseProps}
            isConstructionStage
            isBusinessCaseStage={false}
            isLargeProject
        />);

        fireEvent.change(screen.getByRole("combobox"), { target: { value: "2" } });
        expect(baseProps.onRequestDesignReportChange).toHaveBeenCalledWith(2);
    });
});
