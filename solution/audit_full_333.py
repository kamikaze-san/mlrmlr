import json
import sqlite3
import pandas as pd
import numpy as np
import re
import os
import sys

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.query_engine import QueryEngine
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker

def audit_full_333():
    with open('questions.json') as f:
        qs = json.load(f)['questions']
        
    engine = QueryEngine(use_llm_fallback=False)
    linker = EntityLinker('solution/db/knowledge_base.db')
    conn = sqlite3.connect('solution/db/knowledge_base.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    records = []
    for q in qs:
        qid = q['qid']
        qtxt = q['question']
        atype = q['answer_type']
        
        shape = classify_question(qtxt, atype)
        ent = linker.link(qtxt)
        ans = engine.solve_question(qid, qtxt, atype)
        
        records.append({
            'qid': qid,
            'atype': atype,
            'shape': shape,
            'qtxt': qtxt,
            'ans': ans,
            'client': ent.get('client_name'),
            'eng': ent.get('engineer', {}).get('name') if ent.get('engineer') else None,
            'pkg': ent.get('package_no'),
            'thresh': ent.get('threshold_inr'),
            'excl': ent.get('excluded_category'),
            'years': ent.get('years')
        })
        
    df = pd.DataFrame(records)
    print(f"Total Questions Analyzed: {len(df)}")
    
    # 1. Check any remaining zeros or nulls
    bad_ans = df[df['ans'].isnull() | (df['ans'] == 0)]
    print(f"\n1. Zeros or Nulls: {len(bad_ans)}")
    for _, r in bad_ans.iterrows():
        print(f"  [{r['qid']}] ({r['shape']}) Q: {r['qtxt'][:80]}")

    # 2. Check date_span questions for cert issue date vs valid through
    print("\n2. Checking all 24 DATE_SPAN questions:")
    for _, r in df[df['shape'] == 'date_span'].iterrows():
        q_l = r['qtxt'].lower()
        print(f"  [{r['qid']}] Ans: {r['ans']} | Pkg: {r['pkg']} | Q: {r['qtxt'][:90]}...")
        
    # 3. Check rank_value questions (2nd largest)
    print("\n3. Checking all RANK_VALUE questions:")
    for _, r in df[df['shape'] == 'rank_value'].iterrows():
        print(f"  [{r['qid']}] Ans: {r['ans']} | Client: {r['client']} | Q: {r['qtxt'][:90]}...")
        
    # 4. Check gap_to_threshold questions
    print("\n4. Checking all GAP_TO_THRESHOLD questions:")
    for _, r in df[df['shape'] == 'gap_to_threshold'].iterrows():
        print(f"  [{r['qid']}] Ans: {r['ans']} | Thresh: {r['thresh']} | Client: {r['client']} | Q: {r['qtxt'][:90]}...")
        
    # 5. Check temporal_chain questions
    print("\n5. Checking all TEMPORAL_CHAIN questions:")
    for _, r in df[df['shape'] == 'temporal_chain'].iterrows():
        print(f"  [{r['qid']}] Ans: {r['ans']} | Eng: {r['eng']} | Client: {r['client']} | Q: {r['qtxt'][:90]}...")

if __name__ == '__main__':
    audit_full_333()
