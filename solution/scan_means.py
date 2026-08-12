import json, sqlite3, sys, os, re
import pandas as pd
import numpy as np

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
print("AUDITING MEAN_VS_MEDIAN (19 questions) AND AVG_WORK_SIZE (24 questions)")
print("=" * 80)

# Check all mean_vs_median (19 questions)
print("\n--- MEAN VS MEDIAN (19 questions) ---")
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'mean_vs_median':
        ent = linker.link(q['question'])
        ans = ans_dict.get(q['qid'])
        client = ent.get('client_name')
        eng = ent.get('engineer')
        vals = [r[0] for r in cur.execute("SELECT value_inr FROM projects WHERE client_name = ?", (client,)).fetchall()]
        mean_v = np.mean(vals)
        median_v = np.median(vals)
        calc_diff = int(round(mean_v - median_v))
        print(f"[{q['qid']}] Ans: {ans:12,f} | Client: {client} | n={len(vals)} | mean={mean_v:,.0f} | median={median_v:,.0f}")
        print(f"  Q: {q['question']}\n")

# Check all avg_work_size (24 questions)
print("\n--- AVG WORK SIZE (24 questions) ---")
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'avg_work_size':
        ent = linker.link(q['question'])
        ans = ans_dict.get(q['qid'])
        client = ent.get('client_name')
        vals = [r[0] for r in cur.execute("SELECT value_inr FROM projects WHERE client_name = ?", (client,)).fetchall()]
        mean_v = np.mean(vals)
        calc_mean = int(round(mean_v))
        print(f"[{q['qid']}] Ans: {ans:12,f} | Client: {client} | n={len(vals)} | mean={calc_mean:12,d}")
        print(f"  Q: {q['question']}\n")
