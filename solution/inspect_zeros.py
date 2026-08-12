import json, sqlite3, sys, os
sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
from solution.solver.query_engine import QueryEngine

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

engine = QueryEngine()
linker = EntityLinker('solution/db/knowledge_base.db')

for qid in ['HV-IC-0054', 'HV-IC-0090', 'HV-IC-0280']:
    q = qs[qid]
    qtxt = q['question']
    s = classify_question(qtxt, q['answer_type'])
    ent = linker.link(qtxt)
    ans = engine.solve_question(s, qtxt, ent)
    print(f"[{qid}] Shape: {s} | Ans: {ans}")
    print(f"  Client: {ent.get('client_name')} | Eng: {ent.get('engineer')}")
    print(f"  Q: {qtxt}\n")
