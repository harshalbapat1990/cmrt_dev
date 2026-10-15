import { describe, expect, it } from "vitest";
import {
  getApiErrorMessage,
  hasAllRequired,
  isValidEmission,
  toDataEntryRows,
} from "./dataEntryValidation";

describe("data entry validation contracts", () => {
  it("checks required row fields without requiring a broad untyped object", () => {
    expect(hasAllRequired({ quantity: 0, unit_id: "unit-1" }, ["quantity", "unit_id"])).toBe(true);
    expect(hasAllRequired({ quantity: "", unit_id: "unit-1" }, ["quantity", "unit_id"])).toBe(false);
  });

  it("accepts finite emissions and rejects missing or non-numeric values", () => {
    expect(isValidEmission(0)).toBe(true);
    expect(isValidEmission("1.25")).toBe(true);
    expect(isValidEmission("-")).toBe(false);
    expect(isValidEmission("not calculated")).toBe(false);
    expect(isValidEmission(null)).toBe(false);
  });

  it("formats unknown API errors and validation detail arrays", () => {
    expect(getApiErrorMessage({ response: { data: { detail: [{ msg: "Invalid row" }, { loc: ["year"] }] } } }))
      .toBe('Invalid row, {"loc":["year"]}');
    expect(getApiErrorMessage(new Error("Request failed"))).toBe("Request failed");
    expect(getApiErrorMessage({})).toBe("Emission calculation failed. Please try again.");
  });

  it("filters parser output to object rows with a compatible id", () => {
    expect(toDataEntryRows([
      { id: "row-1", quantity: 1 },
      { id: {} },
      null,
      "invalid",
    ])).toEqual([{ id: "row-1", quantity: 1 }]);
  });
});
