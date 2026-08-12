import json
import sqlite3
import pandas as pd
import sys, os
import re

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker
from solution.solver.query_engine import QueryEngine

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
linker = EntityLinker('solution/db/knowledge_base.db')

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

suspect_qids = ['HV-IC-0148', 'HV-IC-0176', 'HV-IC-0285', 'HV-IC-0098', 'HV-IC-0229', 'HV-IC-0233']

for qid in suspect_qids:
    q = qs[qid]
    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    years = ent.get('years', [])
    
    print(f"[{qid}] Client: {client}")
    print(f"  Q: {qtxt}")
    
    # 1. HV-IC-0148: Annual diff (2022 vs 2023 for Arunodaya)
    if qid == 'HV-IC-0148':
        v1 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND completion_date LIKE '2022%'", (client,)).fetchone()[0] or 0
        v2 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND completion_date LIKE '2023%'", (client,)).fetchone()[0] or 0
        print(f"  Calculated Annual Diff: abs({v1:,} - {v2:,}) = {abs(v1 - v2):,}")
        
    # 2. HV-IC-0176: Exclusion aggregate (Suvarna minus industrial epc)
    if qid == 'HV-IC-0176':
        tot_excl = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND category != 'industrial epc'", (client,)).fetchone()[0] or 0
        print(f"  Calculated Exclusion (excl industrial epc): {tot_excl:,}")
        
    # 3. HV-IC-0285: Billing shortfall (Suvarna awarded vs invoiced)
    if qid == 'HV-IC-0285':
        crow = cur.execute("SELECT total_awarded_inr, total_invoiced_inr FROM clients WHERE client_name = ?", (client,)).fetchone()
        diff = abs(crow[0] - crow[1])
        print(f"  Calculated Billing Shortfall: {diff:,}")
        
    print()
