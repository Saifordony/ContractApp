"use client";

import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

export function ConfidenceBadge({ value }: { value: number }) {
  const t = translator(useStore((s) => s.language));
  const pct = Math.round((value ?? 0) * 100);
  const tone =
    value >= 0.75
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
      : value >= 0.5
        ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
        : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tone}`} title={t("confidence")}>
      {t("confidence")}: {pct}%
    </span>
  );
}
