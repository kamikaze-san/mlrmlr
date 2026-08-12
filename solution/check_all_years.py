import json
import sqlite3
import pandas as pd
import sys, os
import re

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker
from solution.solver.semantic_classifier import SemanticClassifier

with open('questions.json') as f:
    qs = json.load(f)['questions']

linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("=== CHECKING ALL QUESTIONS WITH 2+ YEARS ===")
for q in qs:
    qtxt = q['question']
    txt_l = qtxt.lower()
    years = set(re.findall(r'\b(201\d|202\d)\b', txt_l))
    if len(years) >= 2:
        ent = linker.link(qtxt)
        client = ent.get('client_name')
        print(f"[{q['qid']}] Years: {sorted(list(years))} | Client: {client}")
        print(f"  Q: {qtxt}\n")
