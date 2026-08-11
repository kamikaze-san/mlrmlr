"""
Subagent-mode check on the two workbook (.xlsx -> extracted text) questions --
the one document type not covered by the first two compare scripts. Gold
answers hand-verified by direct summation of the source data (see
run_workbook_test.py).

Each question runs in its own fresh isolated session, same as the other
compare scripts. WB-01's original baseline was first-in-session (clean);
WB-02's had light carryover from WB-01 in that same session.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

sys.path.append(r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset")
from evaluate import score_one  # noqa: E402

CASES = [
    ("WB-01",
     "Quick sanity check on the Jal Nigam, Gujarat account from our sales "
     "ledger receivables ageing — what is the current total net outstanding "
     "balance in rupees we're still owed across all invoices for this client?",
     330010947,
     {"calls": 8, "in": 58696, "out": 3791, "got": 330010947.0, "clean_baseline": True}),
    ("WB-02",
     "Before locking in the final board presentation for FY 2023-24, what "
     "was the combined total credit turnover recorded across all Contract "
     "Revenue streams in the trial balance?",
     2421825979,
     {"calls": 9, "in": 98211, "out": 4081, "got": 2421825979.0, "clean_baseline": False}),
]


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    results = []
    for label, question, gold, baseline in CASES:
        rlm = make_rlm(persistent=True, use_subagents=True)
        got = ask(rlm, f"{label} (subagent mode)", question)
        score = score_one(gold, got)
        results.append((label, gold, got, score, baseline))

        tag = "" if baseline["clean_baseline"] else "  [baseline has light session carryover]"
        print(f"\n--- {label} COMPARISON ---{tag}")
        print(f"  baseline (direct reads): {baseline['calls']} calls, "
              f"{baseline['in']} in / {baseline['out']} out tokens -> {baseline['got']}")
        print(f"  subagent mode:           see USAGE above -> {got}")
        print(f"  gold: {gold}  score: {score}")

    print("\n\n" + "=" * 70)
    print(f"{'id':8s} {'gold':>15s} {'got':>15s}  score")
    for label, gold, got, score, baseline in results:
        mark = "OK " if score == 1.0 else f"{score:.1f}"
        print(f"{label:8s} {str(gold):>15s} {str(got):>15s}  {mark}")
    total = sum(r[3] for r in results)
    print(f"\nTOTAL {total:.1f} / {len(results)}")


if __name__ == "__main__":
    main()
