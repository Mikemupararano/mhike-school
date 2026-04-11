export const brand = {
    name: "Mhike School",
    shortName: "Mhike",
    tagline: "Learning platform",
    description: "A premium learning platform for modern schools.",
} as const;

export const brandColors = {
    navy: "#0f2d4a",
    navySoft: "#133554",
    navyDeep: "#0b2238",
    blue: "#2563EB",
    blueHover: "#1D4ED8",
    blueSoft: "#60A5FA",
    gold: "#f6c453",
    white: "#FFFFFF",
    slate50: "#F8FAFC",
    slate100: "#EEF4FA",
    slate300: "#CBD5E1",
    slate500: "#64748B",
    slate700: "#334155",
    success: "#22C55E",
    warning: "#F59E0B",
    danger: "#EF4444",
} as const;

export const brandRadius = {
    sm: "10px",
    md: "14px",
    lg: "18px",
    xl: "22px",
    "2xl": "24px",
    "3xl": "36px",
    full: "999px",
} as const;

export const brandShadows = {
    sm: "0 4px 12px rgba(15,23,42,0.08)",
    md: "0 12px 30px rgba(15,23,42,0.14)",
    lg: "0 20px 40px rgba(15,23,42,0.20)",
    xl: "0 38px 90px rgba(15,23,42,0.30)",
    glow: "0 20px 40px rgba(37,99,235,0.35)",
} as const;

export const brandSpacing = {
    1: "4px",
    2: "8px",
    3: "12px",
    4: "16px",
    5: "20px",
    6: "24px",
    8: "32px",
    10: "40px",
    12: "48px",
    14: "56px",
    16: "64px",
    18: "72px",
    20: "80px",
} as const;

export const brandTypeScale = {
    display: "72px",
    h1: "56px",
    h2: "40px",
    h3: "32px",
    h4: "24px",
    bodyLg: "22px",
    body: "18px",
    bodySm: "16px",
    label: "14px",
    caption: "12px",
} as const;

export const brandTokens = {
    colors: brandColors,
    radius: brandRadius,
    shadows: brandShadows,
    spacing: brandSpacing,
    typeScale: brandTypeScale,
} as const;

export type BrandColor = keyof typeof brandColors;
export type BrandRadius = keyof typeof brandRadius;
export type BrandShadow = keyof typeof brandShadows;
export type BrandSpacing = keyof typeof brandSpacing;
export type BrandTypeScale = keyof typeof brandTypeScale;