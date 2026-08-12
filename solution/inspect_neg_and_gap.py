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

print("=== 1. ALL NEGATIVE ANSWERS ===")
for q in qs:
    qid = q['qid']
    ans = ans_dict.get(qid, 0)
    if ans < 0:
        shape = classify_question(q['question'], q['answer_type'])
        print(f"[{qid}] ({shape}) Ans: {ans:,.0f}")
        print(f"  Q: {q['question']}\n")

print("=== 2. ALL GAP_TO_THRESHOLD QUESTIONS ===")
for q in qs:
    qid = q['qid']
    shape = classify_question(q['question'], q['answer_type'])
    if shape == 'gap_to_threshold':
        ans = ans_dict.get(qid, 0)
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        thresh = ent.get('threshold_inr')
        cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ?", (client,))
        curr_total = cur.fetchone()[0] or 0
        print(f"[{qid}] Ans: {ans:,.0f} | Current Total: {curr_total:,} | Target Threshold: {thresh:,} | Client: {client}")
        print(f"  Q: {q['question']}\n")
