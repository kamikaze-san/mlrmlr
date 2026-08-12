import json
import sqlite3
import pandas as pd
import sys, os
import re

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = json.load(f)['questions']

linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("=" * 80)
print("ANALYZING ALL 24 ANNUAL_DIFF QUESTIONS FOR SIGN CONVENTION")
print("=" * 80)

for q in qs:
    qtxt = q['question']
    txt_l = qtxt.lower()
    years = set(re.findall(r'\b(201\d|202\d)\b', txt_l))
    if len(years) >= 2:
        ent = linker.link(qtxt)
        client = ent.get('client_name')
        
        # Extract chronological order from question
        y_in_order = re.findall(r'\b(201\d|202\d)\b', txt_l)
        # Unique years in order of appearance
        seen = []
        for y in y_in_order:
            if y not in seen: seen.append(y)
            
        y1, y2 = seen[0], seen[1]
        v1 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND completion_date LIKE ?", (client, f"{y1}%")).fetchone()[0] or 0
        v2 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND completion_date LIKE ?", (client, f"{y2}%")).fetchone()[0] or 0
        
        signed_chron = v2 - v1 if int(y2) > int(y1) else v1 - v2
        signed_appear = v2 - v1
        abs_diff = abs(v2 - v1)
        
        print(f"[{q['qid']}] Client: {client}")
        print(f"  Years in Q: {seen} | v({y1})={v1:,}, v({y2})={v2:,}")
        print(f"  abs_diff:      {abs_diff:,}")
        print(f"  signed (y2-y1): {signed_appear:,}")
        print(f"  Q: {qtxt}\n")
