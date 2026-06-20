"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { register } from "@/lib/api";
import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

export default function RegisterPage() {
  const router = useRouter();
  const language = useStore((s) => s.language);
  const t = translator(language);
  const [form, setForm] = useState({ username: "", email: "", password: "", full_name: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const update = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await register({
        username: form.username,
        email: form.email,
        password: form.password,
        full_name: form.full_name || undefined,
      });
      useStore.setState({ user: res.user });
      router.replace("/workspace");
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <h1 className="text-xl font-semibold">{t("register")}</h1>
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}
      <div>
        <label className="label">{t("fullName")}</label>
        <input className="input" value={form.full_name} onChange={update("full_name")} />
      </div>
      <div>
        <label className="label">{t("username")}</label>
        <input className="input" value={form.username} onChange={update("username")} required minLength={3} />
      </div>
      <div>
        <label className="label">{t("email")}</label>
        <input className="input" type="email" value={form.email} onChange={update("email")} required />
      </div>
      <div>
        <label className="label">{t("password")}</label>
        <input className="input" type="password" value={form.password} onChange={update("password")} required minLength={8} />
      </div>
      <button className="btn-primary w-full" disabled={busy}>
        {busy ? t("loading") : t("register")}
      </button>
      <p className="text-center text-sm text-slate-500">
        {t("haveAccount")}{" "}
        <Link href="/login" className="text-brand-600 hover:underline">
          {t("login")}
        </Link>
      </p>
    </form>
  );
}
