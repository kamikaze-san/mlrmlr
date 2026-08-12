import json, sqlite3, sys, os, re
import pandas as pd
from collections import Counter

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker
from solution.solver.question_parser import classify_question
from solution.solver.query_engine import QueryEngine

with open('questions.json') as f:
    qs = json.load(f)['questions']

engine = QueryEngine()
linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

df_ans = pd.read_csv('solution/answers_submission.csv')
ans_dict = dict(zip(df_ans['question_id'], df_ans['answer']))

print("=" * 80)
print("AUDITING MONEY SHAPES FOR REMAINING DISCREPANCIES")
print("=" * 80)

# Check all gap_to_threshold (3 questions)
print("\n--- GAP TO THRESHOLD (3 questions) ---")
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'gap_to_threshold':
        ent = linker.link(q['question'])
        ans = ans_dict.get(q['qid'])
        client = ent.get('client_name')
        thresh = ent.get('threshold_inr')
        cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ?", (client,))
        actual = cur.fetchone()[0] or 0
        gap = thresh - actual
        print(f"[{q['qid']}] Ans: {ans:,} | Client: {client} | Thresh: {thresh:,} | Actual: {actual:,} | Gap: {gap:,}")
        print(f"  Q: {q['question']}\n")

# Check all absence questions (1 question)
print("\n--- ABSENCE (1 question) ---")
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'absence':
        ent = linker.link(q['question'])
        ans = ans_dict.get(q['qid'])
        client = ent.get('client_name')
        cur.execute("SELECT COUNT(*) FROM projects WHERE client_name = ? AND has_reference_letter = 0", (client,))
        c = cur.fetchone()[0]
        print(f"[{q['qid']}] Ans: {ans} | Client: {client} | Unreferenced count: {c}")
        print(f"  Q: {q['question']}\n")

# Check all rank_value questions (16 questions)
print("\n--- RANK VALUE (16 questions) ---")
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'rank_value':
        ent = linker.link(q['question'])
        ans = ans_dict.get(q['qid'])
        client = ent.get('client_name')
        cur.execute("SELECT value_inr FROM projects WHERE client_name = ? ORDER BY value_inr DESC", (client,))
        vals = [r[0] for r in cur.fetchall()]
        diff1_2 = vals[0] - vals[1] if len(vals) >= 2 else 0
        print(f"[{q['qid']}] Ans: {ans:,} | Client: {client} | top2: {vals[:2]} | diff: {diff1_2:,}")
        print(f"  Q: {q['question']}\n")
