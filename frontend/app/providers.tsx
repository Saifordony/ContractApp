"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { setAuthFailureHandler } from "@/lib/api";
import { isRtl } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const theme = useStore((s) => s.theme);
  const language = useStore((s) => s.language);

  useEffect(() => {
    setAuthFailureHandler(() => router.replace("/login"));
  }, [router]);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.lang = language;
    root.dir = isRtl(language) ? "rtl" : "ltr";
  }, [theme, language]);

  return <>{children}</>;
}
