import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface ResponsiveGridProps {
  children: ReactNode;
  className?: string;
  cols?: {
    mobile?: 1 | 2 | 3 | 4;
    tablet?: 1 | 2 | 3 | 4;
    desktop?: 1 | 2 | 3 | 4;
  };
}

const mobileCols = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-3",
  4: "grid-cols-4",
} as const;

const tabletCols = {
  1: "md:grid-cols-1",
  2: "md:grid-cols-2",
  3: "md:grid-cols-3",
  4: "md:grid-cols-4",
} as const;

const desktopCols = {
  1: "lg:grid-cols-1",
  2: "lg:grid-cols-2",
  3: "lg:grid-cols-3",
  4: "lg:grid-cols-4",
} as const;

export function ResponsiveGrid({
  children,
  className,
  cols = { mobile: 1, tablet: 2, desktop: 3 },
}: ResponsiveGridProps) {
  const mobile = cols.mobile ?? 1;
  const tablet = cols.tablet ?? 2;
  const desktop = cols.desktop ?? 3;

  return <div className={cn("grid gap-4", mobileCols[mobile], tabletCols[tablet], desktopCols[desktop], className)}>{children}</div>;
}
