import json, sqlite3, sys, os, re
sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker
from solution.solver.question_parser import classify_question

with open('questions.json') as f:
    qs = json.load(f)['questions']

linker = EntityLinker('solution/db/knowledge_base.db')
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

annual_diff_qs = []
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'annual_diff':
        ent = linker.link(q['question'])
        client = ent.get('client_name')
        years = ent.get('years')
        unique_years = sorted(list(set(years)))
        if client and len(unique_years) >= 2:
            y1, y2 = str(unique_years[0]), str(unique_years[1])
            cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND completion_date LIKE ?", (client, f"{y1}%"))
            v1 = cur.fetchone()[0] or 0
            cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = ? AND completion_date LIKE ?", (client, f"{y2}%"))
            v2 = cur.fetchone()[0] or 0
            diff = v2 - v1
            is_abs = 'absolute' in q['question'].lower()
            ans_signed = int(abs(diff)) if is_abs else int(diff)
            ans_pos = int(abs(diff))
            annual_diff_qs.append({
                'qid': q['qid'],
                'client': client,
                'years': (y1, y2),
                'v1': v1,
                'v2': v2,
                'diff': diff,
                'is_abs': is_abs,
                'ans_signed': ans_signed,
                'ans_pos': ans_pos,
                'q': q['question']
            })

print(f"Total annual_diff questions: {len(annual_diff_qs)}")
neg_count = sum(1 for a in annual_diff_qs if a['ans_signed'] < 0)
print(f"Number of questions that would become negative: {neg_count}")
print()
for a in annual_diff_qs:
    if a['ans_signed'] < 0:
        print(f"[{a['qid']}] {a['client']} ({a['years'][0]} -> {a['years'][1]}): {a['v1']:,} -> {a['v2']:,} = {a['ans_signed']:,}")
        print(f"  Q: {a['q']}\n")
