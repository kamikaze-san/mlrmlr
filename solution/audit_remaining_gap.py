import json
import sqlite3
import pandas as pd
import sys, os

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
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
print("COMPREHENSIVE AUDIT OF ALL SHAPES AND SUSPICIOUS VALUES")
print("=" * 80)

# 1. Check any negative answers
print("\n--- 1. ALL NEGATIVE ANSWERS ---")
for q in qs:
    qid = q['qid']
    ans = ans_dict.get(qid, 0)
    if ans < 0:
        shape = classify_question(q['question'], q['answer_type'])
        print(f"[{qid}] ({shape}) Answer: {ans:,.0f}")
        print(f"  Q: {q['question']}")

# 2. Check all gap_to_threshold questions
print("\n--- 2. GAP_TO_THRESHOLD QUESTIONS (3 total) ---")
for q in qs:
    qid = q['qid']
    shape = classify_question(q['question'], q['answer_type'])
    if shape == 'gap_to_threshold':
        ans = ans_dict.get(qid, 0)
        ent = linker.link(q['question'])
        print(f"[{qid}] Ans: {ans:,.0f} | Threshold: {ent.get('threshold_inr'):,}")
        print(f"  Q: {q['question']}")

# 3. Check all mean_vs_median questions
print("\n--- 3. MEAN_VS_MEDIAN QUESTIONS ---")
for q in qs:
    qid = q['qid']
    shape = classify_question(q['question'], q['answer_type'])
    if shape == 'mean_vs_median':
        ans = ans_dict.get(qid, 0)
        print(f"[{qid}] Ans: {ans:,.0f}")
        print(f"  Q: {q['question']}")

# 4. Check all annual_diff questions
print("\n--- 4. ANNUAL_DIFF QUESTIONS ---")
for q in qs:
    qid = q['qid']
    shape = classify_question(q['question'], q['answer_type'])
    if shape == 'annual_diff':
        ans = ans_dict.get(qid, 0)
        ent = linker.link(q['question'])
        years = ent.get('years', [])
        client = ent.get('client_name')
        print(f"[{qid}] Ans: {ans:,.0f} | Years: {years} | Client: {client}")
        print(f"  Q: {q['question']}")
