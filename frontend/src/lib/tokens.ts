export const colors = {
  theme: {
    light: {
      background: "#ffffff",
      foreground: "#111827",
      card: "#ffffff",
      border: "#e5e7eb",
    },
    dark: {
      background: "#111827",
      foreground: "#f9fafb",
      card: "#1f2937",
      border: "#374151",
    },
  },
  primary: {
    50: "#eff6ff",
    100: "#dbeafe",
    500: "#3b82f6",
    600: "#2563eb",
    700: "#1d4ed8",
  },
  gray: {
    50: "#f9fafb",
    100: "#f3f4f6",
    500: "#6b7280",
    900: "#111827",
  },
  success: "#10b981",
  warning: "#f59e0b",
  error: "#ef4444",
  info: "#3b82f6",
} as const;

export const breakpoints = {
  sm: "640px",
  md: "768px",
  lg: "1024px",
  xl: "1280px",
  "2xl": "1536px",
} as const;

export const spacing = {
  xs: "0.25rem",
  sm: "0.5rem",
  md: "1rem",
  lg: "1.5rem",
  xl: "2rem",
  mobile: {
    padding: "1rem",
    margin: "0.75rem",
    gap: "0.75rem",
  },
  touch: {
    minHeight: "44px",
    minWidth: "44px",
    preferred: "48px",
  },
} as const;

export const typography = {
  fontFamily: {
    sans: "Inter, system-ui, sans-serif",
    mono: "Fira Code, monospace",
  },
  fontSize: {
    xs: "0.75rem",
    sm: "0.875rem",
    base: "1rem",
    lg: "1.125rem",
    xl: "1.25rem",
  },
} as const;
