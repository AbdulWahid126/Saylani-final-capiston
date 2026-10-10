import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--text-primary))",
        surface: {
          DEFAULT: "hsl(var(--surface))",
          hover: "hsl(var(--surface-hover))",
          raised: "hsl(var(--surface-raised))",
        },
        border: {
          DEFAULT: "hsl(var(--border))",
          active: "hsl(var(--border-active))",
        },
        text: {
          primary: "hsl(var(--text-primary))",
          secondary: "hsl(var(--text-secondary))",
          tertiary: "hsl(var(--text-tertiary))",
        },
        profit: {
          DEFAULT: "hsl(var(--profit))",
          subtle: "hsl(var(--profit-subtle))",
        },
        loss: {
          DEFAULT: "hsl(var(--loss))",
          subtle: "hsl(var(--loss-subtle))",
        },
        warning: "hsl(var(--warning))",
        "neutral-blue": "hsl(var(--neutral-blue))",
        badge: {
          verified: "hsl(var(--badge-verified))",
          calc: "hsl(var(--badge-calc))",
          hist: "hsl(var(--badge-hist))",
          ml: "hsl(var(--badge-ml))",
          ai: "hsl(var(--badge-ai))",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
