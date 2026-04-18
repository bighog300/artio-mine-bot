import { useEffect } from "react";

export function useKeyboard(key: string, handler: (event: KeyboardEvent) => void, enabled = true) {
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === key) {
        handler(event);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [enabled, handler, key]);
}

export function useEscapeKey(handler: () => void, enabled = true) {
  useKeyboard("Escape", () => handler(), enabled);
}
