import json
import os
import sys
import re
from collections import Counter

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker

def classify_question(qtext: str, atype: str) -> str:
    txt = qtext.lower()
    
    # 1. PERCENT questions
    if atype == 'percent':
        if 'endorsement' in txt or 'recommendation' in txt or 'reference letter' in txt or 'letters on file' in txt or 'client letters' in txt or 'track record' in txt or 'endorse' in txt or 'portion that cleared' in txt:
            return 'referenced_share'
        if 'collection' in txt or 'collected' in txt or 'invoiced' in txt or 'received' in txt or 'billed' in txt or 'cleared' in txt:
            return 'collection_rate'
        return 'referenced_share'
            
    # 2. DAYS questions
    if atype == 'days':
        return 'date_span'
        
    # 3. COUNT questions
    if atype == 'count':
        if 'lack' in txt or 'no client reference' in txt or 'no reference letter' in txt or 'have no reference' in txt or 'unreferenced' in txt:
            return 'absence'
        return 'distinct_count'
        
    # 4. MONEY questions
    if atype == 'money':
        if 'excluding' in txt or 'exclude' in txt or 'remove the' in txt or 'set aside' in txt:
            return 'exclusion_aggregate'

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
        ) and 'credential' not in txt and 'contract value' not in txt:
            return 'outstanding_balance'

        # Check annual diff (requires at least 2 distinct years)
        years = set(re.findall(r'\b(201\d|202\d)\b', txt))
        if len(years) >= 2 and ('moved' in txt or 'variance' in txt or 'dollar amount' in txt or 'actual move' in txt or 'net difference' in txt or 'between 20' in txt or 'vs 20' in txt or 'and 20' in txt or 'absolute difference' in txt):
            return 'annual_diff'

        if ('gap between' in txt or 'shortfall' in txt or 'net difference' in txt or 'amount after we cross-check' in txt or 'delta between' in txt or 'unbilled portion' in txt or 'missing amount between commitments' in txt) and ('invoiced' in txt or 'billed' in txt or 'sanctioned' in txt or 'actual gap' in txt or 'submitted claims' in txt or 'claimed' in txt or 'cash flow' in txt or 'commitments' in txt):
            return 'billing_shortfall'

        # Category comparison
        cats_in_txt = [c for c in ['large bridges', 'bridges flyovers', 'bridges and flyovers', 'bridges', 'water treatment', 'water supply', 'tunnels', 'industrial epc', 'irrigation', 'roads highways', 'roads and highways', 'roads maintenance', 'maintenance', 'roads', 'small buildings', 'buildings', 'drainage', 'sewerage drainage', 'sewerage', 'expressways'] if c in txt]
        if len(cats_in_txt) >= 2:
            if 'largest' not in txt and 'median' not in txt and '201' not in txt and '202' not in txt:
                return 'category_diff'
            
        if 'mean and the median' in txt or 'mean and median' in txt or 'average and median' in txt or 'avg and median' in txt or 'mean against the median' in txt or 'avg dips' in txt or 'mean-median gap' in txt:
            return 'mean_vs_median'
            
        if 'average size' in txt or 'mean size' in txt or 'overall average' in txt or 'actual average' in txt or 'mean volume' in txt or 'mean scale' in txt or 'proper baseline' in txt or 'mean across all' in txt or 'mean across' in txt or 'mean contract value' in txt:
            if 'median' not in txt and 'gap' not in txt:
                return 'avg_work_size'
            
        if 'additional work' in txt or 'reach our credential target' in txt or 'how much more contract value' in txt or 'bring in to hit' in txt or 'still need to secure' in txt or 'need to clear the' in txt or 'how much more value do we need' in txt:
            return 'gap_to_threshold'
            
        if 'largest' in txt and ('second' in txt or 'second-largest' in txt or 'second-biggest' in txt):
            return 'rank_value'
            
        if 'excluding' in txt or 'remove the' in txt:
            return 'exclusion_aggregate'
            
        if 'completed after' in txt or 'wrapped up after' in txt or 'finished after' in txt or 'reached completion after' in txt:
            return 'temporal_chain'
            
        if ('threshold' in txt or 'mark' in txt or 'cutoff' in txt or 'limit' in txt or 'crossing' in txt or 'clear' in txt or 'exceed' in txt or 'hitting the' in txt or 'at or over' in txt or 'meet or exceed' in txt or 'clear that mark' in txt or 'clearing the' in txt):
            return 'threshold_aggregate'
            
        return 'hop_aggregate'
        
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
