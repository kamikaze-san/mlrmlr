"""
Production run: answers every question in the real hidden-set questions.json
(371 questions) and writes submission.csv matching sample_submission.csv's
format (question_id,answer header). Incremental and resumable.

Resumability: on startup, loads any existing submission.csv into memory as
{question_id: answer}. Only BLANK/missing answers are (re)computed -- a
question that already has a real answer from a prior run is skipped, so
re-running after a crash picks up where it left off instead of redoing (and
re-paying for) already-answered questions.

Incremental writing: after every single question, the full answers dict is
rewritten to a temp file and atomically swapped into place (os.replace --
atomic on both POSIX and Windows). This is safer than plain append mode: a
crash mid-write leaves the previous good file intact instead of a
half-written row, and it naturally de-duplicates retried questions instead
of appending a second row for the same qid.

Own cost/token tracking: the DeepSeek backend never reports `total_cost` in
usage_summary (confirmed -- every usage dump this whole project has shown
only calls/input_tokens/output_tokens) so RLM's own max_budget is a silent
no-op with this backend. This script sums real token totals itself and
prints running totals as it goes, since that's the only signal we actually
have.

Env vars:
    SUBMISSION_LIMIT   optional int -- cap how many NEW questions to process
                       this invocation (for a bounded trial run). Unset =
                       process everything still unanswered.
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

# Recreate the RLM session every N questions to bound cross-question context
# growth/contamination (see conversation history -- HS-IC-0024 previously
# picked up an unrelated prior question's variables at session depth 13,
# fixed by periodic reset). Only validated on a small 8-question toy batch
# so far, not at this scale -- watch actual behavior and retune if sessions
# still look too deep/expensive before reset kicks in, or too shallow to let
# cache reuse help.
RESET_EVERY = 1


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

    questions = load_questions()
    order = [q["qid"] for q in questions]
    answers = load_existing_answers()
    n_already_done = sum(1 for qid in order if answers.get(qid, "").strip())
    print(f"{len(questions)} total questions, {n_already_done} already answered -- resuming")

    limit = os.environ.get("SUBMISSION_LIMIT")
    limit = int(limit) if limit else None

    total_in_tokens = total_out_tokens = total_calls = 0
    n_errors = 0
    n_processed_this_run = 0
    start_time = time.time()

    rlm = None
    for i, q in enumerate(questions):
        qid = q["qid"]
        if answers.get(qid, "").strip():
            continue
        if limit is not None and n_processed_this_run >= limit:
            print(f"\nSUBMISSION_LIMIT={limit} reached, stopping early (rest remain unanswered for next run).")
            break

        if rlm is None or n_processed_this_run % RESET_EVERY == 0:
            rlm = make_rlm(persistent=True)

        usage: dict = {}
        try:
            got = ask(rlm, qid, q["question"], usage_out=usage)
        except Exception as e:
            print(f"[{i + 1}/{len(questions)}] {qid} -- UNEXPECTED ERROR: {e!r}")
            got = None
            n_errors += 1

        answers[qid] = str(got) if got is not None else "0"
        write_all_answers(answers, order)

        for summary in usage.get("model_usage_summaries", {}).values():
            total_in_tokens += summary.get("total_input_tokens", 0)
            total_out_tokens += summary.get("total_output_tokens", 0)
            total_calls += summary.get("total_calls", 0)

        n_processed_this_run += 1
        elapsed = time.time() - start_time
        print(
            f"[{i + 1}/{len(questions)}] {qid} ({q['answer_type']}) -> {answers[qid]}   "
            f"[running: {total_calls} calls, {total_in_tokens} in / {total_out_tokens} out tok, "
            f"{elapsed:.0f}s, {n_errors} errors]"
        )

    n_done_total = sum(1 for qid in order if answers.get(qid, "").strip())
    print("\nDONE for this invocation.")
    print(f"Processed {n_processed_this_run} new questions this run; {n_done_total}/{len(questions)} total answered.")
    print(f"This run's totals: {total_calls} calls, {total_in_tokens} input tokens, "
          f"{total_out_tokens} output tokens, {n_errors} unexpected errors, "
          f"{time.time() - start_time:.0f}s elapsed.")
    if n_done_total < len(questions):
        print(f"{len(questions) - n_done_total} questions still unanswered -- rerun this script to continue.")


if __name__ == "__main__":
    main()
