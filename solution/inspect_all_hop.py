import json
import sqlite3
import pandas as pd
import sys, os

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = json.load(f)['questions']

linker = EntityLinker('solution/db/knowledge_base.db')

hop_questions = []
for q in qs:
    qid = q['qid']
    qtxt = q['question']
    atype = q['answer_type']
    s = classify_question(qtxt, atype)
    if s == 'hop_aggregate':
        hop_questions.append((qid, atype, qtxt))

print(f"Total classified as hop_aggregate: {len(hop_questions)}")
print("=" * 80)

for qid, atype, qtxt in hop_questions:
    txt_l = qtxt.lower()
    possible_shape = "hop_aggregate"
    
    if any(w in txt_l for w in ['shortfall', 'unbilled', 'invoice amount', 'claims we submitted', 'gap between', 'billed', 'submitted claims']):
        possible_shape = "REAL_SHAPE: billing_shortfall"
    elif any(w in txt_l for w in ['minus', 'excluding', 'exclude', 'set aside', 'without']):
        possible_shape = "REAL_SHAPE: exclusion_aggregate"
    elif any(w in txt_l for w in ['highest-value', 'second', 'exceeds', 'surplus value', 'next one down']):
        possible_shape = "REAL_SHAPE: rank_value"
    elif any(w in txt_l for w in ['from 201', 'from 202', 'between 201', 'between 202', 'movement in', 'net shift']):
        possible_shape = "REAL_SHAPE: annual_diff"
    elif any(w in txt_l for w in ['average', 'mean', 'median']):
        possible_shape = "REAL_SHAPE: avg_work_size / mean_vs_median"
    elif any(w in txt_l for w in ['exceeding', 'threshold', 'crore mark', 'limit', 'or higher', 'or more']):
        possible_shape = "REAL_SHAPE: threshold_aggregate"
        
    print(f"\n[{qid}] ({possible_shape})")
    print(f"  Q: {qtxt}")
