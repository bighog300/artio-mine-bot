import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { navSections } from "@/components/shared/navigation";
import { cn } from "@/lib/utils";

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-50 h-14 border-b border-border bg-card lg:hidden">
        <div className="flex h-full items-center justify-between px-4">
          <p className="text-base font-semibold text-foreground">Artio Miner</p>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => setIsOpen((open) => !open)}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 transition-colors hover:bg-accent"
              aria-label="Toggle menu"
              aria-expanded={isOpen}
              aria-controls="mobile-primary-nav"
            >
              {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </header>

      {isOpen ? <button type="button" className="fixed inset-0 top-14 z-40 bg-black/50 lg:hidden" aria-label="Close menu" onClick={() => setIsOpen(false)} /> : null}

      <nav
        id="mobile-primary-nav"
        aria-label="Mobile primary"
        className={cn(
          "fixed right-0 top-14 z-40 h-[calc(100vh-3.5rem)] w-72 border-l border-border bg-card transition-transform duration-200 lg:hidden",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex flex-col gap-4 overflow-y-auto p-4">
          {navSections.map((section) => (
            <div key={section.heading} className="space-y-1">
              <h2 className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground/80">{section.heading}</h2>
              {section.items.map((item) => {
                const isActive = location.pathname === item.to || (item.to !== "/" && location.pathname.startsWith(item.to));
                return (
                  <Link
                    key={item.to}
                    to={item.to}
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
          ))}
        </div>
      </nav>
    </>
  );
}
