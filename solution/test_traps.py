import sqlite3

conn = sqlite3.connect('solution/db/knowledge_base.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== [1] Farhan Roy projects for Trishakti ===")
cur.execute("SELECT project_name, value_inr FROM projects WHERE lead_engineer LIKE '%Farhan Roy%' AND client_name = 'Trishakti Power Generation Corporation'")
rows = cur.fetchall()
for r in rows:
    print(f"  * {r['project_name']}: {r['value_inr']:,} INR")
print(f"Sum: {sum(r['value_inr'] for r in rows):,} INR")

print("\n=== [2] Jaya Desai projects for Mahanadi Steel ===")
cur.execute("SELECT project_name, value_inr FROM projects WHERE lead_engineer LIKE '%Jaya Desai%' AND client_name = 'Mahanadi Steel Corporation'")
rows = cur.fetchall()
for r in rows:
    print(f"  * {r['project_name']}: {r['value_inr']:,} INR")
print(f"Sum: {sum(r['value_inr'] for r in rows):,} INR")

print("\n=== [3] Neha Chopra projects completed after 2021-03-10 ===")
cur.execute("SELECT project_name, completion_date, value_inr FROM projects WHERE lead_engineer LIKE '%Neha Chopra%'")
for r in cur.fetchall():
    print(f"  * {r['project_name']} | {r['completion_date']} | {r['value_inr']:,} INR")

print("\n=== [4] Trishakti Endorsements (Reference Letters) Share ===")
cur.execute("SELECT COUNT(*), SUM(has_reference_letter) FROM projects WHERE client_name = 'Trishakti Power Generation Corporation'")
tot, refs = cur.fetchone()
print(f"Total: {tot}, Refs: {refs}, Percent: {(refs/tot)*100:.2f}%")
