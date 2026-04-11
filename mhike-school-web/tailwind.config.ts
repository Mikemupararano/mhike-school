import type { Config } from "tailwindcss";

export default {
    content: [
        "./app/**/*.{ts,tsx}",
        "./components/**/*.{ts,tsx}",
        "./lib/**/*.{ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                brand: {
                    navy: "#0f2d4a",
                    navySoft: "#133554",
                    navyDeep: "#0b2238",
                    blue: "#2563EB",
                    blueHover: "#1D4ED8",
                    blueSoft: "#60A5FA",
                    gold: "#f6c453",
                },
            },
            boxShadow: {
                brand: "0 38px 90px rgba(15,23,42,0.30)",
                glow: "0 20px 40px rgba(37,99,235,0.35)",
            },
        },
    },
    plugins: [],
} satisfies Config;