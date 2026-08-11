"""Standalone test of 10 high-risk questions through the harness with the new
gotcha #12 (awarded-invoiced-gap vs outstanding-receivables distinction).
Does NOT touch submission.csv/submission_v1.csv -- this is purely to check
whether DeepSeek + the updated prompt gets these right, compared against
values already independently verified by hand where we have them."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

DATASET = os.environ.get("DATASET_ROOT", r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset-revised")

QIDS = ['HV-IC-0055', 'HV-IC-0284', 'HV-IC-0028', 'HV-IC-0149', 'HV-IC-0206',
        'HV-IC-0193', 'HV-IC-0292', 'HV-IC-0044', 'HV-IC-0051', 'HV-IC-0287']

# known-correct values from independent verification, where we have them
KNOWN = {
    'HV-IC-0055': 2728865201,
    'HV-IC-0284': 875511822,
}


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    data = json.loads(open(os.path.join(DATASET, "questions.json"), encoding="utf-8").read())
    by_id = {q["qid"]: q for q in data["questions"]}

    for qid in QIDS:
        rlm = make_rlm(persistent=True)
        got = ask(rlm, qid, by_id[qid]["question"])
        known = KNOWN.get(qid)
        if known is not None:
            match = got is not None and abs(got - known) < max(1, abs(known) * 0.001)
            tag = f"  [known correct: {known}, {'MATCH' if match else 'DIFFERS'}]"
        else:
            tag = ""
        print(f"\n>>> RESULT {qid}: {got}{tag}")


if __name__ == "__main__":
    main()
