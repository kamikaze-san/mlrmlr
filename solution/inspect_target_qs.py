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
targets = [
    'Gujarat Municipal Corporation',
    'Irrigation & Waterways Dept, Govt of Uttar Pradesh',
    'Jal Nigam, Gujarat',
    'Maharashtra Municipal Corporation'
]

print("=== QUESTIONS TARGETING THE 4 UNUSUAL BALANCE CLIENTS ===")
for q in qs:
    ent = linker.link(q['question'])
    client = ent.get('client_name')
    if client in targets:
        s = classify_question(q['question'], q['answer_type'])
        if s in ['billing_shortfall', 'outstanding_balance']:
            print(f"[{q['qid']}] Shape: {s:20s} | Client: {client}")
            print(f"  Q: {q['question']}\n")
