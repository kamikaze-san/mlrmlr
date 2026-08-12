import pandas as pd
import json

df_new = pd.read_csv('solution/answers_submission.csv')
with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

df_v1 = pd.read_csv(r'C:\Users\NewGr\Downloads\hackathon_rlm\submission_v1.1.csv')
merged_v1 = pd.merge(df_new, df_v1, on='question_id', suffixes=('_fixed', '_v1_1'))
diffs_v1 = merged_v1[merged_v1['answer_fixed'] != merged_v1['answer_v1_1']]

print(f"Total Questions: {len(df_new)}")
print(f"Exact Matches with submission_v1.1: {len(merged_v1) - len(diffs_v1)} / 333 ({(len(merged_v1) - len(diffs_v1))/333*100:.1f}%)")
print(f"Disagreements: {len(diffs_v1)}")

key_fixes = ['HV-IC-0398', 'HV-IC-0193', 'HV-IC-0220', 'HV-IC-0258', 'HV-IC-0340', 'HV-IC-0306', 'HV-IC-0322']
print("\n" + "=" * 80)
print("AUDIT OF SPECIFIC REFINED & FIXED QUESTIONS")
print("=" * 80)

for k in key_fixes:
    row_new = df_new[df_new['question_id'] == k]
    row_v1 = df_v1[df_v1['question_id'] == k]
    ans_new = row_new['answer'].values[0] if not row_new.empty else None
    ans_v1 = row_v1['answer'].values[0] if not row_v1.empty else None
    print(f"\n[{k}] (Type: {qs[k]['answer_type'].upper()})")
    print(f"  Question: \"{qs[k]['question']}\"")
    print(f"  Newly Fixed Answer: {ans_new}")
    print(f"  submission_v1.1:    {ans_v1}")
