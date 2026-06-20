"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ContractRepository } from "@/components/ContractRepository";
import { ContractViewer } from "@/components/ContractViewer";
import { IntelligencePanel } from "@/components/IntelligencePanel";
import { NewContractDialog } from "@/components/NewContractDialog";
import { Topbar } from "@/components/Topbar";
import { WorkspaceOverview } from "@/components/WorkspaceOverview";
import { isAuthenticated } from "@/lib/api";
import { useStore } from "@/store/useStore";

type Highlight = { char_start: number; char_end: number } | null;

export default function WorkspacePage() {
  const router = useRouter();
  const hydrated = useStore((s) => s.hydrated);
  const bootstrap = useStore((s) => s.bootstrap);
  const activeContract = useStore((s) => s.activeContract);
  const activeId = useStore((s) => s.activeContractId);
  const error = useStore((s) => s.error);
  const setError = useStore((s) => s.setError);

  const [highlight, setHighlight] = useState<Highlight>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Clearing the highlight when switching contracts keeps panes in sync.
  useEffect(() => {
    setHighlight(null);
  }, [activeId]);

  if (!hydrated) {
    return <div className="grid min-h-screen place-items-center text-slate-400">Loading…</div>;
  }

  return (
    <div className="flex h-screen flex-col">
      <Topbar />
      {error && (
        <div className="flex items-center justify-between bg-red-600 px-4 py-1 text-sm text-white">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">
            ✕
          </button>
        </div>
      )}
      <div className="flex flex-1 overflow-hidden">
        <ContractRepository onNew={() => setDialogOpen(true)} />
        {activeContract ? <ContractViewer highlight={highlight} /> : <WorkspaceOverview />}
        {activeContract && <IntelligencePanel onHighlight={setHighlight} />}
      </div>
      <NewContractDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  );
}
