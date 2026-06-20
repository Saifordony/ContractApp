"use client";

import { useStore } from "@/store/useStore";

export function LanguageThemeToggle() {
  const language = useStore((s) => s.language);
  const theme = useStore((s) => s.theme);
  const setLanguage = useStore((s) => s.setLanguage);
  const setTheme = useStore((s) => s.setTheme);

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => setLanguage(language === "en" ? "ar" : "en")}
        className="btn-ghost px-2 py-1 text-xs"
        aria-label="Toggle language"
        title="EN / العربية"
      >
        {language === "en" ? "العربية" : "EN"}
      </button>
      <button
        type="button"
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        className="btn-ghost px-2 py-1 text-xs"
        aria-label="Toggle theme"
        title="Theme"
      >
        {theme === "dark" ? "☀" : "☾"}
      </button>
    </div>
  );
}
