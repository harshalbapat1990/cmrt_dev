import * as XLSX from "xlsx";
import { describe, expect, it } from "vitest";
import { parseFileToRows } from "./parseFileToRows";

const headers = [
  { key: "vehicle_type", label: "Vehicle type" },
  { key: "quantity", label: "Quantity" },
];

describe("parseFileToRows", () => {
  it("returns typed row records for CSV headers", async () => {
    const file = new File(["Vehicle type,Quantity\nSmall car,12"], "vehicles.csv");

    await expect(parseFileToRows(file, headers, ["quantity"])).resolves.toEqual([
      expect.objectContaining({ vehicle_type: "Small car", quantity: 12 }),
    ]);
  });

  it("reads XLSX rows from the selected worksheet", async () => {
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([
      ["Vehicle type", "Quantity"],
      ["Bus", "25"],
    ]), "Vehicles");
    const bytes = XLSX.write(workbook, { type: "array", bookType: "xlsx" });
    const file = new File([bytes], "vehicles.xlsx");

    await expect(parseFileToRows(file, headers, ["quantity"])).resolves.toEqual([
      expect.objectContaining({ vehicle_type: "Bus", quantity: 25 }),
    ]);
  });
});
