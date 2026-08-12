import json
import os
import sys
import sqlite3
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.query_engine import QueryEngine

def audit_sample():
    engine = QueryEngine()
    with open('questions.json') as f:
        qs = json.load(f)['questions']
        
    sample_indices = [3, 15, 33, 52, 70, 95, 120, 145, 180, 210, 235, 260, 290, 315, 330]
    
    conn = sqlite3.connect('solution/db/knowledge_base.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("=" * 80)
    print(f"DEEP AUDIT OF {len(sample_indices)} DIVERSE QUESTIONS FROM questions.json")
    print("=" * 80)
    
    for idx in sample_indices:
        q = qs[idx]
        qid = q['qid']
        qtxt = q['question']
        atype = q['answer_type']
        
        ent = engine.linker.link(qtxt)
        shape = engine.solve_question.__globals__['classify_question'](qtxt, atype)
        ans = engine.solve_question(qid, qtxt, atype)
        
        print(f"\n[Index {idx:3d} | ID: {qid}] Type: {atype.upper()} | Shape: {shape}")
        print(f"Question: \"{qtxt}\"")
        print(f"Entities: client='{ent['client_name']}', eng='{ent['engineer'].get('name') if ent['engineer'] else None}', pkg='{ent['package_no']}', thresh={ent['threshold_inr']}, excl='{ent['excluded_category']}', years={ent['years']}")
        print(f"Answer Generated: {ans}")
        
        # Print intermediate database facts for verification
        if ent['client_name']:
            cur.execute("SELECT project_name, value_inr, category, completion_date, has_reference_letter FROM projects WHERE client_name = ?", (ent['client_name'],))
            projs = cur.fetchall()
            print(f"-> Client Projects ({len(projs)} total):")
            for p in projs[:4]:
                print(f"   * {p['project_name']} | INR {p['value_inr']:,} | {p['category']} | {p['completion_date']} | Ref: {bool(p['has_reference_letter'])}")
            if len(projs) > 4:
                print(f"   * ... ({len(projs)-4} more projects)")
                
if __name__ == '__main__':
    audit_sample()
