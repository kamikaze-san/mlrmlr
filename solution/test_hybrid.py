import json
import sys, os
sys.path.insert(0, os.path.abspath('.'))

from solution.solver.question_parser import classify_question
from solution.solver.semantic_classifier import SemanticClassifier

with open('sample_questions.json') as f:
    sample = json.load(f)['questions']

clf = SemanticClassifier()

def hybrid_classify(qtxt: str, atype: str) -> str:
    # 1. Structural rules
    txt = qtxt.lower()
    
    # Days & percent
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
        
    # Temporal chain explicit date filter
    if 'completed after' in txt or 'wrapped up after' in txt or 'finished after' in txt or 'reached completion after' in txt or 'only the works he led that finished after' in txt or 'just the works she led that finished after' in txt:
        return 'temporal_chain'
        
    # Exclusion
    if 'excluding' in txt or 'exclude' in txt or 'remove the' in txt or 'set aside' in txt or 'filter out' in txt or 'dropping the' in txt:
        return 'exclusion_aggregate'
        
    # Mean vs Median
    if ('average' in txt or 'mean' in txt or 'avg' in txt) and 'median' in txt:
        return 'mean_vs_median'
        
    # Category Diff
    cats_in_txt = [c for c in ['large bridges', 'bridges flyovers', 'bridges and flyovers', 'bridges', 'water treatment', 'water supply', 'tunnels', 'industrial epc', 'irrigation', 'roads highways', 'roads and highways', 'roads maintenance', 'maintenance', 'roads', 'small buildings', 'buildings', 'drainage', 'sewerage drainage', 'sewerage', 'expressways'] if c in txt]
    if len(cats_in_txt) >= 2 and 'median' not in txt and '201' not in txt and '202' not in txt:
        return 'category_diff'
        
    # Use Semantic Classifier for remaining natural language questions
    sem_shape, conf = clf.classify(qtxt, atype)
    return sem_shape

print("=" * 80)
print("TESTING HYBRID CLASSIFIER ON sample_questions.json")
print("=" * 80)

correct = 0
for q in sample:
    qid = q['qid']
    gold_shape = q.get('shape')
    qtxt = q['question']
    atype = q['answer_type']
    pred = hybrid_classify(qtxt, atype)
    
    match = (pred == gold_shape)
    if match: correct += 1
    print(f"[{qid}] {'[OK]' if match else '[MISMATCH]'} | Gold: {gold_shape:20s} | Pred: {pred:20s}")
    if not match:
        print(f"  Q: {qtxt}")

print("\n" + "=" * 80)
print(f"Hybrid Accuracy on Benchmark: {correct} / {len(sample)} ({correct/len(sample)*100:.1f}%)")
print("=" * 80)
