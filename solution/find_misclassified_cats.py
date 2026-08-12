import json
import sqlite3
import pandas as pd
import sys, os
import re

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker, CLIENT_ALIASES

with open('questions.json') as f:
    qs = json.load(f)['questions']

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

print("=== CHECKING FOR MISCLASSIFIED CATEGORY_DIFF QUESTIONS ===")
misclassified_cat_diff = []

for q in qs:
    qid = q['qid']
    qtxt = q['question']
    txt_l = qtxt.lower()
    shape = classify_question(qtxt, q['answer_type'])
    
    # Extract categories found
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
    
    unique_cats = set(CAT_MAP.get(c, c) for c in cats_found)
    
    if len(unique_cats) >= 2 and any(w in txt_l for w in ['versus', 'vs', 'difference', 'delta', 'gap', 'compared to', 'against']) and shape != 'category_diff':
        if not any(w in txt_l for w in ['average and median', 'mean and median', 'mean against the median', 'avg minus median', 'sanctioned and what we']):
            misclassified_cat_diff.append((qid, shape, unique_cats, qtxt))

print(f"Total misclassified category_diff questions: {len(misclassified_cat_diff)}")
for m in misclassified_cat_diff:
    print(f"[{m[0]}] Current Shape: {m[1]} | Cats: {m[2]}")
    print(f"  Q: {m[3]}\n")
