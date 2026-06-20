"use client";

import { useState } from "react";

import { BenchmarkPanel } from "./BenchmarkPanel";
import { ChatPanel } from "./ChatPanel";
import { ClauseList } from "./ClauseList";
import { DegradedModeBanner } from "./DegradedModeBanner";
import { HealthScore } from "./HealthScore";
import { downloadExport } from "@/lib/api";
import { translator } from "@/lib/i18n";
import type { Citation, Evidence } from "@/lib/types";
import { useStore } from "@/store/useStore";

type Tab = "findings" | "chat" | "benchmark";
type Highlight = { char_start: number; char_end: number } | null;

function ProgressBar({ label }: { label: string }) {
  return (
    <div>
      <div className="h-1.5 w-full overflow-hidden rounded bg-slate-200 dark:bg-slate-800">
        <div className="h-full w-1/3 animate-pulse rounded bg-brand-500" />
      </div>
      {label && <p className="mt-1 text-xs text-slate-500">{label}</p>}
    </div>
  );
}

function ExportMenu({ contractId, disabled }: { contractId: string; disabled: boolean }) {
  const t = translator(useStore((s) => s.language));
  const go = (format: "pdf" | "csv" | "json") =>
    downloadExport(contractId, format, `analysis-${contractId}.${format}`).catch(() => {});
  return (
    <details className="relative">
      <summary className={`btn-ghost cursor-pointer list-none ${disabled ? "pointer-events-none opacity-50" : ""}`}>
        {t("export")}
      </summary>
      <div className="card absolute end-0 z-10 mt-1 w-40 p-1">
        <button className="block w-full rounded px-2 py-1 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => go("pdf")}>
          {t("exportPdf")}
        </button>
        <button className="block w-full rounded px-2 py-1 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => go("csv")}>
          {t("exportCsv")}
        </button>
        <button className="block w-full rounded px-2 py-1 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => go("json")}>
          {t("exportJson")}
        </button>
      </div>
    </details>
  );
}

export function IntelligencePanel({ onHighlight }: { onHighlight: (h: Highlight) => void }) {
  const language = useStore((s) => s.language);
  const t = translator(language);
  const contract = useStore((s) => s.activeContract);
  const analysis = useStore((s) => s.analysis);
  const analyzing = useStore((s) => s.analyzing);
  const streamStatus = useStore((s) => s.streamStatus);
  const runAnalysis = useStore((s) => s.runAnalysis);
  const [tab, setTab] = useState<Tab>("findings");

  if (!contract) return null;

  const tabs: { key: Tab; label: string }[] = [
    { key: "findings", label: t("findings") },
    { key: "chat", label: t("chat") },
    { key: "benchmark", label: t("benchmark") },
  ];

  return (
    <aside className="flex w-[26rem] flex-shrink-0 flex-col border-s border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950">
      <div className="space-y-3 border-b border-slate-200 p-3 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <button className="btn-primary flex-1" onClick={() => runAnalysis()} disabled={analyzing}>
            {analyzing ? t("analyzing") : analysis ? t("reAnalyze") : t("analyze")}
          </button>
          <ExportMenu contractId={contract.id} disabled={!analysis} />
        </div>
        {analyzing && <ProgressBar label={streamStatus} />}
        {analysis && <DegradedModeBanner show={analysis.degraded} />}
        {analysis && <HealthScore health={analysis.health} />}
      </div>

      <div className="flex border-b border-slate-200 text-sm dark:border-slate-800">
        {tabs.map((tabItem) => (
          <button
            key={tabItem.key}
            onClick={() => setTab(tabItem.key)}
            className={`flex-1 py-2 ${
              tab === tabItem.key
                ? "border-b-2 border-brand-500 font-medium text-brand-600"
                : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            }`}
          >
            {tabItem.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-hidden p-3">
        {tab === "findings" && (
          <div className="scrollbar-thin h-full overflow-y-auto">
            {analysis ? (
              <ClauseList clauses={analysis.clauses} onHighlight={(e: Evidence | null) => onHighlight(e)} />
            ) : (
              <p className="text-sm text-slate-400">{t("analyze")} →</p>
            )}
          </div>
        )}
        {tab === "chat" && <ChatPanel onHighlight={(c: Citation | null) => onHighlight(c)} />}
        {tab === "benchmark" && (
          <div className="scrollbar-thin h-full overflow-y-auto">
            <BenchmarkPanel onHighlight={(e: Evidence | null) => onHighlight(e)} />
          </div>
        )}
      </div>
    </aside>
  );
}
