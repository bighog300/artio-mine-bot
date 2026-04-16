import { describe, expect, it } from "vitest";
import { colors, spacing, typography } from "@/lib/tokens";

describe("design tokens", () => {
  it("exports expected color tokens", () => {
    expect(colors.primary[600]).toBe("#2563eb");
    expect(colors.gray[900]).toBe("#111827");
    expect(colors.error).toBe("#ef4444");
    expect(colors.theme.dark.background).toBe("#111827");
    expect(colors.theme.light.foreground).toBe("#111827");
  });

  it("exports spacing and typography scales", () => {
    expect(spacing.md).toBe("1rem");
    expect(typography.fontFamily.sans).toContain("system-ui");
    expect(typography.fontSize.lg).toBe("1.125rem");
  });
});
