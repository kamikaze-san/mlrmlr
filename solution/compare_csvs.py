import pandas as pd
import json

df_sub = pd.read_csv('solution/answers_submission.csv')
with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

for c in ['new2_solved.csv', 'answers_all_179_solved_2dec.csv', 'answers_batch_0361_to_0404_2dec.csv', 'answers_batch_0405_to_0435_2dec.csv', 'answers_batch_0436_to_0467_2dec.csv']:
    df_old = pd.read_csv(c)
    if 'qid' in df_old.columns:
        df_old = df_old.rename(columns={'qid': 'question_id'})
    merged = pd.merge(df_sub, df_old, on='question_id', suffixes=('_ours', '_old'))
    match_exact = (merged['answer_ours'] == merged['answer_old']).sum()
    print("=" * 60)
    print(f"=== {c} ({len(merged)} overlapping) ===")
    print(f"Exact match: {match_exact} / {len(merged)} ({match_exact/len(merged)*100:.1f}%)")
    
    diffs = merged[merged['answer_ours'] != merged['answer_old']]
    print(f"Disagreements: {len(diffs)}")
    for _, r in diffs.head(10).iterrows():
        qid = r['question_id']
        print(f"\n  [{qid}]")
        print(f"    Q: {qs[qid]['question']}")
        print(f"    Type: {qs[qid]['answer_type']}")
        print(f"    Ours: {r['answer_ours']}")
        print(f"    Old:  {r['answer_old']}")
