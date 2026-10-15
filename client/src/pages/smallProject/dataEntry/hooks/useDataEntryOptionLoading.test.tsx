import { act, renderHook, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import { useDataEntryOptionLoading } from "./useDataEntryOptionLoading";

const businessStage = { id: "business", stage: "BUSINESS_CASE" as const };
const options: ProjectOption[] = [{
    id: "option-1",
    project_id: "project-1",
    stage_instance_id: "business",
    report_number: 1,
    option_number: 1,
    label: "Option 1",
    is_default: true,
    approval_status: "draft",
}];
const businessAccess = [{
    stage_instance_id: "business",
    stage: "BUSINESS_CASE",
    stage_label: "Business case",
    sequence: 1,
    access: "EDIT" as const,
}];

describe("useDataEntryOptionLoading", () => {
    it("loads missing options for the active stage only when access is available", async () => {
        const loadStageOptions = vi.fn().mockResolvedValue(options);
        const common = {
            enabled: true,
            activeStage: "Business case" as const,
            projectClass: "SMALL" as const,
            showMitigations: false,
            activeStageInstance: businessStage,
            mitigationStageInstance: null,
            mitigationBucketStageEnum: "DESIGN",
            designStageInstance: null,
            stageAccess: businessAccess,
            projectOptions: [],
            loadStageOptions,
            refreshStageOptions: vi.fn().mockResolvedValue(options),
            setSelectedOptionByStage: vi.fn(),
        };

        const { rerender } = renderHook((props) => useDataEntryOptionLoading(props), { initialProps: common });
        await waitFor(() => expect(loadStageOptions).toHaveBeenCalledWith("business", "EDIT"));

        rerender({ ...common, projectOptions: options });
        expect(loadStageOptions).toHaveBeenCalledTimes(1);
        rerender({ ...common, enabled: false });
        expect(loadStageOptions).toHaveBeenCalledTimes(1);
    });

    it("drops a stale option override after refreshing options", async () => {
        const refreshStageOptions = vi.fn().mockResolvedValue(options);
        const { result } = renderHook(() => {
            const [selectedOptionByStage, setSelectedOptionByStage] = useState({ business: "deleted-option" });
            const actions = useDataEntryOptionLoading({
                enabled: true,
                activeStage: "Business case",
                projectClass: "SMALL",
                showMitigations: false,
                activeStageInstance: businessStage,
                mitigationStageInstance: null,
                mitigationBucketStageEnum: "DESIGN",
                designStageInstance: null,
                stageAccess: businessAccess,
                projectOptions: options,
                loadStageOptions: vi.fn().mockResolvedValue(options),
                refreshStageOptions,
                setSelectedOptionByStage,
            });
            return { ...actions, selectedOptionByStage };
        });

        await act(async () => result.current.onOptionsChange());

        expect(refreshStageOptions).toHaveBeenCalledWith("business");
        expect(result.current.selectedOptionByStage).toEqual({});
    });
});
