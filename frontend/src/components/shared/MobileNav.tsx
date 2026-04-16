import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { cn } from "@/lib/utils";

interface NavItem {
  path: string;
  label: string;
}

const navItems: NavItem[] = [
  { path: "/", label: "Dashboard" },
  { path: "/sources", label: "Sources" },
  { path: "/pages", label: "Pages" },
  { path: "/jobs", label: "Jobs" },
  { path: "/queues", label: "Queues" },
  { path: "/workers", label: "Workers" },
  { path: "/backfill", label: "Backfill" },
  { path: "/records", label: "Records" },
  { path: "/admin-review", label: "Admin Review" },
  { path: "/duplicates", label: "Duplicates" },
  { path: "/semantic", label: "Semantic" },
  { path: "/audit", label: "Audit Trail" },
  { path: "/images", label: "Images" },
  { path: "/export", label: "Export" },
  { path: "/logs", label: "Logs" },
  { path: "/settings", label: "Settings" },
  { path: "/api-access", label: "API Access" },
  { path: "/mobile-test", label: "Mobile Test" },
];

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-50 h-14 border-b border-border bg-card lg:hidden">
        <div className="flex h-full items-center justify-between px-4">
          <h1 className="text-base font-semibold text-foreground">Artio Miner</h1>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => setIsOpen((open) => !open)}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 transition-colors hover:bg-accent"
              aria-label="Toggle menu"
              aria-expanded={isOpen}
            >
              {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </header>

      {isOpen ? <button type="button" className="fixed inset-0 top-14 z-40 bg-black/50 lg:hidden" aria-label="Close menu" onClick={() => setIsOpen(false)} /> : null}

      <nav
        className={cn(
          "fixed right-0 top-14 z-40 h-[calc(100vh-3.5rem)] w-72 border-l border-border bg-card transition-transform duration-200 lg:hidden",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex flex-col gap-2 overflow-y-auto p-4">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={cn(
                  "flex min-h-[48px] items-center rounded-lg px-4 py-3 text-sm font-medium transition-colors",
                  isActive ? "bg-primary/15 text-primary" : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
