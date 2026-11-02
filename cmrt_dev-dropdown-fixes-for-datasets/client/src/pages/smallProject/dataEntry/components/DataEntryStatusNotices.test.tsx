import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DataEntryStatusNotices } from "./DataEntryStatusNotices";

const baseProps = {
    showMitigations: false,
    isProjectAdmin: false,
    isReopenRequested: false,
    isApproved: false,
    isStageLocked: false,
    isPeriodWorkflowStage: false,
    constructionPeriodCount: 0,
    isSubmitted: false,
    isRejected: false,
    rejectionComment: null,
    reopenReason: "",
    adminViewOnly: false,
    statusBasedReadOnly: false,
};

describe("DataEntryStatusNotices", () => {
    it("shows the approved notice to a non-admin and hides it during a reopen request", () => {
        const { rerender } = render(<DataEntryStatusNotices {...baseProps} isApproved />);
        expect(screen.getByText("This report has been approved")).toBeTruthy();

        rerender(<DataEntryStatusNotices {...baseProps} isApproved isReopenRequested />);
        expect(screen.queryByText("This report has been approved")).toBeNull();
        expect(screen.getByText("Reopen requested")).toBeTruthy();
    });

    it("shows the admin reopen reason and admin view-only notice in their respective states", () => {
        const { rerender } = render(<DataEntryStatusNotices
            {...baseProps}
            isProjectAdmin
            isReopenRequested
            reopenReason="Please correct the submitted values"
        />);
        expect(screen.getByText("Please correct the submitted values")).toBeTruthy();

        rerender(<DataEntryStatusNotices {...baseProps} adminViewOnly />);
        expect(screen.getByText("View-only access")).toBeTruthy();
    });
});
