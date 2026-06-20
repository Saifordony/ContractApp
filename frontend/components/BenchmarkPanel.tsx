"use client";

import { ConfidenceBadge } from "./ConfidenceBadge";
import { DegradedModeBanner } from "./DegradedModeBanner";
import { translator } from "@/lib/i18n";
import type { Evidence } from "@/lib/types";
import { useStore } from "@/store/useStore";

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  low: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

export function BenchmarkPanel({ onHighlight }: { onHighlight: (e: Evidence | null) => void }) {
  const language = useStore((s) => s.language);
  const t = translator(language);
  const benchmark = useStore((s) => s.benchmark);
  const benchmarking = useStore((s) => s.benchmarking);
  const streamStatus = useStore((s) => s.streamStatus);
  const run = useStore((s) => s.runBenchmark);

  return (
    <div className="space-y-3">
      <button className="btn-primary w-full" onClick={() => run()} disabled={benchmarking}>
        {benchmarking ? streamStatus || t("loading") : t("runBenchmark")}
      </button>

      {benchmark && (
        <>
          <DegradedModeBanner show={benchmark.degraded} />
          <div className="card p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">{t("benchmark")}</span>
              <ConfidenceBadge value={benchmark.confidence} />
            </div>
            <div className="mt-1 text-3xl font-bold">
              {benchmark.overall_score}
              <span className="text-base font-normal text-slate-500"> / 100 · {benchmark.grade}</span>
            </div>
            <p className="text-xs text-slate-500">
              {benchmark.contract_type} · {benchmark.region}
            </p>
          </div>

          <h4 className="text-sm font-semibold">{t("gaps")}</h4>
          {benchmark.gaps.length === 0 && <p className="text-sm text-emerald-600">✓ No gaps vs. the benchmark.</p>}
          <ul className="space-y-2">
            {benchmark.gaps.map((g) => (
              <li key={g.clause_key} className="card p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium capitalize">{g.clause_key.replace(/_/g, " ")}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${SEVERITY_STYLES[g.severity] ?? SEVERITY_STYLES.low}`}>
                    {g.severity}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{t(("status_" + g.contract_status) as any)}</p>
                <p className="mt-1 text-sm">{g.recommendation}</p>
                {g.evidence?.[0] && (
                  <button
                    onClick={() => onHighlight(g.evidence[0])}
                    className="mt-2 block w-full rounded border-s-2 border-brand-400 bg-slate-50 p-1.5 text-start text-xs italic text-slate-600 hover:bg-brand-50 dark:bg-slate-800"
                  >
                    “{g.evidence[0].text.slice(0, 140)}…”
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
