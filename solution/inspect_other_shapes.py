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

print("=== TEMPORAL CHAIN QUESTIONS (11 total) ===")
for q in qs:
    qid = q['qid']
    shape = classify_question(q['question'], q['answer_type'])
    if shape == 'temporal_chain':
        ans = ans_dict.get(qid, 0)
        ent = linker.link(q['question'])
        eng = ent.get('engineer', {}).get('name')
        cert = ent.get('cert')
        issue_date = cert.get('issue_date') if cert else None
        print(f"[{qid}] Ans: {ans:,.0f} | Eng: {eng} | Cert Date: {issue_date}")
        print(f"  Q: {q['question']}\n")

print("=== REFERENCED SHARE (PERCENT) QUESTIONS (7 total) ===")
for q in qs:
    qid = q['qid']
    shape = classify_question(q['question'], q['answer_type'])
    if shape == 'referenced_share':
        ans = ans_dict.get(qid, 0)
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        print(f"[{qid}] Ans: {ans}% | Client: {client}")
        print(f"  Q: {q['question']}\n")

print("=== ABSENCE QUESTIONS (1 total) ===")
for q in qs:
    qid = q['qid']
    shape = classify_question(q['question'], q['answer_type'])
    if shape == 'absence':
        ans = ans_dict.get(qid, 0)
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        print(f"[{qid}] Ans: {ans} | Client: {client}")
        print(f"  Q: {q['question']}\n")

print("=== DISTINCT COUNT QUESTIONS (9 total) ===")
for q in qs:
    qid = q['qid']
    shape = classify_question(q['question'], q['answer_type'])
    if shape == 'distinct_count':
        ans = ans_dict.get(qid, 0)
        ent = linker.link(q['question'])
        eng = ent.get('engineer', {}).get('name')
        print(f"[{qid}] Ans: {ans} | Eng: {eng}")
        print(f"  Q: {q['question']}\n")
