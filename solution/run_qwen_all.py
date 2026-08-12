import json
import sqlite3
import pandas as pd
import numpy as np
import time
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.query_engine import QueryEngine
from solution.solver.llm_router import LLMRouter

V1_1_PATH = r'C:\Users\NewGr\Downloads\hackathon_rlm\submission_v1.1.csv'
DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'knowledge_base.db')

def solve_one(q):
    qid = q['qid']
    qtxt = q['question']
    atype = q['answer_type']
    
    router = LLMRouter(model_name='qwen3.5:4b')
    engine = QueryEngine(use_llm_fallback=False)
    
    t0 = time.time()
    # 1. Deterministic
    det_ans = engine.solve_question(qid, qtxt, atype)
    
    # 2. Qwen 3.5 Text-to-SQL
    sql = router.generate_sql(qtxt, atype)
    llm_ans = router.execute_llm_query(qtxt, atype, DB_PATH)
    dur = time.time() - t0
    
    return {
        'qid': qid,
        'type': atype,
        'question': qtxt,
        'sql': sql,
        'llm_ans': llm_ans,
        'det_ans': det_ans,
        'time_sec': round(dur, 2)
    }

def main():
    print("=" * 80)
    print("RUNNING QWEN 3.5 ACROSS ALL 333 QUESTIONS & COMPARING WITH submission_v1.1.csv")
    print("=" * 80)

    # Read-only load of submission_v1.1.csv
    df_v1 = pd.read_csv(V1_1_PATH)
    v1_dict = dict(zip(df_v1['question_id'], df_v1['answer']))
    print(f"Loaded submission_v1.1.csv: {len(v1_dict)} questions in total (READ-ONLY).")

    with open('questions.json') as f:
        qs = json.load(f)['questions']
    print(f"Loaded questions.json: {len(qs)} questions in total.")

    results = {}
    print("\nStarting generation across 333 questions with parallel worker threads...")
    
    # We use ThreadPoolExecutor with 3 workers for fast local generation
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(solve_one, q): q['qid'] for q in qs}
        completed_count = 0
        for f in as_completed(futures):
            res = f.result()
            results[res['qid']] = res
            completed_count += 1
            if completed_count % 25 == 0 or completed_count == len(qs):
                elapsed = time.time() - t_start
                rate = completed_count / elapsed
                rem = (len(qs) - completed_count) / (rate + 1e-6)
                print(f"Progress: [{completed_count:3d}/{len(qs)}] questions completed ({completed_count/len(qs)*100:.1f}%) | Speed: {rate:.1f} q/s | Est. Remaining: {rem:.0f}s")

    print("\nGeneration finished! Compiling detailed comparison report...")
    
    records = []
    for q in qs:
        qid = q['qid']
        r = results[qid]
        v1_ans = v1_dict.get(qid)
        
        # Determine best answer (Deterministic or LLM if LLM valid)
        llm_a = r['llm_ans']
        det_a = r['det_ans']
        
        # Match checks with v1.1
        exact_match_llm = (llm_a == v1_ans) if llm_a is not None else False
        exact_match_det = (det_a == v1_ans)
        
        close_match_det = (abs(det_a - v1_ans) <= 1.0) if v1_ans is not None else False
        
        records.append({
            'question_id': qid,
            'answer_type': r['type'],
            'question': r['question'],
            'generated_sql': r['sql'],
            'qwen35_ans': llm_a,
            'det_ans': det_a,
            'v1_1_ans': v1_ans,
            'match_exact': exact_match_det,
            'match_close': close_match_det
        })

    df_out = pd.DataFrame(records)
    out_csv = 'solution/qwen35_all_333_comparison.csv'
    df_out.to_csv(out_csv, index=False)
    print(f"Saved complete comparison to {out_csv}")

    # Summary Statistics
    total_qs = len(df_out)
    exact_det_v1 = df_out['match_exact'].sum()
    close_det_v1 = df_out['match_close'].sum()
    
    # LLM vs v1.1
    valid_llm = df_out['qwen35_ans'].notnull()
    llm_exact_v1 = ((df_out['qwen35_ans'] == df_out['v1_1_ans']) & valid_llm).sum()
    
    # Qwen 3.5 vs Deterministic
    qwen_det_match = ((df_out['qwen35_ans'] == df_out['det_ans']) & valid_llm).sum()

    print("\n" + "=" * 80)
    print("FINAL SUMMARY REPORT: QWEN 3.5 & DETERMINISTIC vs submission_v1.1.csv")
    print("=" * 80)
    print(f"Total Questions Evaluated: {total_qs}")
    print(f"1. Deterministic vs submission_v1.1 Exact Matches: {exact_det_v1} / {total_qs} ({exact_det_v1/total_qs*100:.1f}%)")
    print(f"2. Deterministic vs submission_v1.1 Close Matches (<= 1.0 rupee/unit): {close_det_v1} / {total_qs} ({close_det_v1/total_qs*100:.1f}%)")
    print(f"3. Qwen 3.5 Text-to-SQL vs Deterministic Match Rate: {qwen_det_match} / {total_qs} ({qwen_det_match/total_qs*100:.1f}%)")
    print(f"4. Qwen 3.5 Text-to-SQL vs submission_v1.1 Exact Match Rate: {llm_exact_v1} / {total_qs} ({llm_exact_v1/total_qs*100:.1f}%)")

if __name__ == '__main__':
    main()
