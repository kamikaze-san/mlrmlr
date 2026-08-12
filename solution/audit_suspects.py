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

linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

df_ans = pd.read_csv('solution/answers_submission.csv')
ans_dict = dict(zip(df_ans['question_id'], df_ans['answer']))

print("=== CHECKING ALL QUESTIONS FOR POTENTIAL ZERO / UNLINKED / SUSPECT DATA ===")

suspects = []
for q in qs:
    qid = q['qid']
    qtxt = q['question']
    atype = q['answer_type']
    ans = ans_dict.get(qid)
    shape = classify_question(qtxt, atype)
    ent = linker.link(qtxt)
    
    # 1. Missing client when shape requires client
    if shape in ['annual_diff', 'category_diff', 'avg_work_size', 'rank_value', 'threshold_aggregate', 'gap_to_threshold', 'billing_shortfall', 'outstanding_balance', 'collection_rate', 'referenced_share'] and not ent.get('client_name'):
        suspects.append((qid, 'MISSING CLIENT', shape, qtxt))
        
    # 2. Missing engineer when shape requires engineer
    if shape in ['distinct_count', 'temporal_chain'] and not ent.get('engineer'):
        suspects.append((qid, 'MISSING ENGINEER', shape, qtxt))
        
    # 3. Missing threshold when shape is threshold_aggregate / gap_to_threshold
    if shape in ['threshold_aggregate', 'gap_to_threshold'] and (not ent.get('threshold_inr') or ent.get('threshold_inr') == 0):
        suspects.append((qid, 'MISSING THRESHOLD', shape, qtxt))
        
    # 4. Missing cert when shape is date_span
    if shape == 'date_span' and not ent.get('cert'):
        suspects.append((qid, 'MISSING CERT', shape, qtxt))
        
    # 5. Missing project when shape is date_span
    if shape == 'date_span' and not ent.get('project'):
        suspects.append((qid, 'MISSING PROJECT', shape, qtxt))

print(f"Total suspects found: {len(suspects)}")
for s in suspects:
    print(f"[{s[0]}] Reason: {s[1]:20s} | Shape: {s[2]}")
    print(f"  Q: {s[3]}\n")
