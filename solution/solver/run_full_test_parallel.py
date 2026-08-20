import csv
import json
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from solution.solver.llm_engine import LLMEngine
from solution.solver.ollama_client import OllamaClient


def score_one(gold, got):
    if got is None:
        return 0.0
    try:
        gold, got = float(gold), float(got)
    except (TypeError, ValueError):
        return 0.0
    if gold == 0:
        return 1.0 if got == 0 else 0.0
    return max(0.0, 1.0 - abs(got - gold) / abs(gold))


def solve_one(q, db_path, model):
    client = OllamaClient(model=model)
    engine = LLMEngine(db_path=db_path, ollama_client=client)
    t0 = time.time()
    try:
        pred = engine.solve(q['question'], q['answer_type'], verbose=False)
    except Exception:
        pred = None
    elapsed = time.time() - t0
    return q['qid'], q.get('answer_type'), pred, elapsed


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else 'qwen2.5-coder:7b-instruct'
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    out_csv = sys.argv[3] if len(sys.argv) > 3 else f"solution/solver/full_run_{model.replace(':','_').replace('.','_')}.csv"

    with open('questions.json', encoding='utf-8') as f:
        data = json.load(f)
    qs = data if isinstance(data, list) else data.get('questions', [])
    qs = [{'qid': q.get('qid') or q.get('question_id'), 'question': q.get('question') or q.get('question_text'),
           'answer_type': q.get('answer_type')} for q in qs]

    gold = {}
    with open('local_gold_answers.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            gold[row['question_id']] = row['answer']

    db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'knowledge_base.db')

    print(f"model: {model}, workers: {workers}, questions: {len(qs)}", flush=True)
    results = []
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(solve_one, q, db_path, model) for q in qs]
        for fut in as_completed(futures):
            results.append(fut.result())
            done += 1
            if done % 25 == 0 or done == len(qs):
                print(f"  {done}/{len(qs)} done ({time.time()-t0:.0f}s elapsed)", flush=True)
    total_elapsed = time.time() - t0

    results.sort(key=lambda r: r[0])
    total = 0.0
    exact = 0
    n = 0
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['question_id', 'answer', 'score'])
        for qid, atype, pred, elapsed in results:
            g = gold.get(qid)
            s = score_one(g, pred)
            total += s
            n += 1
            if pred is not None and g is not None:
                try:
                    if abs(float(pred) - float(g)) < 1e-6:
                        exact += 1
                except (TypeError, ValueError):
                    pass
            w.writerow([qid, pred, round(s, 3)])

    print()
    print(f"exact matches: {exact}/{n}")
    print(f"proportional-credit total: {total:.2f}/{n} = {total/n:.1%}")
    print(f"wall-clock time ({workers} workers): {total_elapsed:.1f}s ({total_elapsed/n:.2f}s/question average)")
    print(f"wrote per-question results to {out_csv}")


if __name__ == '__main__':
    main()
