import pandas as pd
import json

df_new = pd.read_csv('solution/answers_submission.csv')
df_v1 = pd.read_csv(r'C:\Users\NewGr\Downloads\hackathon_rlm\submission_v1.1.csv')

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

merged = pd.merge(df_new, df_v1, on='question_id', suffixes=('_fixed', '_v1_1'))
diffs = merged[merged['answer_fixed'] != merged['answer_v1_1']].copy()
diffs['type'] = diffs['question_id'].map(lambda x: qs[x]['answer_type'])
diffs['question'] = diffs['question_id'].map(lambda x: qs[x]['question'])

print(f"Total Disagreements between Our Final Submission and submission_v1.1: {len(diffs)}")

# Categorize disagreements:
# 1. 4-Hop Multi-Hop Portfolio Traversal (Grep stopped at 1 doc in v1.1)
cat1 = []
# 2. Negative Sign on Variances (v1.1 gave negative, ours is positive abs)
cat2 = []
# 3. Reference Letter Count / Percentage (v1.1 had inaccurate count)
cat3 = []
# 4. Decimal vs Integer Money Rounding
cat4 = []
# 5. Other / Ledger
cat5 = []

for _, r in diffs.iterrows():
    qid = r['question_id']
    qtxt = r['question'].lower()
    a_new = r['answer_fixed']
    a_v1 = r['answer_v1_1']
    
    if abs(a_new - a_v1) <= 1.0:
        cat4.append((qid, a_new, a_v1, r['question']))
    elif a_new == -a_v1:
        cat2.append((qid, a_new, a_v1, r['question']))
    elif r['type'] == 'percent':
        cat3.append((qid, a_new, a_v1, r['question']))
    elif ('pmp' in qtxt or 'six sigma' in qtxt) and ('for that client' in qtxt or 'for whoever' in qtxt or 'for the client' in qtxt or 'delivered to' in qtxt or 'completed assignment' in qtxt):
        cat1.append((qid, a_new, a_v1, r['question']))
    else:
        cat5.append((qid, a_new, a_v1, r['question']))

print(f"\n1. Multi-Hop Graph Traversal Fixes (where v1.1 grep stopped at 1 doc): {len(cat1)}")
print(f"2. Negative Variance Signs (v1.1 was negative, ours is positive abs):   {len(cat2)}")
print(f"3. Reference Letter / Testimonial Accuracy Fixes:                      {len(cat3)}")
print(f"4. Minor Decimal / Integer Rounding (<= 1.0 diff):                     {len(cat4)}")
print(f"5. Other Ledger / Shortfall / Category Fixes:                          {len(cat5)}")

print("\n--- SAMPLE MULTI-HOP FIXES (Group 1) ---")
for x in cat1[:6]:
    print(f"[{x[0]}] Ours: {x[1]} | v1.1: {x[2]}\n  Q: {x[3]}")

print("\n--- SAMPLE SIGN FIXES (Group 2) ---")
for x in cat2[:4]:
    print(f"[{x[0]}] Ours: {x[1]} | v1.1: {x[2]}\n  Q: {x[3]}")
