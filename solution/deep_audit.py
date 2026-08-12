import sqlite3
import json
import numpy as np
import pandas as pd

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

old = pd.read_csv('solution/answers_qwen35_oldbackup.csv')
old_dict = dict(zip(old['question_id'], old['answer']))

import sys
sys.path.insert(0, '.')
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
linker = EntityLinker('solution/db/knowledge_base.db')

# Focus on these known-tricky shapes: category_diff, annual_diff, hop_aggregate, billing_shortfall
# For each, re-verify the logic carefully and flag anything suspicious

print("=" * 80)
print("DEEP AUDIT: Questions with potential wrong answers in OLD BACKUP")
print("=" * 80)

suspects = []

for qid, q in qs.items():
    qtxt = q['question']
    atype = q['answer_type']
    shape = classify_question(qtxt, atype)
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    old_ans = old_dict.get(qid)
    
    if shape == 'billing_shortfall' and client:
        row = cur.execute("SELECT total_awarded_inr, total_invoiced_inr FROM clients WHERE client_name = ?", (client,)).fetchone()
        if row:
            awarded, invoiced = row[0] or 0, row[1] or 0
            expected = awarded - invoiced
            if expected < 0:
                suspects.append({
                    'qid': qid, 'shape': shape, 'client': client,
                    'old_ans': old_ans, 'expected': expected,
                    'issue': f'Invoiced ({invoiced:,}) > Awarded ({awarded:,}) — data anomaly',
                    'q': qtxt[:100]
                })
    
    if shape == 'outstanding_balance' and client:
        row = cur.execute("SELECT total_outstanding_inr FROM clients WHERE client_name = ?", (client,)).fetchone()
        if row and row[0] is not None and row[0] < 0:
            suspects.append({
                'qid': qid, 'shape': shape, 'client': client,
                'old_ans': old_ans, 'expected': row[0],
                'issue': f'Outstanding is negative ({row[0]:,}) — overpayment in raw data',
                'q': qtxt[:100]
            })

    if shape == 'category_diff' and client:
        # Check that both categories exist for client
        rows = cur.execute("SELECT DISTINCT category FROM projects WHERE client_name = ?", (client,)).fetchall()
        cats_in_db = {r[0] for r in rows}
        
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
        import re
        txt_l = qtxt.lower()
        found = []
        spans = []
        for cat in sorted(CAT_MAP.keys(), key=len, reverse=True):
            for m in re.finditer(rf'\b{re.escape(cat)}\b', txt_l):
                start, end = m.start(), m.end()
                if not any(s <= start < e or s < end <= e for s, e in spans):
                    spans.append((start, end))
                    found.append((start, cat))
        found.sort()
        cats_found = [c for _, c in found]
        
        if len(cats_found) >= 2:
            db_c1 = CAT_MAP.get(cats_found[0], cats_found[0])
            db_c2 = CAT_MAP.get(cats_found[1], cats_found[1])
            if db_c1 not in cats_in_db or db_c2 not in cats_in_db:
                suspects.append({
                    'qid': qid, 'shape': shape, 'client': client,
                    'old_ans': old_ans, 'expected': '???',
                    'issue': f'Cat "{db_c1}" in DB: {db_c1 in cats_in_db}, Cat "{db_c2}" in DB: {db_c2 in cats_in_db}. DB has: {cats_in_db}',
                    'q': qtxt[:100]
                })

print(f"Suspects found: {len(suspects)}")
for s in suspects:
    print(f"\n[{s['qid']}] ({s['shape']})")
    print(f"  Old Answer: {s['old_ans']}")
    print(f"  Expected:   {s['expected']}")
    print(f"  Issue: {s['issue']}")
    print(f"  Q: {s['q']}")
