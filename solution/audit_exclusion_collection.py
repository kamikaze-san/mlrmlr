"""
Check exclusion_aggregate for the "roads" bug:
If excl = "roads maintenance" and category = "roads highways",
our code checks: any(w in "roads highways" for w in "roads maintenance".split() if len(w) > 3)
"roads" (len=5) is in "roads highways" -> True -> wrongly excluded!

Also check collection_rate > 100%.
"""
import sqlite3
import json
import sys
sys.path.insert(0, '.')
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
import pandas as pd

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
linker = EntityLinker('solution/db/knowledge_base.db')

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

df_ans = pd.read_csv('solution/answers_submission.csv')
ans_dict = dict(zip(df_ans['question_id'], df_ans['answer']))

print("=== EXCLUSION_AGGREGATE: Checking for wrong exclusions ===\n")

for qid, q in qs.items():
    if classify_question(q['question'], q['answer_type']) != 'exclusion_aggregate':
        continue

    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    excl = ent.get('excluded_category')
    our_ans = ans_dict.get(qid, 0)

    if not client or not excl:
        print(f"[{qid}] MISSING ENTITY: client={client} excl={excl}")
        print(f"  Q: {qtxt[:100]}")
        continue

    # Get all projects for client
    rows = cur.execute(
        "SELECT category, value_inr FROM projects WHERE client_name = ?", (client,)
    ).fetchall()

    # Simulate our current (potentially buggy) exclusion
    current_total = 0
    wrongly_excluded = []
    correctly_excluded = []
    for cat, val in rows:
        if excl and (excl in cat.lower() or any(w in cat.lower() for w in excl.split() if len(w) > 3)):
            if excl not in cat.lower():  # excl substring not exact match -> possibly wrong
                wrongly_excluded.append((cat, val))
            else:
                correctly_excluded.append((cat, val))
            continue
        current_total += val

    # Correct exclusion: only exclude exact match
    correct_total = sum(val for cat, val in rows if excl not in cat.lower())

    if current_total != correct_total:
        print(f"[{qid}] BUG FOUND!")
        print(f"  excl='{excl}' | our_ans={our_ans:,.0f}")
        print(f"  Correct total (exact match only): {correct_total:,.0f}")
        print(f"  Current total (substring match):  {current_total:,.0f}")
        print(f"  Wrongly excluded cats: {wrongly_excluded}")
        print(f"  Correctly excluded cats: {correctly_excluded}")
        print(f"  Q: {qtxt[:115]}")
        print()
    else:
        pass  # print(f"[{qid}] OK: excl='{excl}' | ans={our_ans:,.0f}")

print("\n=== COLLECTION_RATE: Any rates > 100%? ===\n")
for qid, q in qs.items():
    if classify_question(q['question'], q['answer_type']) != 'collection_rate':
        continue
    ans = ans_dict.get(qid, 0)
    if ans > 100:
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        row = cur.execute(
            "SELECT total_received_inr, total_invoiced_inr FROM clients WHERE client_name = ?", (client,)
        ).fetchone()
        if row:
            print(f"[{qid}] Rate={ans:.2f}% | Received={row[0]:,} Invoiced={row[1]:,}")
            print(f"  Q: {q['question'][:100]}")
