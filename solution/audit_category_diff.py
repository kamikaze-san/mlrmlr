import json
import sqlite3
import pandas as pd
import sys, os
import re

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

CAT_MAP = {
    'large bridges': 'large bridges', 'bridges and flyovers': 'bridges flyovers',
    'bridges flyovers': 'bridges flyovers', 'bridges': 'bridges flyovers',
    'water treatment': 'water treatment', 'water supply': 'water supply',
    'sewerage drainage': 'sewerage drainage', 'sewerage': 'sewerage drainage',
    'drainage': 'sewerage drainage', 'roads and highways': 'roads highways',
    'roads highways': 'roads highways', 'roads maintenance': 'roads maintenance',
    'maintenance': 'roads maintenance', 'roads': 'roads highways',
    'expressways': 'expressways', 'tunnels': 'tunnels',
    'industrial epc': 'industrial epc', 'epc': 'industrial epc',
    'irrigation': 'irrigation', 'small buildings': 'small buildings', 'buildings': 'buildings'
}

print("=== AUDITING ALL 61 CATEGORY_DIFF QUESTIONS ===")

cat_diff_qs = [q for q in qs if classify_question(q['question'], q['answer_type']) == 'category_diff']
print(f"Total category_diff questions: {len(cat_diff_qs)}")

zero_cats = []
for q in cat_diff_qs:
    qid = q['qid']
    qtxt = q['question']
    txt_l = qtxt.lower()
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    
    spans = []
    found = []
    for cat in sorted(CAT_MAP.keys(), key=len, reverse=True):
        for m in re.finditer(rf'\b{re.escape(cat)}\b', txt_l):
            start, end = m.start(), m.end()
            if not any(s <= start < e or s < end <= e for s, e in spans):
                spans.append((start, end))
                found.append((start, cat))
    found.sort()
    cats_found = [c for _, c in found]
    
    if len(cats_found) < 2:
        print(f"[{qid}] LESS THAN 2 CATEGORIES FOUND: {cats_found} | Client: {client}")
        print(f"  Q: {qtxt}\n")
    else:
        c1 = CAT_MAP.get(cats_found[0], cats_found[0])
        c2 = CAT_MAP.get(cats_found[1], cats_found[1])
        v1 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND category = ?", (client, c1)).fetchone()[0] or 0
        v2 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND category = ?", (client, c2)).fetchone()[0] or 0
        diff = abs(v1 - v2)
        if diff == 0:
            print(f"[{qid}] ZERO DIFF: c1={c1}({v1:,}) c2={c2}({v2:,}) | Client: {client}")
            print(f"  Q: {qtxt}\n")
