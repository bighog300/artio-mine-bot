import {
  ActivitySquare,
  Compass,
  Database,
  FileText,
  GitMerge,
  Globe,
  History,
  Image,
  KeyRound,
  Layers3,
  LayoutDashboard,
  ListChecks,
  RefreshCw,
  SearchCheck,
  Settings,
  TerminalSquare,
  Upload,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

export interface NavSection {
  heading: string;
  items: NavItem[];
}

const baseNavSections: NavSection[] = [
  { heading: "Overview", items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }] },
  {
    heading: "Mining Pipeline",
    items: [
      { to: "/sources", label: "Sources", icon: Globe },
      { to: "/pages", label: "Pages", icon: FileText },
      { to: "/jobs", label: "Jobs", icon: ListChecks },
      { to: "/queues", label: "Queues", icon: Layers3 },
      { to: "/workers", label: "Workers", icon: ActivitySquare },
      { to: "/backfill", label: "Backfill", icon: RefreshCw },
    ],
  },
  {
    heading: "Data Review",
    items: [
      { to: "/records", label: "Records", icon: Database },
      { to: "/admin-review", label: "Admin Review", icon: SearchCheck },
      { to: "/duplicates", label: "Duplicates", icon: GitMerge },
      { to: "/semantic", label: "Semantic", icon: Compass },
      { to: "/audit", label: "Audit Trail", icon: History },
    ],
  },
  {
    heading: "Assets & Export",
    items: [
      { to: "/images", label: "Images", icon: Image },
      { to: "/export", label: "Export", icon: Upload },
      { to: "/logs", label: "Logs", icon: TerminalSquare },
    ],
  },
  {
    heading: "System",
    items: [
      { to: "/settings", label: "Settings", icon: Settings },
      { to: "/api-access", label: "API Access", icon: KeyRound },
      { to: "/mobile-test", label: "Mobile Test", icon: TerminalSquare },
    ],
  },
];

export const navSections: NavSection[] = baseNavSections.map((section) => ({
  ...section,
  items: section.items.filter((item) => item.to !== "/mobile-test" || import.meta.env.DEV),
}));
