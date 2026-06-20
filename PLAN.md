# Contract Analysis Platform — Build Plan (Phase 0)

A clean, from-scratch rebuild. This document is the single source of truth for the
data model, API surface, and AI pipeline. Every later phase must conform to it. If
reality forces a change, this file changes first.

## Scope decisions (v1)

All 8 product features are **in scope** and shipped through the one Next.js UI:
clause extraction, contract health score, grounded chat, benchmark comparison,
real PDF/CSV/JSON export, client + contract CRUD, full auth (access+refresh, rate
limit, revocation, wired password reset), and **full bilingual EN/AR** (RTL UI +
Arabic localization, respected by both extraction and chat).

**Dropped from the legacy app:** the sales-pipeline/opportunity-funnel analytics
feature (not part of the product brief, no linkage to contracts).

## Non-negotiable architecture rules (from the brief)

1. **One implementation per feature.** Exactly one code path for extraction, health
   scoring, chat, benchmark — all routed through `services/ai_pipeline.py`.
2. **No silent degradation.** If the LLM is unreachable, the *same response shape*
   returns with `degraded: true`; the UI always renders a degraded banner.
3. **Evidence-grounded everywhere.** Every LLM result cites exact source spans,
   passes one reviewer-verification pass (re-prompt once on rejection), and carries
   a visible confidence score.
4. **Schema-validated Mongo from day one**, real `ObjectId` references, one canonical
   shape per document, indexes for every real query pattern, server-side aggregation.
5. **One global frontend store** for active contract / chat / analysis.
6. **Streaming (SSE)** for every call that can exceed ~5s.

---

## 1. MongoDB — collections, validators, indexes

All created by `backend/database.py` (validators via `collMod`/`create_collection`)
and `backend/migrations.py` (indexes + seed). All `*_id` references are real `ObjectId`s.

### `users`
- Fields: `username:str` (unique), `email:str` (unique), `hashed_password:str`,
  `full_name:str?`, `preferences:{theme:'light'|'dark', language:'en'|'ar'}`,
  `created_at:date`, `updated_at:date`.
- Validator required: `username, email, hashed_password, preferences, created_at`.
- Indexes: `username` unique, `email` unique.

### `refresh_tokens`  (rotation + revocation)
- Fields: `user_id:ObjectId`, `token_hash:str` (sha256 of opaque token), `expires_at:date`,
  `revoked:bool`, `created_at:date`.
- Indexes: `token_hash` unique, `user_id`, TTL on `expires_at`.

### `password_reset_tokens`
- Fields: `user_id:ObjectId`, `token_hash:str`, `expires_at:date`, `used:bool`, `created_at:date`.
- Indexes: `token_hash` unique, TTL on `expires_at`.

### `login_attempts`  (sliding-window rate limit; survives restarts/workers)
- Fields: `key:str` (ip+username), `ts:date`.
- Indexes: `(key, ts)`, TTL on `ts` (window seconds).

### `clients`
- Fields: `created_by:ObjectId`, `name:str`, `email:str?`, `company:str?`, `notes:str?`,
  `created_at:date`, `updated_at:date`.
- Indexes: `created_by`, `(created_by, name)`.

### `contracts`
- Fields: `created_by:ObjectId`, `client_id:ObjectId?`, `title:str`,
  `contract_type:str`, `region:str`, `language:'en'|'ar'`,
  `source_format:'pdf'|'docx'|'text'`, `content:str`, `page_count:int?`,
  `ocr_used:bool`, `status:'uploaded'|'analyzed'`, `created_at:date`, `updated_at:date`.
- Indexes: `created_by`, `(created_by, created_at)`, `client_id`, `(created_by, contract_type)`.

### `contract_analyses`  (ONE canonical shape — no flat+structured duplication)
- Fields: `contract_id:ObjectId`, `created_by:ObjectId`, `language:str`, `degraded:bool`,
  `model:str`, `confidence:float`,
  `clauses:[ {key, label:{en,ar}, status:'found'|'partially_found'|'needs_review'|'not_found',
    extracted_text, explanation, evidence:[{text,char_start,char_end,chunk_id}], confidence} ]`,
  `health:{ overall_score:int, grade:str,
    dimensions:[{key:'clarity'|'risk_exposure'|'completeness'|'enforceability', score:int,
    explanation, evidence:[...] }], confidence:float }`,
  `created_at:date`.
- Indexes: `(contract_id, created_at)`, `created_by`.

### `benchmark_standards`  (the ONE benchmark knowledge base; seeded by migration)
- Fields: `contract_type:str`, `region:str`, `language:str`,
  `clauses:[{key, importance:'high'|'medium'|'low', typical_terms, description}]`, `created_at`.
- Indexes: `(contract_type, region)` unique.

### `benchmark_results`
- Fields: `contract_id:ObjectId`, `created_by:ObjectId`, `contract_type:str`, `region:str`,
  `language:str`, `overall_score:int`, `grade:str`, `degraded:bool`, `confidence:float`, `model:str`,
  `gaps:[{clause_key, importance, benchmark_expectation, contract_status, severity, recommendation,
    evidence:[...]}]`, `created_at:date`.
- Indexes: `(contract_id, created_at)`, `created_by`.

### `chat_messages`
- Fields: `contract_id:ObjectId`, `created_by:ObjectId`, `role:'user'|'assistant'`, `content:str`,
  `citations:[{text,char_start,char_end}]`, `confidence:float?`, `degraded:bool?`, `created_at:date`.
- Indexes: `(contract_id, created_at)`.

### `logs`  (one consistent `action` naming scheme: `<domain>_<verb>`)
- Fields: `user_id:ObjectId?`, `action:str`, `resource_type:str?`, `resource_id:ObjectId?`,
  `metadata:object?`, `created_at:date`.
- Action vocabulary: `user_register, user_login, user_logout, client_create, client_update,
  client_delete, contract_create, contract_update, contract_delete, analysis_run, chat_query,
  benchmark_run, export_generate`.
- Indexes: `created_at`, `user_id`, `action`.

---

## 2. API surface (request → response shapes)

Base `/api`. JSON unless noted. Auth = `Authorization: Bearer <access>`. Errors use a
consistent `{detail, code}` envelope. Streaming endpoints are SSE (`text/event-stream`)
with events: `status` (step text), `token` (partial text), `result` (final JSON),
`error`, `done`.

### Auth `/api/auth`
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/register` | `{username,email,password,full_name?}` | `201 {user, tokens}` |
| POST | `/login` | `{username,password}` | `200 {user, tokens}` (rate-limited) |
| POST | `/refresh` | `{refresh_token}` | `200 {tokens}` (rotates+revokes old) |
| POST | `/logout` | `{refresh_token}` | `204` (revokes) |
| GET | `/me` | — | `200 {user}` |
| PATCH | `/me/preferences` | `{theme?,language?}` | `200 {user}` |
| POST | `/password-reset/request` | `{email}` | `202 {reset_token?}` (token in dev/no-mail mode) |
| POST | `/password-reset/confirm` | `{token,new_password}` | `204` |

`tokens = {access_token, refresh_token, token_type:'bearer', expires_in}`.
`user = {id, username, email, full_name, preferences, created_at}`.

### Clients `/api/clients`  (all scoped to `created_by`)
`GET /?search=&limit=&skip=` → `{items, total}` · `POST /` → `201 client` ·
`GET /{id}` · `PATCH /{id}` · `DELETE /{id}` → `204`.

### Contracts `/api/contracts`  (all scoped to owner)
- `GET /?search=&client_id=&contract_type=&status=&limit=&skip=` → `{items,total}`
- `POST /` `{title,contract_type,region,language?,client_id?,content}` → `201 contract`
- `POST /upload` multipart `file` + form fields → parses (PyMuPDF/python-docx/OCR), → `201 contract`
- `GET /{id}` → full contract incl. `content`
- `PATCH /{id}` `{title?,contract_type?,region?,client_id?,status?}` · `DELETE /{id}` → `204` (cascades)
- `GET /{id}/analysis` → latest `contract_analyses` or `404`
- `GET /{id}/chat` → `{items}` chat history · `GET /{id}/benchmark` → latest result

### AI (one pipeline) — streaming
- `POST /api/contracts/{id}/analyze` (SSE) → runs extraction + health in one pipeline pass,
  persists `contract_analyses`, emits `status`→`result`(full analysis).
- `POST /api/contracts/{id}/chat` (SSE) `{question}` → grounded answer, streams `token`s then
  `result`(content+citations+confidence+degraded); persists user+assistant `chat_messages`.
- `POST /api/contracts/{id}/benchmark` (SSE) → compares vs `benchmark_standards`, persists result.

### Export `/api/contracts/{id}/export`
- `GET /pdf` → `application/pdf` (reportlab, real file) · `GET /json` · `GET /csv`.

### Stats `/api/stats/summary`
Server-side aggregation only → `{contracts_total, clients_total, analyzed_total,
avg_health_score, high_risk:[{contract_id,title,score}], recent_findings:[...],
outstanding_reviews:[...]}`.

### System `/api/health`
→ `{status, db:'up'|'down', ai:{reachable:bool, model, base_url}}`.

---

## 3. The ONE AI pipeline — call sequence

`services/ai_pipeline.py` exposes a single grounded primitive reused by all four
features. Configured entirely by env (`OLLAMA_BASE_URL/MODEL/TEMPERATURE/NUM_CTX/TIMEOUT`).

```
run_grounded(task_spec, contract) -> GroundedResult
  1. CHUNK      sentence-aware (split into sentences, group to ~target tokens with
                sentence-level overlap; never sever mid-sentence). chunk = {id,text,start,end}.
  2. RETRIEVE   score chunks vs task query with deterministic lexical relevance
                (TF-IDF cosine + term overlap; offline, no embedding service).
                BUDGET-AWARE: select top chunks until token budget
                (NUM_CTX − prompt_overhead − max_response) is hit — pick fewer, better
                chunks BEFORE building the prompt. Never truncate a finished prompt.
  3. PROMPT     build structured prompt: schema + "cite exact spans from CONTEXT" +
                language directive (answer in contract language; bilingual labels).
  4. GENERATE   Ollama OpenAI-compatible /v1/chat/completions, response_format=json_object.
                Stream tokens for SSE endpoints; collect full text for internal steps.
  5. PARSE      json.loads → on failure ONE repair retry (model fixes its JSON) → on
                second failure, degraded deterministic result. No json→ast→regex chain.
  6. VERIFY     reviewer pass: confirm each cited span is actually present in source
                (normalized containment). If ungrounded spans exist → RE-PROMPT ONCE
                forcing exact quotes. Remaining ungrounded → drop span, mark needs_review.
  7. CONFIDENCE multi-factor 0..1: evidence_count, retrieval_relevance, reviewer_approval,
                ambiguity_penalty. Surfaced on EVERY result.
  8. DEGRADE    any Ollama failure/timeout at step 4 → same shape, degraded=true,
                deterministic lexical fallback, confidence capped low.
```

**Feature composition (DRY, no re-extraction):**
- **Analyze** = `run_grounded(extraction_spec)` → clauses+evidence, then
  `run_grounded(health_spec, evidence=clauses)` consuming those clauses (no re-extract).
- **Chat** = `run_grounded(chat_spec(question))` → answer + citations.
- **Benchmark** = consume latest analysis clauses, compare vs `benchmark_standards`,
  one `run_grounded(benchmark_spec)` scoring pass → gaps + grade.

---

## 4. Layout

```
backend/  main.py config.py database.py migrations.py
          models/{auth,clients,contracts,analysis,chat,benchmark,common}.py
          routers/{auth,clients,contracts,ai,export,stats,system}.py
          services/{ai_pipeline,chunking,retrieval,llm_client,document_parsing,
                    benchmark,pdf_export,confidence}.py
          auth/security.py
tests/    one module per service + per router (LLM mocked, Mongo via mongomock/docker)
frontend/ app/(auth)/{login,register,reset-password}  app/workspace
          components/{ContractRepository,ContractViewer,IntelligencePanel,
                      ConfidenceBadge,DegradedModeBanner,...}
          lib/{api,types,i18n}.ts   store/ (Zustand: active contract/chat/analysis)
docker-compose.yml  (mongo+backend+frontend, no hardcoded container_name)
```

## 5. Phase order
- **P1** backend core: app, config, db schemas/indexes, auth, client+contract CRUD, parsing. Tested.
- **P2** the one AI pipeline (extraction/health/chat/benchmark), SSE, degraded, bilingual. Tested.
- **P3** Next.js workspace wired to real backend, global store, RTL/i18n.
- **P4** real PDF/CSV/JSON export, streaming UI, degraded banner, server-persisted settings.
- **P5** full pytest suite, docker-compose one-command stack, README.

## 6. Verification reality in this container
Real `llama3.1:8b` inference and a full `docker compose up` with the browser frontend
can't run here. Backend is verified with `pytest` against a **mocked Ollama** and a
**Docker MongoDB** (or `mongomock`); the frontend is type-checked/built (`tsc`/`next build`).
End-to-end with live Ollama is the user's machine step (`ollama pull llama3.1:8b`).
