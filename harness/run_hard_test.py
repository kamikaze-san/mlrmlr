"""Three hard, 5-hop synthetic questions spanning PMP certs -> completion
certs -> workbooks. Gold answers independently re-verified by hand against
the source documents before this script was written (not just trusted from
the coding agent that proposed them)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402
sys.path.append(r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset")
from evaluate import score_one  # noqa: E402

CASES = [
    ("HARD-01",
     "Cross-checking our project delivery records against Meera Roy's PMP "
     "certification issued on March 10, 2021, what is the combined total "
     "outstanding receivables balance currently owed to us across all client "
     "accounts for which she led a completed project after her certification "
     "date?",
     440403101),
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
    print(f"{'id':10s} {'gold':>15s} {'got':>15s}  score")
    for label, gold, got, score in results:
        mark = "OK " if score == 1.0 else f"{score:.1f}"
        print(f"{label:10s} {str(gold):>15s} {str(got):>15s}  {mark}")
    total = sum(r[3] for r in results)
    print(f"\nTOTAL {total:.1f} / {len(results)}")


if __name__ == "__main__":
    main()
