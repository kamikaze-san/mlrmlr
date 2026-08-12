import json
import sqlite3
import pandas as pd
import sys, os

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.semantic_classifier import SemanticClassifier
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = json.load(f)['questions']

clf = SemanticClassifier()
linker = EntityLinker('solution/db/knowledge_base.db')

print("=" * 80)
print("PRINTING ALL RULE vs SEMANTIC CLASSIFIER DISAGREEMENTS")
print("=" * 80)

disagreements = []
for q in qs:
    qid = q['qid']
    qtxt = q['question']
    atype = q['answer_type']
    
    rule_shape = classify_question(qtxt, atype)
    sem_shape, sem_score = clf.classify(qtxt, atype)
    
    if rule_shape != sem_shape:
        ent = linker.link(qtxt)
        disagreements.append({
            'qid': qid,
            'rule_shape': rule_shape,
            'sem_shape': sem_shape,
            'sem_score': sem_score,
            'client': ent.get('client_name'),
            'qtxt': qtxt
        })

print(f"Total Disagreements: {len(disagreements)}\n")
for d in disagreements:
    print(f"[{d['qid']}] RULE: {d['rule_shape']:20s} | SEMANTIC: {d['sem_shape']:20s} ({d['sem_score']:.3f}) | Client: {d['client']}")
    print(f"  Q: {d['qtxt']}\n")
