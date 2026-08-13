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

from solution.db.build_database import populate_database, DB_PATH
from solution.solver.query_engine import QueryEngine


def load_questions(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get('questions') or data.get('answers') or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--docs', required=True, help='Directory of source PDF/XLSX documents')
    ap.add_argument('--questions', required=True, help='Path to the questions JSON file')
    ap.add_argument('--out', required=True, help='Path to write the submission CSV')
    args = ap.parse_args()

    t0 = time.time()
    print(f'[run_submission] Ingesting documents from {args.docs} ...', flush=True)
    populate_database(db_path=DB_PATH, docs_root=args.docs)
    print(f'[run_submission] Ingestion + DB build done in {time.time()-t0:.1f}s', flush=True)

    print(f'[run_submission] Loading questions from {args.questions} ...', flush=True)
    questions = load_questions(args.questions)
    print(f'[run_submission] {len(questions)} questions to answer', flush=True)

    engine = QueryEngine(db_path=DB_PATH)

    rows = []
    t1 = time.time()
    for i, q in enumerate(questions, 1):
        qid = q.get('qid') or q.get('question_id')
        qtext = q.get('question') or q.get('question_text')
        atype = q.get('answer_type')
        try:
            answer = engine.solve_question(qid, qtext, atype)
        except Exception as e:
            print(f'[run_submission] ERROR on {qid}: {e}', flush=True)
            answer = None
        rows.append((qid, answer))
        if i % 25 == 0 or i == len(questions):
            elapsed = time.time() - t1
            print(f'[run_submission] {i}/{len(questions)} answered ({elapsed:.1f}s elapsed)', flush=True)

    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['question_id', 'answer'])
        for qid, answer in rows:
            w.writerow([qid, answer if answer is not None else ''])

    print(f'[run_submission] Wrote {len(rows)} answers to {args.out}', flush=True)
    print(f'[run_submission] Total run time: {time.time()-t0:.1f}s', flush=True)


if __name__ == '__main__':
    main()
