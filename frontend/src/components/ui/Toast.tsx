import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { CheckCircle2, Loader2, OctagonX, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "loading";

interface ToastItem {
  id: string;
  title: string;
  description?: string;
  type: ToastType;
}

interface ToastContextValue {
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  loading: (title: string, description?: string) => string;
  dismiss: (id: string) => void;
  update: (id: string, type: ToastType, title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback((type: ToastType, title: string, description?: string) => {
    const id = crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    setToasts((prev) => [...prev, { id, type, title, description }]);
    if (type !== "loading") {
      window.setTimeout(() => dismiss(id), 3500);
    }
    return id;
  }, [dismiss]);

  const update = useCallback((id: string, type: ToastType, title: string, description?: string) => {
    setToasts((prev) => prev.map((toast) => (toast.id === id ? { ...toast, type, title, description } : toast)));
    if (type !== "loading") {
      window.setTimeout(() => dismiss(id), 3500);
    }
  }, [dismiss]);

  const value = useMemo<ToastContextValue>(
    () => ({
      success: (title, description) => {
        push("success", title, description);
      },
      error: (title, description) => {
        push("error", title, description);
      },
      loading: (title, description) => push("loading", title, description),
      dismiss,
      update,
    }),
    [dismiss, push, update],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-[100] space-y-2" aria-live="polite" aria-label="Notifications">
        {toasts.map((toast) => (
          <div key={toast.id} className={cn("pointer-events-auto flex w-80 gap-3 rounded-lg border px-3 py-2 shadow-md", toast.type === "success" && "border-emerald-300 bg-emerald-50 text-emerald-900", toast.type === "error" && "border-red-300 bg-red-50 text-red-900", toast.type === "loading" && "border-blue-300 bg-blue-50 text-blue-900")}>
            <div className="mt-0.5" aria-hidden="true">
              {toast.type === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {toast.type === "success" ? <CheckCircle2 className="h-4 w-4" /> : null}
              {toast.type === "error" ? <OctagonX className="h-4 w-4" /> : null}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{toast.title}</p>
              {toast.description ? <p className="text-xs opacity-80">{toast.description}</p> : null}
            </div>
            <button type="button" className="inline-flex h-5 w-5 items-center justify-center rounded hover:bg-black/5" onClick={() => dismiss(toast.id)} aria-label="Dismiss notification">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
}
