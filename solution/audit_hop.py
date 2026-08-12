"""
Deep dive into hop_aggregate questions.
Question: does "combined value of completed assignments" mean:
  (a) ALL projects for that client (our current approach), or
  (b) Only projects where the engineer was the lead?

The sample benchmark HS-IC-0007 and HS-IC-0008 both use ALL projects for client.
Let's verify all 36 hop_aggregate questions look consistent.
Also check mean_vs_median questions where the PMP engineer's client changes the scope.
"""
import sqlite3
import json
import sys
sys.path.insert(0, '.')
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker
import pandas as pd

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
linker = EntityLinker('solution/db/knowledge_base.db')

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

df_ans = pd.read_csv('solution/answers_submission.csv')
ans_dict = dict(zip(df_ans['question_id'], df_ans['answer']))

# For hop_aggregate: the pattern is Engineer -> Client -> SUM all projects for client
# But some questions say "completed assignments" — does that mean ALL or filtered by completion?
print("=== HOP_AGGREGATE: All 36 questions with engineer->client chain ===\n")

for qid, q in qs.items():
    if classify_question(q['question'], q['answer_type']) != 'hop_aggregate':
        continue

    qtxt = q['question']
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    eng = ent.get('engineer', {})
    our_ans = ans_dict.get(qid, 0)

    # Check if the question has any "completed" or "finished" filter
    has_completion_filter = any(w in qtxt.lower() for w in ['completed', 'finished', 'delivered', 'wrapped'])

    # What if we only count projects where the engineer is the lead?
    eng_name = eng.get('name') if eng else None
    if eng_name and client:
        eng_led = cur.execute(
            "SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND lead_engineer = ?",
            (client, eng_name)
        ).fetchone()[0] or 0
        all_client = cur.execute(
            "SELECT SUM(value_inr) FROM projects WHERE client_name = ?",
            (client,)
        ).fetchone()[0] or 0

        if eng_led != all_client:
            print(f"[{qid}] OUR ANS: {our_ans:,.0f}")
            print(f"  ALL for client:          {all_client:,.0f}")
            print(f"  Only eng-led for client: {eng_led:,.0f}")
            print(f"  Completion filter: {has_completion_filter}")
            print(f"  Q: {qtxt[:115]}")
            print()
