"use client";

import { useRouter } from "next/navigation";

import { LanguageThemeToggle } from "./LanguageThemeToggle";
import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

export function Topbar() {
  const router = useRouter();
  const language = useStore((s) => s.language);
  const t = translator(language);
  const user = useStore((s) => s.user);
  const logout = useStore((s) => s.logout);

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2 dark:border-slate-800 dark:bg-slate-900">
      <span className="text-lg font-semibold text-brand-600">{t("appName")}</span>
      <div className="flex items-center gap-3">
        <LanguageThemeToggle />
        <span className="hidden text-sm text-slate-500 sm:inline">{user?.full_name || user?.username}</span>
        <button
          className="btn-ghost px-2 py-1 text-xs"
          onClick={async () => {
            await logout();
            router.replace("/login");
          }}
        >
          {t("logout")}
        </button>
      </div>
    </header>
  );
}
