import { NavLink } from "react-router-dom";
import { LayoutDashboard, Globe, Database, Image, Upload, FileText, Settings, TerminalSquare, GitMerge, SearchCheck, Compass, History, KeyRound, ListChecks, Layers3, RefreshCw, ActivitySquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/ThemeToggle";

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
];

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen bg-background text-foreground transition-colors">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col border-r border-border bg-card transition-colors">
        <div className="border-b border-border p-4">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h1 className="text-lg font-bold text-foreground">Artio Miner</h1>
              <p className="text-xs text-muted-foreground">v1.0.0</p>
            </div>
            <ThemeToggle />
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
