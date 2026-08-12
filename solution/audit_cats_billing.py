"""
Two-part audit:
1. Verify all DB category names match our CAT_MAP keys
2. Check billing_shortfall sign convention
"""
import sqlite3
import json
import sys
sys.path.insert(0, '.')
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
import re

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

# ================================================================
# PART 1: Category names in DB
# ================================================================
print("=== ACTUAL CATEGORY NAMES IN DB ===")
cats = [r[0] for r in cur.execute("SELECT DISTINCT category FROM projects ORDER BY category").fetchall()]
for c in cats:
    print(f"  '{c}'")

# Now check what our CAT_MAP maps TO (the "target" side)
CAT_MAP = {
    'large bridges': 'large bridges',
    'bridges and flyovers': 'bridges flyovers',
    'bridges flyovers': 'bridges flyovers',
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

cat_targets = set(CAT_MAP.values())
print(f"\n=== CAT_MAP TARGET VALUES (what we query for) ===")
for t in sorted(cat_targets):
    in_db = t in cats
    print(f"  {'✓' if in_db else '✗ MISSING'} '{t}'")

print(f"\n=== DB CATEGORIES NOT IN CAT_MAP (potential unmapped categories) ===")
for c in cats:
    if c not in cat_targets:
        print(f"  UNMAPPED: '{c}'")

# ================================================================
# PART 2: Check all category_diff questions
# ================================================================
print("\n\n=== CATEGORY_DIFF QUESTION AUDIT ===")
with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

linker = EntityLinker('solution/db/knowledge_base.db')
import pandas as pd
df_ans = pd.read_csv('solution/answers_submission.csv')
ans_dict = dict(zip(df_ans['question_id'], df_ans['answer']))

issues = []
for qid, q in qs.items():
    if classify_question(q['question'], q['answer_type']) != 'category_diff':
        continue
    
    qtxt = q['question']
    txt_l = qtxt.lower()
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    our_ans = ans_dict.get(qid, 0)
    
    # Find category keywords
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
    
    if len(cats_found) >= 2:
        db_c1 = CAT_MAP.get(cats_found[0], cats_found[0])
        db_c2 = CAT_MAP.get(cats_found[1], cats_found[1])
        
        # Check if those categories exist for this client
        client_cats = [r[0] for r in cur.execute(
            "SELECT DISTINCT category FROM projects WHERE client_name = ?", (client,)
        ).fetchall()] if client else []
        
        c1_exists = db_c1 in client_cats
        c2_exists = db_c2 in client_cats
        
        if not c1_exists or not c2_exists:
            issues.append({
                'qid': qid, 'client': client,
                'q_kw1': cats_found[0], 'db_c1': db_c1, 'c1_exists': c1_exists,
                'q_kw2': cats_found[1], 'db_c2': db_c2, 'c2_exists': c2_exists,
                'our_ans': our_ans,
                'client_cats': client_cats,
                'q': qtxt[:110]
            })
    elif len(cats_found) < 2:
        issues.append({
            'qid': qid, 'client': client,
            'q_kw1': cats_found[0] if cats_found else None, 'db_c1': None, 'c1_exists': False,
            'q_kw2': None, 'db_c2': None, 'c2_exists': False,
            'our_ans': our_ans,
            'client_cats': [],
            'q': qtxt[:110]
        })

print(f"category_diff questions with missing category in DB for that client: {len(issues)}")
for i in issues:
    print(f"\n[{i['qid']}] Client: {i['client']}")
    print(f"  Keyword1: '{i['q_kw1']}' -> DB: '{i['db_c1']}' exists: {i['c1_exists']}")
    print(f"  Keyword2: '{i['q_kw2']}' -> DB: '{i['db_c2']}' exists: {i['c2_exists']}")
    print(f"  Our Answer: {i['our_ans']}")
    print(f"  Client categories in DB: {i['client_cats']}")
    print(f"  Q: {i['q']}")

# ================================================================
# PART 3: Billing shortfall — which ones are negative?
# ================================================================
print("\n\n=== BILLING_SHORTFALL QUESTIONS WITH NEGATIVE ANSWERS ===")
for qid, q in qs.items():
    if classify_question(q['question'], q['answer_type']) != 'billing_shortfall':
        continue
    ans = ans_dict.get(qid, 0)
    if ans < 0:
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        row = cur.execute("SELECT total_awarded_inr, total_invoiced_inr FROM clients WHERE client_name = ?", (client,)).fetchone()
        print(f"[{qid}] Answer: {ans:,.0f}")
        if row:
            print(f"  Awarded: {row[0]:,}  Invoiced: {row[1]:,}")
        print(f"  Q: {q['question'][:100]}")
