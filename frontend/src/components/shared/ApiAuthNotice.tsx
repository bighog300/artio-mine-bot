import { useEffect } from "react";
import { API_EVENTS } from "@/lib/api";
import { useToast } from "@/components/ui";

export function ApiAuthNotice() {
  const toast = useToast();

  useEffect(() => {
    const onAuthRequired = () => {
      toast.error("Admin authentication required", "Your admin token is missing or invalid.");
    };
    window.addEventListener(API_EVENTS.authRequired, onAuthRequired);
    return () => {
      window.removeEventListener(API_EVENTS.authRequired, onAuthRequired);
    };
  }, [toast]);

  return null;
}

