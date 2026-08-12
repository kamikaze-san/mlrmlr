import sqlite3
import json

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

temporal_qids = ['HV-IC-0039', 'HV-IC-0048', 'HV-IC-0081', 'HV-IC-0151', 'HV-IC-0186', 'HV-IC-0207', 'HV-IC-0270', 'HV-IC-0305', 'HV-IC-0334', 'HV-IC-0348', 'HV-IC-0351']

for qid in temporal_qids:
    q = qs[qid]
    print(f"\n[{qid}]")
    print(f"  Q: {q['question']}")
    # Check engineers mentioned
    for r in cur.execute("SELECT DISTINCT lead_engineer FROM projects"):
        eng = r[0]
        if eng and eng.lower() in q['question'].lower():
            # Get projects
            projs = cur.execute("SELECT project_name, completion_date, value_inr FROM projects WHERE lead_engineer = ?", (eng,)).fetchall()
            after_projs = [p for p in projs if p[1] > '2021-03-10']
            total = sum(p[2] for p in after_projs)
            print(f"  Engineer: {eng} | Total > 2021-03-10: {total:,} INR ({len(after_projs)} projects)")
            for p in after_projs:
                print(f"    * {p[0]} | {p[1]} | {p[2]:,}")
