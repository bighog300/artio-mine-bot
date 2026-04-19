import { NavLink, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { MobileNav } from "@/components/shared/MobileNav";
import { navSections } from "@/components/shared/navigation";

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();

  useEffect(() => {
    const titleByPath = [
      { path: /^\/$/, title: "Dashboard" },
      { path: /^\/sources$/, title: "Sources" },
      { path: /^\/sources\/[^/]+$/, title: "Source Details" },
      { path: /^\/sources\/[^/]+\/operations$/, title: "Source Operations" },
      { path: /^\/sources\/[^/]+\/mapping$/, title: "Source Mapping" },
      { path: /^\/pages$/, title: "Pages" },
      { path: /^\/jobs$/, title: "Jobs" },
      { path: /^\/jobs\/[^/]+$/, title: "Job Details" },
      { path: /^\/queues$/, title: "Queues" },
      { path: /^\/workers$/, title: "Workers" },
      { path: /^\/backfill$/, title: "Backfill" },
      { path: /^\/records$/, title: "Records" },
      { path: /^\/records\/[^/]+$/, title: "Record Details" },
      { path: /^\/admin-review$/, title: "Admin Review" },
      { path: /^\/duplicates$/, title: "Duplicate Resolution" },
      { path: /^\/semantic$/, title: "Semantic Explorer" },
      { path: /^\/audit$/, title: "Audit Trail" },
      { path: /^\/images$/, title: "Images" },
      { path: /^\/export$/, title: "Export" },
      { path: /^\/logs$/, title: "Logs" },
      { path: /^\/settings$/, title: "Settings" },
      { path: /^\/api-access$/, title: "API Access" },
      { path: /^\/mobile-test$/, title: "Mobile Test" },
    ];

    const matched = titleByPath.find(({ path }) => path.test(location.pathname));
    document.title = `${matched?.title ?? "App"} - Artio Mine Bot`;
  }, [location.pathname]);

  return (
    <div className="flex h-screen bg-background text-foreground transition-colors">
      <a
        href="#main-content"
        className="skip-link rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        Skip to main content
      </a>
      <aside className="hidden w-60 flex-col border-r border-border bg-card transition-colors lg:flex" aria-label="Sidebar navigation">
        <div className="border-b border-border p-4">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-lg font-bold text-foreground">Artio Miner</p>
              <p className="text-xs text-muted-foreground">v1.0.0</p>
            </div>
            <ThemeToggle />
          </div>
        </div>
        <nav className="flex-1 space-y-4 overflow-y-auto p-3" aria-label="Primary">
          {navSections.map((section) => (
            <div key={section.heading}>
              <h2 className="px-3 pb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground/80">{section.heading}</h2>
              <div className="space-y-1">
                {section.items.map(({ to, label, icon: Icon }) => (
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
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <MobileNav />

      <main id="main-content" tabIndex={-1} className="flex-1 overflow-auto pt-14 lg:pt-0">
        <div className="px-4 py-4 lg:p-6">{children}</div>
      </main>
    </div>
  );
}
