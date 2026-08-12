import json
import sqlite3
import pandas as pd
import sys, os

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.query_engine import QueryEngine
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = json.load(f)['questions']

engine = QueryEngine(use_llm_fallback=False)
linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

# 1. Audit ANNUAL_DIFF
print("=== 1. AUDIT ANNUAL_DIFF (19 Questions) ===")
for q in qs:
    if classify_question(q['question'], q['answer_type']) == 'annual_diff':
        ans = engine.solve_question(q['qid'], q['question'], q['answer_type'])
        ent = linker.link(q['question'])
        print(f"[{q['qid']}] Ans: {ans:,} | Client: {ent.get('client_name')} | Years: {ent.get('years')}")

# 2. Audit MEAN_VS_MEDIAN
print("\n=== 2. AUDIT MEAN_VS_MEDIAN (16 Questions) ===")
for q in qs:
    if classify_question(q['question'], q['answer_type']) == 'mean_vs_median':
        ans = engine.solve_question(q['qid'], q['question'], q['answer_type'])
        ent = linker.link(q['question'])
        print(f"[{q['qid']}] Ans: {ans:,} | Client: {ent.get('client_name')}")

# 3. Audit AVG_WORK_SIZE
print("\n=== 3. AUDIT AVG_WORK_SIZE (21 Questions) ===")
for q in qs:
    if classify_question(q['question'], q['answer_type']) == 'avg_work_size':
        ans = engine.solve_question(q['qid'], q['question'], q['answer_type'])
        ent = linker.link(q['question'])
        print(f"[{q['qid']}] Ans: {ans:,} | Client: {ent.get('client_name')}")
