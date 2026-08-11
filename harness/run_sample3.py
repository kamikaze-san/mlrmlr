"""Run a hand-picked 3-question sample from the real sample_questions.json
through the harness, and score with evaluate.py's own logic -- a small,
cheap preview of what a real batch run would look like, before committing
to all 25."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402 -- import real `rlm` package first

# Appended, not inserted at front: BITS-Hackathon-Dataset/ contains its own
# subfolder literally named rlm/ (the cloned library repo) which would shadow
# the real installed `rlm` package if placed ahead of it on sys.path.
sys.path.append(r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset")
from evaluate import score_one  # noqa: E402

# Targeted retest, not a broad batch: session A is 5 cheap already-cached
# fillers (to advance session depth realistically, at near-zero cost) so that
# session B's reset actually gets exercised rather than trivially starting
# clean. Session B leads with the two entities that showed cache key drift
# before (Jharkhand Municipal Corporation typo in 0016, Asha Nair's 4-way
# guessing in 0010) to test cache_search, then HS-IC-0024 -- the one that
# previously got the wrong answer from cross-question variable contamination
# at session-depth 13 -- now sits at depth 3 of a FRESH session instead.
QIDS = ["HS-IC-0002", "HS-IC-0018", "HS-IC-0019", "HS-IC-0021", "HS-IC-0025",
        "HS-IC-0016", "HS-IC-0010", "HS-IC-0024"]

RESET_EVERY = 5

DATASET = os.environ.get("DATASET_ROOT", r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset")


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    data = json.loads(open(os.path.join(DATASET, "sample_questions.json"), encoding="utf-8").read())
    by_id = {q["qid"]: q for q in data["questions"]}

    rlm = None
    results = []
    for i, qid in enumerate(QIDS):
        if i % RESET_EVERY == 0:
            print(f"\n### fresh session starting at question {i} ({qid}) ###")
            rlm = make_rlm(persistent=True)
        q = by_id[qid]
        got = ask(rlm, qid, q["question"])
        gold = q["answer"]
        score = score_one(gold, got)
        results.append((qid, q["shape"], gold, got, score))

    print("\n\n" + "=" * 70)
    print(f"{'qid':12s} {'shape':22s} {'gold':>15s} {'got':>15s}  score")
    for qid, shape, gold, got, score in results:
        mark = "OK " if score == 1.0 else f"{score:.1f}"
        print(f"{qid:12s} {shape:22s} {str(gold):>15s} {str(got):>15s}  {mark}")
    total = sum(r[4] for r in results)
    print(f"\nTOTAL {total:.1f} / {len(results)}")


if __name__ == "__main__":
    main()
