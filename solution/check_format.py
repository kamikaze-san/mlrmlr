import pandas as pd
import json

df_sample = pd.read_csv('sample_submission.csv')
with open('questions.json') as f:
    qs = json.load(f)['questions']
qids_json = [q['qid'] for q in qs]

print("=== 1. FORMAT & QID CHECK ===")
print("sample_submission.csv shape:", df_sample.shape)
print("sample_submission.csv columns:", df_sample.columns.tolist())
print("sample_submission.csv first 5 rows:\n", df_sample.head(5))
print("sample_submission.csv last 5 rows:\n", df_sample.tail(5))
print("Are QIDs in questions.json identical in order to sample_submission.csv?", df_sample['question_id'].tolist() == qids_json)

print("\n=== 2. NEGATIVE VALUES CHECK ===")
df_qwen = pd.read_csv('solution/answers_qwen35.csv')
negs = df_qwen[df_qwen['answer'] < 0]
print(f"Negative answers count: {len(negs)}")
for _, r in negs.iterrows():
    qid = r['question_id']
    q_match = [q for q in qs if q['qid'] == qid][0]
    print(f"\n[{qid}] Answer = {r['answer']}")
    print(f"Question: \"{q_match['question']}\"")
    print(f"Type: {q_match['answer_type']}")
