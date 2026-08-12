import json, sqlite3, sys, os
sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker
from solution.solver.query_engine import QueryEngine

with open('questions.json') as f:
    qs = json.load(f)['questions']

linker = EntityLinker('solution/db/knowledge_base.db')
engine = QueryEngine()
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("=== CHECKING ALL DATE_SPAN QUESTIONS (24 questions) ===")
date_span_qs = [q for q in qs if q['answer_type'] == 'days']
print(f"Total date_span questions: {len(date_span_qs)}")

for q in date_span_qs:
    qtxt = q['question']
    ent = linker.link(qtxt)
    ans = engine.solve_question('date_span', qtxt, ent)
    eng = ent.get('engineer')
    cert = ent.get('cert')
    proj = ent.get('project')
    pkg = ent.get('package_no')
    
    # Check if there are other candidate projects for this engineer in the DB
    candidate_projs = []
    if eng:
        candidate_projs = cur.execute("SELECT package_no, project_name, completion_date FROM projects WHERE lead_engineer LIKE ?", (f"%{eng['name']}%",)).fetchall()
        
    print(f"[{q['qid']}] Ans: {ans} days")
    print(f"  Q: {qtxt}")
    print(f"  Eng: {eng['name'] if eng else None} | Cert issue: {cert.get('issue_date') if cert else None}")
    print(f"  Linked Proj: {proj.get('project_name') if proj else None} ({proj.get('package_no') if proj else None}) comp: {proj.get('completion_date') if proj else None}")
    if len(candidate_projs) > 1:
        print(f"  All Eng Projs: {candidate_projs}")
    print()
