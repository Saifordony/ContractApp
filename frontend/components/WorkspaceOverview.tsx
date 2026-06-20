"use client";

import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="card p-3">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

export function WorkspaceOverview() {
  const language = useStore((s) => s.language);
  const t = translator(language);
  const stats = useStore((s) => s.stats);
  const select = useStore((s) => s.selectContract);

  return (
    <section className="scrollbar-thin flex-1 overflow-y-auto p-6">
      <h2 className="text-lg font-semibold">{t("overview")}</h2>
      <p className="text-sm text-slate-500">{t("selectContract")}</p>

      {stats && (
        <div className="mt-4 space-y-6">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label={t("contracts")} value={stats.contracts_total} />
            <Stat label={t("avgHealth")} value={stats.avg_health_score ?? "—"} />
            <Stat label={t("outstandingReviews")} value={stats.outstanding_reviews} />
            <Stat label={t("clients")} value={stats.clients_total} />
          </div>

          {stats.high_risk.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-red-600">{t("highRisk")}</h3>
              <ul className="space-y-1">
                {stats.high_risk.map((h) => (
                  <li key={h.contract_id}>
                    <button
                      onClick={() => select(h.contract_id)}
                      className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-start text-sm hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
                    >
                      <span className="truncate">{h.title || "Untitled"}</span>
                      <span className="font-semibold text-red-600">{h.score}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {stats.recent_findings.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">{t("recentFindings")}</h3>
              <ul className="space-y-1">
                {stats.recent_findings.map((f) => (
                  <li key={f.contract_id}>
                    <button
                      onClick={() => select(f.contract_id)}
                      className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-start text-sm hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
                    >
                      <span className="truncate">
                        {f.title || "Untitled"}
                        {f.degraded && <span className="ms-2 text-xs text-amber-600">⚠ degraded</span>}
                      </span>
                      <span className="flex items-center gap-2 text-xs text-slate-500">
                        {f.needs_review > 0 && <span className="text-orange-600">{f.needs_review} review</span>}
                        <span className="font-semibold">{f.overall_score ?? "—"}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
