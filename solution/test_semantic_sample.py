import json
import sys, os
sys.path.insert(0, os.path.abspath('.'))

from solution.solver.semantic_classifier import SemanticClassifier

with open('sample_questions.json') as f:
    sample = json.load(f)['questions']

clf = SemanticClassifier()

correct = 0
total = len(sample)

print("=" * 80)
print("EVALUATING SEMANTIC CLASSIFIER ON sample_questions.json")
print("=" * 80)

for q in sample:
    qid = q['qid']
    gold_shape = q.get('shape')
    qtxt = q['question']
    atype = q['answer_type']
    
    pred_shape, score = clf.classify(qtxt, atype)
    
    is_match = (pred_shape == gold_shape)
    if is_match:
        correct += 1
        status = "[OK]"
    else:
        status = "[MISMATCH]"
        
    print(f"[{qid}] {status} | Gold: {gold_shape:20s} | Pred: {pred_shape:20s} ({score:.3f})")
    if not is_match:
        print(f"  Q: {qtxt}")

print("\n" + "=" * 80)
print(f"Semantic Classifier Sample Accuracy: {correct} / {total} ({correct/total*100:.1f}%)")
print("=" * 80)
