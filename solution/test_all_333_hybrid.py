import json
import sqlite3
import pandas as pd
import sys, os
from collections import Counter

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.query_engine import QueryEngine
from solution.solver.entity_linker import EntityLinker
from solution.solver.semantic_classifier import SemanticClassifier
import re
import numpy as np

with open('questions.json') as f:
    qs = json.load(f)['questions']

clf = SemanticClassifier()

def hybrid_classify(qtxt: str, atype: str) -> str:
    txt = qtxt.lower()
    
    # 1. Type constraints
    if atype == 'days':
        return 'date_span'
    if atype == 'count':
        if 'lack' in txt or 'no client reference' in txt or 'no reference letter' in txt or 'unreferenced' in txt:
            return 'absence'
        return 'distinct_count'
    if atype == 'percent':
        if 'endorsement' in txt or 'recommendation' in txt or 'reference letter' in txt or 'letters on file' in txt or 'client letters' in txt or 'endorse' in txt:
            return 'referenced_share'
        if 'collection' in txt or 'collected' in txt or 'invoiced' in txt or 'received' in txt or 'billed' in txt:
            return 'collection_rate'
        return 'referenced_share'
        
    # 2. MONEY structural rules
    # Temporal chain: MUST have a completion/date condition
    if ('completed after' in txt or 'wrapped up after' in txt or 'finished after' in txt or 'reached completion after' in txt) and ('2021' in txt or 'march' in txt or 'issuance' in txt or 'date' in txt or 'certification' in txt):
        return 'temporal_chain'
        
    # Exclusion
    if 'excluding' in txt or 'exclude' in txt or 'remove the' in txt or 'set aside' in txt or 'filter out' in txt or 'dropping the' in txt:
        return 'exclusion_aggregate'
        
    # Mean vs Median
    if ('average' in txt or 'mean' in txt or 'avg' in txt) and 'median' in txt:
        return 'mean_vs_median'
        
    # Annual diff (2+ distinct years mentioned)
    years = set(re.findall(r'\b(201\d|202\d)\b', txt))
    if len(years) >= 2 and any(w in txt for w in ['variance', 'difference', 'shift', 'movement', 'versus', 'gap', 'between 20', 'and 20']):
        return 'annual_diff'
        
    # Category Diff (2+ distinct work categories)
    cats_in_txt = [c for c in ['large bridges', 'bridges flyovers', 'bridges and flyovers', 'bridges', 'water treatment', 'water supply', 'tunnels', 'industrial epc', 'irrigation', 'roads highways', 'roads and highways', 'roads maintenance', 'maintenance', 'roads', 'small buildings', 'buildings', 'drainage', 'sewerage drainage', 'sewerage', 'expressways'] if c in txt]
    if len(cats_in_txt) >= 2 and 'median' not in txt and '201' not in txt and '202' not in txt and 'largest' not in txt:
        return 'category_diff'
        
    # Semantic Classifier for remaining natural language shapes
    allowed = [
        'rank_value', 'billing_shortfall', 'outstanding_balance',
        'avg_work_size', 'mean_vs_median', 'exclusion_aggregate',
        'threshold_aggregate', 'gap_to_threshold', 'hop_aggregate'
    ]
    
    q_vec = clf._get_embedding(qtxt)
    best_shape = 'hop_aggregate'
    best_score = -1.0
    for shape in allowed:
        if shape in clf.prototype_embeddings:
            score = float(np.dot(q_vec, clf.prototype_embeddings[shape]))
            if score > best_score:
                best_score = score
                best_shape = shape
                
    return best_shape

# Classify all 333 questions
shapes = Counter()
for q in qs:
    s = hybrid_classify(q['question'], q['answer_type'])
    shapes[s] += 1

print("=" * 80)
print("HYBRID CLASSIFICATION DISTRIBUTION ACROSS ALL 333 QUESTIONS")
print("=" * 80)
for k, v in shapes.most_common():
    print(f"  {k:25s}: {v:3d}")
