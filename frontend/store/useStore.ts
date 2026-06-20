// The single global store. Every screen reads active contract / analysis / chat /
// benchmark from here, so navigating between panels never loses in-progress work.
import { create } from "zustand";

import * as api from "@/lib/api";
import type {
  Analysis,
  Benchmark,
  ChatMessage,
  Contract,
  ContractListItem,
  Language,
  StatsSummary,
  Theme,
  User,
} from "@/lib/types";

interface AppState {
  hydrated: boolean;
  user: User | null;
  language: Language;
  theme: Theme;

  contracts: ContractListItem[];
  search: string;

  activeContractId: string | null;
  activeContract: Contract | null;
  analysis: Analysis | null;
  chat: ChatMessage[];
  benchmark: Benchmark | null;

  stats: StatsSummary | null;

  analyzing: boolean;
  benchmarking: boolean;
  chatting: boolean;
  streamStatus: string;
  error: string | null;

  bootstrap: () => Promise<void>;
  loadContracts: (search?: string) => Promise<void>;
  setSearch: (s: string) => void;
  selectContract: (id: string) => Promise<void>;
  clearActive: () => void;
  createTextContract: (p: {
    title: string;
    contract_type: string;
    region: string;
    language?: string;
    content: string;
  }) => Promise<void>;
  uploadContract: (file: File, fields: Record<string, string>) => Promise<void>;
  removeContract: (id: string) => Promise<void>;
  runAnalysis: () => Promise<void>;
  runBenchmark: () => Promise<void>;
  sendChat: (question: string) => Promise<void>;
  setTheme: (t: Theme) => Promise<void>;
  setLanguage: (l: Language) => Promise<void>;
  loadStats: () => Promise<void>;
  logout: () => Promise<void>;
  setError: (e: string | null) => void;
}

export const useStore = create<AppState>((set, get) => ({
  hydrated: false,
  user: null,
  language: "en",
  theme: "light",
  contracts: [],
  search: "",
  activeContractId: null,
  activeContract: null,
  analysis: null,
  chat: [],
  benchmark: null,
  stats: null,
  analyzing: false,
  benchmarking: false,
  chatting: false,
  streamStatus: "",
  error: null,

  setError: (e) => set({ error: e }),

  bootstrap: async () => {
    if (!api.isAuthenticated()) {
      set({ hydrated: true });
      return;
    }
    try {
      const user = await api.me();
      set({ user, language: user.preferences.language, theme: user.preferences.theme });
      await Promise.all([get().loadContracts(), get().loadStats()]);
    } catch {
      // token invalid; clear and let the guard redirect
      await api.logout();
    } finally {
      set({ hydrated: true });
    }
  },

  loadContracts: async (search) => {
    const page = await api.listContracts({ search: search ?? get().search });
    set({ contracts: page.items });
  },

  setSearch: (s) => {
    set({ search: s });
    void get().loadContracts(s);
  },

  selectContract: async (id) => {
    set({ activeContractId: id, activeContract: null, analysis: null, chat: [], benchmark: null });
    const [contract, analysis, chat, benchmark] = await Promise.all([
      api.getContract(id),
      api.getAnalysis(id),
      api.getChatHistory(id),
      api.getBenchmark(id),
    ]);
    // Guard against a race if the user clicked another contract meanwhile.
    if (get().activeContractId !== id) return;
    set({ activeContract: contract, analysis, chat, benchmark });
  },

  clearActive: () =>
    set({ activeContractId: null, activeContract: null, analysis: null, chat: [], benchmark: null }),

  createTextContract: async (payload) => {
    const contract = await api.createContract(payload);
    await get().loadContracts();
    await get().selectContract(contract.id);
  },

  uploadContract: async (file, fields) => {
    const contract = await api.uploadContract(file, fields);
    await get().loadContracts();
    await get().selectContract(contract.id);
  },

  removeContract: async (id) => {
    await api.deleteContract(id);
    if (get().activeContractId === id) get().clearActive();
    await Promise.all([get().loadContracts(), get().loadStats()]);
  },

  runAnalysis: async () => {
    const id = get().activeContractId;
    if (!id) return;
    set({ analyzing: true, streamStatus: "Starting analysis…", error: null });
    await api.streamAnalyze(id, {
      onStatus: (message) => set({ streamStatus: message }),
      onResult: (data: Analysis) => {
        set((s) => ({
          analysis: data,
          contracts: s.contracts.map((c) => (c.id === id ? { ...c, status: "analyzed" } : c)),
          activeContract: s.activeContract ? { ...s.activeContract, status: "analyzed" } : s.activeContract,
        }));
      },
      onError: (message) => set({ error: message }),
      onDone: () => {
        set({ analyzing: false, streamStatus: "" });
        void get().loadStats();
      },
    });
  },

  runBenchmark: async () => {
    const id = get().activeContractId;
    if (!id) return;
    set({ benchmarking: true, streamStatus: "Starting benchmark…", error: null });
    await api.streamBenchmark(id, {
      onStatus: (message) => set({ streamStatus: message }),
      onResult: (data: Benchmark) => set({ benchmark: data }),
      onError: (message) => set({ error: message }),
      onDone: () => {
        set({ benchmarking: false, streamStatus: "" });
        // A benchmark may have auto-run analysis; refresh it.
        if (!get().analysis) void api.getAnalysis(id).then((a) => set({ analysis: a }));
      },
    });
  },

  sendChat: async (question) => {
    const id = get().activeContractId;
    if (!id || !question.trim()) return;
    set((s) => ({
      chatting: true,
      error: null,
      chat: [
        ...s.chat,
        { role: "user", content: question },
        { role: "assistant", content: "", streaming: true },
      ],
    }));
    const patchLast = (patch: Partial<ChatMessage>) =>
      set((s) => {
        const chat = [...s.chat];
        chat[chat.length - 1] = { ...chat[chat.length - 1], ...patch };
        return { chat };
      });
    await api.streamChat(id, question, {
      onToken: (text) =>
        set((s) => {
          const chat = [...s.chat];
          const last = chat[chat.length - 1];
          chat[chat.length - 1] = { ...last, content: last.content + text };
          return { chat };
        }),
      onResult: (data) =>
        patchLast({
          content: data.content,
          citations: data.citations,
          confidence: data.confidence,
          degraded: data.degraded,
          streaming: false,
        }),
      onError: (message) => {
        patchLast({ content: `⚠️ ${message}`, streaming: false });
        set({ error: message });
      },
      onDone: () => set({ chatting: false }),
    });
  },

  setTheme: async (theme) => {
    set({ theme });
    try {
      await api.updatePreferences({ theme });
    } catch {
      /* preference persistence is best-effort */
    }
  },

  setLanguage: async (language) => {
    set({ language });
    try {
      await api.updatePreferences({ language });
    } catch {
      /* best effort */
    }
  },

  loadStats: async () => {
    try {
      set({ stats: await api.statsSummary() });
    } catch {
      /* ignore */
    }
  },

  logout: async () => {
    await api.logout();
    set({
      user: null,
      contracts: [],
      activeContractId: null,
      activeContract: null,
      analysis: null,
      chat: [],
      benchmark: null,
      stats: null,
    });
  },
}));
