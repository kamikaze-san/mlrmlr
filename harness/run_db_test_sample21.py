"""
Live end-to-end test of the query_db-equipped harness against all 21
sample_questions.json questions (known gold answers). Fresh RLM session per
question (matches the production pattern). Captures wall time and token
usage per question alongside correctness, so we can see whether wiring
query_db into custom_tools actually reduces token/time cost versus the
pre-DB baseline, not just whether it's still correct.

Writes results incrementally to run_db_test_sample21_results.jsonl so
progress survives interruption and can be tailed while running.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

DATASET = os.environ.get("DATASET_ROOT", r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset-revised")
RESULTS_PATH = os.environ.get(
    "RESULTS_PATH", os.path.join(os.path.dirname(__file__), "run_db_test_sample21_results.jsonl")
)
LIMIT_N = int(os.environ.get("LIMIT_N", "0")) or None


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    data = json.loads(open(os.path.join(DATASET, "sample_questions.json"), encoding="utf-8").read())
    questions = data["questions"][:LIMIT_N] if LIMIT_N else data["questions"]

    # resume support: skip qids already present in the results file
    done = set()
    if os.path.exists(RESULTS_PATH):
        for line in open(RESULTS_PATH, encoding="utf-8"):
            line = line.strip()
            if line:
                done.add(json.loads(line)["qid"])

    with open(RESULTS_PATH, "a", encoding="utf-8") as out:
        for q in questions:
            qid = q["qid"]
            if qid in done:
                print(f"SKIP {qid}: already have a result")
                continue

            expected = q["answer"]
            rlm = make_rlm(persistent=True)
            usage: dict = {}
            start = time.time()
            try:
                got = ask(rlm, qid, q["question"], usage_out=usage)
            except Exception as e:
                got = None
                usage["error"] = repr(e)
            elapsed = time.time() - start

            ok = None
            if isinstance(got, (int, float)) and isinstance(expected, (int, float)):
                tol = max(1, abs(expected) * 0.005)
                ok = abs(got - expected) < tol

            in_tok = out_tok = calls = 0
            for summary in usage.get("model_usage_summaries", {}).values():
                in_tok += summary.get("total_input_tokens", 0)
                out_tok += summary.get("total_output_tokens", 0)
                calls += summary.get("total_calls", 0)

            record = {
                "qid": qid, "question": q["question"], "expected": expected,
                "got": got, "match": ok, "elapsed_s": round(elapsed, 1),
                "input_tokens": in_tok, "output_tokens": out_tok, "calls": calls,
                "shape": q.get("shape"),
            }
            out.write(json.dumps(record) + "\n")
            out.flush()
            print(f"{qid} [{q.get('shape')}] -> got={got} expected={expected} "
                  f"match={ok} time={elapsed:.0f}s in={in_tok} out={out_tok} calls={calls}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
