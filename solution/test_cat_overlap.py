import json
import sqlite3
import pandas as pd
import sys, os
import re

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = json.load(f)['questions']

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

def count_categories(txt_l):
    spans = []
    found = []
    for cat in sorted(CAT_MAP.keys(), key=len, reverse=True):
        for m in re.finditer(rf'\b{re.escape(cat)}\b', txt_l):
            start, end = m.start(), m.end()
            if not any(s <= start < e or s < end <= e for s, e in spans):
                spans.append((start, end))
                found.append((start, cat))
    found.sort()
    unique_cats = set(CAT_MAP.get(c, c) for _, c in found)
    return len(unique_cats)

print("=== CHECKING ALL BILLING SHORTFALL QUESTIONS FOR CATEGORY OVERLAP ===")
from solution.solver.question_parser import classify_question
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'billing_shortfall':
        num_cats = count_categories(q['question'].lower())
        print(f"[{q['qid']}] Cats found: {num_cats} | Q: {q['question']}")
