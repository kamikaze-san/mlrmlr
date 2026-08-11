"""
Isolate whether the "HOW TURNS WORK" addition to GOTCHAS itself changed
model behavior (more iterations / more tokens), separate from ordinary
run-to-run variance. Strips just that paragraph back out of GOTCHAS (does
NOT touch run_test.py -- the real fix stays in place there) and reruns
WB-01/WB-02 against the resulting near-original prompt.

Existing data points for comparison:
  true original (pre-any-edit):        WB-01  8 calls/58,696 in   WB-02  9 calls/98,211 in
  rerun, WITH turn-taking addition:     WB-01 17 calls/136,160 in  WB-02 16 calls/256,345 in
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import GOTCHAS, RLM, RLMLogger, RLM_ERRORS, ask  # noqa: E402
from tools import (  # noqa: E402
    list_documents, list_doc_types, read_document, grep_documents,
    verify_client_work_count, read_workbook_table,
)
from cache import cache_lookup, cache_save, cache_search  # noqa: E402

sys.path.append(r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset")
from evaluate import score_one  # noqa: E402

TURN_TAKING_BLOCK = (
    "\nHOW TURNS WORK -- read this carefully: you get exactly ONE response per\n"
    "turn, and you will NOT see any execution output until your NEXT turn. There\n"
    "is no way to check, mid-response, whether a code block \"worked\" -- nothing\n"
    "executes until your response is finished. Do not write the same or a similar\n"
    "code block multiple times in one response hoping to see if it runs this\n"
    "time -- it will not, and repeating it wastes your turn. Write ONE clean code\n"
    "block, stop, and wait for the real output on your next turn before deciding\n"
    "what to do next.\n"
)

assert TURN_TAKING_BLOCK in GOTCHAS, "turn-taking block text no longer matches run_test.py -- update this script"
STRIPPED_GOTCHAS = GOTCHAS.replace(TURN_TAKING_BLOCK, "\n")

CASES = [
    ("WB-01",
     "Quick sanity check on the Jal Nigam, Gujarat account from our sales "
     "ledger receivables ageing — what is the current total net outstanding "
     "balance in rupees we're still owed across all invoices for this client?",
     330010947),
    ("WB-02",
     "Before locking in the final board presentation for FY 2023-24, what "
     "was the combined total credit turnover recorded across all Contract "
     "Revenue streams in the trial balance?",
     2421825979),
]


def make_stripped_rlm() -> RLM:
    return RLM(
        backend="openai",
        backend_kwargs={
            "model_name": os.environ.get("MODEL_NAME", "deepseek-v4-flash"),
            "base_url": os.environ.get("MODEL_BASE_URL", "https://api.deepseek.com"),
            "api_key": os.environ.get("MODEL_API_KEY"),
        },
        environment="local",
        persistent=True,
        custom_tools={
            "list_documents": list_documents,
            "list_doc_types": list_doc_types,
            "read_document": read_document,
            "grep_documents": grep_documents,
            "verify_client_work_count": verify_client_work_count,
            "read_workbook_table": read_workbook_table,
            "cache_lookup": cache_lookup,
            "cache_search": cache_search,
            "cache_save": cache_save,
        },
        user_prologue=STRIPPED_GOTCHAS,
        max_iterations=20,
        max_budget=0.5,
        max_timeout=600,
        max_errors=4,
        verbose=False,
        logger=RLMLogger(log_dir=os.path.join(os.path.dirname(__file__), "logs")),
    )


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    print(f"stripped-prompt length: {len(STRIPPED_GOTCHAS)} chars "
          f"(original with turn-taking: {len(GOTCHAS)} chars)")

    results = []
    for label, question, gold in CASES:
        rlm = make_stripped_rlm()
        got = ask(rlm, f"{label} (no turn-taking block)", question)
        score = score_one(gold, got)
        results.append((label, gold, got, score))

    print("\n\n" + "=" * 70)
    print(f"{'id':8s} {'gold':>15s} {'got':>15s}  score")
    for label, gold, got, score in results:
        mark = "OK " if score == 1.0 else f"{score:.1f}"
        print(f"{label:8s} {str(gold):>15s} {str(got):>15s}  {mark}")


if __name__ == "__main__":
    main()
