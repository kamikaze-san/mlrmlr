import json
import sqlite3
import pandas as pd
import sys, os
from collections import Counter

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
from solution.solver.query_engine import QueryEngine

with open('questions.json') as f:
    qs = json.load(f)['questions']

with open('sample_questions.json') as f:
    sample_qs = json.load(f)['questions']

engine = QueryEngine()
linker = EntityLinker('solution/db/knowledge_base.db')

print("=== TESTING HV-IC-0296 ===")
for q in qs:
    if q['qid'] == 'HV-IC-0296':
        s = classify_question(q['question'], q['answer_type'])
        ent = linker.link(q['question'])
        ans = engine.solve_question(s, q['question'], ent)
        print(f"Shape: {s} | Ans: {ans:,}")
        print(f"Q: {q['question']}")
