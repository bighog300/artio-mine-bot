import { useEffect, useState } from "react";

function getViewport() {
  if (typeof window === "undefined") {
    return { width: 0, height: 0 };
  }
  return { width: window.innerWidth, height: window.innerHeight };
}

export function useIsMobile(breakpoint: number = 768) {
  const [isMobile, setIsMobile] = useState(() => getViewport().width < breakpoint);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < breakpoint);

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, [breakpoint]);

  return isMobile;
}

export function useIsTouchDevice() {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return false;
  }
  return "ontouchstart" in window || navigator.maxTouchPoints > 0;
}

export function useViewport() {
  const [viewport, setViewport] = useState(getViewport);

  useEffect(() => {
    const handleResize = () => setViewport(getViewport());

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return viewport;
}
