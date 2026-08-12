import json
import os
import sys
import sqlite3
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.query_engine import QueryEngine

def check_all_333():
    engine = QueryEngine()
    with open('questions.json') as f:
        qs = json.load(f)['questions']
        
    results = []
    zero_records = []
    
    for q in qs:
        qid = q['qid']
        qtxt = q['question']
        atype = q['answer_type']
        
        ans = engine.solve_question(qid, qtxt, atype)
        results.append({'qid': qid, 'ans': ans, 'type': atype, 'question': qtxt})
        if ans == 0 or ans is None:
            zero_records.append({'qid': qid, 'type': atype, 'question': qtxt})
            
    print(f"Total evaluated: {len(results)}")
    print(f"Zero answers: {len(zero_records)}")
    if zero_records:
        for z in zero_records:
            print(f"[{z['qid']}] ({z['type']}): {z['question']}")

if __name__ == '__main__':
    check_all_333()
