import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LargeRoadUsersYearSelector } from "./LargeRoadUsersYearSelector";

vi.mock("@/components/common/Select", () => ({
  SelectListbox: ({
    value,
    options,
    onChange,
    disabled,
  }: {
    value: string;
    options: Array<{ label: string; value: string }>;
    onChange: (value: string) => void;
    disabled?: boolean;
  }) => (
    <select
      aria-label="Modelled year"
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    >
      {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
    </select>
  ),
}));

describe("LargeRoadUsersYearSelector", () => {
  it("selects years and exposes add, copy, and delete actions", () => {
    const onYearChange = vi.fn();
    const onAddYear = vi.fn();
    const onCopyYear = vi.fn();
    const onDeleteYear = vi.fn();
    render(<LargeRoadUsersYearSelector
      years={[2024, 2030]}
      activeYear={2030}
      readOnly={false}
      onYearChange={onYearChange}
      onAddYear={onAddYear}
      onCopyYear={onCopyYear}
      onDeleteYear={onDeleteYear}
    />);

    fireEvent.change(screen.getByRole("combobox", { name: "Modelled year" }), { target: { value: "2024" } });
    expect(onYearChange).toHaveBeenCalledWith(2024);

    fireEvent.click(screen.getByRole("button", { name: "More modelled year options" }));
    fireEvent.click(screen.getByRole("button", { name: "Add year" }));
    expect(onAddYear).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: "More modelled year options" }));
    fireEvent.click(screen.getByRole("button", { name: "Copy from…" }));
    expect(onCopyYear).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: "More modelled year options" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete year 2030" }));
    expect(onDeleteYear).toHaveBeenCalledOnce();
  });

  it("hides year actions and disables selection in read-only mode", () => {
    render(<LargeRoadUsersYearSelector years={[2030]} activeYear={2030} readOnly />);

    expect(screen.getByRole("combobox", { name: "Modelled year" }).hasAttribute("disabled")).toBe(true);
    expect(screen.queryByRole("button", { name: "More modelled year options" })).toBeNull();
  });

  it("shows an empty state and omits copy/delete when no years are available", () => {
    render(<LargeRoadUsersYearSelector years={[]} activeYear={null} readOnly={false} />);

    expect(screen.getByText("No years")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "More modelled year options" }));
    expect(screen.getByRole("button", { name: "Add year" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Copy from…" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Delete year/ })).toBeNull();
  });
});
