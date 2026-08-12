import json, sqlite3, sys, os
from datetime import datetime
sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = [q for q in json.load(f)['questions'] if q['answer_type'] == 'days']

linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("=" * 80)
print("AUDITING ALL 24 DATE_SPAN QUESTIONS FOR PROJECT MATCHING")
print("=" * 80)

for q in qs:
    qtxt = q['question']
    ent = linker.link(qtxt)
    eng = ent.get('engineer')
    cert = ent.get('cert')
    proj = ent.get('project')
    pkg = ent.get('package_no')
    
    # Check all projects for engineer
    eng_projs = []
    if eng:
        eng_projs = cur.execute("SELECT package_no, project_name, completion_date FROM projects WHERE lead_engineer LIKE ?", (f"%{eng['name']}%",)).fetchall()
        
    print(f"[{q['qid']}]")
    print(f"  Q: {qtxt}")
    print(f"  Linked Engineer: {eng['name'] if eng else None}")
    print(f"  Linked Proj: {proj.get('project_name') if proj else None} ({proj.get('package_no') if proj else None})")
    
    # Check if another project of this engineer has a better text match in question
    best_proj = None
    best_matches = []
    for p_pkg, p_name, p_date in eng_projs:
        words = [w.lower() for w in p_name.replace('–', ' ').replace('-', ' ').split() if len(w) > 3 and w.lower() not in ['package', 'pkg']]
        match_count = sum(1 for w in words if w in qtxt.lower())
        if match_count > 0:
            best_matches.append((p_pkg, p_name, p_date, match_count))
            
    best_matches.sort(key=lambda x: x[3], reverse=True)
    if best_matches:
        top_match = best_matches[0]
        curr_pkg = proj.get('package_no') if proj else None
        if top_match[0] != curr_pkg:
            print(f"  *** MISMATCH DETECTED ***")
            print(f"      Currently linked: {curr_pkg}")
            print(f"      Better match:     {top_match[0]} - {top_match[1]} (score: {top_match[3]})")
    print()
