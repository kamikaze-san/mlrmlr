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

print("=== CHECKING ALL ANSWERS FOR ANOMALIES ===")

# Check if any answers are 0
zeros = [q for q in qs if ans_dict.get(q['qid'], 0) == 0]
print(f"Total zero answers: {len(zeros)}")
for q in zeros:
    shape = classify_question(q['question'], q['answer_type'])
    print(f"[{q['qid']}] ({shape}) {q['question']}")

# Check if any answer types have wrong data types
type_mismatches = []
for q in qs:
    qid = q['qid']
    atype = q['answer_type']
    ans = ans_dict.get(qid)
    
    if atype == 'count' and (not float(ans).is_integer() or ans < 0):
        type_mismatches.append((qid, atype, ans, q['question']))
    elif atype == 'days' and (not float(ans).is_integer() or ans < 0):
        type_mismatches.append((qid, atype, ans, q['question']))
    elif atype == 'percent' and (ans < 0 or ans > 100):
        type_mismatches.append((qid, atype, ans, q['question']))

print(f"\nTotal type/range mismatches: {len(type_mismatches)}")
for m in type_mismatches:
    print(f"[{m[0]}] Type: {m[1]} | Ans: {m[2]}")
    print(f"  Q: {m[3]}")
