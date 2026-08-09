/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#14181F",
        surface: "#1C222B",
        raised: "#242B36",
        border: "#2C333F",
        accent: {
          DEFAULT: "#C99B4A",
          soft: "#3A3222",
        },
        signal: {
          DEFAULT: "#4FB8AE",
          soft: "#1C3532",
        },
        ink: {
          primary: "#EDEFF3",
          secondary: "#9AA3B2",
          muted: "#5B6272",
        },
        good: "#6FBE8F",
        bad: "#E2685F",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        sans: ["Inter", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: 0, transform: "translateY(4px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        blink: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.2 },
        },
      },
      animation: {
        "fade-in": "fade-in 180ms ease-out",
        blink: "blink 1.1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
