// White-label theming (F16): apply a company's brand colour to the CSS variables
// that Tailwind's `primary` token reads. Shades are derived so hover/badge states
// stay on-brand.

type RGB = [number, number, number];

function hexToRgb(hex: string): RGB | null {
  const m = hex.replace("#", "");
  const full =
    m.length === 3
      ? m
          .split("")
          .map((c) => c + c)
          .join("")
      : m;
  if (full.length !== 6) return null;
  const n = Number.parseInt(full, 16);
  if (Number.isNaN(n)) return null;
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// Mix `rgb` toward `target` by ratio t (0..1).
function mix([r, g, b]: RGB, [tr, tg, tb]: RGB, t: number): RGB {
  return [Math.round(r + (tr - r) * t), Math.round(g + (tg - g) * t), Math.round(b + (tb - b) * t)];
}

const channels = ([r, g, b]: RGB): string => `${r} ${g} ${b}`;

const VARS = ["--color-primary", "--color-primary-dark", "--color-primary-light"] as const;

export function applyBrandColor(hex: string): void {
  const rgb = hexToRgb(hex);
  if (!rgb) return;
  const root = document.documentElement.style;
  root.setProperty("--color-primary", channels(rgb));
  root.setProperty("--color-primary-dark", channels(mix(rgb, [0, 0, 0], 0.15)));
  root.setProperty("--color-primary-light", channels(mix(rgb, [255, 255, 255], 0.85)));
}

export function resetBrandColor(): void {
  const root = document.documentElement.style;
  for (const v of VARS) root.removeProperty(v);
}
