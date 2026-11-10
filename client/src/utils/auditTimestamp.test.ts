import { describe, expect, it } from "vitest";
import { formatAuditTimestamp, parseAuditTimestamp } from "./auditTimestamp";

describe("audit timestamp formatting", () => {
  it("interprets legacy timezone-naive values as UTC and renders Sydney daylight time", () => {
    expect(parseAuditTimestamp("2026-01-15T12:00:00")?.toISOString()).toBe("2026-01-15T12:00:00.000Z");
    expect(formatAuditTimestamp("2026-01-15T12:00:00")).toContain("AEDT");
  });

  it("renders Australian Eastern standard time in winter and preserves explicit offsets", () => {
    expect(formatAuditTimestamp("2026-07-15T12:00:00")).toContain("AEST");
    expect(parseAuditTimestamp("2026-01-15T23:00:00+11:00")?.toISOString()).toBe("2026-01-15T12:00:00.000Z");
  });

  it("returns a dash for missing values and preserves invalid input for diagnosis", () => {
    expect(formatAuditTimestamp(null)).toBe("—");
    expect(formatAuditTimestamp("not-a-date")).toBe("not-a-date");
  });
});
