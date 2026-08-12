import sqlite3

conn = sqlite3.connect('solution/db/knowledge_base.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== [1] HV-IC-0006: Lakshya Engineering & Construction ===")
cur.execute("SELECT project_name, value_inr FROM projects WHERE client_name = 'Lakshya Engineering & Construction'")
projs = cur.fetchall()
tot_awarded = sum(p['value_inr'] for p in projs)
print(f"Awarded ({len(projs)} projects): {tot_awarded:,} INR")
for p in projs:
    print(f"  * {p['project_name']}: {p['value_inr']:,} INR")
cur.execute("SELECT total_invoiced_inr, total_awarded_inr FROM clients WHERE client_name = 'Lakshya Engineering & Construction'")
crow = cur.fetchone()
print(f"Total Invoiced in Receivables: {crow['total_invoiced_inr']:,} INR")
print(f"Shortfall (Awarded - Invoiced): {tot_awarded - crow['total_invoiced_inr']:,} INR")

print("\n=== [2] HV-IC-0233: Mahanadi Steel Corporation ===")
cur.execute("SELECT project_name, lead_engineer, value_inr FROM projects WHERE client_name = 'Mahanadi Steel Corporation'")
projs = cur.fetchall()
tot_mahanadi = sum(p['value_inr'] for p in projs)
print(f"Mahanadi ({len(projs)} projects): Total = {tot_mahanadi:,} INR")
for p in projs:
    print(f"  * {p['project_name']} | Lead: {p['lead_engineer']} | {p['value_inr']:,} INR")

print("\n=== [3] HV-IC-0291: Mega Infrastructure Authority ===")
cur.execute("SELECT project_name, value_inr FROM projects WHERE client_name = 'Mega Infrastructure Authority'")
projs = cur.fetchall()
tot_mega = sum(p['value_inr'] for p in projs)
avg_mega = tot_mega / len(projs)
print(f"Mega Infrastructure ({len(projs)} projects): Total = {tot_mega:,} INR | Average = {avg_mega:.2f} -> {int(round(avg_mega)):,} INR")
for p in projs:
    print(f"  * {p['project_name']}: {p['value_inr']:,} INR")

print("\n=== [4] HV-IC-0402: National Special Projects Office ===")
cur.execute("SELECT total_invoiced_inr, total_received_inr, total_outstanding_inr FROM clients WHERE client_name = 'National Special Projects Office'")
crow = cur.fetchone()
print(f"Invoiced: {crow['total_invoiced_inr']:,} INR")
print(f"Received: {crow['total_received_inr']:,} INR")
print(f"Unpaid Outstanding: {crow['total_outstanding_inr']:,} INR")

print("\n=== [5] HV-IC-0368: Pkg-31 STP Days Elapsed ===")
cur.execute("SELECT project_name, completion_date, lead_engineer FROM projects WHERE package_no = 'Pkg-31'")
p31 = cur.fetchone()
print(f"Project: {p31['project_name']} | Lead: {p31['lead_engineer']} | Completion: {p31['completion_date']}")
from datetime import datetime
d_ref = datetime(2021, 3, 10)
d_comp = datetime.strptime(p31['completion_date'], '%Y-%m-%d')
print(f"Days: ({d_comp.strftime('%Y-%m-%d')} - {d_ref.strftime('%Y-%m-%d')}).days = {(d_comp - d_ref).days}")

print("\n=== [6] HV-IC-0432: Mahanadi EPC vs Water Treatment ===")
cur.execute("SELECT project_name, category, value_inr FROM projects WHERE client_name = 'Mahanadi Steel Corporation'")
projs = cur.fetchall()
epc_sum = sum(p['value_inr'] for p in projs if 'industrial epc' in p['category'])
wt_sum = sum(p['value_inr'] for p in projs if 'water treatment' in p['category'])
print(f"Industrial EPC Sum: {epc_sum:,} INR")
print(f"Water Treatment Sum: {wt_sum:,} INR")
print(f"Difference: {abs(epc_sum - wt_sum):,} INR")
