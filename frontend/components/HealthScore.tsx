"use client";

import { ConfidenceBadge } from "./ConfidenceBadge";
import { translator } from "@/lib/i18n";
import type { Health } from "@/lib/types";
import { useStore } from "@/store/useStore";

export function HealthScore({ health }: { health: Health }) {
  const language = useStore((s) => s.language);
  const t = translator(language);
  const scoreColor =
    health.overall_score >= 80 ? "text-emerald-600" : health.overall_score >= 60 ? "text-amber-600" : "text-red-600";

  return (
    <div>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{t("healthScore")}</h3>
        <ConfidenceBadge value={health.confidence} />
      </div>
      <div className="mt-1 flex items-end gap-2">
        <span className={`text-4xl font-bold ${scoreColor}`}>{health.overall_score}</span>
        <span className="mb-1 text-sm text-slate-500">/ 100 · {health.grade}</span>
      </div>
      <div className="mt-3 space-y-2">
        {health.dimensions.map((d) => (
          <div key={d.key}>
            <div className="flex justify-between text-xs text-slate-600 dark:text-slate-300">
              <span>{d.label[language]}</span>
              <span>{d.score}</span>
            </div>
            {/* Bar width reflects the actual score (no fixed-width lie). */}
            <div className="mt-1 h-2 rounded bg-slate-200 dark:bg-slate-800">
              <div className="h-2 rounded bg-brand-500" style={{ width: `${Math.max(0, Math.min(100, d.score))}%` }} />
            </div>
            {d.explanation && <p className="mt-1 text-xs text-slate-500">{d.explanation}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
