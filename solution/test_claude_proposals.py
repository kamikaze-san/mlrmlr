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

print("=" * 80)
print("TESTING CLAUDE'S FIX #1 ON SAMPLE BENCHMARK")
print("=" * 80)

for q in sample:
    qid = q['qid']
    qtxt = q['question']
    shape = q.get('shape')
    gold = q.get('answer', q.get('answer_gold'))
    if shape == 'hop_aggregate':
        ent = linker.link(qtxt)
        eng = ent.get('engineer')
        client = ent.get('client_name')
        
        txt_lower = qtxt.lower()
        is_anaphoric = bool(re.search(r'\b(that client|to them|for them|delivered to them|done for that)\b', txt_lower))
        
        print(f"[{qid}] Gold = {gold:,}")
        print(f"  Q: {qtxt}")
        print(f"  is_anaphoric: {is_anaphoric} | client: {client} | eng: {eng['name'] if eng else None}")

print("\n" + "=" * 80)
print("TESTING CLAUDE'S 7 CONFIRMED CASES IN FULL DATASET")
print("=" * 80)

cases = ['HV-IC-0001', 'HV-IC-0028', 'HV-IC-0111', 'HV-IC-0149', 'HV-IC-0206', 'HV-IC-0224', 'HV-IC-0260', 'HV-IC-0302', 'HV-IC-0343']

for qid in cases:
    if qid not in qs:
        print(f"[{qid}] NOT FOUND in questions.json")
        continue
    q = qs[qid]
    qtxt = q['question']
    ent = linker.link(qtxt)
    eng = ent.get('engineer')
    client = ent.get('client_name')
    eng_name = eng['name'] if eng else None
    
    txt_lower = qtxt.lower()
    is_anaphoric = bool(re.search(r'\b(that client|to them|for them|delivered to them|done for that)\b', txt_lower))
    
    # 1. Total for Client (Our current logic)
    tot_client = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ?", (client,)).fetchone()[0] if client else 0
    # 2. Total for Engineer on that Client
    tot_eng_client = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND lead_engineer = ?", (client, eng_name)).fetchone()[0] if client and eng_name else 0
    # 3. Claude's query: Total for Engineer across ALL clients in DB
    tot_eng_all = cur.execute("SELECT SUM(value_inr) FROM projects WHERE lead_engineer LIKE ?", (f"%{eng_name}%",)).fetchone()[0] if eng_name else 0
    
    print(f"\n[{qid}] Client: {client} | Eng: {eng_name}")
    print(f"  Q: {qtxt}")
    print(f"  is_anaphoric regex matched: {is_anaphoric}")
    print(f"  Option 1 (Current: All projects for Client):              {tot_client:,}")
    print(f"  Option 2 (Engineer-led projects for THAT Client):         {tot_eng_client:,}")
    print(f"  Option 3 (Claude's SQL: Engineer projects ALL Clients):    {tot_eng_all:,}")
