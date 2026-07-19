import { describe, expect, it } from "vitest";

import { parseCsv } from "@/lib/csv";

describe("parseCsv", () => {
  it("parses headers (lower-cased) and rows", () => {
    const { headers, rows } = parseCsv("Address,Weight\n12 Rue X,5\n45 Bd Y,8\n");
    expect(headers).toEqual(["address", "weight"]);
    expect(rows).toEqual([
      { address: "12 Rue X", weight: "5" },
      { address: "45 Bd Y", weight: "8" },
    ]);
  });

  it("handles quoted fields with commas and escaped quotes", () => {
    const { rows } = parseCsv('address\n"12 Rue X, Alger"\n"He said ""hi"""\n');
    expect(rows[0].address).toBe("12 Rue X, Alger");
    expect(rows[1].address).toBe('He said "hi"');
  });

  it("handles quoted newlines and CRLF", () => {
    const { rows } = parseCsv('address,order_id\r\n"line1\nline2",CMD-1\r\n');
    expect(rows).toHaveLength(1);
    expect(rows[0].address).toBe("line1\nline2");
    expect(rows[0].order_id).toBe("CMD-1");
  });

  it("skips blank lines", () => {
    const { rows } = parseCsv("address\n12 Rue X\n\n\n45 Bd Y\n");
    expect(rows).toHaveLength(2);
  });
});
