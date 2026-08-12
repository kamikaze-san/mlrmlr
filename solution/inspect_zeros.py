import json, sys
sys.path.insert(0, '.')
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
from solution.solver.query_engine import QueryEngine

engine = QueryEngine()
linker = EntityLinker('solution/db/knowledge_base.db')

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

for qid in ['HV-IC-0215', 'HV-IC-0315']:
    q = qs[qid]
    s = classify_question(q['question'], q['answer_type'])
    ent = linker.link(q['question'])
    ans = engine.solve_question(qid, q['question'], q['answer_type'])
    print(f"[{qid}] shape={s} ans={ans}")
    print(f"  ent={ent}")
    print(f"  q={q['question']}")
    print()
