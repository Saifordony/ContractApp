// Thin, typed client for the FastAPI backend.
//
// One place owns the base URL, the bearer token, and error normalisation so every
// screen gets the same behaviour: a failed call throws an ApiError with a
// human-readable message (never a raw {"detail": ...} blob leaked to the UI).

import type { ChatResponse, ChatTurn, GroundedAnalysis, LoginResponse } from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") || "http://localhost:8000";

const TOKEN_KEY = "contractapp_token";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
  } catch {
    /* fall through to status text */
  }
  return res.statusText || "Request failed";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      `Cannot reach the backend at ${BASE_URL}. Is it running?`,
      0
    );
  }

  if (!res.ok) {
    throw new ApiError(await readError(res), res.status);
  }
  return (await res.json()) as T;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const data = await request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function analyzeContractText(
  contractText: string,
  responseLanguage = "english"
): Promise<GroundedAnalysis> {
  return request<GroundedAnalysis>("/genai/analyze", {
    method: "POST",
    body: JSON.stringify({ contract_text: contractText, response_language: responseLanguage }),
  });
}

export async function chatWithContract(args: {
  message: string;
  contractText: string;
  analysisResults?: unknown;
  history: ChatTurn[];
  responseLanguage?: string;
}): Promise<ChatResponse> {
  return request<ChatResponse>("/genai/contract-chat", {
    method: "POST",
    body: JSON.stringify({
      message: args.message,
      contract_text: args.contractText,
      analysis_results: args.analysisResults ?? {},
      chat_history: args.history.map((t) => ({ role: t.role, content: t.content })),
      response_language: args.responseLanguage ?? "english",
    }),
  });
}

export { BASE_URL };
