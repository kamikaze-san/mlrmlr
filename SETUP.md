# Running this harness on a fresh machine

## 1. Install the RLM library (bundled, patched)

`rlm/` in this repo is a vendored copy of https://github.com/alexzhang13/rlm
(MIT licensed) with two small local patches on top, both required by
`harness/run_test.py`:

- `rlm/core/rlm.py` — adds an `output_validator` constructor argument. Called
  every time the REPL calls `FINAL()`; on failure the answer is rejected and
  fed back into the same conversation (REPL state intact) instead of being
  silently accepted or requiring a separate repair pass.
- `rlm/utils/parsing.py` — `find_code_blocks()` gets progressively looser
  fallback patterns (XML-tag drift, ```python-tagged fences, bare fences)
  beyond the documented ` ```repl ` fence, because weaker/local models drift
  off the strict format under load and would otherwise silently produce zero
  output with no way to tell what went wrong.

Install it in editable mode:
```bash
pip install -e ./rlm
```

## 2. Install the harness's own dependencies
```bash
pip install openai python-dateutil openpyxl
```
(`rlm`'s own dependencies — anthropic, google-genai, openai, portkey-ai,
python-dotenv, requests, rich — are pulled in automatically by step 1.)

## 3. Point the harness at this repo's data
```bash
export DATASET_ROOT="$(pwd)"          # this repo root has documents/, questions.json, document_index.csv
export MODEL_NAME="<your-model-id>"    # e.g. deepseek-v4-flash, or your local Qwen model id
export MODEL_BASE_URL="<your-endpoint>"  # e.g. https://api.deepseek.com, or http://localhost:PORT/v1
export MODEL_API_KEY="<key-or-anything>" # local OpenAI-compatible servers usually ignore this
```

## 4. Run
```bash
cd harness
python run_test.py          # 2-question smoke test
```

`harness/estate.db` (a pre-built SQLite knowledge layer over the corpus) and
`harness/text_cache/` (pre-extracted document text) are already included, so
no separate build step is needed to get started. `harness/db_build.py`
rebuilds `estate.db` from scratch if you ever need to (e.g. after a corpus
update).
