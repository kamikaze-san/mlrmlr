"""Test the DB-augmented harness against 5 real hidden-set (HV-IC-*) questions
with independently-verified gold answers from earlier this session (hand
document reads + cross-validation, not sample_questions.json examples). Two
anaphoric-narrow and one explicit-wide gotcha #7 scope cases, two gotcha #12
gap/awarded-vs-invoiced cases -- exactly the trap patterns the DB layer
hasn't been exercised against yet."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

DATASET = os.environ.get("DATASET_ROOT", r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset-revised")

KNOWN = {
    "HV-IC-0001": 129400000,     # anaphoric "for that client" -> narrow, Rajesh Rao's own NEDA work
    "HV-IC-0028": 1329700000,    # anaphoric "to that client" -> narrow, Sunita Joshi's own NEDA work
    "HV-IC-0055": 2728865201,    # gap: Mahanadi Steel Corp awarded - invoiced
    "HV-IC-0229": 2341700000,    # explicit "to Suvarna Projects Limited" -> wide, whole client
    "HV-IC-0284": 875511822,     # gap: Meridian Constructors & Co. secured - billed
}


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    data = json.loads(open(os.path.join(DATASET, "questions.json"), encoding="utf-8").read())
    by_id = {q["qid"]: q for q in data["questions"]}

    for qid, expected in KNOWN.items():
        q = by_id[qid]
        rlm = make_rlm(persistent=True)
        usage: dict = {}
        start = time.time()
        got = ask(rlm, qid, q["question"], usage_out=usage)
        elapsed = time.time() - start

        ok = isinstance(got, (int, float)) and abs(got - expected) < max(1, abs(expected) * 0.005)
        in_tok = out_tok = calls = 0
        for summary in usage.get("model_usage_summaries", {}).values():
            in_tok += summary.get("total_input_tokens", 0)
            out_tok += summary.get("total_output_tokens", 0)
            calls += summary.get("total_calls", 0)

        print(f"\n>>> RESULT {qid} -> got={got} expected={expected} match={ok} "
              f"time={elapsed:.0f}s in={in_tok} out={out_tok} calls={calls}")


if __name__ == "__main__":
    main()
