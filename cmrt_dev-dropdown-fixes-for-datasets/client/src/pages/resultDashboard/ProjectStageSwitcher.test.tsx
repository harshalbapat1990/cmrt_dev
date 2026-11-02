import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProjectStageSwitcher } from "./ProjectStageSwitcher";
import type { StageNavigationItem } from "../smallProject/dataEntry/stageNavigationOptions";

vi.mock("@/components/common/Select", () => ({
  SelectListbox: ({
    value,
    options,
    onChange,
    ...props
  }: {
    value: string;
    options: Array<{ label: string; value: string }>;
    onChange: (value: string) => void;
    "aria-label"?: string;
  }) => (
    <select value={value} onChange={(event) => onChange(event.target.value)} {...props}>
      {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
    </select>
  ),
}));

const options: StageNavigationItem[] = [
  {
    label: "Business case",
    value: "Business case__1",
    stageLabel: "Business case",
    reportNumber: 1,
    stageInstanceId: "stage-bc",
    disabled: false,
  },
  {
    label: "Results dashboard",
    value: "RESULTS_DASHBOARD",
    stageLabel: "RESULTS_DASHBOARD",
    reportNumber: 1,
    disabled: false,
  },
];

describe("ProjectStageSwitcher", () => {
  it("shows Results dashboard as selected and forwards stage selections", () => {
    const onChange = vi.fn();
    render(<ProjectStageSwitcher options={options} collapsed={false} onChange={onChange} />);

    const selector = screen.getByRole("combobox", { name: "Project stage and dashboard" });
    expect((selector as HTMLSelectElement).value).toBe("RESULTS_DASHBOARD");
    expect(screen.getByText("Project navigation")).toBeTruthy();

    fireEvent.change(selector, { target: { value: "Business case__1" } });
    expect(onChange).toHaveBeenCalledWith("Business case__1");
  });

  it("keeps the selector available in the collapsed sidebar", () => {
    render(<ProjectStageSwitcher options={options} collapsed onChange={vi.fn()} />);

    expect(screen.getByRole("combobox", { name: "Project stage and dashboard" })).toBeTruthy();
    expect(screen.queryByText("Project navigation")).toBeNull();
  });
});
