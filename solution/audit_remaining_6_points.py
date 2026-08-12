import json
import sqlite3
import pandas as pd
import sys, os
from collections import Counter

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
from solution.solver.query_engine import QueryEngine

with open('questions.json') as f:
    qs = json.load(f)['questions']

linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

df_ans = pd.read_csv('solution/answers_submission.csv')
ans_dict = dict(zip(df_ans['question_id'], df_ans['answer']))

shapes = [classify_question(q['question'], q['answer_type']) for q in qs]
counts = Counter(shapes)
print("=== SHAPE DISTRIBUTION (333 total) ===")
for s, c in counts.most_common():
    print(f"{s:25s}: {c}")

print("\n" + "=" * 80)
print("INSPECTING SHAPES WITH POTENTIAL EDGE CASES")
print("=" * 80)

# 1. Inspect all exclusion_aggregate (18 questions)
print("\n--- 1. EXCLUSION AGGREGATE ---")
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'exclusion_aggregate':
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        excl = ent.get('excluded_cat')
        ans = ans_dict.get(q['qid'])
        print(f"[{q['qid']}] Ans: {ans:,.0f} | Client: {client} | Excl: '{excl}'")
        print(f"  Q: {q['question']}")

# 2. Inspect all billing_shortfall (10 questions)
print("\n--- 2. BILLING SHORTFALL ---")
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'billing_shortfall':
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        ans = ans_dict.get(q['qid'])
        print(f"[{q['qid']}] Ans: {ans:,.0f} | Client: {client}")
        print(f"  Q: {q['question']}")

# 3. Inspect all mean_vs_median (14 questions)
print("\n--- 3. MEAN VS MEDIAN ---")
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'mean_vs_median':
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        ans = ans_dict.get(q['qid'])
        print(f"[{q['qid']}] Ans: {ans:,.0f} | Client: {client}")
        print(f"  Q: {q['question']}")
