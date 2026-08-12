import sqlite3
import json
import re
import sys
import pandas as pd
sys.path.insert(0, '.')
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker

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

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

linker = EntityLinker('solution/db/knowledge_base.db')
df_ans = pd.read_csv('solution/answers_submission.csv')
ans_dict = dict(zip(df_ans['question_id'], df_ans['answer']))

print("=== CATEGORY_DIFF: Questions where one/both categories are ZERO for client ===")
issues = []
for qid, q in qs.items():
    if classify_question(q['question'], q['answer_type']) != 'category_diff':
        continue

    qtxt = q['question']
    txt_l = qtxt.lower()
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    our_ans = ans_dict.get(qid, 0)

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

        rows = cur.execute(
            "SELECT category, SUM(value_inr) FROM projects WHERE client_name = ? AND category IN (?, ?) GROUP BY category",
            (client, db_c1, db_c2)
        ).fetchall()
        cat_vals = {r[0]: r[1] for r in rows}
        v1 = cat_vals.get(db_c1, 0)
        v2 = cat_vals.get(db_c2, 0)

        if v1 == 0 or v2 == 0:
            issues.append({
                'qid': qid, 'client': client,
                'kw1': cats_found[0], 'db1': db_c1, 'v1': v1,
                'kw2': cats_found[1], 'db2': db_c2, 'v2': v2,
                'our_ans': our_ans,
                'q': qtxt[:115]
            })

print(f"Total with zero-value category: {len(issues)}")
for i in issues:
    print(f"\n[{i['qid']}] Client: {i['client']}")
    print(f"  Kw1: '{i['kw1']}' -> DB: '{i['db1']}' = {i['v1']:,}")
    print(f"  Kw2: '{i['kw2']}' -> DB: '{i['db2']}' = {i['v2']:,}")
    print(f"  Our ans: {i['our_ans']:,.0f}")
    print(f"  Q: {i['q']}")

print("\n\n=== BILLING_SHORTFALL: Negative answers ===")
for qid, q in qs.items():
    if classify_question(q['question'], q['answer_type']) != 'billing_shortfall':
        continue
    ans = ans_dict.get(qid, 0)
    if ans < 0:
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        row = cur.execute(
            "SELECT total_awarded_inr, total_invoiced_inr FROM clients WHERE client_name = ?",
            (client,)
        ).fetchone()
        print(f"[{qid}] ans={ans:,.0f} | awarded={row[0]:,} invoiced={row[1]:,}")
        print(f"  Q: {q['question'][:110]}")

print("\n\n=== OUTSTANDING_BALANCE: Negative answers ===")
for qid, q in qs.items():
    if classify_question(q['question'], q['answer_type']) != 'outstanding_balance':
        continue
    ans = ans_dict.get(qid, 0)
    if ans < 0:
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        row = cur.execute(
            "SELECT total_outstanding_inr FROM clients WHERE client_name = ?",
            (client,)
        ).fetchone()
        print(f"[{qid}] ans={ans:,.0f} | outstanding_in_db={row[0]:,}")
        print(f"  Q: {q['question'][:110]}")
