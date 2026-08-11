"""Two synthetic, hand-verified workbook questions -- no sample_questions.json
involvement, since none of the 25 samples touch the .xlsx workbooks at all.
Gold answers independently confirmed by direct summation of the source data
before this script was written (see conversation, not re-derived here)."""
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
     330010947),
    ("WB-02",
     "Before locking in the final board presentation for FY 2023-24, what "
     "was the combined total credit turnover recorded across all Contract "
     "Revenue streams in the trial balance?",
     2421825979),
]


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    rlm = make_rlm(persistent=True)
    results = []
    for label, question, gold in CASES:
        got = ask(rlm, label, question)
        score = score_one(gold, got)
        results.append((label, gold, got, score))

    print("\n\n" + "=" * 70)
    print(f"{'id':8s} {'gold':>15s} {'got':>15s}  score")
    for label, gold, got, score in results:
        mark = "OK " if score == 1.0 else f"{score:.1f}"
        print(f"{label:8s} {str(gold):>15s} {str(got):>15s}  {mark}")
    total = sum(r[3] for r in results)
    print(f"\nTOTAL {total:.1f} / {len(results)}")


if __name__ == "__main__":
    main()
