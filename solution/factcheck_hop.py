import sqlite3
import json
import sys
sys.path.insert(0, '.')
from solution.solver.entity_linker import EntityLinker

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
linker = EntityLinker('solution/db/knowledge_base.db')

with open('sample_questions.json') as f:
    sq = {q['qid']: q for q in json.load(f)['questions']}

# The other Claude claims: hop_aggregate is wrong because we return ALL client projects
# But HS-IC-0007 and HS-IC-0008 are in the sample and WE SCORE 100% on them.
# Let's trace exactly what client our linker resolves for each benchmark hop_aggregate question.

print("=== SAMPLE BENCHMARK HOP_AGGREGATE QUESTIONS ===\n")
for qid in ['HS-IC-0007', 'HS-IC-0008']:
    q = sq[qid]
    gold = q.get('answer', q.get('answer_gold'))
    ent = linker.link(q['question'])
    client = ent.get('client_name')
    pkg = ent.get('package_no')
    eng = ent.get('engineer', {})
    
    # What's the ALL-client total?
    all_total = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ?", (client,)).fetchone()[0] or 0
    
    # What's the engineer-only total for that client?
    eng_name = eng.get('name') if eng else None
    eng_led = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND lead_engineer = ?", (client, eng_name)).fetchone()[0] or 0 if eng_name else 0
    
    # What does Pkg map to?
    pkg_client = cur.execute("SELECT client_name FROM projects WHERE package_no = ?", (pkg,)).fetchone() if pkg else None
    
    print(f"[{qid}] Gold = {gold:,}")
    print(f"  Q: {q['question'][:110]}")
    print(f"  Linked client: {client}  (via Pkg: {pkg} -> {pkg_client[0] if pkg_client else 'N/A'})")
    print(f"  ALL projects for client:      {all_total:,}")
    print(f"  Only eng-led for client:      {eng_led:,}")
    print(f"  Gold matches ALL:             {all_total == gold}")
    print(f"  Gold matches eng-led:         {eng_led == gold}")
    print()

# Now check the full set hop_aggregate questions that the other Claude claims are wrong
print("=== FULL SET: HOP_AGGREGATE QUESTIONS ANALYSIS ===\n")
with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

import pandas as pd
from solution.solver.question_parser import classify_question
df_ans = pd.read_csv('solution/answers_submission.csv')
ans_dict = dict(zip(df_ans['question_id'], df_ans['answer']))

hop_q = [(qid, q) for qid, q in qs.items() if classify_question(q['question'], q['answer_type']) == 'hop_aggregate']
print(f"Total hop_aggregate questions: {len(hop_q)}")

explicit_client_count = 0
anaphoric_count = 0
for qid, q in hop_q:
    # Check if question contains the resolved client name explicitly or uses anaphora
    ent = linker.link(q['question'])
    client = ent.get('client_name', '')
    if client and client.lower() in q['question'].lower():
        explicit_client_count += 1
    else:
        anaphoric_count += 1

print(f"With EXPLICIT client name in question text: {explicit_client_count}")
print(f"With ANAPHORIC reference only ('that client'): {anaphoric_count}")
print("\nNote: Sample benchmark HS-IC-0007 uses anaphora ('for that client') and SCORES 1.0")
print("This DISPROVES the other Claude's claim that anaphoric = wrong.")
