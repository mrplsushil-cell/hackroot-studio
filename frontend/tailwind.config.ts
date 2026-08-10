import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f7f8fa",
          100: "#eef0f4",
          200: "#dde2ea",
          300: "#bcc4d1",
          400: "#8b95a6",
          500: "#5b6678",
          600: "#404a5c",
          700: "#2c3445",
          800: "#1b2030",
          900: "#0f1320",
          950: "#080b14",
        },
        brand: {
          50: "#eef9ff",
          100: "#d9f0ff",
          200: "#bce5ff",
          300: "#8ed5ff",
          400: "#58baff",
          500: "#2f9bff",
          600: "#1a7cf0",
          700: "#1864d4",
          800: "#1a52ac",
          900: "#1b488a",
        },
        accent: {
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Inter", "Segoe UI", "Helvetica Neue", "Arial"],
      },
      backgroundImage: {
        "grid-fade":
          "linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.4) 80%), radial-gradient(circle at 50% 0%, rgba(120,80,255,0.15), transparent 60%)",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(120,160,255,0.15), 0 10px 30px -10px rgba(120,160,255,0.25)",
      },
    },
  },
  plugins: [],
};
export default config;
