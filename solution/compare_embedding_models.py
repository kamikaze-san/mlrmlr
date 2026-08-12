import json
import urllib.request
import numpy as np
import os, sys
from collections import Counter
import pandas as pd

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.semantic_classifier import PROTOTYPES

def get_embedding(text: str, model_name: str, host='http://127.0.0.1:11434') -> np.ndarray:
    data = {'model': model_name, 'prompt': text}
    req = urllib.request.Request(
        f"{host}/api/embeddings",
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        vec = np.array(res.get('embedding', []), dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

def build_centroids(model_name: str):
    cache_path = f"solution/solver/{model_name.replace(':', '_').replace('/', '_')}_centroids.json"
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            raw = json.load(f)
            return {k: np.array(v, dtype=np.float32) for k, v in raw.items()}
            
    print(f"Building prototype centroids for {model_name}...")
    centroids = {}
    serializable = {}
    for shape, examples in PROTOTYPES.items():
        vecs = [get_embedding(ex, model_name) for ex in examples]
        c = np.mean(vecs, axis=0)
        norm = np.linalg.norm(c)
        c = c / norm if norm > 0 else c
        centroids[shape] = c
        serializable[shape] = c.tolist()
        
    with open(cache_path, 'w') as f:
        json.dump(serializable, f)
    return centroids

def classify_dataset(model_name: str, centroids: dict, qs: list):
    import re
    results = {}
    for q in qs:
        qid = q['qid']
        qtxt = q['question']
        atype = q['answer_type']
        txt = qtxt.lower()
        
        # Structural rules
        if atype == 'days':
            results[qid] = 'date_span'
            continue
        if atype == 'count':
            results[qid] = 'absence' if any(w in txt for w in ['lack', 'no client reference', 'no reference letter', 'unreferenced']) else 'distinct_count'
            continue
        if atype == 'percent':
            if any(w in txt for w in ['endorsement', 'recommendation', 'reference letter', 'letters on file', 'client letters', 'endorse']):
                results[qid] = 'referenced_share'
            elif any(w in txt for w in ['collection', 'collected', 'invoiced', 'received', 'billed']):
                results[qid] = 'collection_rate'
            else:
                results[qid] = 'referenced_share'
            continue
            
        if ('completed after' in txt or 'wrapped up after' in txt or 'finished after' in txt or 'reached completion after' in txt) and ('2021' in txt or 'march' in txt or 'issuance' in txt or 'date' in txt or 'certification' in txt):
            results[qid] = 'temporal_chain'
            continue
        if any(w in txt for w in ['excluding', 'exclude', 'remove the', 'set aside', 'filter out', 'dropping the']):
            results[qid] = 'exclusion_aggregate'
            continue
        if ('average' in txt or 'mean' in txt or 'avg' in txt) and 'median' in txt:
            results[qid] = 'mean_vs_median'
            continue
        years = set(re.findall(r'\b(201\d|202\d)\b', txt))
        if len(years) >= 2 and any(w in txt for w in ['variance', 'difference', 'shift', 'movement', 'versus', 'gap', 'between 20', 'and 20', 'vs 20', 'move', 'delta']):
            results[qid] = 'annual_diff'
            continue
        cats_in_txt = [c for c in ['large bridges', 'bridges flyovers', 'bridges and flyovers', 'bridges', 'water treatment', 'water supply', 'tunnels', 'industrial epc', 'irrigation', 'roads highways', 'roads and highways', 'roads maintenance', 'maintenance', 'roads', 'small buildings', 'buildings', 'drainage', 'sewerage drainage', 'sewerage', 'expressways'] if c in txt]
        if len(cats_in_txt) >= 2 and 'median' not in txt and '201' not in txt and '202' not in txt and 'largest' not in txt:
            results[qid] = 'category_diff'
            continue
            
        # Semantic matching for remaining
        allowed = [
            'rank_value', 'billing_shortfall', 'outstanding_balance',
            'avg_work_size', 'mean_vs_median', 'exclusion_aggregate',
            'threshold_aggregate', 'gap_to_threshold', 'hop_aggregate'
        ]
        q_vec = get_embedding(qtxt, model_name)
        best_shape = 'hop_aggregate'
        best_score = -1.0
        for shape in allowed:
            if shape in centroids:
                score = float(np.dot(q_vec, centroids[shape]))
                if score > best_score:
                    best_score = score
                    best_shape = shape
        results[qid] = best_shape
    return results

def main():
    with open('questions.json') as f:
        qs = json.load(f)['questions']
        
    models = ['nomic-embed-text:latest', 'qwen3-embedding:4b']
    
    print("=" * 80)
    print("COMPARING EMBEDDING MODELS: Nomic-Embed-Text vs Qwen3-Embedding-4B")
    print("=" * 80)
    
    predictions = {}
    for m in models:
        centroids = build_centroids(m)
        print(f"Classifying 333 questions with {m}...")
        preds = classify_dataset(m, centroids, qs)
        predictions[m] = preds
        dist = Counter(preds.values())
        print(f"\nShape Distribution for {m}:")
        for k, v in dist.most_common():
            print(f"  {k:25s}: {v:3d}")
        print()
        
    # Compare differences
    m1, m2 = models[0], models[1]
    diffs = []
    for q in qs:
        qid = q['qid']
        p1 = predictions[m1][qid]
        p2 = predictions[m2][qid]
        if p1 != p2:
            diffs.append((qid, p1, p2, q['question']))
            
    print("=" * 80)
    print(f"COMPARISON SUMMARY: Agreement = {len(qs) - len(diffs)} / {len(qs)} ({(len(qs)-len(diffs))/len(qs)*100:.2f}%)")
    print(f"Total Disagreements: {len(diffs)}")
    print("=" * 80)
    
    for qid, p1, p2, qtxt in diffs:
        print(f"\n[{qid}]")
        print(f"  Nomic: {p1:20s} | Qwen3: {p2:20s}")
        print(f"  Q: {qtxt}")

if __name__ == '__main__':
    main()
