"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { confirmPasswordReset, requestPasswordReset } from "@/lib/api";
import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

export default function ResetPasswordPage() {
  const router = useRouter();
  const language = useStore((s) => s.language);
  const t = translator(language);
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function requestReset(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await requestPasswordReset(email);
      setInfo(t("emailSentIfExists"));
      // In dev/no-mail mode the backend returns the token so the flow can complete.
      if (res.reset_token) setToken(res.reset_token);
    } catch (err: any) {
      setError(err.message || "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function confirm(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await confirmPasswordReset(token, newPassword);
      router.replace("/login");
    } catch (err: any) {
      setError(err.message || "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">{t("resetPassword")}</h1>
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}
      {info && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">{info}</p>}

      <form onSubmit={requestReset} className="space-y-3">
        <div>
          <label className="label">{t("email")}</label>
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <button className="btn-ghost w-full" disabled={busy}>
          {t("resetPassword")}
        </button>
      </form>

      <form onSubmit={confirm} className="space-y-3 border-t border-slate-200 pt-4 dark:border-slate-800">
        <div>
          <label className="label">Reset token</label>
          <input className="input" value={token} onChange={(e) => setToken(e.target.value)} required />
        </div>
        <div>
          <label className="label">{t("newPassword")}</label>
          <input className="input" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} />
        </div>
        <button className="btn-primary w-full" disabled={busy || !token}>
          {t("newPassword")}
        </button>
      </form>

      <Link href="/login" className="block text-center text-sm text-brand-600 hover:underline">
        {t("backToLogin")}
      </Link>
    </div>
  );
}
