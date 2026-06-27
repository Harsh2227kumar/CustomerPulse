import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./contexts/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      // ── Stitch Design System: Precision Operations System ───────────────
      colors: {
        // Primary palette (Slate 900)
        primary: "#0f172a",
        "on-primary": "#ffffff",
        "primary-container": "#131b2e",
        "on-primary-container": "#7c839b",
        "primary-fixed": "#dae2fd",
        "primary-fixed-dim": "#bec6e0",
        "on-primary-fixed": "#131b2e",
        "on-primary-fixed-variant": "#3f465c",
        "inverse-primary": "#bec6e0",

        // Secondary palette (Slate 600)
        secondary: "#334155",
        "on-secondary": "#ffffff",
        "secondary-container": "#d5e3fd",
        "on-secondary-container": "#57657b",
        "secondary-fixed": "#d5e3fd",
        "secondary-fixed-dim": "#b9c7e0",
        "on-secondary-fixed": "#0d1c2f",
        "on-secondary-fixed-variant": "#3a485c",

        // Tertiary
        tertiary: "#000000",
        "on-tertiary": "#ffffff",
        "tertiary-container": "#271901",
        "on-tertiary-container": "#98805d",
        "tertiary-fixed": "#fcdeb5",
        "tertiary-fixed-dim": "#dec29a",
        "on-tertiary-fixed": "#271901",
        "on-tertiary-fixed-variant": "#574425",

        // Error (Rose)
        error: "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",

        // Surface hierarchy
        background: "#f8fafc",       // Slate 50
        "on-background": "#0f172a",  // Slate 900
        surface: "#ffffff",
        "on-surface": "#1e293b",     // Slate 800
        "on-surface-variant": "#64748b", // Slate 500
        "surface-variant": "#e2e8f0",
        "surface-dim": "#dcd9db",
        "surface-bright": "#ffffff",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f1f5f9",  // Slate 100
        "surface-container": "#e2e8f0",      // Slate 200
        "surface-container-high": "#cbd5e1", // Slate 300
        "surface-container-highest": "#94a3b8", // Slate 400

        // Outline
        outline: "#94a3b8",          // Slate 400
        "outline-variant": "#e2e8f0", // Slate 200

        // Inverse
        "inverse-surface": "#1e293b",
        "inverse-on-surface": "#f1f5f9",
        "surface-tint": "#334155",

        // Functional status colors
        status: {
          resolved: {
            DEFAULT: "#059669", // Emerald 600
            bg: "#d1fae5",      // Emerald 100
            text: "#065f46",    // Emerald 900
          },
          pending: {
            DEFAULT: "#d97706", // Amber 600
            bg: "#fef3c7",      // Amber 100
            text: "#92400e",    // Amber 900
          },
          breach: {
            DEFAULT: "#dc2626", // Rose 600
            bg: "#fee2e2",      // Rose 100
            text: "#991b1b",    // Rose 800
          },
          processing: {
            DEFAULT: "#2563eb", // Blue 600
            bg: "#dbeafe",      // Blue 100
            text: "#1e40af",    // Blue 800
          },
        },
      },

      fontFamily: {
        sans: ["Geist", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "ui-monospace", "monospace"],
      },

      fontSize: {
        "headline-lg": [
          "24px",
          { lineHeight: "32px", fontWeight: "600", letterSpacing: "-0.02em" },
        ],
        "headline-md": [
          "20px",
          { lineHeight: "28px", fontWeight: "600", letterSpacing: "-0.01em" },
        ],
        "headline-sm": [
          "16px",
          { lineHeight: "24px", fontWeight: "600" },
        ],
        "body-lg": ["16px", { lineHeight: "24px", fontWeight: "400" }],
        "body-md": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        "body-sm": ["13px", { lineHeight: "18px", fontWeight: "400" }],
        "label-md": [
          "12px",
          { lineHeight: "16px", fontWeight: "600", letterSpacing: "0.05em" },
        ],
        "mono-data": ["13px", { lineHeight: "20px", fontWeight: "400" }],
      },

      borderRadius: {
        DEFAULT: "0.25rem",   // 4px — standard
        sm: "0.125rem",       // 2px
        md: "0.375rem",       // 6px
        lg: "0.5rem",         // 8px — large containers
        xl: "0.75rem",        // 12px
        full: "9999px",       // pills
      },

      spacing: {
        xs: "4px",
        sm: "8px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        gutter: "16px",
        "sidebar-width": "260px",
      },

      boxShadow: {
        // Elevation Level 2 — modals / dropdowns
        modal: "0px 4px 12px rgba(15, 23, 42, 0.08)",
        // Subtle card elevation
        card: "0 1px 3px rgba(15, 23, 42, 0.05)",
      },
    },
  },
  plugins: [],
};

export default config;
