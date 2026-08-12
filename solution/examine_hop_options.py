import json
import sqlite3
import pandas as pd
import sys, os

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

hop_qs = [q for q in qs.values() if classify_question(q['question'], q['answer_type']) == 'hop_aggregate']

print(f"Total hop_aggregate questions: {len(hop_qs)}")

for q in hop_qs[:15]:
    qid = q['qid']
    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    eng = ent.get('engineer')
    eng_name = eng.get('name') if eng else None
    
    # 1. Total for client (all engineers)
    tot_client = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ?", (client,)).fetchone()[0] if client else 0
    # 2. Total for engineer on that client
    tot_eng_client = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND lead_engineer = ?", (client, eng_name)).fetchone()[0] if client and eng_name else 0
    # 3. Total for engineer across ALL clients
    tot_eng_all = cur.execute("SELECT SUM(value_inr) FROM projects WHERE lead_engineer = ?", (eng_name,)).fetchone()[0] if eng_name else 0
    
    print(f"\n[{qid}] Client: {client} | Eng: {eng_name}")
    print(f"  Q: {qtxt}")
    print(f"  Option A (All projects for Client):        {tot_client:,}")
    print(f"  Option B (Eng-led projects for Client):    {tot_eng_client:,}")
    print(f"  Option C (Eng-led projects across ALL):    {tot_eng_all:,}")
