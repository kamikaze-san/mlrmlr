import json
import sqlite3
import pandas as pd
import sys, os

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.semantic_classifier import SemanticClassifier
from solution.solver.entity_linker import EntityLinker
from solution.solver.query_engine import QueryEngine

with open('questions.json') as f:
    qs = json.load(f)['questions']

clf = SemanticClassifier()
linker = EntityLinker('solution/db/knowledge_base.db')
engine = QueryEngine()

df_ans = pd.read_csv('solution/answers_submission.csv')
ans_dict = dict(zip(df_ans['question_id'], df_ans['answer']))

print("=" * 80)
print("EXHAUSTIVE AUDIT OF ALL 333 REAL QUESTIONS WITH SEMANTIC CONFIDENCE")
print("=" * 80)

audit_results = []
for q in qs:
    qid = q['qid']
    qtxt = q['question']
    atype = q['answer_type']
    
    # 1. Structural rule classification
    rule_shape = classify_question(qtxt, atype)
    
    # 2. Semantic classifier raw score
    sem_shape, sem_score = clf.classify(qtxt, atype)
    
    # 3. Entity extraction
    ent = linker.link(qtxt)
    
    # 4. Computed answer
    ans = ans_dict.get(qid)
    
    audit_results.append({
        'qid': qid,
        'qtxt': qtxt,
        'atype': atype,
        'final_shape': rule_shape,
        'sem_shape': sem_shape,
        'sem_score': sem_score,
        'client': ent.get('client_name'),
        'eng': ent.get('engineer', {}).get('name') if ent.get('engineer') else None,
        'ans': ans
    })

# Check where rule_shape and sem_shape disagree
disagreements = [r for r in audit_results if r['final_shape'] != r['sem_shape']]
print(f"\nTotal Rule vs Semantic Classifier Disagreements: {len(disagreements)}")
for d in disagreements:
    print(f"[{d['qid']}] Rule: {d['final_shape']:20s} | Semantic: {d['sem_shape']:20s} (Score: {d['sem_score']:.3f}) | Client: {d['client']}")
    print(f"  Q: {d['qtxt']}\n")

# Check questions with lowest semantic scores (< 0.70)
low_conf = [r for r in audit_results if r['sem_score'] < 0.70]
print(f"\nTotal Low Confidence Semantic Classifications (< 0.70): {len(low_conf)}")
for l in low_conf:
    print(f"[{l['qid']}] Final: {l['final_shape']:20s} | Sem: {l['sem_shape']:20s} (Score: {l['sem_score']:.3f})")
    print(f"  Q: {l['qtxt']}\n")
