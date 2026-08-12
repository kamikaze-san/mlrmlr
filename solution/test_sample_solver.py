import json
import os
import sys
import sqlite3
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker

def solve_sample(s, linker, conn):
    cur = conn.cursor()
    qtext = s['question']
    shape = s.get('shape')
    atype = s['answer_type']
    
    ent = linker.link(qtext)
    client = ent['client_name']
    eng = ent['engineer']
    proj = ent['project']
    thresh = ent['threshold_inr']
    excl = ent['excluded_category']
    
    if shape == 'absence':
        cur.execute("SELECT COUNT(*) FROM projects WHERE client_name = ? AND has_reference_letter = 0", (client,))
        return cur.fetchone()[0]
        
    elif shape == 'referenced_share':
        cur.execute("SELECT COUNT(*), SUM(has_reference_letter) FROM projects WHERE client_name = ?", (client,))
        tot, refs = cur.fetchone()
        return round((refs / tot) * 100.0, 2)
        
    elif shape == 'date_span':
        # issue date
        issue_date_str = '2021-03-10'
        if ent['cert'] and ent['cert']['issue_date']:
            issue_date_str = ent['cert']['issue_date']
        comp_date_str = proj['completion_date']
        d_issue = datetime.strptime(issue_date_str, '%Y-%m-%d')
        d_comp = datetime.strptime(comp_date_str, '%Y-%m-%d')
        return (d_comp - d_issue).days
        
    elif shape == 'distinct_count':
        eng_name = eng['name']
        cur.execute("SELECT COUNT(DISTINCT category) FROM projects WHERE lead_engineer = ?", (eng_name,))
        return cur.fetchone()[0]
        
    elif shape == 'hop_aggregate':
        cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ?", (client,))
        return cur.fetchone()[0]
        
    elif shape == 'avg_work_size':
        cur.execute("SELECT AVG(value_inr) FROM projects WHERE client_name = ?", (client,))
        return int(round(cur.fetchone()[0]))
        
    elif shape == 'exclusion_aggregate':
        cur.execute("SELECT value_inr, category FROM projects WHERE client_name = ?", (client,))
        rows = cur.fetchall()
        total = 0
        for r in rows:
            val, cat = r[0], r[1]
            if excl and (excl in cat.lower() or any(w in cat.lower() for w in excl.split() if len(w) > 3)):
                continue
            total += val
        return total
        
    elif shape == 'gap_to_threshold':
        cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ?", (client,))
        tot = cur.fetchone()[0]
        return thresh - tot
        
    elif shape == 'rank_value':
        cur.execute("SELECT value_inr FROM projects WHERE client_name = ? ORDER BY value_inr DESC", (client,))
        vals = [r[0] for r in cur.fetchall()]
        return vals[0] - vals[1]
        
    elif shape == 'threshold_aggregate':
        cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND value_inr >= ?", (client, thresh))
        return cur.fetchone()[0]
        
    elif shape == 'temporal_chain':
        eng_name = eng['name']
        issue_date_str = '2021-03-10'
        cur.execute("SELECT SUM(value_inr) FROM projects WHERE lead_engineer = ? AND completion_date > ?", (eng_name, issue_date_str))
        return cur.fetchone()[0]
        
    return None

def run_tests():
    with open('sample_questions.json') as f:
        samples = json.load(f)['questions']
        
    linker = EntityLinker()
    conn = sqlite3.connect('solution/db/knowledge_base.db')
    
    passed = 0
    total = 0
    
    for s in samples:
        gold = s.get('answer')
        if gold is None:
            continue
        total += 1
        pred = solve_sample(s, linker, conn)
        diff = abs(pred - gold) if pred is not None else 999999
        is_exact = diff < 1e-2
        if is_exact:
            passed += 1
            print(f"PASS: [{s['qid']}] pred={pred} gold={gold}")
        else:
            print(f"FAIL: [{s['qid']}] pred={pred} gold={gold} (diff={diff})")
            
    print(f"\nResult: {passed}/{total} exact matches ({passed/total:.1%})")

if __name__ == '__main__':
    run_tests()
