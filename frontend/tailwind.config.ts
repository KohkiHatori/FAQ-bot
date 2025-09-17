import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  prefix: "",
  safelist: [
    // Role badge colors - ensure these are always included
    "bg-red-100",
    "text-red-800",
    "border-red-200",
    "bg-blue-100",
    "text-blue-800",
    "border-blue-200",
    "bg-green-100",
    "text-green-800",
    "border-green-200",
    "bg-purple-100",
    "text-purple-800",
    "border-purple-200",
    "bg-orange-100",
    "text-orange-800",
    "border-orange-200",
    "bg-cyan-100",
    "text-cyan-800",
    "border-cyan-200",
    "bg-gray-100",
    "text-gray-800",
    "border-gray-200",
    // Dark mode variants
    "dark:bg-red-900",
    "dark:text-red-200",
    "dark:border-red-700",
    "dark:bg-blue-900",
    "dark:text-blue-200",
    "dark:border-blue-700",
    "dark:bg-green-900",
    "dark:text-green-200",
    "dark:border-green-700",
    "dark:bg-purple-900",
    "dark:text-purple-200",
    "dark:border-purple-700",
    "dark:bg-orange-900",
    "dark:text-orange-200",
    "dark:border-orange-700",
    "dark:bg-cyan-900",
    "dark:text-cyan-200",
    "dark:border-cyan-700",
    "dark:bg-gray-900",
    "dark:text-gray-200",
    "dark:border-gray-700",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        navy: "#1A2A40",
        accentBlue: "#0099ce",
        chart: {
          "1": "hsl(var(--chart-1))",
          "2": "hsl(var(--chart-2))",
          "3": "hsl(var(--chart-3))",
          "4": "hsl(var(--chart-4))",
          "5": "hsl(var(--chart-5))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: {
            height: "0",
          },
          to: {
            height: "var(--radix-accordion-content-height)",
          },
        },
        "accordion-up": {
          from: {
            height: "var(--radix-accordion-content-height)",
          },
          to: {
            height: "0",
          },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;

export default config;
