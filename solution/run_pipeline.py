import json
import os
import sys
import csv
import pandas as pd

sys.path.insert(0, os.path.abspath('.'))

from solution.db.build_database import populate_database, DB_PATH
from solution.solver.query_engine import QueryEngine

def run_sample_evaluation(engine: QueryEngine):
    print("\n" + "="*50)
    print("Running Evaluation on sample_questions.json ...")
    print("="*50)
    
    with open('sample_questions.json') as f:
        sq_data = json.load(f)
    samples = sq_data['questions']
    
    out_csv = 'solution/sample_answers.csv'
    with open(out_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['question_id', 'answer'])
        for s in samples:
            ans = engine.solve_question(s['qid'], s['question'], s['answer_type'])
            writer.writerow([s['qid'], ans])
            
    print(f"Saved sample answers to {out_csv}")
    
    # Run evaluate.py on sample_answers.csv
    import subprocess
    cmd = [sys.executable, 'evaluate.py', '--submission', out_csv, '--questions', 'sample_questions.json', '--per-question']
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("Errors:", res.stderr)

def run_full_submission(engine: QueryEngine):
    print("\n" + "="*50)
    print("Generating Answers for questions.json (333 questions)...")
    print("="*50)
    
    with open('questions.json') as f:
        q_data = json.load(f)
    questions = q_data['questions']
    
    out_csv = 'solution/answers_submission.csv'
    with open(out_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['question_id', 'answer'])
        for q in questions:
            ans = engine.solve_question(q['qid'], q['question'], q['answer_type'])
            writer.writerow([q['qid'], ans])
            
    print(f"Generated {len(questions)} answers into {out_csv}!")
    
    # Sanity check on submission CSV
    df = pd.read_csv(out_csv)
    print(f"Submission shape: {df.shape}")
    print(f"Null values count: {df['answer'].isnull().sum()}")
    print("First 10 rows:")
    print(df.head(10))

def main():
    # 1. Build and populate database
    populate_database(DB_PATH)
    
    # 2. Initialize Query Engine
    engine = QueryEngine(DB_PATH)
    
    # 3. Evaluate against samples
    run_sample_evaluation(engine)
    
    # 4. Generate final submission
    run_full_submission(engine)

if __name__ == '__main__':
    main()
