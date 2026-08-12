import json
import sqlite3
import pandas as pd
import re
import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.query_engine import QueryEngine
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker

def audit_all_questions():
    with open('questions.json') as f:
        qs = json.load(f)['questions']
        
    engine = QueryEngine(use_llm_fallback=False)
    linker = EntityLinker('solution/db/knowledge_base.db')
    
    shapes_count = {}
    suspicious = []
    
    for q in qs:
        qid = q['qid']
        qtxt = q['question']
        atype = q['answer_type']
        
        shape = classify_question(qtxt, atype)
        shapes_count[shape] = shapes_count.get(shape, 0) + 1
        
        ans = engine.solve_question(qid, qtxt, atype)
        ent = linker.link(qtxt)
        
        # Check suspicious conditions
        is_suspicious = False
        reason = ""
        
        if ans == 0 or ans is None:
            is_suspicious = True
            reason = "Answer is 0 or None"
        elif shape == 'hop_aggregate' and ('average' in qtxt.lower() or 'mean' in qtxt.lower()):
            is_suspicious = True
            reason = "Average/Mean in hop_aggregate question"
        elif shape == 'hop_aggregate' and ('excluding' in qtxt.lower() or 'exclude' in qtxt.lower()):
            is_suspicious = True
            reason = "Exclusion in hop_aggregate question"
        elif shape == 'hop_aggregate' and ('after' in qtxt.lower() or 'before' in qtxt.lower() or 'since' in qtxt.lower()) and ('201' in qtxt or '202' in qtxt):
            is_suspicious = True
            reason = "Date filter in hop_aggregate question"
        elif shape == 'hop_aggregate' and ('threshold' in qtxt.lower() or 'exceeding' in qtxt.lower() or 'valued at' in qtxt.lower() or 'crore' in qtxt.lower()):
            is_suspicious = True
            reason = "Threshold in hop_aggregate question"
            
        if is_suspicious:
            suspicious.append({
                'qid': qid,
                'type': atype,
                'shape': shape,
                'question': qtxt,
                'ans': ans,
                'reason': reason,
                'entities': ent
            })
            
    print("=== SHAPE DISTRIBUTION (333 Questions) ===")
    for s, c in sorted(shapes_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  * {s:25s}: {c:3d} questions ({c/len(qs)*100:.1f}%)")
        
    print(f"\n=== POTENTIALLY MISCLASSIFIED OR SUSPICIOUS QUESTIONS ({len(suspicious)}) ===")
    for item in suspicious:
        print(f"\n[{item['qid']}] ({item['type']}) -> classified as '{item['shape']}' | Reason: {item['reason']}")
        print(f"  Q: \"{item['question']}\"")
        print(f"  Ans: {item['ans']}")

if __name__ == '__main__':
    audit_all_questions()
