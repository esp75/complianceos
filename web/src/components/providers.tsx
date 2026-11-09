"use client";

import { ThemeProvider } from "next-themes";
import { useEffect, type ReactNode } from "react";
import { recordUsage } from "@/lib/api";

export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    recordUsage("session_start");
    if (new URLSearchParams(window.location.search).get("from") === "alert") recordUsage("alert_opened");
  }, []);
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      {children}
    </ThemeProvider>
  );
}
