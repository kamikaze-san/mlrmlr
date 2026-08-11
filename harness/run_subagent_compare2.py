"""
Second subagent-mode spot check: 5 questions with independently-verified gold
answers, picked for a spread of failure modes rather than more of the same
shape as the first check (HV-IC-0001/0003, both plain multi-doc aggregation,
both already fixed by subagent mode).

Each question runs in its OWN fresh isolated session (use_subagents=True),
same structure as the first compare script.

Baseline fairness note -- not all 5 baselines below are apples-to-apples:
  - HARD-01 and HS-IC-0007 were the FIRST question in their original
    session -- clean, uncontaminated baselines.
  - HS-IC-0006 and HS-IC-0025 were 3rd-4th in a longer batch (session depth
    2-4 with periodic reset every 5) -- their baseline token counts include
    real carryover from prior questions in that batch, not just their own
    document reads. Treat the token comparison for these two as optimistic/
    directional, not a clean delta. Correctness is still a clean signal
    regardless of session depth.
  - HS-IC-0017 was 3rd in a 3-question session (after 0007, 0008) -- same
    caveat, lighter carryover (only 2 prior questions).

Gold answers: HARD-01 from run_hard_test.py (hand-verified against source
docs). The four HS-IC-* golds are from BITS-Hackathon-Dataset/sample_questions.json
directly (the real released sample answers).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

sys.path.append(r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset")
from evaluate import score_one  # noqa: E402

DATASET = os.environ.get("DATASET_ROOT", r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset")

CASES = [
    ("HARD-01",
     "Cross-checking our project delivery records against Meera Roy's PMP "
     "certification issued on March 10, 2021, what is the combined total "
     "outstanding receivables balance currently owed to us across all client "
     "accounts for which she led a completed project after her certification "
     "date?",
     440403101,
     {"calls": 17, "in": 192253, "out": 22853, "got": 597573146.0, "clean_baseline": True}),
    ("HS-IC-0007", None, 2008199999,
     {"calls": 11, "in": 52509, "out": 4930, "got": 2008199999.0, "clean_baseline": True}),
    ("HS-IC-0006", None, 4,
     {"calls": 21, "in": 362354, "out": 13897, "got": 4.0, "clean_baseline": False}),
    ("HS-IC-0025", None, 634500000,
     {"calls": 3, "in": 211671, "out": 16957, "got": 634500000.0, "clean_baseline": False}),
    ("HS-IC-0017", None, 28700000,
     {"calls": 20, "in": 248825, "out": 17269, "got": 28700000.0, "clean_baseline": False}),
]


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    data = json.loads(open(os.path.join(DATASET, "sample_questions.json"), encoding="utf-8").read())
    by_id = {q["qid"]: q for q in data["questions"]}

    results = []
    for label, question, gold, baseline in CASES:
        if question is None:
            question = by_id[label]["question"]
        rlm = make_rlm(persistent=True, use_subagents=True)
        got = ask(rlm, f"{label} (subagent mode)", question)
        score = score_one(gold, got)
        results.append((label, gold, got, score, baseline))

        tag = "" if baseline["clean_baseline"] else "  [baseline has session carryover -- not a clean delta]"
        print(f"\n--- {label} COMPARISON ---{tag}")
        print(f"  baseline (direct reads): {baseline['calls']} calls, "
              f"{baseline['in']} in / {baseline['out']} out tokens -> {baseline['got']}")
        print(f"  subagent mode:           see USAGE above -> {got}")
        print(f"  gold: {gold}  score: {score}")

    print("\n\n" + "=" * 70)
    print(f"{'id':12s} {'gold':>15s} {'got':>15s}  score   base_in -> (see log)")
    for label, gold, got, score, baseline in results:
        mark = "OK " if score == 1.0 else f"{score:.1f}"
        print(f"{label:12s} {str(gold):>15s} {str(got):>15s}  {mark}   baseline_in={baseline['in']}")
    total = sum(r[3] for r in results)
    print(f"\nTOTAL {total:.1f} / {len(results)}")


if __name__ == "__main__":
    main()
