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

print("=== AUDITING ALL ANNUAL_DIFF QUESTIONS (21 total) ===")
ann_qs = [q for q in qs if classify_question(q['question'], q['answer_type']) == 'annual_diff']

for q in ann_qs:
    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    years = ent.get('years', [])
    unique_years = sorted(list(set(years)))
    if len(unique_years) >= 2:
        y1, y2 = str(unique_years[0]), str(unique_years[1])
        v1 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND completion_date LIKE ?", (client, f"{y1}%")).fetchone()[0] or 0
        v2 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND completion_date LIKE ?", (client, f"{y2}%")).fetchone()[0] or 0
        diff = abs(v1 - v2)
        print(f"[{q['qid']}] Diff: {diff:,} | Years: {y1} vs {y2} (v1={v1:,}, v2={v2:,}) | Client: {client}")
        if diff == 0:
            print(f"  SUSPECT ZERO DIFF: {qtxt}\n")
    else:
        print(f"[{q['qid']}] LESS THAN 2 YEARS: {unique_years} | Client: {client} | {qtxt}\n")
