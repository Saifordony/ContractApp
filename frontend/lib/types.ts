// Types mirroring the backend API shapes.

export type Theme = "light" | "dark";
export type Language = "en" | "ar";

export interface Preferences {
  theme: Theme;
  language: Language;
}

export interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string | null;
  preferences: Preferences;
  created_at: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: Tokens;
}

export interface Client {
  id: string;
  name: string;
  email?: string | null;
  company?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractListItem {
  id: string;
  client_id?: string | null;
  title: string;
  contract_type: string;
  region: string;
  language: Language;
  status: "uploaded" | "analyzed";
  created_at: string;
  updated_at: string;
}

export interface Contract extends ContractListItem {
  created_by: string;
  source_format: string;
  content: string;
  page_count?: number | null;
  ocr_used: boolean;
}

export interface Evidence {
  text: string;
  char_start: number;
  char_end: number;
  chunk_id?: number | null;
}

export type ClauseStatus = "found" | "partially_found" | "needs_review" | "not_found";

export interface Clause {
  key: string;
  label: { en: string; ar: string };
  status: ClauseStatus;
  extracted_text: string;
  explanation: string;
  evidence: Evidence[];
  confidence: number;
}

export interface Dimension {
  key: string;
  label: { en: string; ar: string };
  score: number;
  explanation: string;
  evidence: Evidence[];
}

export interface Health {
  overall_score: number;
  grade: string;
  dimensions: Dimension[];
  confidence: number;
}

export interface Analysis {
  id: string;
  contract_id: string;
  language: Language;
  degraded: boolean;
  model: string;
  confidence: number;
  clauses: Clause[];
  health: Health;
  created_at: string;
}

export interface Citation {
  text: string;
  char_start: number;
  char_end: number;
}

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: number | null;
  degraded?: boolean | null;
  created_at?: string;
  // Client-only flag while a streamed answer is still arriving.
  streaming?: boolean;
}

export interface Gap {
  clause_key: string;
  importance: string;
  benchmark_expectation: string;
  contract_status: string;
  severity: string;
  recommendation: string;
  evidence: Evidence[];
}

export interface Benchmark {
  id: string;
  contract_id: string;
  contract_type: string;
  region: string;
  overall_score: number;
  grade: string;
  degraded: boolean;
  confidence: number;
  gaps: Gap[];
  created_at: string;
}

export interface StatsSummary {
  contracts_total: number;
  clients_total: number;
  analyzed_total: number;
  avg_health_score: number | null;
  high_risk: { contract_id: string; title: string; score: number }[];
  recent_findings: {
    contract_id: string;
    title: string;
    overall_score: number | null;
    degraded: boolean;
    needs_review: number;
  }[];
  outstanding_reviews: number;
}

export interface Page<T> {
  items: T[];
  total: number;
}

export interface SSEHandlers {
  onStatus?: (message: string) => void;
  onToken?: (text: string) => void;
  onResult?: (data: any) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}
