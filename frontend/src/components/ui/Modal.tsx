import { useEffect, useId, useRef } from "react";
import type { HTMLAttributes, ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEscapeKey } from "@/hooks/useKeyboard";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
}

export function Modal({ open, onClose, title, children, size = "md" }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const headingId = useId();

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "unset";
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [open]);

  useEscapeKey(onClose, open);

  useEffect(() => {
    if (!open || !dialogRef.current) {
      return undefined;
    }

    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    dialog.focus();

    const trapFocus = (event: KeyboardEvent) => {
      if (event.key !== "Tab") {
        return;
      }

      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          "a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex='-1'])",
        ),
      ).filter((element) => !element.hasAttribute("aria-hidden"));

      if (focusable.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    dialog.addEventListener("keydown", trapFocus);
    return () => {
      dialog.removeEventListener("keydown", trapFocus);
      previousFocusRef.current?.focus();
    };
  }, [open]);

  if (!open) {
    return null;
  }

  const sizeStyles = {
    sm: "max-w-md",
    md: "max-w-lg",
    lg: "max-w-2xl",
    xl: "max-w-4xl",
  } as const;

  return (
    <>
      <button type="button" className="fixed inset-0 z-40 bg-black/50" onClick={onClose} aria-label="Close modal" />

      <div className="fixed inset-0 z-50 flex items-end justify-center p-0 lg:items-center lg:p-4">
        <div
          ref={dialogRef}
          className={cn(
            "max-h-[90vh] w-full overflow-hidden bg-background shadow-xl lg:max-h-[85vh] lg:w-auto",
            "rounded-t-2xl lg:rounded-lg",
            sizeStyles[size],
          )}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? headingId : undefined}
          tabIndex={-1}
        >
          {title ? (
            <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-4 py-4 lg:px-6">
              <h2 id={headingId} className="text-lg font-semibold text-foreground">{title}</h2>
              <button
                type="button"
                onClick={onClose}
                className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 transition-colors hover:bg-muted"
                aria-label="Close"
              >
                <X className="h-5 w-5 text-muted-foreground" />
              </button>
            </div>
          ) : null}

          <div className="overflow-auto">{children}</div>
        </div>
      </div>
    </>
  );
}

export function ModalContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-4 py-4 lg:px-6", className)} {...props}>
      {children}
    </div>
  );
}

export function ModalFooter({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("sticky bottom-0 flex flex-col-reverse gap-3 border-t bg-muted/40 px-4 py-4 lg:flex-row lg:justify-end lg:px-6", className)} {...props}>
      {children}
    </div>
  );
}
