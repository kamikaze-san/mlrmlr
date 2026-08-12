import json
import sqlite3
import sys
sys.path.insert(0, '.')
from solution.solver.llm_router import LLMRouter

llm = LLMRouter(model_name='qwen3.5:4b')
print(f"Model: {llm.model_name}, Available: {llm.is_available}")

# Test questions - mix of known correct, known wrong, and suspected wrong
# We know the OLD backup answers for these
test_cases = [
    # (qid, question, atype, old_backup_answer, deterministic_answer, notes)
    ('HV-IC-0001', 
     "Starting with Rajesh Rao's Six Sigma Black Belt (6S-500161) work on the Material Handling Plant - Uttar Pradesh Pkg-47 project with the National Expressway Development Authority, what is the combined value of every completed assignment he has done for that client right now to lock the submission?",
     'money', 129400000, 2942400000, 'hop_aggregate - v1.1 used single doc grep'),
    
    ('HV-IC-0003', 
     "We need to confirm the exact total number of days from Pooja Bose's March 2021 PMP issuance to the completion of the Madhya Pradesh Pkg-23 Water Treatment Plant assignment.",
     'days', 536, 536, 'date_span - KNOWN CORRECT'),
    
    ('HV-IC-0041',
     "That number for the UP irrigation account looks too clean, so what's the actual gap between what they've sanctioned and what we've billed?",
     'money', -377309701, -377309701, 'billing_shortfall - NEGATIVE SUSPICIOUS'),
    
    ('HV-IC-0044',
     "imran joshi six sigma black belt project, what's the rupee gap between avg and median, negative if lower?",
     'money', -192266667, -192266667, 'mean_vs_median - negative is correct per question wording'),
    
    ('HV-IC-0021',
     "What is the net difference in the value of work completed for Meridian Constructors & Co. between 2020 and 2022?",
     'money', -1189100000, 1189100000, 'annual_diff - v1.1 was negative, we abs()'),
    
    ('HV-IC-0412',
     "Maharashtra Municipal Corporation has multiple invoices on file, so could you please calculate the total amount still due across all of them?",
     'money', -13279236, -13279236, 'outstanding_balance - NEGATIVE SUSPICIOUS'),
]

print()
print("=" * 80)
print("QWEN SQL TEST — Generating SQL for each question")
print("=" * 80)

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

for qid, question, atype, old_ans, det_ans, notes in test_cases:
    print(f"\n[{qid}] {notes}")
    print(f"  Q: {question[:90]}")
    
    sql = llm.generate_sql(question, atype)
    print(f"  SQL: {sql}")
    
    if sql:
        try:
            cur.execute(sql)
            res = cur.fetchone()
            qwen_ans = res[0] if res else None
            print(f"  Qwen Answer: {qwen_ans}")
        except Exception as e:
            qwen_ans = f"ERROR: {e}"
            print(f"  Qwen Answer: {qwen_ans}")
    else:
        qwen_ans = "NO SQL GENERATED"
        print(f"  Qwen Answer: {qwen_ans}")
    
    print(f"  Old Backup:  {old_ans:,}" if isinstance(old_ans, (int, float)) else f"  Old Backup:  {old_ans}")
    print(f"  Deterministic: {det_ans:,}" if isinstance(det_ans, (int, float)) else f"  Deterministic: {det_ans}")
