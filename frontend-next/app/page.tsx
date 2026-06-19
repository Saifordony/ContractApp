"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, analyzeContractText, getToken, login, setToken } from "@/lib/api";
import type { GroundedAnalysis } from "@/lib/types";
import { AnalysisResult } from "@/components/AnalysisResult";
import { ContractChat } from "@/components/ContractChat";

const ANALYSIS_STEPS = [
  "Retrieving relevant clauses",
  "Grounding the answer in evidence",
  "Verifying citations & confidence",
];

function LoginPanel({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      onSuccess();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={submit} style={{ maxWidth: 380 }}>
      <h2 style={{ marginTop: 0 }}>Sign in</h2>
      {error && <div className="banner error">{error}</div>}
      <label htmlFor="u">Username</label>
      <input id="u" type="text" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
      <label htmlFor="p">Password</label>
      <input id="p" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
      <div style={{ marginTop: "1rem" }}>
        <button type="submit" disabled={busy || !username || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </div>
    </form>
  );
}

function AnalyzingSkeleton({ step }: { step: number }) {
  return (
    <div className="panel">
      <strong>Analyzing contract…</strong>
      <ul className="steps">
        {ANALYSIS_STEPS.map((label, i) => (
          <li key={label} className={i < step ? "done" : i === step ? "active" : ""}>
            {i < step ? "✓ " : i === step ? "• " : "  "}
            {label}
          </li>
        ))}
      </ul>
      <div className="skeleton" style={{ height: 18, width: "70%", margin: "1rem 0 0.6rem" }} />
      <div className="skeleton" style={{ height: 14, width: "95%", marginBottom: "0.4rem" }} />
      <div className="skeleton" style={{ height: 14, width: "88%" }} />
    </div>
  );
}

export default function Home() {
  const [authed, setAuthed] = useState(false);
  const [text, setText] = useState("");
  const [result, setResult] = useState<GroundedAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    setAuthed(Boolean(getToken()));
  }, []);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  function startStepper() {
    setStep(0);
    timers.current.forEach(clearTimeout);
    // Perceived-progress only; the real call resolves whenever the model does.
    timers.current = [
      setTimeout(() => setStep(1), 1200),
      setTimeout(() => setStep(2), 3200),
    ];
  }

  async function analyze() {
    setBusy(true);
    setError(null);
    setResult(null);
    startStepper();
    try {
      const data = await analyzeContractText(text);
      setResult(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setToken(null);
        setAuthed(false);
        setError("Your session expired. Please sign in again.");
      } else {
        setError(err instanceof ApiError ? err.message : "Analysis failed");
      }
    } finally {
      timers.current.forEach(clearTimeout);
      setBusy(false);
    }
  }

  const tooShort = text.trim().length < 100;

  return (
    <main className="container">
      <div className="brand">
        <div className="brand-mark">CI</div>
        <div>
          <div style={{ fontWeight: 700 }}>Contract Intelligence</div>
          <div className="subtle" style={{ fontSize: "0.8rem" }}>
            Evidence-grounded analysis — every claim cites the contract
          </div>
        </div>
      </div>

      {!authed ? (
        <div style={{ marginTop: "1.5rem" }}>
          <LoginPanel onSuccess={() => setAuthed(true)} />
        </div>
      ) : (
        <div style={{ marginTop: "1.5rem" }}>
          <div className="panel" style={{ marginBottom: "1.5rem" }}>
            <div className="row spread">
              <strong>Contract text</strong>
              <button
                className="secondary"
                onClick={() => {
                  setToken(null);
                  setAuthed(false);
                }}
              >
                Sign out
              </button>
            </div>
            <label htmlFor="contract">Paste the contract text to analyze</label>
            <textarea
              id="contract"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste the full contract text here…"
            />
            <div className="row spread" style={{ marginTop: "0.75rem" }}>
              <span className="subtle" style={{ fontSize: "0.8rem" }}>
                {tooShort ? "At least 100 characters needed to analyze." : `${text.trim().length} characters`}
              </span>
              <button onClick={analyze} disabled={busy || tooShort}>
                {busy ? "Analyzing…" : "Analyze contract"}
              </button>
            </div>
          </div>

          {error && <div className="banner error">{error}</div>}
          {busy && <AnalyzingSkeleton step={step} />}
          {!busy && result && (
            <>
              <AnalysisResult data={result} />
              <ContractChat contractText={text} analysis={result} />
            </>
          )}
        </div>
      )}
    </main>
  );
}
