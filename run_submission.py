#!/usr/bin/env python3
"""End-to-end pipeline entry point: ingest documents, build the knowledge
base, answer every question, write the submission CSV.

    python run_submission.py --docs <dir> --questions <path> --out <path>
"""
import argparse
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concurrent.futures import ThreadPoolExecutor, as_completed
from solution.db.build_database import populate_database, DB_PATH
from solution.solver.llm_engine import LLMEngine


def load_questions(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get('questions') or data.get('answers') or []


def solve_single(engine: LLMEngine, q: dict) -> tuple:
    qid = q.get('qid') or q.get('question_id')
    qtext = q.get('question') or q.get('question_text')
    atype = q.get('answer_type')
    try:
        ans = engine.solve(qtext, atype, verbose=False)
    except Exception as e:
        print(f'[run_submission] ERROR on {qid}: {e}', flush=True)
        ans = None
    return qid, ans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--docs', required=True, help='Directory of source PDF/XLSX documents')
    ap.add_argument('--questions', required=True, help='Path to the questions JSON file')
    ap.add_argument('--out', required=True, help='Path to write the submission CSV')
    ap.add_argument('--workers', type=int, default=4, help='Number of parallel worker threads (default: 4)')
    args = ap.parse_args()

    t0 = time.time()
    print(f'[run_submission] Ingesting documents from {args.docs} ...', flush=True)
    populate_database(db_path=DB_PATH, docs_root=args.docs)
    print(f'[run_submission] Ingestion + DB build done in {time.time()-t0:.1f}s', flush=True)

    print(f'[run_submission] Loading questions from {args.questions} ...', flush=True)
    questions = load_questions(args.questions)
    print(f'[run_submission] {len(questions)} questions to answer using {args.workers} worker(s)...', flush=True)

    engine = LLMEngine(db_path=DB_PATH)

    results_dict = {}
    t1 = time.time()

    if args.workers <= 1:
        # Sequential
        for i, q in enumerate(questions, 1):
            qid, ans = solve_single(engine, q)
            results_dict[qid] = ans
            if i % 10 == 0 or i == len(questions):
                elapsed = time.time() - t1
                print(f'[run_submission] {i}/{len(questions)} answered ({elapsed:.1f}s elapsed)', flush=True)
    else:
        # Parallel concurrent execution
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            future_to_qid = {pool.submit(solve_single, engine, q): (q.get('qid') or q.get('question_id')) for q in questions}
            completed = 0
            for future in as_completed(future_to_qid):
                qid, ans = future.result()
                results_dict[qid] = ans
                completed += 1
                if completed % 5 == 0 or completed == len(questions):
                    elapsed = time.time() - t1
                    print(f'[run_submission] {completed}/{len(questions)} answered ({elapsed:.1f}s elapsed, {completed/elapsed:.2f} q/s)', flush=True)

    # Write in original question order
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['question_id', 'answer'])
        for q in questions:
            qid = q.get('qid') or q.get('question_id')
            ans = results_dict.get(qid)
            w.writerow([qid, ans if ans is not None else ''])

    print(f'[run_submission] Wrote {len(questions)} answers to {args.out}', flush=True)
    print(f'[run_submission] Total run time: {time.time()-t0:.1f}s', flush=True)


if __name__ == '__main__':
    main()
