"""Targeted single-question retest: HV-IC-0001, the exact question that
just blew up to 82 code blocks in one turn after the turn-taking guidance
was removed. Testing the few-shot (good/bad example) replacement instead of
the removed verbose paragraph."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

DATASET = os.environ.get("DATASET_ROOT", r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset-latest")


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    data = json.loads(open(os.path.join(DATASET, "questions.json"), encoding="utf-8").read())
    by_id = {q["qid"]: q for q in data["questions"]}
    question = by_id["HV-IC-0001"]["question"]

    rlm = make_rlm(persistent=True)
    got = ask(rlm, "HV-IC-0001 (few-shot turn-taking)", question)
    print(f"\n\nRESULT: {got}  (gold: 2942400000, prior baseline: 12 calls/102925 in, "
          f"failed run: 56 calls/204236 in)")


if __name__ == "__main__":
    main()
