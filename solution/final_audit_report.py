import json, sqlite3, sys, os
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
print("FINAL AUDIT REPORT ACROSS ALL 333 QUESTIONS")
print("=" * 80)

shape_counts = Counter()
for q in qs:
    qid = q['qid']
    qtxt = q['question']
    atype = q['answer_type']
    s = classify_question(qtxt, atype)
    shape_counts[s] += 1
    ans = ans_dict.get(qid)

print("\nShape distribution across 333 questions:")
for s, c in shape_counts.most_common():
    print(f"  {s:22s}: {c:3d}")

print(f"\nTotal questions: {len(qs)}")
print("Null count in submission:", df_ans['answer'].isnull().sum())
print("Zero count in submission:", (df_ans['answer'] == 0).sum())
print("Negative count in submission:", (df_ans['answer'] < 0).sum())
print("Total valid non-zero answers:", (df_ans['answer'] > 0).sum() + (df_ans['answer'] < 0).sum())
