"use client";

import { useEffect, useRef } from "react";

import { useStore } from "@/store/useStore";

export function ContractViewer({
  highlight,
}: {
  highlight: { char_start: number; char_end: number } | null;
}) {
  const contract = useStore((s) => s.activeContract);
  const markRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (highlight) markRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [highlight]);

  if (!contract) return null;
  const content = contract.content;

  let body: React.ReactNode = content;
  if (highlight && highlight.char_start >= 0 && highlight.char_end <= content.length && highlight.char_end > highlight.char_start) {
    body = (
      <>
        {content.slice(0, highlight.char_start)}
        <mark ref={markRef as any}>{content.slice(highlight.char_start, highlight.char_end)}</mark>
        {content.slice(highlight.char_end)}
      </>
    );
  }

  return (
    <section className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b border-slate-200 p-3 dark:border-slate-800">
        <h2 className="text-base font-semibold">{contract.title}</h2>
        <p className="text-xs text-slate-500">
          <span className="capitalize">{contract.contract_type.replace(/_/g, " ")}</span> · {contract.region} ·{" "}
          {contract.language.toUpperCase()}
          {contract.ocr_used ? " · OCR" : ""}
        </p>
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto p-4">
        <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed">{body}</pre>
      </div>
    </section>
  );
}
