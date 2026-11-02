import { describe, expect, it } from "vitest";
import { emptyRowMap, keepTableRows } from "./useTableRows";

describe("data-entry table row state", () => {
  it("initializes every supported table with an independent empty row list", () => {
    const rows = emptyRowMap();

    expect(Object.values(rows).every((tableRows) => tableRows.length === 0)).toBe(true);
    expect(rows.asset).not.toBe(rows.component);
  });

  it("clears stage rows while preserving only explicitly retained tables", () => {
    const rows = emptyRowMap();
    rows.asset = [{ id: "asset-1" }];
    rows.concreteRegSimplified = [{ id: "mix-1" }];
    rows.concreteRegDetailed = [{ id: "epd-1" }];

    const next = keepTableRows(rows, ["concreteRegSimplified", "concreteRegDetailed"]);

    expect(next.asset).toEqual([]);
    expect(next.concreteRegSimplified).toEqual([{ id: "mix-1" }]);
    expect(next.concreteRegDetailed).toEqual([{ id: "epd-1" }]);
  });
});
