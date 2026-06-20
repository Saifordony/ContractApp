"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { login } from "@/lib/api";
import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

export default function LoginPage() {
  const router = useRouter();
  const language = useStore((s) => s.language);
  const t = translator(language);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await login(username, password);
      useStore.setState({ user: res.user, language: res.user.preferences.language, theme: res.user.preferences.theme });
      router.replace("/workspace");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <h1 className="text-xl font-semibold">{t("login")}</h1>
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}
      <div>
        <label className="label">{t("username")}</label>
        <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
      </div>
      <div>
        <label className="label">{t("password")}</label>
        <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
      </div>
      <button className="btn-primary w-full" disabled={busy}>
        {busy ? t("loading") : t("login")}
      </button>
      <div className="flex items-center justify-between text-sm">
        <Link href="/reset-password" className="text-brand-600 hover:underline">
          {t("forgotPassword")}
        </Link>
        <span className="text-slate-500">
          {t("noAccount")}{" "}
          <Link href="/register" className="text-brand-600 hover:underline">
            {t("register")}
          </Link>
        </span>
      </div>
    </form>
  );
}
