"use client";

import { ConfidenceBadge } from "./ConfidenceBadge";
import { translator } from "@/lib/i18n";
import type { Clause, Evidence } from "@/lib/types";
import { useStore } from "@/store/useStore";

const STATUS_STYLES: Record<string, string> = {
  found: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  partially_found: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  needs_review: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300",
  not_found: "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

export function ClauseList({
  clauses,
  onHighlight,
}: {
  clauses: Clause[];
  onHighlight: (e: Evidence | null) => void;
}) {
  const language = useStore((s) => s.language);
  const t = translator(language);

  return (
    <ul className="space-y-3">
      {clauses.map((c) => (
        <li key={c.key} className="card p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium">{c.label[language]}</span>
            <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[c.status]}`}>
              {t(("status_" + c.status) as any)}
            </span>
          </div>
          <div className="mt-1">
            <ConfidenceBadge value={c.confidence} />
          </div>
          {c.explanation && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{c.explanation}</p>}
          {c.evidence.length > 0 && (
            <button
              onClick={() => onHighlight(c.evidence[0])}
              className="mt-2 block w-full rounded border-s-2 border-brand-400 bg-slate-50 p-2 text-start text-xs italic text-slate-600 hover:bg-brand-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              title={t("evidence")}
            >
              “{c.evidence[0].text.slice(0, 200)}
              {c.evidence[0].text.length > 200 ? "…" : ""}”
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
