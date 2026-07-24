import { describe, expect, it } from "vitest";

import { parseCsv } from "@/lib/csv";
import { buildTemplateCsv, mapRows } from "@/lib/delivery-import";

function rows(csv: string) {
  return parseCsv(csv).rows;
}

describe("mapRows", () => {
  it("accepts a minimal valid row (address only)", () => {
    const preview = mapRows(rows("address\n12 Rue Didouche Mourad\n"));
    expect(preview.valid).toHaveLength(1);
    expect(preview.invalid).toHaveLength(0);
    expect(preview.valid[0]).toEqual({ address: "12 Rue Didouche Mourad" });
  });

  it("flags missing address with the correct file line number", () => {
    const preview = mapRows(rows("address,weight\n,5\n"));
    expect(preview.valid).toHaveLength(0);
    expect(preview.invalid[0].line).toBe(2); // header is line 1
    expect(preview.invalid[0].errors).toContain("Adresse manquante");
  });

  it("normalizes HH:MM to HH:MM:SS and rejects reversed windows", () => {
    const ok = mapRows(rows("address,time_window_start,time_window_end\nX,9:00,12:00\n"));
    expect(ok.valid[0].time_window_start).toBe("09:00:00");
    expect(ok.valid[0].time_window_end).toBe("12:00:00");

    const bad = mapRows(rows("address,time_window_start,time_window_end\nX,14:00,10:00\n"));
    expect(bad.invalid[0].errors.some((e) => e.includes("début est après"))).toBe(true);
  });

  it("validates priority and non-negative numbers", () => {
    const preview = mapRows(rows("address,priority,weight\nX,5,-3\n"));
    const errs = preview.invalid[0].errors;
    expect(errs).toContain("Priorité doit être 1, 2 ou 3");
    expect(errs).toContain("Poids invalide");
  });

  it("requires lat and lon together and in range", () => {
    expect(mapRows(rows("address,lat\nX,36.7\n")).invalid[0].errors).toContain(
      "lat et lon doivent être fournis ensemble",
    );
    const good = mapRows(rows("address,lat,lon\nX,36.75,3.06\n"));
    expect(good.valid[0]).toMatchObject({ lat: 36.75, lon: 3.06 });
    expect(mapRows(rows("address,lat,lon\nX,99,3\n")).invalid[0].errors).toContain(
      "Latitude invalide",
    );
  });

  it("maps phone to customer_phone and keeps order_id", () => {
    const preview = mapRows(rows("address,phone,order_id\nX,0550123456,CMD-1\n"));
    expect(preview.valid[0]).toMatchObject({
      customer_phone: "0550123456",
      order_id: "CMD-1",
    });
  });
});

describe("buildTemplateCsv", () => {
  it("round-trips through the parser with an example row", () => {
    const { headers, rows: parsed } = parseCsv(buildTemplateCsv());
    expect(headers).toContain("address");
    expect(parsed).toHaveLength(1);
    expect(mapRows(parsed).valid).toHaveLength(1);
  });
});
