import json
import sqlite3
import pandas as pd
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = json.load(f)['questions']

linker = EntityLinker('solution/db/knowledge_base.db')

print("=== AUDITING ALL 24 DATE_SPAN QUESTIONS ===")
date_qs = [q for q in qs if classify_question(q['question'], q['answer_type']) == 'date_span']

for q in date_qs:
    qid = q['qid']
    qtxt = q['question']
    ent = linker.link(qtxt)
    cert = ent.get('cert')
    proj = ent.get('project')
    
    c_date = cert.get('issue_date') if cert else None
    p_date = proj.get('completion_date') if proj else None
    
    days = None
    if c_date and p_date:
        d1 = datetime.strptime(c_date, '%Y-%m-%d')
        d2 = datetime.strptime(p_date, '%Y-%m-%d')
        days = abs((d2 - d1).days)
        
    print(f"[{qid}] Days: {days} | Cert: {c_date} | Proj: {p_date} | Pkg: {ent.get('package_no')}")
    if days is None or days == 0:
        print(f"  FAILED/SUSPECT: {qtxt}\n")
