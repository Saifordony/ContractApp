# Contract Intelligence — frontend (Next.js)

Replacement for the Streamlit UI. The audit found Streamlit's full-script-rerun
model was the root cause of the duplicated, state-desynced screens; this app is
the migration target.

## Develop
```bash
npm install
cp .env.example .env.local   # point NEXT_PUBLIC_BACKEND_URL at the FastAPI backend
npm run dev                  # http://localhost:3000
```

## Verify
```bash
npm run typecheck   # tsc --noEmit
npm run build       # production build
```

## First slice
`app/page.tsx` implements the core flow: sign in → paste contract → one
`POST /genai/analyze` call → grounded result. Each section renders its own
evidence citations and a bucketed confidence badge, with designed loading
(step indicator + skeleton), error, and degraded-mode (model-unreachable)
states. Subsequent slices add file upload, the contract list, follow-up chat,
and benchmark on top of this shell.
