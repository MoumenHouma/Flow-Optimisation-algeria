import { describe, expect, it } from "vitest";

import { formatDuration, formatKm } from "@/lib/format";

describe("formatKm", () => {
  it("formats meters as km", () => {
    expect(formatKm(1500)).toBe("1.5 km");
    expect(formatKm(0)).toBe("0.0 km");
  });
  it("handles null/undefined", () => {
    expect(formatKm(null)).toBe("—");
    expect(formatKm(undefined)).toBe("—");
  });
});

describe("formatDuration", () => {
  it("formats seconds as h/min", () => {
    expect(formatDuration(600)).toBe("10min");
    expect(formatDuration(3600)).toBe("1h 0min");
    expect(formatDuration(5400)).toBe("1h 30min");
  });
  it("handles null", () => {
    expect(formatDuration(null)).toBe("—");
  });
});
