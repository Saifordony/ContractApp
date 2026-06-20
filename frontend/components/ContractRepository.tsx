"use client";

import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

export function ContractRepository({ onNew }: { onNew: () => void }) {
  const language = useStore((s) => s.language);
  const t = translator(language);
  const contracts = useStore((s) => s.contracts);
  const activeId = useStore((s) => s.activeContractId);
  const select = useStore((s) => s.selectContract);
  const search = useStore((s) => s.search);
  const setSearch = useStore((s) => s.setSearch);

  return (
    <aside className="flex w-72 flex-shrink-0 flex-col border-e border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="space-y-2 p-3">
        <button className="btn-primary w-full" onClick={onNew}>
          + {t("newContract")}
        </button>
        <input
          className="input"
          placeholder={t("search")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto px-2 pb-3">
        {contracts.length === 0 && <p className="p-3 text-sm text-slate-400">{t("noContracts")}</p>}
        {contracts.map((c) => (
          <button
            key={c.id}
            onClick={() => select(c.id)}
            className={`mb-1 block w-full rounded-lg p-2 text-start transition ${
              activeId === c.id ? "bg-brand-50 dark:bg-brand-900/30" : "hover:bg-slate-50 dark:hover:bg-slate-800"
            }`}
          >
            <div className="truncate text-sm font-medium">{c.title}</div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="capitalize">{c.contract_type.replace(/_/g, " ")}</span>
              {c.status === "analyzed" && <span className="text-emerald-600">● analyzed</span>}
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
}
