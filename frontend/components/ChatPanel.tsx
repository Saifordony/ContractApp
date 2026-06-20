"use client";

import { useEffect, useRef, useState } from "react";

import { ConfidenceBadge } from "./ConfidenceBadge";
import { translator } from "@/lib/i18n";
import type { Citation } from "@/lib/types";
import { useStore } from "@/store/useStore";

export function ChatPanel({ onHighlight }: { onHighlight: (c: Citation | null) => void }) {
  const language = useStore((s) => s.language);
  const t = translator(language);
  const chat = useStore((s) => s.chat);
  const chatting = useStore((s) => s.chatting);
  const sendChat = useStore((s) => s.sendChat);
  const [question, setQuestion] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || chatting) return;
    void sendChat(question);
    setQuestion("");
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto scrollbar-thin pe-1">
        {chat.length === 0 && <p className="text-sm text-slate-400">{t("askQuestion")}</p>}
        {chat.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-end" : ""}>
            <div
              className={`inline-block max-w-[90%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                m.role === "user" ? "bg-brand-600 text-white" : "bg-slate-100 dark:bg-slate-800"
              }`}
            >
              {m.content || (m.streaming ? "…" : "")}
            </div>
            {m.role === "assistant" && !m.streaming && (
              <div className="mt-1 space-y-1">
                {m.degraded && <p className="text-xs font-medium text-amber-600">⚠ {t("degradedTitle")}</p>}
                {m.confidence != null && <ConfidenceBadge value={m.confidence} />}
                {m.citations?.map((c, ci) => (
                  <button
                    key={ci}
                    onClick={() => onHighlight(c)}
                    className="block w-full rounded border-s-2 border-brand-400 bg-slate-50 p-1.5 text-start text-xs italic text-slate-600 hover:bg-brand-50 dark:bg-slate-800 dark:text-slate-300"
                  >
                    “{c.text.slice(0, 160)}
                    {c.text.length > 160 ? "…" : ""}”
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form onSubmit={submit} className="mt-2 flex gap-2">
        <input
          className="input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("askQuestion")}
          disabled={chatting}
        />
        <button className="btn-primary" disabled={chatting || !question.trim()}>
          {t("send")}
        </button>
      </form>
    </div>
  );
}
