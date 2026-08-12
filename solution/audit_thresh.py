import json
import sqlite3
import pandas as pd
import sys, os

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = json.load(f)['questions']

linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("=== AUDITING ALL 24 THRESHOLD_AGGREGATE QUESTIONS ===")
thresh_qs = [q for q in qs if classify_question(q['question'], q['answer_type']) == 'threshold_aggregate']

for q in thresh_qs:
    qid = q['qid']
    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    thresh = ent.get('threshold_inr')
    
    cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND value_inr >= ?", (client, thresh))
    res = cur.fetchone()[0]
    
    print(f"[{qid}] Sum: {res:,.0f} if res else 0 | Thresh: {thresh:,} | Client: {client}")
    if not thresh or thresh == 0 or not client:
        print(f"  SUSPECT/FAILED: {qtxt}\n")
