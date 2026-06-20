// Typed API client. Centralizes the auth header, transparent refresh-on-401,
// SSE streaming, and authenticated file downloads. This is the only module that
// talks to the backend.
import type {
  Analysis,
  AuthResponse,
  Benchmark,
  ChatMessage,
  Client,
  Contract,
  ContractListItem,
  Page,
  Preferences,
  SSEHandlers,
  StatsSummary,
  Tokens,
  User,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

const ACCESS_KEY = "cap_access";
const REFRESH_KEY = "cap_refresh";

let onAuthFailure: (() => void) | null = null;
export function setAuthFailureHandler(fn: () => void) {
  onAuthFailure = fn;
}

export function getAccess(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}
function getRefresh(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}
export function setTokens(tokens: Tokens) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}
export function clearTokens() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}
export function isAuthenticated(): boolean {
  return Boolean(getAccess());
}

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function refreshTokens(): Promise<boolean> {
  const refresh = getRefresh();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const tokens = (await res.json()) as Tokens;
    setTokens(tokens);
    return true;
  } catch {
    return false;
  }
}

async function authFetch(path: string, options: RequestInit = {}, retry = true): Promise<Response> {
  const access = getAccess();
  const headers = new Headers(options.headers || {});
  if (access) headers.set("Authorization", `Bearer ${access}`);
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401 && retry && getRefresh()) {
    if (await refreshTokens()) return authFetch(path, options, false);
    clearTokens();
    onAuthFailure?.();
  }
  return res;
}

async function jsonRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  // For FormData (file upload), let the browser set multipart/form-data with its
  // boundary — forcing application/json here breaks server-side form parsing (422).
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (options.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await authFetch(path, { ...options, headers });
  if (res.status === 204) return undefined as T;
  let body: any = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!res.ok) {
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : `Request failed (${res.status})`;
    throw new ApiError(res.status, message, body?.code);
  }
  return body as T;
}

// ---- Auth (these set/clear tokens directly; not via authFetch) ----
export async function register(payload: {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) throw new ApiError(res.status, body?.detail || "Registration failed", body?.code);
  setTokens(body.tokens);
  return body as AuthResponse;
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await res.json();
  if (!res.ok) throw new ApiError(res.status, body?.detail || "Login failed", body?.code);
  setTokens(body.tokens);
  return body as AuthResponse;
}

export async function logout(): Promise<void> {
  const refresh = getRefresh();
  if (refresh) {
    try {
      await authFetch("/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
    } catch {
      /* best effort */
    }
  }
  clearTokens();
}

export function me(): Promise<User> {
  return jsonRequest<User>("/auth/me");
}

export function updatePreferences(prefs: Partial<Preferences>): Promise<User> {
  return jsonRequest<User>("/auth/me/preferences", { method: "PATCH", body: JSON.stringify(prefs) });
}

export function requestPasswordReset(email: string): Promise<{ detail: string; reset_token?: string }> {
  return fetch(`${API_BASE}/auth/password-reset/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  }).then((r) => r.json());
}

export function confirmPasswordReset(token: string, new_password: string): Promise<void> {
  return fetch(`${API_BASE}/auth/password-reset/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password }),
  }).then(async (r) => {
    if (!r.ok) {
      const b = await r.json().catch(() => ({}));
      throw new ApiError(r.status, b?.detail || "Reset failed", b?.code);
    }
  });
}

// ---- Clients ----
export function listClients(search?: string): Promise<Page<Client>> {
  const q = search ? `?search=${encodeURIComponent(search)}` : "";
  return jsonRequest<Page<Client>>(`/clients${q}`);
}
export function createClient(payload: Partial<Client>): Promise<Client> {
  return jsonRequest<Client>("/clients", { method: "POST", body: JSON.stringify(payload) });
}
export function deleteClient(id: string): Promise<void> {
  return jsonRequest<void>(`/clients/${id}`, { method: "DELETE" });
}

// ---- Contracts ----
export function listContracts(params: {
  search?: string;
  contract_type?: string;
  status?: string;
} = {}): Promise<Page<ContractListItem>> {
  const q = new URLSearchParams();
  if (params.search) q.set("search", params.search);
  if (params.contract_type) q.set("contract_type", params.contract_type);
  if (params.status) q.set("status", params.status);
  const qs = q.toString();
  return jsonRequest<Page<ContractListItem>>(`/contracts${qs ? `?${qs}` : ""}`);
}
export function getContract(id: string): Promise<Contract> {
  return jsonRequest<Contract>(`/contracts/${id}`);
}
export function createContract(payload: {
  title: string;
  contract_type: string;
  region: string;
  language?: string;
  content: string;
}): Promise<Contract> {
  return jsonRequest<Contract>("/contracts", { method: "POST", body: JSON.stringify(payload) });
}
export async function uploadContract(file: File, fields: Record<string, string>): Promise<Contract> {
  const form = new FormData();
  form.append("file", file);
  Object.entries(fields).forEach(([k, v]) => v && form.append(k, v));
  return jsonRequest<Contract>("/contracts/upload", { method: "POST", body: form });
}
export function deleteContract(id: string): Promise<void> {
  return jsonRequest<void>(`/contracts/${id}`, { method: "DELETE" });
}
export function getAnalysis(id: string): Promise<Analysis | null> {
  return jsonRequest<Analysis>(`/contracts/${id}/analysis`).catch((e: ApiError) => {
    if (e.status === 404) return null;
    throw e;
  });
}
export function getChatHistory(id: string): Promise<ChatMessage[]> {
  return jsonRequest<ChatMessage[]>(`/contracts/${id}/chat`).catch(() => []);
}
export function getBenchmark(id: string): Promise<Benchmark | null> {
  return jsonRequest<Benchmark>(`/contracts/${id}/benchmark`).catch((e: ApiError) => {
    if (e.status === 404) return null;
    throw e;
  });
}

// ---- Stats ----
export function statsSummary(): Promise<StatsSummary> {
  return jsonRequest<StatsSummary>("/stats/summary");
}

// ---- Health ----
export function health(): Promise<any> {
  return jsonRequest<any>("/health");
}

// ---- Streaming (SSE over fetch, so we can POST with an auth header) ----
export async function streamSSE(path: string, body: any, handlers: SSEHandlers): Promise<void> {
  let res: Response;
  try {
    res = await authFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    handlers.onError?.((e as Error).message);
    handlers.onDone?.();
    return;
  }
  if (!res.ok || !res.body) {
    handlers.onError?.(`Request failed (${res.status})`);
    handlers.onDone?.();
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const dispatch = (frame: string) => {
    let event = "message";
    let data = "";
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data += line.slice(5).trim();
    }
    let parsed: any = {};
    try {
      parsed = data ? JSON.parse(data) : {};
    } catch {
      parsed = {};
    }
    if (event === "status") handlers.onStatus?.(parsed.message);
    else if (event === "token") handlers.onToken?.(parsed.text);
    else if (event === "result") handlers.onResult?.(parsed);
    else if (event === "error") handlers.onError?.(parsed.message);
    else if (event === "done") handlers.onDone?.();
  };
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      if (frame.trim()) dispatch(frame);
    }
  }
}

export function streamAnalyze(contractId: string, handlers: SSEHandlers) {
  return streamSSE(`/contracts/${contractId}/analyze`, null, handlers);
}
export function streamChat(contractId: string, question: string, handlers: SSEHandlers) {
  return streamSSE(`/contracts/${contractId}/chat`, { question }, handlers);
}
export function streamBenchmark(contractId: string, handlers: SSEHandlers) {
  return streamSSE(`/contracts/${contractId}/benchmark`, null, handlers);
}

// ---- Authenticated file export (download via blob, since <a> can't send a header) ----
export async function downloadExport(contractId: string, format: "pdf" | "csv" | "json", filename: string) {
  const res = await authFetch(`/contracts/${contractId}/export/${format}`);
  if (!res.ok) throw new ApiError(res.status, `Export failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
