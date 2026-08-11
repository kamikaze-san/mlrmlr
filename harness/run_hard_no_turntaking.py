"""
Same "no turn-taking block + read_workbook_table" combo that won big on
WB-01/WB-02, tried on the 3 HARD 5-hop questions -- all three touch a
workbook at some point in their chain (HARD-01: ageing_workbook,
HARD-02: asset_register_workbook, HARD-03: boq_workbook). HARD-01 is also
our one known accuracy failure (baseline gave 597,573,146 vs gold
440,403,101 -- a reasoning error about excluding negative/credit balances,
not a retrieval error), so this doubles as a check on whether cleaner
structured access changes that outcome, not just cost.

Baselines for comparison (original, turn-taking present, old read_document path):
  HARD-01  17 calls  192,253 in / 22,853 out  -> WRONG (597573146)
  HARD-02  20 calls  325,671 in / 24,343 out  -> correct (1403600000), needed repair pass
  HARD-03  11 calls   72,716 in /  3,242 out  -> correct (221058142)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import GOTCHAS, RLM, RLMLogger, ask  # noqa: E402
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
    ("HARD-01",
     "Cross-checking our project delivery records against Meera Roy's PMP "
     "certification issued on March 10, 2021, what is the combined total "
     "outstanding receivables balance currently owed to us across all client "
     "accounts for which she led a completed project after her certification "
     "date?",
     440403101),
]
_UNUSED_CASES = [
    ("HARD-02",
     "Starting from Rahul Menon's PMP certificate, if we look at the single "
     "largest completed work he managed by executed value, what is the total "
     "acquisition cost in rupees of all company-owned and safety-certified "
     "equipment currently stationed in that project's state?",
     1403600000),
    ("HARD-03",
     "Looking at Rohit Singh's PMP portfolio for the ROB project in Gujarat "
     "commissioned by Jal Nigam, Gujarat (Pkg-71), what is the exact amount "
     "in rupees allocated to the single largest line item in that contract's "
     "BOQ register?",
     221058142),
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

    rlm = make_stripped_rlm()
    results = []
    for label, question, gold in CASES:
        got = ask(rlm, f"{label} (no turn-taking, new tool)", question)
        score = score_one(gold, got)
        results.append((label, gold, got, score))

    print("\n\n" + "=" * 70)
    print(f"{'id':10s} {'gold':>15s} {'got':>15s}  score")
    for label, gold, got, score in results:
        mark = "OK " if score == 1.0 else f"{score:.1f}"
        print(f"{label:10s} {str(gold):>15s} {str(got):>15s}  {mark}")
    total = sum(r[3] for r in results)
    print(f"\nTOTAL {total:.1f} / {len(results)}")


if __name__ == "__main__":
    main()
