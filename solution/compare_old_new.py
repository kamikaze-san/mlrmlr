import pandas as pd
import json

old = pd.read_csv('solution/answers_qwen35_oldbackup.csv')
new = pd.read_csv('solution/answers_submission.csv')

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

merged = pd.merge(old, new, on='question_id', suffixes=('_old', '_new'))
same = merged[merged['answer_old'] == merged['answer_new']]
changed = merged[merged['answer_old'] != merged['answer_new']]

print(f'Total questions: {len(merged)}')
print(f'Unchanged (same answer): {len(same)}')
print(f'Changed answers: {len(changed)}')
print()
print('--- ALL CHANGED QUESTIONS ---')
for _, r in changed.iterrows():
    qid = r['question_id']
    old_ans = r['answer_old']
    new_ans = r['answer_new']
    q_text = qs[qid]['question'][:100]
    print(f'[{qid}] OLD: {old_ans:>20,.2f}  -->  NEW: {new_ans:>20,.2f}')
    print(f'  Q: {q_text}')
    print()
