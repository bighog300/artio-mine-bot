import { NavLink } from "react-router-dom";
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { MobileNav } from "@/components/shared/MobileNav";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/sources", label: "Sources", icon: Globe },
  { to: "/pages", label: "Pages", icon: FileText },
  { to: "/jobs", label: "Jobs", icon: ListChecks },
  { to: "/queues", label: "Queues", icon: Layers3 },
  { to: "/workers", label: "Workers", icon: ActivitySquare },
  { to: "/backfill", label: "Backfill", icon: RefreshCw },
  { to: "/records", label: "Records", icon: Database },
  { to: "/admin-review", label: "Admin Review", icon: SearchCheck },
  { to: "/duplicates", label: "Duplicates", icon: GitMerge },
  { to: "/semantic", label: "Semantic", icon: Compass },
  { to: "/audit", label: "Audit Trail", icon: History },
  { to: "/images", label: "Images", icon: Image },
  { to: "/export", label: "Export", icon: Upload },
  { to: "/logs", label: "Logs", icon: TerminalSquare },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/api-access", label: "API Access", icon: KeyRound },
  { to: "/mobile-test", label: "Mobile Test", icon: TerminalSquare },
];

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen bg-background text-foreground transition-colors">
      <aside className="hidden w-56 flex-col border-r border-border bg-card transition-colors lg:flex">
        <div className="border-b border-border p-4">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h1 className="text-lg font-bold text-foreground">Artio Miner</h1>
              <p className="text-xs text-muted-foreground">v1.0.0</p>
            </div>
            <ThemeToggle />
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex min-h-[44px] items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-primary/15 text-primary" : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <MobileNav />

      <main className="flex-1 overflow-auto pt-14 lg:pt-0">
        <div className="px-4 py-4 lg:p-6">{children}</div>
      </main>
    </div>
  );
}
