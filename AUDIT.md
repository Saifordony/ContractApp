# ContractApp — Phase 0 Audit

Read-only audit of the full codebase (FastAPI backend, MongoDB, local Llama 3.1:8b via Ollama, Streamlit frontend), produced before any redesign work. No code was changed to produce this document.

---

## 1. Every user-facing feature, traced to what it actually does

| Feature (as presented to user) | Entry point | What actually happens |
|---|---|---|
| Register / Login | Sidebar / login form | `POST /auth/register`, `POST /auth/login` → JWT (HS256, 30 min, no refresh) |
| Password reset | *(not wired into any UI — see §2)* | `POST /auth/reset-password[/confirm]` exist and work, but no frontend screen calls them |
| Client management | "Clients & Contracts" page + duplicated form in "Analyze" page | CRUD on `db.clients`, ownership-scoped by `created_by` |
| Contract upload | "Analyze" page (main app) **and** `pages/2_Analysis.py` (two separate implementations) | `POST /contracts` creates a record; file bytes are parsed client-mime-side then sent as raw text to `/genai/analyze-contract[-text]` |
| Clause extraction | Same pages, "Analyze Contract Clauses" button | Tries LLM extraction (`gen1.analyze_contract`) first; **silently** falls back to keyword/regex extraction (`contract_intelligence.extract_key_clauses`) on any LLM failure, with no signal to the user about which path produced the result |
| Contract health evaluation | "Evaluate Contract Health" button | Runs **both** an LLM evaluator (`gen1.evaluate_contract`) and a deterministic rule-based evaluator (`contract_health.evaluate_contract_health_from_clauses`), then shallow-merges the two dicts — the merge order means rule-based fields silently overwrite LLM fields with the same key |
| Contract chat / Q&A | Embedded chat in main "Analyze" page **and** separate `pages/3_Chat.py` | Two unsynchronized chat histories (`chat_messages_by_contract[id]` vs. a page-local `chat_history` key). Routes through `contract_chat_service.build_contract_chat_response`, which itself can call a third reasoning path (`ollama_contract_ai.run_contract_reasoning_pipeline`, the only one with real evidence-citation enforcement), or gen1's direct LLM chat, or the keyword-retrieval fallback — three different answer-generation strategies depending on what's available |
| Benchmark comparison | "Benchmark" page (main app, contract-selector based) **and** `pages/4_Benchmark.py` (session-state based) **and** a third standalone flow `POST /benchmark/analyze` (upload-and-compare in one shot) | Backend itself has **two independent benchmark engines** — `benchmark_service.py` (deterministic hash-embeddings + cosine similarity against a seeded corpus) and `benchmark_comparison_service.py` (keyword/rule-based against hardcoded baseline dicts) — invoked from different endpoints with different output schemas |
| PDF / CSV / JSON report export | "Report" tab in Analysis | JSON/CSV work; the PDF button is a stub — it shows a toast and does not produce a file in `pages/2_Analysis.py` |
| Pipeline / sales-funnel analytics | "Pipeline" page | Entirely separate feature (sales opportunity stages, not contracts); accepts manually-uploaded JSON or manual form entry; has zero data linkage to contracts/clients |
| Dashboard / stats | "Home" page **and** main app's `dashboard_page()` | Both call `/stats/summary` independently, no caching, no shared state |
| Settings (theme, language, LLM status, sign out) | `pages/6_Settings.py` | Theme/language are session-only — lost on every browser refresh, not persisted server-side |
| Admin logs/metrics | Hidden in Settings/Admin areas | `/logs`, `/metrics`, `/metrics/chat-quality` — functional, read-only, no UI issues found |
| Multilingual (EN/AR) support | Toggle in sidebar | Real and reasonably well-built: Unicode-block language detection, diacritic-normalized Arabic matching, bilingual prompts and bilingual structured chat output |

**Bottom line:** almost every core feature (analysis, chat, benchmark) exists in **two or three parallel implementations** that don't share state or produce consistent output. A new user cannot tell which version of a feature they're using, and the two won't agree with each other if used side by side.

---

## 2. Redundant/overlapping features, dead code, duplicate logic

**Backend — three competing "answer the user" pipelines, used inconsistently:**
1. `gen1.py` — direct LLM call (analysis, evaluation, chat) with silent fallback on any exception.
2. `contract_intelligence.py` — deterministic BM25 + synonym keyword retrieval, used both as gen1's fallback *and* sometimes called directly.
3. `ollama_contract_ai.py` — hybrid retrieval + LLM + reviewer-verification + re-prompt-on-rejection. This is by far the most rigorous (evidence citation, confidence scoring, JSON-repair retries) but is only reached via `contract_chat_service.py`'s intent router for certain intents — not used for the initial clause extraction or health evaluation at all.

**Backend — duplicate benchmark engines:** `benchmark_service.py` (vector/embedding-based) and `benchmark_comparison_service.py` (rule-based) solve the same problem with different math and different output shapes, called from different routes (`/benchmark/analyze` vs `/benchmark/compare/{id}` vs `/contracts/{id}/benchmark`). The latter two of those three routes are functionally identical to each other (`backend/routers/benchmark.py:22-65` vs `:68-94`); only one is called from the frontend.

**Backend — confirmed dead code:**
- `backend/services/benchmark_baselines.py:run_benchmark()` — implemented, never imported anywhere.
- `backend/gen1.py` module-level `full_pipeline_chain` — set to `None`, never used.
- `POST/GET /contracts/{contract_id}/benchmark` — orphaned, no frontend caller (duplicate of `/benchmark/compare/{contract_id}`).
- `/auth/reset-password` and `/auth/reset-password/confirm` — fully implemented backend flow with no frontend entry point at all.

**Backend — schema duplication:** `contract_analyses.results` stores extracted clauses in **two parallel shapes** simultaneously — `clauses` (flat string dict) and `structured_clauses.clauses` (the rich validated-record shape) — both written on every analysis, both read by different call sites. `health_evaluation` similarly merges LLM output and rule-based output into one dict with key collisions silently resolved by *whichever was spread second* in the dict-merge, which is non-obvious from reading either function alone.

**Frontend — the same three features built twice, with no state sync:**
- Chat: main-app chat (`streamlit_app.py:1353-1470`) vs `pages/3_Chat.py` — two different `session_state` keys, so conversations don't carry over between them.
- Analysis: main-app `contract_analysis_page()` vs `pages/2_Analysis.py` — both run extraction independently; results aren't shared.
- Benchmark: main-app `benchmark_page()` vs `pages/4_Benchmark.py` — same problem, plus a third code path via the standalone `/benchmark/analyze` upload flow.

This isn't incidental overlap — it's the direct result of bolting a Streamlit multipage app (`pages/`) onto an already-complete single-file app (`streamlit_app.py`) without migrating or removing the original screens.

---

## 3. UX friction points (ranked by severity)

**Critical — breaks the core flow:**
- **Session-state key mismatch.** The main app stores the active contract as `current_contract_content`; every multipage screen (`pages/2`, `3`, `4`) reads `contract_text`. Any user who uploads/analyzes in the main app and then clicks into a multipage tab sees a blank screen, as if nothing happened. This is the single biggest "my work disappeared" bug in the product.
- **Two unsynchronized chat histories**, as above — a user's conversation can vanish depending on which entry point they click.
- **Sidebar "AI Assistant" button routes to a page that just says "use Ask AI inside Contract Analysis"** — a dead end with no link back into the actual feature.
- **Benchmark requires re-selecting the contract from a dropdown** even immediately after analyzing it — the app already knows which contract is "current" everywhere else.

**High:**
- Every long-running action (extraction, evaluation, chat, benchmark — all of which can take up to 180s against an 8B local model) shows a bare, contextless spinner with no progress, no step indicator, no time estimate, and no cancel.
- Settings (theme, language) reset on every browser refresh — there's no server-side persistence of user preference at all.
- PDF report generation is a non-functional stub (shows a success toast, produces no file).
- `/stats/summary` is called fresh, uncached, on every single page load that touches the dashboard (two separate dashboard implementations, both doing this independently).
- Errors from the backend are surfaced as raw `detail` strings (occasionally including raw response bodies, `chat_response.text[:800]`), with no retry affordance.

**Medium:**
- The onboarding banner is unconditionally shown until dismissed and consumes real vertical space rather than being a one-time tour.
- Visual elements lie about their own data: `score_breakdown_bars.py` renders severity bars at fixed widths (e.g. always 80% for "high") regardless of the actual numeric score, and `readiness_review.py` applies one overall risk-level label to every individual finding's "Severity" column even when findings differ in severity.
- A long list of features need a tooltip to be usable as-is: health-score bands, benchmark "alignment score" units, the five chat "response modes," clause status nuances (found / partially found / needs review / not found), and what "OCR" toggling actually does if left off.

**This satisfies the brief's own bar ("if it needs a tooltip to be usable, redesign it") for at least 6 distinct UI elements** — those are flagged as redesign targets in Phase 1, not as a todo to write more tooltips.

---

## 4. Where the AI pipeline is weak

- **Silent quality degradation.** When the LLM path fails or is unreachable, `gen1.py` catches the exception and falls back to keyword-matching — invisibly. The user gets a materially lower-quality answer with the exact same visual presentation as a real LLM answer. This is the single most important AI-quality problem to fix: the user has no way to know whether they're looking at model output or a regex match.
- **No grounding/citation requirement in the two weakest prompts.** `analysis_system_prompt` and `contract_chat_prompt` (in `gen1.py`) never require the model to quote/cite the source text it's drawing from, so they're free to paraphrase or invent. By contrast, `ollama_contract_ai.py`'s pipeline *does* enforce this (reviewer-verification step that rejects ungrounded answers and re-prompts forcing exact quotes) — but that rigor only applies to a subset of chat intents, not to the primary clause-extraction or evaluation calls that actually drive the headline "health score."
- **No confidence signaling surfaced consistently.** `ollama_contract_ai.compute_confidence()` is a genuinely well-built multi-factor confidence score (evidence count, retrieval relevance, reviewer approval, ambiguity penalty), but it's only computed in one of the three pipelines and isn't shown next to clause-extraction results at all — only sometimes next to chat answers.
- **No streaming anywhere.** Every LLM call is a single blocking `.invoke()`, which is exactly wrong for a local 8B model that can take 30–180 seconds — the perceived latency is the worst it could be given the actual latency.
- **Brittle JSON parsing as the default, not the exception.** `_extract_json_payload()` in `gen1.py` chains `json.loads` → `ast.literal_eval` → regex-extracted braces — a "best effort" parser accepted as normal operation rather than a last resort. `ollama_contract_ai.py` does this more defensibly (JSON-repair retry via a second LLM call, then a deterministic grounded fallback), but again, only in the chat path.
- **Context handling is reactive, not designed-in.** Chunking is a fixed 900-character window with naive 2-line overlap that doesn't respect sentence boundaries, so it can sever a clause mid-sentence right at the retrieval boundary. The token-budget guard in `ollama_contract_ai.py` only kicks in *after* a prompt is already at 85% of the context window, by which point it's just dropping evidence chunks rather than retrieving smarter ones.
- **Two redundant clause-extraction implementations and two redundant health-evaluation implementations** (see §2) mean prompt-quality fixes have to be made twice to actually change user-visible behavior, and the LLM/rule-based merge in `health_evaluation` makes it genuinely ambiguous which system produced a given field in the final output.

---

## 5. Architectural weaknesses

- **Streamlit is the actual ceiling here, not just "currently used."** The product needs token-streaming chat, optimistic UI during multi-step analysis, persistent state across navigation, and layouts that don't fully re-execute and flash on every interaction. Streamlit structurally cannot do any of these (full top-to-bottom script rerun on every state change is the core execution model, not a configuration issue) — and the multipage/main-app duplication described in §2 exists *because of* that limitation: the team didn't want to lose working main-app screens by migrating to the multipage pattern, so both were kept running in parallel, permanently, instead of one replacing the other.
- **MongoDB schema has no enforced shape.** No collection has schema validation; this is how the same analysis writes both `clauses` and `structured_clauses.clauses` redundantly, and how `logs.action` ended up with inconsistent naming per router (`contract_analysis` vs `contract_analysis_text` vs `contract_evaluation` vs `contract_chat`) that breaks any aggregation-by-action query.
- **No indexes beyond the one TTL index** on `password_reset_tokens`. Every other query — `contracts.created_by`, `contract_analyses.contract_id` + sort by `created_at`, `clients.created_by`, `logs.timestamp`/`user`/`endpoint` — is doing a full collection scan. `/stats/summary` additionally pulls up to 1000 full analysis documents into Python memory to compute averages that MongoDB's aggregation pipeline would do server-side.
- **`client_id` is stored as a string on `contracts` while `clients._id` is a real ObjectId** — it works today because every call site happens to validate the string as ObjectId-shaped before using it, but it's a latent correctness bug waiting for one call site that doesn't.
- **The FastAPI/router/Mongo layer itself is sound** — the recent split into `backend/routers/*.py` + `models.py` + `database.py` is clean, the auth/ownership checks are consistently applied per-endpoint, and Motor's async usage is correct throughout. This layer is worth keeping; the redesign should change what's built on top of it and how the AI/data layers are organized, not the FastAPI foundation itself.
- **Auth is functionally minimal but not production-grade**: no rate limiting on login, no refresh tokens (hard 30-minute cliff with no warning), no logout/token revocation, no unique index on `users.username`/`email` (a race could create duplicate accounts).

---

## Recommendation entering Phase 1

The backend's HTTP/auth/data-access layer (FastAPI + routers + Motor) is solid and should be kept. Everything built *on top of it* — the duplicated AI pipelines, the duplicated benchmark engines, the duplicated frontend screens, and the schema-less Mongo documents — needs to be consolidated to one implementation per feature, with the AI quality bar set by `ollama_contract_ai.py`'s evidence-grounded pattern (the only one of the three that actually does what "on par with Claude" requires) applied universally instead of selectively. On the frontend, the dual main-app/multipage structure should not be patched — Phase 1 will make the case for replacing Streamlit outright, since the friction it audited isn't implementation bugs, it's Streamlit's execution model fighting the product's actual requirements.
