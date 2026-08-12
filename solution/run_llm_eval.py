import json
import sqlite3
import pandas as pd
import numpy as np
import time
import os
import sys

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.query_engine import QueryEngine
from solution.solver.llm_router import LLMRouter

def run_llm_comparison():
    print("=" * 80)
    print("RUNNING QWEN 3.5 TEXT-TO-SQL & COMPARISON AGAINST PREVIOUS CSV ATTEMPTS")
    print("=" * 80)

    engine = QueryEngine(use_llm_fallback=False) # deterministic engine
    router = LLMRouter(model_name='qwen3.5:4b')
    
    if not router.is_available:
        print("Error: Ollama qwen3.5:4b is not responding!")
        return

    with open('questions.json') as f:
        qs = json.load(f)['questions']

    # Load previous CSVs
    old_csvs = {}
    for fname in ['new2_solved.csv', 'answers_all_179_solved_2dec.csv', 'answers_batch_0405_to_0435_2dec.csv', 'answers_batch_0436_to_0467_2dec.csv']:
        if os.path.exists(fname):
            df = pd.read_csv(fname)
            col_id = 'question_id' if 'question_id' in df.columns else 'qid'
            old_csvs[fname] = dict(zip(df[col_id], df['answer']))

    # Sample 20 diverse questions from across the dataset
    sample_indices = [2, 5, 14, 25, 45, 65, 90, 115, 140, 165, 190, 215, 240, 265, 290, 310, 325]
    
    records = []
    print(f"\nEvaluating {len(sample_indices)} questions with qwen3.5:4b Text-to-SQL...")
    
    for idx in sample_indices:
        q = qs[idx]
        qid = q['qid']
        qtxt = q['question']
        atype = q['answer_type']
        
        t0 = time.time()
        sql = router.generate_sql(qtxt, atype)
        llm_ans = router.execute_llm_query(qtxt, atype)
        dur = time.time() - t0
        
        det_ans = engine.solve_question(qid, qtxt, atype)
        
        # Find old answers
        old_val = None
        old_src = None
        for src, d in old_csvs.items():
            if qid in d:
                old_val = d[qid]
                old_src = src
                break
                
        records.append({
            'qid': qid,
            'type': atype,
            'question': qtxt,
            'sql': sql,
            'llm_ans': llm_ans,
            'det_ans': det_ans,
            'old_ans': old_val,
            'old_src': old_src,
            'time_sec': round(dur, 2)
        })
        print(f"[{qid}] Done in {dur:.2f}s | LLM: {llm_ans} | Det: {det_ans} | Old: {old_val}")

    print("\n" + "=" * 80)
    print("DETAILED COMPARISON & VERIFICATION")
    print("=" * 80)
    
    for r in records:
        print(f"\n[{r['qid']}] ({r['type'].upper()}) - {r['question']}")
        print(f"  * Generated SQL: {r['sql']}")
        print(f"  * LLM Execution Result:   {r['llm_ans']}")
        print(f"  * Deterministic Result:   {r['det_ans']}")
        print(f"  * Old Gemini Grep Result: {r['old_ans']} (from {r['old_src']})")
        
        if r['llm_ans'] == r['det_ans']:
            print("  ==> [AGREEMENT] LLM Text-to-SQL exactly confirms Deterministic Engine!")
        elif r['old_ans'] is not None and r['det_ans'] == r['old_ans']:
            print("  ==> [AGREEMENT] Deterministic Engine exactly matches Old CSV!")
        else:
            print(f"  ==> [DIVERGENCE] Checking nuance between LLM ({r['llm_ans']}), Det ({r['det_ans']}), Old ({r['old_ans']})")

if __name__ == '__main__':
    run_llm_comparison()
