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

print("=== AUDITING ALL RANK_VALUE QUESTIONS (14 total) ===")
rank_qs = [q for q in qs if classify_question(q['question'], q['answer_type']) == 'rank_value']

for q in rank_qs:
    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    cur.execute("SELECT value_inr FROM projects WHERE client_name = ? ORDER BY value_inr DESC LIMIT 2", (client,))
    rows = cur.fetchall()
    diff = rows[0][0] - rows[1][0] if len(rows) >= 2 else 0
    print(f"[{q['qid']}] Diff: {diff:,} | Client: {client}")
    if len(rows) < 2:
        print(f"  FAILED/SUSPECT: {qtxt}\n")

print("\n=== AUDITING ALL MEAN_VS_MEDIAN QUESTIONS (19 total) ===")
mean_qs = [q for q in qs if classify_question(q['question'], q['answer_type']) == 'mean_vs_median']
for q in mean_qs:
    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    cur.execute("SELECT value_inr FROM projects WHERE client_name = ?", (client,))
    rows = cur.fetchall()
    vals = sorted([r[0] for r in rows])
    if vals:
        mean_v = sum(vals) / len(vals)
        n = len(vals)
        median_v = vals[n // 2] if n % 2 == 1 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
        diff = int(round(mean_v - median_v))
        print(f"[{q['qid']}] Gap (mean - median): {diff:,} | Client: {client} | N={len(vals)}")
    else:
        print(f"[{q['qid']}] NO PROJECTS: {client} | {qtxt}")
