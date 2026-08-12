import sys, json
sys.path.insert(0, '.')
from solution.solver.query_engine import QueryEngine
from solution.solver.entity_linker import EntityLinker

engine = QueryEngine()
linker = EntityLinker('solution/db/knowledge_base.db')

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

test_qids = ['HV-IC-0226', 'HV-IC-0300', 'HV-IC-0328', 'HV-IC-0185', 'HV-IC-0223']
for qid in test_qids:
    q = qs[qid]
    ent = linker.link(q['question'])
    ans = engine.solve_question(qid, q['question'], q['answer_type'])
    excl = ent['excluded_category']
    client = ent['client_name']
    print(f"[{qid}] excl='{excl}' | client='{client}' | answer={ans:,}")
    print(f"  Q: {q['question'][:100]}")
    print()
