import json
import sys, os
sys.path.insert(0, os.path.abspath('.'))

from solution.compare_embedding_models import build_centroids, classify_dataset

with open('sample_questions.json') as f:
    sample = json.load(f)['questions']

qwen_centroids = build_centroids('qwen3-embedding:4b')
preds = classify_dataset('qwen3-embedding:4b', qwen_centroids, sample)

correct = 0
for q in sample:
    qid = q['qid']
    gold = q.get('shape')
    pred = preds[qid]
    match = (pred == gold)
    if match: correct += 1
    print(f"[{qid}] {'[OK]' if match else '[MISMATCH]'} | Gold: {gold:20s} | Pred: {pred:20s}")
    if not match:
        print(f"  Q: {q['question']}")

print("\n" + "=" * 80)
print(f"Qwen3-Embedding-4B Accuracy on Sample Benchmark: {correct} / {len(sample)} ({correct/len(sample)*100:.1f}%)")
print("=" * 80)
