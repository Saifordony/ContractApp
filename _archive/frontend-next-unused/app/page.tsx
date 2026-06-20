"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, analyzeContractText, getToken, setToken } from "@/lib/api";
import type { GroundedAnalysis } from "@/lib/types";
import { ContractChat } from "@/components/ContractChat";
import { LoginScreen } from "@/components/auth/AuthScreens";

type ContractRecord = {
  id: string;
  name: string;
  counterparty: string;
  status: "Needs review" | "In review" | "Ready";
  risk: "Low" | "Medium" | "High" | "Critical";
  updated: string;
  tags: string[];
  text: string;
};

type ClauseHit = { name: string; pattern: RegExp; summary: string; severity: ContractRecord["risk"] };

const SAMPLE_CONTRACT = `MASTER SERVICES AGREEMENT

This Master Services Agreement is entered into by Acme Robotics, Inc. and Northstar Supply LLC. Northstar will provide logistics, warehousing, and procurement services for an initial term of twelve months beginning July 1, 2026.

Fees are payable net 45 days from receipt of invoice. Late payments accrue interest at 1.5% per month. Either party may terminate for uncured material breach after thirty days written notice. Northstar may terminate for convenience upon sixty days notice.

Each party will keep confidential information secret for three years after termination. Liability is capped at fees paid in the prior three months, except for confidentiality breaches and payment obligations. The agreement does not include an indemnity for third-party intellectual property claims.

The agreement automatically renews for successive one-year terms unless either party gives notice at least ninety days before the end of the then-current term. Disputes will be resolved by binding arbitration in New York, and New York law governs.`;

const CLAUSE_MAP: ClauseHit[] = [
  { name: "Termination", pattern: /terminat(e|ion)|material breach|convenience/i, summary: "Exit rights, cure periods, and convenience termination.", severity: "Medium" },
  { name: "Liability", pattern: /liabilit|cap|damages|limitation/i, summary: "Caps, exclusions, and uncapped exposure.", severity: "High" },
  { name: "Confidentiality", pattern: /confidential|non-disclosure|secret/i, summary: "Protection period and handling of sensitive information.", severity: "Medium" },
  { name: "Payment", pattern: /payment|invoice|fees|net \d+|late/i, summary: "Fees, due dates, and late-payment mechanics.", severity: "Low" },
  { name: "Renewal", pattern: /renew|extension|successive/i, summary: "Auto-renewal and notice window.", severity: "High" },
  { name: "IP", pattern: /intellectual property|work product|ip |copyright|patent/i, summary: "Ownership and third-party IP protection.", severity: "High" },
  { name: "Governing law", pattern: /governing law|law governs|jurisdiction/i, summary: "Applicable law and forum assumptions.", severity: "Low" },
  { name: "Dispute resolution", pattern: /dispute|arbitration|mediation|court/i, summary: "Escalation path and binding forum.", severity: "Medium" },
];

const DEFAULT_CONTRACTS: ContractRecord[] = [
  { id: "msa-northstar", name: "Northstar MSA", counterparty: "Northstar Supply LLC", status: "Needs review", risk: "High", updated: "Today", tags: ["MSA", "Operations"], text: SAMPLE_CONTRACT },
  { id: "dpa-aurelia", name: "Aurelia DPA", counterparty: "Aurelia Cloud", status: "In review", risk: "Medium", updated: "Yesterday", tags: ["Privacy", "DPA"], text: "Data Processing Addendum with confidentiality, subprocessors, security controls, audit rights, and termination assistance." },
  { id: "sow-q3", name: "Q3 Implementation SOW", counterparty: "Brightline Systems", status: "Ready", risk: "Low", updated: "Jun 12", tags: ["SOW", "Services"], text: "Statement of work covering deliverables, milestones, fees, acceptance criteria, and payment terms." },
];

function getHits(text: string) {
  return CLAUSE_MAP.map((c) => ({ ...c, found: c.pattern.test(text), excerpt: text.split(/\n+/).find((p) => c.pattern.test(p))?.trim() ?? "Not found in current text." }));
}

function riskScore(risk: ContractRecord["risk"]) { return { Low: 22, Medium: 48, High: 76, Critical: 94 }[risk]; }

export default function Home() {
  const [authed, setAuthed] = useState(false);
  const [activeId, setActiveId] = useState(DEFAULT_CONTRACTS[0].id);
  const [contracts, setContracts] = useState(DEFAULT_CONTRACTS);
  const [text, setText] = useState(SAMPLE_CONTRACT);
  const [result, setResult] = useState<GroundedAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => setAuthed(Boolean(getToken())), []);
  const active = contracts.find((c) => c.id === activeId) ?? contracts[0];
  const hits = useMemo(() => getHits(text), [text]);
  const found = hits.filter((h) => h.found);
  const missing = hits.filter((h) => !h.found);

  async function analyze(nextText = text) {
    setBusy(true); setError(null);
    try { setResult(await analyzeContractText(nextText)); }
    catch (err) {
      if (err instanceof ApiError && err.status === 401) { setToken(null); setAuthed(false); setError("Your session expired. Please sign in again."); }
      else setError(err instanceof ApiError ? err.message : "Analysis failed");
    } finally { setBusy(false); }
  }

  function selectContract(contract: ContractRecord) { setActiveId(contract.id); setText(contract.text); setResult(null); }
  async function upload(file: File) {
    const uploadedText = await file.text();
    const contract: ContractRecord = { id: `${Date.now()}`, name: file.name.replace(/\.[^.]+$/, ""), counterparty: "New counterparty", status: "Needs review", risk: "High", updated: "Just now", tags: ["Uploaded"], text: uploadedText };
    setContracts((all) => [contract, ...all]); selectContract(contract); await analyze(uploadedText);
  }

  if (!authed) return <LoginScreen onSuccess={() => setAuthed(true)} />;

  return (
    <main className="app-shell">
      <nav className="topbar">
        <div className="brand"><div className="brand-mark">CI</div><div><strong>Contract Intelligence</strong><span>Evidence-first legal AI</span></div></div>
        <div className="nav-links"><a>Contracts</a><a>Review Workspace</a><a>Reports</a><a>Settings</a></div>
        <button className="ghost" onClick={() => { setToken(null); setAuthed(false); }}>Sign out</button>
      </nav>

      <section className="overview">
        <div><p className="eyebrow">Workspace overview</p><h1>Contracts requiring attention</h1><p className="muted">No vanity metrics — only active reviews, high-risk terms, recent findings, and outstanding actions.</p></div>
        <div className="action-row"><button className="primary" onClick={() => fileRef.current?.click()}>Upload contract</button><button className="secondary" onClick={() => analyze()}>Run AI review</button><input ref={fileRef} type="file" accept=".txt,.md" hidden onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} /></div>
      </section>

      {error && <div className="banner error">{error}</div>}

      <section className="workspace">
        <aside className="left-rail panel">
          <div className="rail-head"><strong>Contracts</strong><span>{contracts.length}</span></div>
          <input className="search" placeholder="Search contracts, tags, parties…" />
          <div className="contract-list">{contracts.map((c) => <button key={c.id} className={`contract-item ${c.id === activeId ? "active" : ""}`} onClick={() => selectContract(c)}><span><b>{c.name}</b><small>{c.counterparty}</small></span><i className={`risk ${c.risk.toLowerCase()}`}>{c.risk}</i></button>)}</div>
          <div className="activity"><strong>Recent AI findings</strong><p>Auto-renewal notice window found.</p><p>Liability cap may be unusually narrow.</p><p>IP indemnity appears missing.</p></div>
        </aside>

        <section className="document panel">
          <div className="doc-toolbar"><div><p className="eyebrow">Review Workspace</p><h2>{active.name}</h2><span className="muted">{active.counterparty} · Updated {active.updated}</span></div><div className="score"><span>Risk score</span><b>{riskScore(active.risk)}</b></div></div>
          <textarea className="doc-viewer" value={text} onChange={(e) => { setText(e.target.value); setResult(null); }} />
          <div className="clause-strip">{hits.map((h) => <a key={h.name} className={h.found ? "found" : "missing"}>{h.name}</a>)}</div>
          <div className="inline-findings">{found.slice(0, 3).map((h) => <article key={h.name}><span className={`dot ${h.severity.toLowerCase()}`} /><div><strong>{h.name}</strong><p>{h.summary}</p><blockquote>{h.excerpt}</blockquote></div></article>)}</div>
        </section>

        <aside className="right-panel panel">
          <div className="panel-head"><p className="eyebrow">AI Intelligence</p><h3>Legal analyst panel</h3></div>
          {busy && <div className="thinking">Retrieving clauses, ranking evidence, verifying citations…</div>}
          {result?.degraded_mode && <div className="banner degraded">Model unavailable: showing deterministic, source-grounded fallback.</div>}
          <div className="insight-card"><strong>Executive summary</strong><p>{result?.sections.summary?.answer || "Run AI review to generate a cited executive summary."}</p></div>
          <div className="insight-card"><strong>Risk assessment</strong><p>{result?.sections.risks?.answer || `${found.length} key clause families detected; ${missing.length} require confirmation.`}</p></div>
          <div className="risk-list">{missing.slice(0, 3).map((m) => <div key={m.name}><b>Missing protection</b><span>{m.name}: confirm whether this is intentionally omitted.</span></div>)}</div>
          <ContractChat contractText={text} analysis={result} compact />
        </aside>
      </section>

      <section className="reports panel"><div><p className="eyebrow">Reports</p><h2>Decision-ready exports</h2><p className="muted">Executive report, risk report, clause analysis, and review summary are structured for counsel, operators, and leadership.</p></div><div className="report-grid"><button>Executive Markdown</button><button>Risk PDF</button><button>Clause report</button><button>Review summary</button></div></section>
    </main>
  );
}
