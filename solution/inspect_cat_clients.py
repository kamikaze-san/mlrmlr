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
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("=== INSPECTING ALL CATEGORY_DIFF QUESTIONS FOR CLIENT vs COMPANY-WIDE ===")
cat_qs = [q for q in qs if classify_question(q['question'], q['answer_type']) == 'category_diff']

no_client_count = 0
for q in cat_qs:
    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    if not client:
        no_client_count += 1
        print(f"[{q['qid']}] NO CLIENT LINKED: {qtxt}")

print(f"\nTotal category_diff questions without client: {no_client_count} / {len(cat_qs)}")
