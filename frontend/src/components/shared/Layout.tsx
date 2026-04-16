import { NavLink } from "react-router-dom";
import { LayoutDashboard, Globe, Database, Image, Upload, FileText, Settings, TerminalSquare, GitMerge, SearchCheck, Compass, History, KeyRound, ListChecks, Layers3, RefreshCw, ActivitySquare } from "lucide-react";
import { cn } from "@/lib/utils";

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
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-lg font-bold text-gray-900">Artio Miner</h1>
          <p className="text-xs text-gray-500">v1.0.0</p>
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
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
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
