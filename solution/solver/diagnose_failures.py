import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from solution.solver.llm_engine import LLMEngine, get_db_connection
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

    for q in qs:
        # 1. What did the deterministic resolver find, on its own -- no LLM.
        _section, info = engine._build_resolved_entities_section(q['question'])

        # 2. What SQL did the LLM actually write, and what did it execute to.
        conn = get_db_connection(engine.db_path)
        cur = conn.cursor()
        system_prompt = engine._build_system_prompt()
        user_prompt = engine._build_user_prompt(q['question'], q['answer_type'])
        raw_resp = client.generate(prompt=user_prompt, system=system_prompt, json_mode=True, temperature=0.0)
        sql = None
        if raw_resp:
            try:
                sql = json.loads(raw_resp).get('sql')
            except Exception:
                sql = raw_resp[:200]
        val = None
        err = None
        if sql:
            try:
                cur.execute(sql)
                row = cur.fetchone()
                val = row[0] if row else None
            except Exception as e:
                err = str(e)
        conn.close()

        s = score_one(q['answer'], val)
        flag = 'OK' if s > 0.98 else 'WRONG'
        print(f"=== {q['qid']} ({flag}) shape={q.get('shape')} gold={q['answer']} first_sql_result={val} ===")
        print(f"  resolver found: {info}")
        print(f"  SQL: {sql}")
        if err:
            print(f"  SQL ERROR: {err}")
        print()


if __name__ == '__main__':
    main()
