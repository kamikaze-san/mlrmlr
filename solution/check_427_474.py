import sqlite3

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("=== HV-IC-0427: NEDA industrial epc vs roads highways ===")
c1 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = 'National Expressway Development Authority' AND category = 'industrial epc'").fetchone()[0] or 0
c2 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = 'National Expressway Development Authority' AND category = 'roads highways'").fetchone()[0] or 0
print(f"industrial epc: {c1:,}")
print(f"roads highways: {c2:,}")
print(f"Category Diff: {abs(c1 - c2):,}")

print("\n=== HV-IC-0474: Subarnarekha expressways vs tunnels ===")
s1 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = 'Subarnarekha Valley Corporation' AND category = 'expressways'").fetchone()[0] or 0
s2 = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = 'Subarnarekha Valley Corporation' AND category = 'tunnels'").fetchone()[0] or 0
print(f"expressways: {s1:,}")
print(f"tunnels:     {s2:,}")
print(f"Category Diff: {abs(s1 - s2):,}")
