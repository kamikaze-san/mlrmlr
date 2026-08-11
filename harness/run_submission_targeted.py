"""
Same production pipeline as run_submission.py (same CSV format, same
resumability/atomic-write design, same make_rlm/ask), but processes a
SPECIFIC list of question IDs in a SPECIFIC order instead of "next N
unanswered in file order" -- for the backward-from-0389, 10-at-a-time pass.

Extra safety beyond run_submission.py: distinguishes an expected clean stop
(ask() returning None via RLM_ERRORS -- budget/timeout/error-threshold, all
already caught inside a single question) from a genuinely unexpected
exception. Two unexpected exceptions in a row is treated as a systemic
problem (API/auth/connection, not a single bad question) and stops the
WHOLE batch immediately rather than burning through the rest of the list.

Env vars:
    TARGET_QIDS   required -- comma-separated list of qids to process, in
                  the order given.
"""
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

DATASET = os.environ.get("DATASET_ROOT", r"C:\Users\NewGr\Downloads\BITS-Hackathon-Dataset-revised")
QUESTIONS_PATH = os.path.join(DATASET, "questions.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "submission.csv")


def load_questions() -> list[dict]:
    data = json.loads(open(QUESTIONS_PATH, encoding="utf-8").read())
    return data["questions"]


def load_existing_answers() -> dict[str, str]:
    if not os.path.exists(OUTPUT_PATH):
        return {}
    answers = {}
    with open(OUTPUT_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            answers[row["question_id"]] = row["answer"]
    return answers


def write_all_answers(answers: dict[str, str], order: list[str]) -> None:
    tmp_path = OUTPUT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["question_id", "answer"])
        for qid in order:
            writer.writerow([qid, answers.get(qid, "")])
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, OUTPUT_PATH)


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    target_qids = [q.strip() for q in os.environ.get("TARGET_QIDS", "").split(",") if q.strip()]
    if not target_qids:
        sys.exit("Set TARGET_QIDS (comma-separated) before running.")

    questions = load_questions()
    by_id = {q["qid"]: q for q in questions}
    order = [q["qid"] for q in questions]  # full file order, for a complete/consistent CSV
    answers = load_existing_answers()

    print(f"Targeted batch: {len(target_qids)} qids -> {target_qids}")

    total_in_tokens = total_out_tokens = total_calls = 0
    n_processed = 0
    consecutive_unexpected_errors = 0
    start_time = time.time()

    for qid in target_qids:
        if qid not in by_id:
            print(f"SKIP {qid}: not present in questions.json")
            continue
        if answers.get(qid, "").strip():
            print(f"SKIP {qid}: already answered ({answers[qid]})")
            continue

        q = by_id[qid]
        rlm = make_rlm(persistent=True)  # fresh session every question
        usage: dict = {}
        clean_stop = False
        try:
            got = ask(rlm, qid, q["question"], usage_out=usage)
            clean_stop = got is None  # ask() already caught RLM_ERRORS cleanly if so
            consecutive_unexpected_errors = 0
        except Exception as e:
            print(f"{qid} -- UNEXPECTED ERROR: {e!r}")
            got = None
            consecutive_unexpected_errors += 1
            if consecutive_unexpected_errors >= 2:
                print("\nSTOPPING BATCH: 2 unexpected errors in a row -- looks systemic "
                      "(API/auth/connection), not a single bad question. Awaiting instructions.")
                break

        answers[qid] = str(got) if got is not None else "0"
        write_all_answers(answers, order)

        for summary in usage.get("model_usage_summaries", {}).values():
            total_in_tokens += summary.get("total_input_tokens", 0)
            total_out_tokens += summary.get("total_output_tokens", 0)
            total_calls += summary.get("total_calls", 0)

        n_processed += 1
        tag = " [CLEAN STOP -- budget/timeout/error-threshold]" if clean_stop else ""
        elapsed = time.time() - start_time
        print(
            f"{qid} ({q['answer_type']}) -> {answers[qid]}{tag}   "
            f"[running: {total_calls} calls, {total_in_tokens} in / {total_out_tokens} out tok, "
            f"{elapsed:.0f}s]"
        )

    print("\nDONE for this batch.")
    print(f"Processed {n_processed}/{len(target_qids)} in this invocation.")
    print(f"Totals: {total_calls} calls, {total_in_tokens} input tokens, "
          f"{total_out_tokens} output tokens, {time.time() - start_time:.0f}s elapsed.")


if __name__ == "__main__":
    main()
