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
    # Each worker gets its own engine/client -- sqlite connections and
    # requests sessions aren't safe to share across threads.
    client = OllamaClient(model=model)
    engine = LLMEngine(db_path=db_path, ollama_client=client)
    t0 = time.time()
    try:
        pred = engine.solve(q['question'], q['answer_type'], verbose=False)
    except Exception as e:
        pred = None
    elapsed = time.time() - t0
    return q['qid'], q.get('shape'), q['answer'], pred, elapsed


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else 'qwen3:4b-instruct'
    with open('sample_questions.json', encoding='utf-8') as f:
        qs = json.load(f)
    qs = qs if isinstance(qs, list) else qs.get('questions', [])

    db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'knowledge_base.db')

    print(f"model: {model}", flush=True)
    results = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(solve_one, q, db_path, model) for q in qs]
        for fut in as_completed(futures):
            results.append(fut.result())
    total_elapsed = time.time() - t0

    results.sort(key=lambda r: r[0])
    total = 0.0
    exact = 0
    n = 0
    for qid, shape, gold, pred, elapsed in results:
        s = score_one(gold, pred)
        total += s
        n += 1
        if pred is not None and abs(float(pred) - float(gold)) < 1e-6:
            exact += 1
        flag = 'OK' if s > 0.98 else ('CLOSE' if s > 0.5 else 'WRONG')
        print(f"{qid}  shape={shape!s:20s} gold={gold!s:15s} pred={pred!s:15s} score={s:.2f} ({elapsed:.1f}s) {flag}", flush=True)

    print()
    print(f"exact matches: {exact}/{n}")
    print(f"proportional-credit total: {total:.2f}/{n} = {total/n:.1%}")
    print(f"wall-clock time (4 workers): {total_elapsed:.1f}s ({total_elapsed/n:.2f}s/question average)")


if __name__ == '__main__':
    main()
