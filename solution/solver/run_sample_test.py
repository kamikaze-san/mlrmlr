import json
import time
import sys
import os

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


def main():
    with open('sample_questions.json', encoding='utf-8') as f:
        qs = json.load(f)
    qs = qs if isinstance(qs, list) else qs.get('questions', [])

    client = OllamaClient(model='qwen3:4b-instruct')
    engine = LLMEngine(ollama_client=client)

    total = 0.0
    exact = 0
    n = 0
    t0 = time.time()
    for q in qs:
        t1 = time.time()
        try:
            pred = engine.solve(q['question'], q['answer_type'], verbose=False)
        except Exception as e:
            pred = None
            print(f"ERROR {q['qid']}: {e}", flush=True)
        elapsed = time.time() - t1
        s = score_one(q['answer'], pred)
        total += s
        n += 1
        if pred is not None and abs(float(pred) - float(q['answer'])) < 1e-6:
            exact += 1
        flag = 'OK' if s > 0.98 else ('CLOSE' if s > 0.5 else 'WRONG')
        print(f"{q['qid']}  shape={q.get('shape'):20s} gold={q['answer']!s:15s} pred={pred!s:15s} score={s:.2f} ({elapsed:.1f}s) {flag}", flush=True)

    print()
    print(f"exact matches: {exact}/{n}")
    print(f"proportional-credit total: {total:.2f}/{n} = {total/n:.1%}")
    print(f"total time: {time.time()-t0:.1f}s")


if __name__ == '__main__':
    main()
