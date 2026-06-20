"use client";

import { useRef, useState } from "react";
import { ApiError, chatWithContract } from "@/lib/api";
import type { ChatEvidence, ChatTurn, GroundedAnalysis } from "@/lib/types";

interface DisplayTurn extends ChatTurn {
  confidence?: string;
  evidence?: ChatEvidence[];
}

const STARTERS = [
  "What are the main risks?",
  "What should I fix before signing?",
  "Does this cover termination?",
];

function confidenceClass(confidence?: string): "high" | "medium" | "low" {
  const c = (confidence || "").toLowerCase();
  if (c === "high") return "high";
  if (c === "low") return "low";
  return "medium";
}

export function ContractChat({
  contractText,
  analysis,
  compact = false,
}: {
  contractText: string;
  analysis: GroundedAnalysis | null;
  compact?: boolean;
}) {
  const [turns, setTurns] = useState<DisplayTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const historyRef = useRef<ChatTurn[]>([]);

  async function send(question: string) {
    const message = question.trim();
    if (!message || busy) return;
    setError(null);
    setBusy(true);
    setInput("");
    const userTurn: DisplayTurn = { role: "user", content: message };
    setTurns((t) => [...t, userTurn]);

    try {
      const res = await chatWithContract({
        message,
        contractText,
        analysisResults: analysis ?? {},
        history: historyRef.current,
      });
      const assistantTurn: DisplayTurn = {
        role: "assistant",
        content: res.answer,
        confidence: res.confidence,
        evidence: res.evidence_snippets,
      };
      setTurns((t) => [...t, assistantTurn]);
      historyRef.current = [
        ...historyRef.current,
        { role: "user", content: message },
        { role: "assistant", content: res.answer },
      ];
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The assistant could not respond.");
      // Roll the optimistic user turn back out of the visible thread on failure.
      setTurns((t) => t.filter((x) => x !== userTurn));
      setInput(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={compact ? "chat-panel" : "panel chat-panel"}>
      <strong>Ask about this contract</strong>
      <p className="subtle" style={{ fontSize: "0.82rem", marginTop: "0.25rem" }}>
        Answers are grounded in the text above and cite the clauses they rely on.
      </p>

      {turns.length === 0 && (
        <div className="starter-row">
          {STARTERS.map((s) => (
            <button key={s} className="secondary" onClick={() => send(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="chat-messages">
        {turns.map((turn, i) => (
          <div key={i} className={`chat-turn ${turn.role}`}>
            <div
              style={{
                background: turn.role === "user" ? "var(--panel-2)" : "transparent",
                border: turn.role === "assistant" ? "1px solid var(--border)" : "none",
                borderRadius: 10,
                padding: turn.role === "assistant" ? "0.8rem" : "0.5rem 0.8rem",
                width: "100%",
              }}
            >
              {turn.role === "assistant" && (
                <div className="row spread" style={{ marginBottom: "0.4rem" }}>
                  <span className="subtle" style={{ fontSize: "0.75rem" }}>Assistant</span>
                  {turn.confidence && (
                    <span className={`badge ${confidenceClass(turn.confidence)}`}>
                      {turn.confidence} confidence
                    </span>
                  )}
                </div>
              )}
              <div>{turn.content}</div>
              {turn.evidence?.map((ev, j) => (
                <blockquote className="evidence" key={j}>
                  “{ev.quote}”
                  <cite>{ev.clause_name || ev.location || "Contract evidence"}</cite>
                </blockquote>
              ))}
            </div>
          </div>
        ))}
        {busy && <div className="subtle" style={{ fontSize: "0.85rem" }}>Thinking…</div>}
      </div>

      {error && <div className="banner error">{error}</div>}

      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send(input);
          }}
          placeholder="Ask a question about this contract…"
          style={{ flex: 1 }}
        />
        <button onClick={() => send(input)} disabled={busy || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
