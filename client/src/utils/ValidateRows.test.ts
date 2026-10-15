import { describe, expect, it, vi } from "vitest";
import { normalizeValidationRules, validateRows, type FieldRule } from "./ValidateRows";

describe("CSV row validation", () => {
  it("normalizes lookup results and maps labels to ids", async () => {
    const fetch = vi.fn().mockResolvedValue([
      { id: "metric-1", name: "Tonnes" },
    ]);
    const rules: FieldRule[] = normalizeValidationRules([
      {
        label: "Metric",
        key: "metric_id",
        required: true,
        lookup: { fetch, labelField: "name", idField: "id" },
      },
      { label: "Quantity", key: "quantity", number: true },
    ]);

    await expect(validateRows([{ metric: "Tonnes", quantity: "1,250" }], rules))
      .resolves.toEqual({
        errors: [],
        validRows: [{ metric_id: "metric-1", metric: "Tonnes", metric_idName: "Tonnes", quantity: 1250 }],
      });
    expect(fetch).toHaveBeenCalledWith({
      row: expect.objectContaining({ metric_id: "metric-1", quantity: 1250 }),
    });
  });

  it("reports required, option, and numeric input failures", async () => {
    const { errors, validRows } = await validateRows(
      [{ category: "other", amount: "not a number" }, {}],
      [
        { label: "Category", key: "category", required: true, options: ["road"] },
        { label: "Amount", key: "amount", number: true },
      ],
    );

    expect(errors).toEqual([
      'Row 2: Invalid "Category" → "other"',
      'Row 2: "Amount" must be numeric',
      'Row 3: Missing "Category"',
    ]);
    expect(validRows).toEqual([{}, {}]);
  });
});
