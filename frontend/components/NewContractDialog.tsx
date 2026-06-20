"use client";

import { useState } from "react";

import { translator } from "@/lib/i18n";
import { useStore } from "@/store/useStore";

const CONTRACT_TYPES = ["general", "nda", "service_agreement", "employment", "lease", "sales", "license", "partnership"];
const REGIONS = ["US", "EU", "UK", "UAE", "KSA", "Other"];

export function NewContractDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const language = useStore((s) => s.language);
  const t = translator(language);
  const createText = useStore((s) => s.createTextContract);
  const upload = useStore((s) => s.uploadContract);

  const [mode, setMode] = useState<"paste" | "upload">("paste");
  const [form, setForm] = useState({ title: "", contract_type: "general", region: "US", content: "" });
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "paste") {
        await createText({
          title: form.title || "Untitled contract",
          contract_type: form.contract_type,
          region: form.region,
          content: form.content,
        });
      } else {
        if (!file) {
          setError("Choose a file to upload.");
          setBusy(false);
          return;
        }
        await upload(file, { title: form.title, contract_type: form.contract_type, region: form.region });
      }
      setForm({ title: "", contract_type: "general", region: "US", content: "" });
      setFile(null);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to create contract");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-black/40 p-4" onClick={onClose}>
      <div className="card w-full max-w-lg p-5" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{t("newContract")}</h2>
          <div className="flex gap-1 text-sm">
            <button className={`rounded px-2 py-1 ${mode === "paste" ? "bg-brand-100 text-brand-700 dark:bg-brand-900/40" : ""}`} onClick={() => setMode("paste")}>
              {t("pasteText")}
            </button>
            <button className={`rounded px-2 py-1 ${mode === "upload" ? "bg-brand-100 text-brand-700 dark:bg-brand-900/40" : ""}`} onClick={() => setMode("upload")}>
              {t("upload")}
            </button>
          </div>
        </div>

        {error && <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}

        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="label">{t("title")}</label>
            <input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">{t("type")}</label>
              <select className="input" value={form.contract_type} onChange={(e) => setForm({ ...form, contract_type: e.target.value })}>
                {CONTRACT_TYPES.map((ct) => (
                  <option key={ct} value={ct}>
                    {ct.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">{t("region")}</label>
              <select className="input" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })}>
                {REGIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {mode === "paste" ? (
            <div>
              <label className="label">{t("content")}</label>
              <textarea
                className="input min-h-[160px]"
                value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })}
                required
              />
            </div>
          ) : (
            <div>
              <label className="label">PDF / DOCX / TXT</label>
              <input className="input" type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={onClose}>
              {t("cancel")}
            </button>
            <button className="btn-primary" disabled={busy}>
              {busy ? t("loading") : t("create")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
