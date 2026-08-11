"""Test the rewritten gotcha #7 (anaphoric vs explicit client naming) in both
directions: HV-IC-0028 (anaphoric -- should resolve narrow/engineer-only) and
HV-IC-0229 (explicit client name -- should resolve wide/whole-client)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

DATASET = os.environ.get("DATASET_ROOT", r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset-revised")

KNOWN = {
    'HV-IC-0028': 1329700000,   # anaphoric -- narrow (Sunita Joshi's own NEDA work)
    'HV-IC-0229': 2341700000,   # explicit "Suvarna Projects Limited" -- wide (whole client)
}


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    data = json.loads(open(os.path.join(DATASET, "questions.json"), encoding="utf-8").read())
    by_id = {q["qid"]: q for q in data["questions"]}

    for qid, known in KNOWN.items():
        rlm = make_rlm(persistent=True)
        got = ask(rlm, qid, by_id[qid]["question"])
        match = got is not None and abs(got - known) < max(1, abs(known) * 0.001)
        print(f"\n>>> RESULT {qid}: {got}  [known correct: {known}, {'MATCH' if match else 'DIFFERS'}]")


if __name__ == "__main__":
    main()
