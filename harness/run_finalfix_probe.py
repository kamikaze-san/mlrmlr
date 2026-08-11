"""Targeted 2-question probe: HS-IC-0005 and HS-IC-0008, the two worst
offenders for "FINAL value failed validation" (23 and 10 occurrences
respectively across earlier runs) and excessive re-verification. Checks
whether the few-shot GOOD/BAD rewrite of the CRITICAL OUTPUT REQUIREMENT
actually cuts those down, without spending on a full 10-question batch."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

DATASET = os.environ.get("DATASET_ROOT", r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset-revised")
TARGET_QIDS = os.environ.get("PROBE_QIDS", "HS-IC-0005,HS-IC-0008").split(",")


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    data = json.loads(open(os.path.join(DATASET, "sample_questions.json"), encoding="utf-8").read())
    by_id = {q["qid"]: q for q in data["questions"]}

    for qid in TARGET_QIDS:
        q = by_id[qid]
        expected = q["answer"]
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

        print(f"\n>>> RESULT {qid} [{q.get('shape')}] -> got={got} expected={expected} "
              f"match={ok} time={elapsed:.0f}s in={in_tok} out={out_tok} calls={calls}")


if __name__ == "__main__":
    main()
