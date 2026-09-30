/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#12151C",
          panel: "#1B1F29",
          border: "#2A2F3B",
          borderLight: "#353B49",
        },
        paper: {
          DEFAULT: "#E8E6E1",
          muted: "#9CA3AF",
          dim: "#6B7280",
        },
        gold: {
          DEFAULT: "#C9A227",
          hover: "#DDBA46",
          dim: "#8A7220",
        },
        moss: {
          DEFAULT: "#4E9A6B",
          dim: "#2F5C40",
        },
        rust: {
          DEFAULT: "#C1573A",
          dim: "#7A3624",
        },
      },
      fontFamily: {
        serif: ["\"Source Serif 4\"", "Georgia", "serif"],
        sans: ["\"IBM Plex Sans\"", "system-ui", "sans-serif"],
        mono: ["\"IBM Plex Mono\"", "ui-monospace", "monospace"],
      },
      maxWidth: {
        prose: "72ch",
      },
    },
  },
  plugins: [],
};
