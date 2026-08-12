import sqlite3
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print('=== HV-IC-0041: UP Irrigation billing_shortfall ===')
rows = cur.execute("SELECT client_name, total_awarded_inr, total_invoiced_inr FROM clients WHERE client_name LIKE '%Irrigation%Waterways%Uttar%'").fetchall()
for r in rows:
    print(f'  Client: {r[0]}')
    print(f'  Awarded: {r[1]:,}  Invoiced: {r[2]:,}  Diff: {r[1]-r[2]:,}')

print()
print('=== HV-IC-0412: Maharashtra Municipal outstanding_balance ===')
rows = cur.execute("SELECT client_name, total_outstanding_inr, total_invoiced_inr, total_received_inr FROM clients WHERE client_name LIKE '%Maharashtra Municipal%'").fetchall()
for r in rows:
    print(f'  Client: {r[0]}')
    print(f'  Outstanding: {r[1]:,}  Invoiced: {r[2]:,}  Received: {r[3]:,}')

print()
print('=== Raw Receivables for Maharashtra Municipal ===')
rows = cur.execute("SELECT invoice_no, invoiced_inr, received_inr, outstanding_inr, status FROM receivables_ageing WHERE client_name LIKE '%Maharashtra Municipal%'").fetchall()
for r in rows:
    print(f'  {r[0]}: Inv={r[1]:,}  Recv={r[2]:,}  Out={r[3]:,}  Status={r[4]}')

print()
print('=== HV-IC-0044: Jal Nigam Jharkhand mean vs median ===')
rows = cur.execute("SELECT value_inr FROM projects WHERE client_name LIKE '%Jal Nigam%Jharkhand%' ORDER BY value_inr").fetchall()
vals = [r[0] for r in rows]
import numpy as np
print(f'  Projects: {len(vals)}')
print(f'  Values: {vals}')
print(f'  Mean: {np.mean(vals):,.0f}')
print(f'  Median: {np.median(vals):,.0f}')
print(f'  Mean - Median = {np.mean(vals) - np.median(vals):,.0f}')
