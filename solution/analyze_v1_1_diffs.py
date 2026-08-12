import pandas as pd
import json

df_sub = pd.read_csv('solution/answers_submission.csv')
df_v1 = pd.read_csv(r'C:\Users\NewGr\Downloads\hackathon_rlm\submission_v1.1.csv')

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

merged = pd.merge(df_sub, df_v1, on='question_id', suffixes=('_ours', '_v1_1'))
merged['diff'] = abs(merged['answer_ours'] - merged['answer_v1_1'])
merged['is_exact'] = (merged['answer_ours'] == merged['answer_v1_1'])
merged['is_close'] = (merged['diff'] <= 1.0)

print(f"Total overlapping questions: {len(merged)}")
print(f"Exact Matches: {merged['is_exact'].sum()} ({merged['is_exact'].mean()*100:.1f}%)")
print(f"Close Matches (<= 1.0 diff): {merged['is_close'].sum()} ({merged['is_close'].mean()*100:.1f}%)")
print(f"Disagreements (> 1.0 diff): {(~merged['is_close']).sum()}")

diffs = merged[~merged['is_close']].copy()
diffs['type'] = diffs['question_id'].map(lambda x: qs[x]['answer_type'])
print("\nDisagreements by Answer Type:")
print(diffs['type'].value_counts())

print("\n" + "=" * 80)
print("SAMPLE TOP DISAGREEMENTS ANALYSIS")
print("=" * 80)

for idx, (_, r) in enumerate(diffs.head(15).iterrows()):
    qid = r['question_id']
    q = qs[qid]
    print(f"\n[{idx+1}] ID: {qid} | Type: {q['answer_type'].upper()}")
    print(f"Question: \"{q['question']}\"")
    print(f"  * Our Pipeline:       {r['answer_ours']}")
    print(f"  * submission_v1.1:    {r['answer_v1_1']}")
    print(f"  * Absolute Diff:      {r['diff']}")
