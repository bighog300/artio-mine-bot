export type ControlCenterAction = {
  id: string;
  type: "drift" | "repair" | "source" | "crawl";
  title: string;
  description: string;
  impactSummary: string;
  severity: "critical" | "high" | "medium" | "low";
  confidence?: number;
  impactCount?: number;
  sourceId?: string;
  priorityScore: number;
  cta: {
    label: string;
    to: string;
  };
};
