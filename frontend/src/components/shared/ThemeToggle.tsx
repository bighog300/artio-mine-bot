import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme, type Theme } from "@/context/ThemeContext";

const options: Array<{ value: Theme; label: string; icon: LucideIcon }> = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="inline-flex items-center gap-1 rounded-md border border-border bg-card p-1">
      {options.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          aria-label={`Use ${label.toLowerCase()} theme`}
          aria-pressed={theme === value}
          onClick={() => setTheme(value)}
          className={cn(
            "inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium transition-colors",
            theme === value
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          )}
        >
          <Icon size={14} />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}
