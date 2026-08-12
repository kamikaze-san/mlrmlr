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
print("SYSTEMATIC SCAN OF ALL 333 QUESTIONS FOR AMBIGUITIES")
print("=" * 80)

# 1. Check all percent questions (referenced_share, collection_rate)
print("\n--- PERCENT QUESTIONS (31 questions) ---")
for q in qs:
    if q['answer_type'] == 'percent':
        s = classify_question(q['question'], q['answer_type'])
        ent = linker.link(q['question'])
        ans = ans_dict.get(q['qid'])
        client = ent.get('client_name')
        print(f"[{q['qid']}] Shape: {s:18s} | Ans: {ans:6.2f}% | Client: {client}")
        print(f"  Q: {q['question']}\n")

# 2. Check all count questions (distinct_count, absence)
print("\n--- COUNT QUESTIONS (10 questions) ---")
for q in qs:
    if q['answer_type'] == 'count':
        s = classify_question(q['question'], q['answer_type'])
        ent = linker.link(q['question'])
        ans = ans_dict.get(q['qid'])
        print(f"[{q['qid']}] Shape: {s:18s} | Ans: {ans} | Eng: {ent.get('engineer', {}).get('name')} | Client: {ent.get('client_name')}")
        print(f"  Q: {q['question']}\n")

# 3. Check all date_span questions (24 questions)
print("\n--- DATE_SPAN QUESTIONS (24 questions) ---")
for q in qs:
    if q['answer_type'] == 'days':
        s = classify_question(q['question'], q['answer_type'])
        ent = linker.link(q['question'])
        ans = ans_dict.get(q['qid'])
        proj = ent.get('project', {})
        print(f"[{q['qid']}] Ans: {ans:5.0f} days | Proj: {proj.get('package_no')} ({proj.get('project_name')})")
        print(f"  Q: {q['question']}\n")
