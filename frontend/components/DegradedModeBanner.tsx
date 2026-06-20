"use client";

import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

export function DegradedModeBanner({ show }: { show: boolean }) {
  const t = translator(useStore((s) => s.language));
  if (!show) return null;
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-700 dark:bg-amber-950/60">
      <p className="font-semibold text-amber-800 dark:text-amber-300">⚠ {t("degradedTitle")}</p>
      <p className="mt-1 text-amber-700 dark:text-amber-200/80">{t("degradedBody")}</p>
    </div>
  );
}
