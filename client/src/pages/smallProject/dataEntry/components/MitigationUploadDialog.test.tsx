import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { DataEntryRow } from "../dataEntryTypes";
import { MitigationUploadDialog } from "./MitigationUploadDialog";

const captured = vi.hoisted(() => ({ props: null as unknown }));

vi.mock("@/pages/dummy-table/UploadModal", () => ({
  UploadModal: (props: object) => {
    captured.props = props;
    return null;
  },
}));

type ModalContract = {
  validateRows: (rows: DataEntryRow[]) => Promise<{ validRows: DataEntryRow[]; errors: string[] }>;
  onSuccess: (rows: DataEntryRow[]) => Promise<void>;
};

describe("MitigationUploadDialog", () => {
  it("validates parsed rows and uploads validated rows into the selected mitigation table", async () => {
    const upload = vi.fn().mockResolvedValue({ rows: [{ id: "saved-1", quantity: 5 }] });
    const onUploaded = vi.fn();
    render(
      <MitigationUploadDialog
        open
        uploadKey="electricity"
        projectId="project-1"
        projectMitigationId="mitigation-1"
        substitutionLeg="replaced"
        onClose={vi.fn()}
        upload={upload}
        onUploaded={onUploaded}
      />,
    );

    const modal = captured.props as ModalContract;
    const validation = await modal.validateRows([]);
    expect(validation.errors).toEqual(["The selected file contains no data rows."]);
    expect(validation.validRows).toEqual([]);
    expect(upload).not.toHaveBeenCalled();

    const rows: DataEntryRow[] = [{ quantity: 5 }];
    await modal.onSuccess(rows);
    expect(upload).toHaveBeenCalledWith("electricity", "mitigation-1", rows, "replaced");
    expect(onUploaded).toHaveBeenCalledWith("electricity", [{ id: "saved-1", quantity: 5 }]);
  });

  it("surfaces upload failures to the modal for its error state", async () => {
    const upload = vi.fn().mockRejectedValue(new Error("Upload rejected"));
    render(
      <MitigationUploadDialog
        open
        uploadKey="component"
        projectId="project-1"
        projectMitigationId="mitigation-1"
        substitutionLeg={null}
        onClose={vi.fn()}
        upload={upload}
        onUploaded={vi.fn()}
      />,
    );

    await expect((captured.props as ModalContract).onSuccess([])).rejects.toThrow("Upload rejected");
  });
});
