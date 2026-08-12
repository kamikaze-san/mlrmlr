import json
import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker

def test_samples():
    with open('sample_questions.json') as f:
        samples = json.load(f)['questions']
        
    linker = EntityLinker()
    conn = sqlite3.connect('solution/db/knowledge_base.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    for s in samples:
        qid = s['qid']
        qtext = s['question']
        gold = s.get('answer')
        shape = s.get('shape')
        atype = s['answer_type']
        
        entities = linker.link(qtext)
        client = entities['client_name']
        eng = entities['engineer']
        pkg = entities['package_no']
        proj = entities['project']
        cert = entities['cert']
        thresh = entities['threshold_inr']
        
        print(f"\n--- [{qid}] ({atype}) Shape: {shape} ---")
        print(f"Q: {qtext}")
        print(f"Entities: client='{client}', eng='{eng.get('name') if eng else None}', pkg='{pkg}', thresh={thresh}")
        print(f"Gold: {gold}")
        
if __name__ == '__main__':
    test_samples()
