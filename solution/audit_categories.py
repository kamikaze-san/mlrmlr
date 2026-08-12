import json
import sqlite3
import pandas as pd
import re
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

cat_qs = [q for q in qs if classify_question(q['question'], q['answer_type']) == 'category_diff']
print(f"Total Category Diff Questions: {len(cat_qs)}")

CAT_MAP = {
    'bridges and flyovers': 'bridges flyovers',
    'bridges flyovers': 'bridges flyovers',
    'large bridges': 'large bridges',
    'bridges': 'bridges flyovers',
    'water treatment': 'water treatment',
    'water supply': 'water supply',
    'sewerage drainage': 'sewerage drainage',
    'sewerage': 'sewerage drainage',
    'drainage': 'sewerage drainage',
    'roads and highways': 'roads highways',
    'roads highways': 'roads highways',
    'roads maintenance': 'roads maintenance',
    'maintenance': 'roads maintenance',
    'roads': 'roads highways',
    'expressways': 'expressways',
    'tunnels': 'tunnels',
    'industrial epc': 'industrial epc',
    'epc': 'industrial epc',
    'irrigation': 'irrigation',
    'small buildings': 'small buildings',
    'buildings': 'buildings'
}

for q in cat_qs:
    qid = q['qid']
    qtxt = q['question']
    txt_l = qtxt.lower()
    
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    ans = engine.solve_question(qid, qtxt, q['answer_type'])
    
    # Find categories in text
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
    
    if len(cats_found) < 2 or not client or ans == 0:
        print(f"\n[ALERT] [{qid}] Ans: {ans} | Client: {client} | Cats: {cats_found}")
        print(f"  Q: {qtxt}")
    else:
        c1, c2 = cats_found[0], cats_found[1]
        db_c1 = CAT_MAP.get(c1, c1)
        db_c2 = CAT_MAP.get(c2, c2)
        # Verify db categories exist for client
        cur.execute("SELECT category, SUM(value_inr) FROM projects WHERE client_name = ? AND category IN (?, ?) GROUP BY category", (client, db_c1, db_c2))
        rows = cur.fetchall()
        # print(f"[{qid}] OK | Client: {client[:25]} | {db_c1} vs {db_c2} -> {ans:,}")
