import { afterEach, describe, expect, it } from "vitest";

import { applyBrandColor, resetBrandColor } from "@/lib/branding";

const root = document.documentElement.style;

afterEach(() => resetBrandColor());

describe("applyBrandColor", () => {
  it("sets the primary CSS variable to the colour's RGB channels", () => {
    applyBrandColor("#EF4444");
    expect(root.getPropertyValue("--color-primary")).toBe("239 68 68");
    // Derived shades are set too.
    expect(root.getPropertyValue("--color-primary-dark")).not.toBe("");
    expect(root.getPropertyValue("--color-primary-light")).not.toBe("");
  });

  it("expands 3-digit hex", () => {
    applyBrandColor("#fff");
    expect(root.getPropertyValue("--color-primary")).toBe("255 255 255");
  });

  it("ignores an invalid colour", () => {
    applyBrandColor("not-a-color");
    expect(root.getPropertyValue("--color-primary")).toBe("");
  });
});
