"use client";

import { LanguageThemeToggle } from "@/components/LanguageThemeToggle";
import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const language = useStore((s) => s.language);
  const t = translator(language);
  return (
    <div className="grid min-h-screen place-items-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-lg font-semibold text-brand-600">{t("appName")}</span>
          <LanguageThemeToggle />
        </div>
        <div className="card p-6">{children}</div>
      </div>
    </div>
  );
}
