import json
import sqlite3
import sys, os
sys.path.insert(0, '.')
from solution.solver.entity_linker import EntityLinker
from solution.solver.question_parser import classify_question

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

# Get all client names from DB
all_clients = [r[0] for r in cur.execute("SELECT client_name FROM clients").fetchall()]
all_engineers = [r[0] for r in cur.execute("SELECT name FROM engineers").fetchall()]

linker = EntityLinker('solution/db/knowledge_base.db')

print("=" * 80)
print("ENTITY LINKING AUDIT — Checking all 333 questions for failed entity links")
print("=" * 80)

failures = []
for qid, q in qs.items():
    qtxt = q['question']
    atype = q['answer_type']
    shape = classify_question(qtxt, atype)
    ent = linker.link(qtxt)
    
    client = ent.get('client_name')
    engineer = ent.get('engineer')
    
    needs_client = shape in ('hop_aggregate', 'avg_work_size', 'mean_vs_median', 'rank_value',
                             'threshold_aggregate', 'gap_to_threshold', 'exclusion_aggregate',
                             'category_diff', 'annual_diff', 'billing_shortfall',
                             'outstanding_balance', 'collection_rate', 'absence', 
                             'referenced_share')
    needs_engineer = shape in ('distinct_count', 'temporal_chain')
    
    if needs_client and not client:
        failures.append({
            'qid': qid, 'shape': shape, 'issue': 'MISSING CLIENT',
            'client': None, 'engineer': engineer,
            'q': qtxt
        })
    elif needs_engineer and not (engineer and engineer.get('name')):
        failures.append({
            'qid': qid, 'shape': shape, 'issue': 'MISSING ENGINEER',
            'client': client, 'engineer': None,
            'q': qtxt
        })

print(f"\nTotal entity link failures: {len(failures)}")
for f in failures:
    print(f"\n[{f['qid']}] ({f['shape']}) — {f['issue']}")
    print(f"  Q: {f['q'][:120]}")
