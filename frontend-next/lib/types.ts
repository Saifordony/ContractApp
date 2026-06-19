// Shapes returned by the FastAPI backend. Kept in one place so the UI and the API
// client agree on exactly what /genai/analyze and /auth/login return.

export interface EvidenceCitation {
  quote: string;
  location: string;
}

export interface AnalysisSection {
  section: string;
  answer: string;
  /** 0..1 model/retrieval confidence for this section. */
  confidence: number;
  evidence: EvidenceCitation[];
  risks: Array<Record<string, unknown>>;
  missing_information: string[];
  debug?: unknown;
}

export interface GroundedAnalysis {
  sections: Record<string, AnalysisSection>;
  overall_confidence: number;
  /** True when the model was unreachable and results are keyword-derived. */
  degraded_mode: boolean;
  evaluation_source: "llm" | "rule_based_fallback";
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
