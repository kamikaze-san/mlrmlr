import json
import sqlite3
import pandas as pd
import sys, os
import re

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
from solution.solver.query_engine import QueryEngine

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
linker = EntityLinker('solution/db/knowledge_base.db')

with open('sample_questions.json') as f:
    sample = json.load(f)['questions']

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

def solve_hop_aggregate(qtxt, client, eng):
    txt_lower = qtxt.lower()
    is_anaphoric = bool(re.search(r'\b(that client|to them|for them|delivered to them|done for that)\b', txt_lower))
    
    eng_name = eng['name'] if eng else None
    if is_anaphoric and eng_name and client:
        cur.execute("SELECT SUM(value_inr) FROM projects WHERE lead_engineer LIKE ? AND client_name = ?", (f"%{eng_name}%", client))
        res = cur.fetchone()[0]
        return int(res) if res is not None else 0
    elif client:
        cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ?", (client,))
        res = cur.fetchone()[0]
        return int(res) if res is not None else 0
    elif eng_name:
        cur.execute("SELECT SUM(value_inr) FROM projects WHERE lead_engineer LIKE ?", (f"%{eng_name}%",))
        res = cur.fetchone()[0]
        return int(res) if res is not None else 0
    return 0

print("=== CHECKING SAMPLE BENCHMARK WITH CORRECTED ANAPHORIC HOP_AGGREGATE ===")
for q in sample:
    if q.get('shape') == 'hop_aggregate':
        qid = q['qid']
        qtxt = q['question']
        gold = q.get('answer', q.get('answer_gold'))
        ent = linker.link(qtxt)
        ans = solve_hop_aggregate(qtxt, ent.get('client_name'), ent.get('engineer'))
        print(f"[{qid}] Gold: {gold:,} | Ans: {ans:,} | Match: {gold == ans}")

print("\n=== THE 9 ANAPHORIC QUESTIONS IN FULL DATASET ===")
cases = ['HV-IC-0001', 'HV-IC-0028', 'HV-IC-0111', 'HV-IC-0149', 'HV-IC-0206', 'HV-IC-0224', 'HV-IC-0260', 'HV-IC-0302', 'HV-IC-0343']
for qid in cases:
    q = qs[qid]
    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    eng = ent.get('engineer')
    eng_name = eng['name'] if eng else None
    
    # Old (full client)
    old_ans = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ?", (client,)).fetchone()[0]
    # New (eng on that client)
    new_ans = solve_hop_aggregate(qtxt, client, eng)
    
    print(f"[{qid}] Client: {client} | Eng: {eng_name}")
    print(f"  OLD (full client):             {old_ans:,}")
    print(f"  NEW (eng on client):           {new_ans:,}")
    print(f"  Q: {qtxt[:100]}...\n")
