# README_DEV

## Assumptions and implementation notes

1. **No UI/styling changes** were introduced in this round; all changes are backend/service/test focused.
2. **Groundedness policy**: contract Q&A and health outputs are produced only from extracted contract text chunks and include evidence quotes + locations.
3. **Deterministic schemas**: service-layer outputs use fixed JSON keys for downstream reliability.
4. **Pipeline Analysis is separate from Contract Health**:
   - Pipeline Analysis = sales/delivery opportunity funnel metrics.
   - Contract Health = legal/commercial risk and contract quality dimensions.
5. **Page references** are not always available after plain-text extraction; therefore evidence locations use section labels and character offset ranges.
6. **Self-test mode** supports offline deterministic checks even when API is unavailable; if API is reachable, it additionally runs full API flow tests.
7. Existing environment variable behavior is preserved (`SECRET_KEY` remains required at startup with clear runtime error if missing).


## Benchmark Comparison feature

### Feature flag
- `BENCHMARK_ENABLED=true` enables `/benchmark/*` APIs and the Streamlit Benchmark page.
- `BENCHMARK_ENABLED=false` hides/blocks benchmark functionality.

### Seed benchmark corpus
- Seed file: `tests/fixtures/benchmark_seed.json`
- Ingest via API (admin/dev account or `BENCHMARK_ALLOW_ALL_INGEST=true`):
  - `POST /benchmark/ingest` with JSON `{"use_repo_seed": true}`

### Run tests
- `PYTHONPATH=contract-analysis-platform pytest -q contract-analysis-platform/tests`

### Run self-test
- `PYTHONPATH=contract-analysis-platform python -m backend.selftest`
