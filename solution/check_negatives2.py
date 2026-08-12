import sqlite3, json
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print('=== UP Irrigation: raw receivables vs projects ===')
r = cur.execute("SELECT SUM(invoiced_inr), SUM(received_inr), SUM(outstanding_inr) FROM receivables_ageing WHERE client_name LIKE '%Irrigation%Waterways%Uttar%'").fetchone()
print(f'  Invoiced: {r[0]:,}  Received: {r[1]:,}  Outstanding: {r[2]:,}')
r2 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name LIKE '%Irrigation%Waterways%Uttar%'").fetchone()
print(f'  Awarded (projects): {r2[0]:,}')

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

print()
print('Q41:', qs['HV-IC-0041']['question'])
print('Type:', qs['HV-IC-0041']['answer_type'])
print()
print('Q412:', qs['HV-IC-0412']['question'])
print('Type:', qs['HV-IC-0412']['answer_type'])
