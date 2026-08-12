import json
import os
import sys
import re
from collections import Counter

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker

import json
import os
import sys
import re
from collections import Counter
import numpy as np

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker
from solution.solver.semantic_classifier import SemanticClassifier
from solution.solver.llm_classifier import classify_llm
from solution.extractors.money_parser import extract_threshold_rupees

_SEMANTIC_CLF = None

def get_semantic_classifier():
    global _SEMANTIC_CLF
    if _SEMANTIC_CLF is None:
        try:
            _SEMANTIC_CLF = SemanticClassifier()
        except Exception:
            _SEMANTIC_CLF = None
    return _SEMANTIC_CLF

def classify_question(qtext: str, atype: str) -> str:
    txt = qtext.lower()
    
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
        
    # 2. Structural rules for MONEY
    # Temporal chain: MUST have a completion/date condition
    if ('completed after' in txt or 'wrapped up after' in txt or 'finished after' in txt or 'reached completion after' in txt or 'finished after that' in txt or 'wrapped up after that' in txt or 'post-certification' in txt) and ('2021' in txt or 'march' in txt or 'issuance' in txt or 'date' in txt or 'certification' in txt or 'certified' in txt):
        return 'temporal_chain'

    # Exclusion
    if 'excluding' in txt or 'exclude' in txt or 'remove the' in txt or 'set aside' in txt or 'setting aside' in txt or 'filter out' in txt or 'dropping the' in txt or 'stripped out' in txt or 'strip out' in txt or 'without' in txt or 'take out' in txt or 'taking out' in txt or 'leaving out' in txt or 'leave out' in txt or 'not counting' in txt:
        return 'exclusion_aggregate'
        
    # Mean vs Median
    if ('average' in txt or 'mean' in txt or 'avg' in txt) and 'median' in txt:
        return 'mean_vs_median'
        
    # Outstanding balance (unpaid invoices / remaining balance across charges)
    if (
        'unpaid' in txt or 
        'remaining balance' in txt or 
        'remain unpaid' in txt or 
        'still owe' in txt or
        'still due' in txt or
        'pending' in txt or
        'balance due' in txt or
        'net balance' in txt or
        'adjusted balance' in txt or
        'system balance' in txt or
        'credits are applied' in txt or
        'amount remains on the invoices' in txt or
        'balance when i cross-check' in txt or
        'balance still on our books' in txt or
        'balance still on their end' in txt or
        'cleared payments from our total billed' in txt or
        'deduct every cleared payment' in txt or
        'deducting all cleared payments' in txt or
        ('still outstanding' in txt and ('invoice' in txt or 'bill' in txt or 'charge' in txt)) or
        ('currently due' in txt and ('charge' in txt or 'bill' in txt or 'invoice' in txt))
    ) and 'contract value' not in txt and 'awarded' not in txt and 'sanctioned' not in txt:
        return 'outstanding_balance'

    # Annual diff (2+ distinct years mentioned)
    years = set(re.findall(r'\b(201\d|202\d)\b', txt))
    if len(years) >= 2:
        return 'annual_diff'

    # Category Diff (2+ distinct work categories)
    cats_in_txt = [c for c in ['large bridges', 'bridges flyovers', 'bridges and flyovers', 'bridges', 'water treatment', 'water supply', 'tunnels', 'industrial epc', 'irrigation', 'roads highways', 'roads and highways', 'roads maintenance', 'maintenance', 'roads', 'small buildings', 'buildings', 'drainage', 'sewerage drainage', 'sewerage', 'expressways'] if c in txt]
    if len(cats_in_txt) >= 2 and 'median' not in txt and '201' not in txt and '202' not in txt and 'largest' not in txt:
        return 'category_diff'

    # Billing shortfall (gap between contract values/awards and billed/invoiced amounts)
    if ('gap between' in txt or 'shortfall' in txt or 'net difference' in txt or 'amount after we cross-check' in txt or 'delta between' in txt or 'unbilled' in txt or 'missing amount' in txt or 'sitting above' in txt or 'against the total contract value' in txt or 'claims we submitted' in txt) and ('invoiced' in txt or 'billed' in txt or 'sanctioned' in txt or 'actual gap' in txt or 'submitted claims' in txt or 'claimed' in txt or 'cash flow' in txt or 'commitments' in txt or 'awards' in txt or 'total value' in txt or 'contract value' in txt or 'invoice amount' in txt):
        return 'billing_shortfall'
        
    if 'unbilled remainder' in txt or 'shortfall between' in txt or 'gap between what they\'ve sanctioned' in txt:
        return 'billing_shortfall'

    # Avg work size
    if 'average size' in txt or 'mean size' in txt or 'overall average' in txt or 'actual average' in txt or 'mean volume' in txt or 'mean scale' in txt or 'proper baseline' in txt or 'mean across all' in txt or 'mean across' in txt or 'mean contract value' in txt or 'average contract value' in txt or 'average across all' in txt or 'typical scale' in txt or 'typical project scale' in txt or 'typical value' in txt:
        return 'avg_work_size'

    # Rank value (difference between #1 and #2 largest contracts)
    if ('largest' in txt or 'top finished' in txt or 'highest-value' in txt or 'biggest' in txt) and ('second' in txt or 'second-largest' in txt or 'second-biggest' in txt or 'next one down' in txt or 'one just behind' in txt or 'subsequent one' in txt or 'next completed' in txt or 'beats' in txt):
        return 'rank_value'

    # Gap to threshold
    if 'additional work' in txt or 'reach our credential target' in txt or 'how much more contract value' in txt or 'bring in to hit' in txt or 'still need to secure' in txt or 'need to clear the' in txt or 'how much more value do we need' in txt:
        return 'gap_to_threshold'

    # Threshold aggregate (MUST be an actual financial threshold query).
    # Requires a real parsed crore/lakh amount, not just words that happen to
    # contain "cr" or "line" as a substring (e.g. "across", "deadline").
    if (
        ('threshold' in txt or 'mark' in txt or ('line' in txt and 'line item' not in txt) or 'hitting' in txt or 'at or over' in txt or 'meet or exceed' in txt or 'clear that mark' in txt or 'clearing the' in txt or 'or higher' in txt or 'or more' in txt or 'valued at' in txt or 'crossing the' in txt)
        and any(w in txt for w in ['crore', 'cr', 'lakh', 'valued at', 'mark', 'threshold', 'or more', 'or higher', 'at or over', 'hitting'])
        and extract_threshold_rupees(qtext) > 0
    ):
        return 'threshold_aggregate'

    # Hop aggregate: Explicit full portfolio rollups across completed assignments
    if (
        'every completed assignment' in txt or
        'all completed assignments' in txt or
        'every completed work' in txt or
        'all completed work' in txt or
        'all completed projects' in txt or
        'every completed scope' in txt or
        'total value of all her completed' in txt or
        'total value of all his completed' in txt or
        'combined value of every completed' in txt or
        'combined value of all completed' in txt or
        'aggregate value of all completed' in txt or
        'full rollup of every completed' in txt or
        'total value of all completed' in txt or
        'combined value of completed' in txt or
        ('completed work with' in txt and 'combined value' in txt)
    ):
        return 'hop_aggregate'

    # Fallback for remaining natural language phrasing that no keyword rule
    # matched. Tries a small local LLM first (tested more accurate than the
    # embedding classifier on unfamiliar phrasing), then falls back to
    # semantic embeddings, then a hardcoded default. Each tier only runs if
    # the one before it is unavailable or fails — never a hard dependency.
    llm_shape = classify_llm(qtext, atype)
    if llm_shape:
        return llm_shape

    clf = get_semantic_classifier()
    if clf and clf.prototype_embeddings:
        try:
            best_shape, _ = clf.classify(qtext, atype)
            return best_shape
        except Exception as e:
            print(f"Error in semantic classifier: {e}")

    # Fallback to regex if neither the LLM nor semantic classifier is available
    return 'hop_aggregate'

def test_classification():
    with open('questions.json') as f:
        qs = json.load(f)['questions']
        
    classes = Counter()
    for q in qs:
        c = classify_question(q['question'], q['answer_type'])
        classes[c] += 1
            
    print(f"Total target questions: {len(qs)}")
    print("Classified distribution:")
    for k, v in classes.most_common():
        print(f"  {k:22s}: {v:3d}")

if __name__ == '__main__':
    test_classification()
