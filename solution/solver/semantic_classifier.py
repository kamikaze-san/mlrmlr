import json
import urllib.request
import numpy as np
import os
import re

PROTOTYPES = {
    'rank_value': [
        "what is the exact surplus value separating our highest-value finished contract from the next one down?",
        "by how much does our largest completed contract exceed the second-largest?",
        "how much our top finished contract beats the one just behind it by?",
        "difference between our biggest and next completed jobs",
        "precise difference between our highest-value completed assignment and the subsequent one",
        "amount by which our highest-value finished contract exceeds the runner up"
    ],
    'billing_shortfall': [
        "what is the actual gap between what they've sanctioned and what we've billed?",
        "confirm the unbilled remainder after comparing the total awarded contract value against our submitted claims",
        "what is the amount after we cross-check against the invoice amount?",
        "shortfall between the total value of the projects handed over and what we've managed to bill so far",
        "how much of the total value is still sitting above what we've actually invoiced?",
        "outstanding balance against the total contract value and submitted claims",
        "true gap between the full value of awards and what we managed to invoice"
    ],
    'outstanding_balance': [
        "calculate the total remaining balance across all charged amounts for this account",
        "what is the total amount still due across all unpaid invoices on file?",
        "what is the pending balance on our books after deducting all cleared payments?",
        "remaining balance across all billing charges and invoices on record"
    ],
    'collection_rate': [
        "what percentage of the billed amount has been collected and cleared?",
        "what whole number or decimal percentage of submitted claims have we actually received against invoiced?",
        "collection rate across all invoice charges on file"
    ],
    'date_span': [
        "how many days elapsed from the PMP certification issue date to project completion?",
        "what is the exact span in days from certification issuance to wrap up and handover?",
        "number of days from March 10 2021 PMP issue to completion date"
    ],
    'avg_work_size': [
        "what is the average contract value across all completed engagements for this client?",
        "what is the mean contract scale across our completed jobs for this commissioning authority?",
        "what is the typical project scale across all finished engagements we have delivered?",
        "typical scale across every completed assignment handed over to the client",
        "proper baseline average contract value across completed projects"
    ],
    'mean_vs_median': [
        "how much larger the average contract value is than the median, negative if smaller?",
        "what is the rupee gap between the mean project value and median project value?",
        "avg minus median client value in rupees, negative if lower?",
        "derive how much larger the average contract value is than the median, leave negative if average is smaller"
    ],
    'category_diff': [
        "what is the absolute difference in completed work value between roads highways and bridges flyovers?",
        "expressways versus tunnels totals, what is the net difference in total contract value?",
        "what is the difference in value between large bridges and water treatment for this client?",
        "compare industrial epc and sewerage drainage completed contract amounts"
    ],
    'annual_diff': [
        "what is the net difference in the value of work completed between 2020 and 2022?",
        "what is the year-on-year movement in completed work value from 2016 through 2018?",
        "2019 versus 2021 completed work value shifted, what is the actual variance?",
        "net shift in completed work value between 2013 and 2017",
        "verified gap between 2013 completed work total and the 2025 figure"
    ],
    'exclusion_aggregate': [
        "excluding water treatment, what is the auditable sum of every completed project?",
        "what is the defensible figure we should quote once we filter out the industrial epc work?",
        "minus the water treatment side, what is the actual total value?",
        "excluding small buildings, what is the actual value we are carrying?",
        "after the water treatment division is excluded, what is the aggregate figure?",
        "what is the sum we need to quote after dropping the industrial epc work?"
    ],
    'threshold_aggregate': [
        "what is the cumulative figure for contracts valued at twenty-two crore rupees or higher?",
        "what is the sum for anything hitting fifteen crore or more?",
        "combined value for anything clearing the eleven crore mark",
        "contracts meeting or exceeding the 23 crore threshold limit",
        "contracts valued at twenty-two crore rupees or higher",
        "combined value of contracts crossing the 15 crore cutoff"
    ],
    'gap_to_threshold': [
        "how much more contract value do we need to clear the 70 crore threshold mark?",
        "how much additional value do we need to reach our credential target?",
        "how much more value do we need to bring in to hit the threshold?"
    ],
    'temporal_chain': [
        "what is the combined value of only the works he led that finished after that PMP issuance date?",
        "what is the aggregate value of assignments that wrapped up after that certification date 2021-03-10?",
        "sum of projects she led that reached completion after her PMP was issued on 2021-03-10"
    ],
    'distinct_count': [
        "how many different categories of work has Chandan Banerjee led to completion?",
        "how many unique distinct sectors has the engineer delivered projects in?",
        "how many different categories of work has the engineer led to completion under his credential?"
    ],
    'absence': [
        "how many completed projects lack a client reference letter on file?",
        "how many assignments have no reference letter or client testimonial?",
        "how many works have no reference letter on record?"
    ],
    'referenced_share': [
        "what percentage of completed works have an official reference letter endorsement on file?",
        "what is the proportion of projects with cleared testimonial letters and endorsements?",
        "what percentage of client projects have reference letters attached?"
    ],
    'hop_aggregate': [
        "what is the combined value of every completed assignment he has done for that client right now to lock the submission?",
        "what is the combined value of all completed assignments she has delivered to that client under her credential?",
        "what is the total value of all completed assignments delivered to that client?",
        "what is the full tally of every completed scope she has delivered to the client?"
    ]
}

CACHE_FILE = 'solution/solver/qwen3_embedding_4b_centroids.json'

class SemanticClassifier:
    def __init__(self, host='http://127.0.0.1:11434', model='qwen3-embedding:4b'):
        self.host = host
        self.model = model
        self.prototype_embeddings = {}
        self._load_or_build_prototypes()
        
    def _get_embedding(self, text: str) -> np.ndarray:
        data = {'model': self.model, 'prompt': text}
        req = urllib.request.Request(
            f"{self.host}/api/embeddings",
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            vec = np.array(res.get('embedding', []), dtype=np.float32)
            norm = np.linalg.norm(vec)
            return vec / norm if norm > 0 else vec

    def _load_or_build_prototypes(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    raw = json.load(f)
                    self.prototype_embeddings = {k: np.array(v, dtype=np.float32) for k, v in raw.items()}
                    print(f"Loaded {len(self.prototype_embeddings)} prototype centroid embeddings from cache.")
                    return
            except Exception:
                pass
                
        print("Computing prototype embeddings via Ollama...")
        self.prototype_embeddings = {}
        serializable = {}
        for shape, examples in PROTOTYPES.items():
            vecs = [self._get_embedding(ex) for ex in examples]
            centroid = np.mean(vecs, axis=0)
            norm = np.linalg.norm(centroid)
            centroid = centroid / norm if norm > 0 else centroid
            self.prototype_embeddings[shape] = centroid
            serializable[shape] = centroid.tolist()
            
        with open(CACHE_FILE, 'w') as f:
            json.dump(serializable, f)
        print(f"Cached {len(self.prototype_embeddings)} prototype centroids to {CACHE_FILE}.")

    def classify(self, question_text: str, answer_type: str) -> tuple[str, float]:
        # Fast type-constrained filtering
        allowed_shapes = []
        if answer_type == 'percent':
            allowed_shapes = ['referenced_share', 'collection_rate']
        elif answer_type == 'days':
            return 'date_span', 1.0
        elif answer_type == 'count':
            allowed_shapes = ['absence', 'distinct_count']
        elif answer_type == 'money':
            allowed_shapes = [
                'rank_value', 'billing_shortfall', 'outstanding_balance',
                'avg_work_size', 'mean_vs_median', 'category_diff',
                'annual_diff', 'exclusion_aggregate', 'threshold_aggregate',
                'gap_to_threshold', 'temporal_chain', 'hop_aggregate'
            ]
        else:
            allowed_shapes = list(self.prototype_embeddings.keys())
            
        q_vec = self._get_embedding(question_text)
        
        best_shape = allowed_shapes[0]
        best_score = -1.0
        
        for shape in allowed_shapes:
            if shape in self.prototype_embeddings:
                score = float(np.dot(q_vec, self.prototype_embeddings[shape]))
                if score > best_score:
                    best_score = score
                    best_shape = shape
                    
        return best_shape, best_score

if __name__ == '__main__':
    clf = SemanticClassifier()
    test_q = "National Expressway Development Authority, what is the exact surplus value separating our highest-value finished contract from the next one down?"
    shape, score = clf.classify(test_q, 'money')
    print(f"Test Classification: {shape} (Cosine Similarity: {score:.4f})")
