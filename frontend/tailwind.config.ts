import type { Config } from "tailwindcss";

// Design tokens from docs/DESIGN.md §2.1–2.2
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Driven by CSS variables so a company's brand colour applies at runtime
        // (F16 white-label). Defaults live in index.css.
        primary: {
          DEFAULT: "rgb(var(--color-primary) / <alpha-value>)",
          dark: "rgb(var(--color-primary-dark) / <alpha-value>)",
          light: "rgb(var(--color-primary-light) / <alpha-value>)",
        },
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
        info: "#06B6D4",
        map: {
          primary: "#3B82F6",
          secondary: "#9CA3AF",
          depot: "#10B981",
          stop: "#2563EB",
          stopLate: "#EF4444",
        },
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans Arabic", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
