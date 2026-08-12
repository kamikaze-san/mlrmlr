import sqlite3

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("--- Imran Joshi ---")
cur.execute("SELECT doc_id, project_name, client_name, value_inr FROM projects WHERE lead_engineer LIKE '%Imran Joshi%'")
for r in cur.fetchall():
    print(r)

print("\n--- Meera ---")
cur.execute("SELECT emp_id, name FROM engineers WHERE name LIKE '%Meera%'")
for r in cur.fetchall():
    print(r)
cur.execute("SELECT doc_id, project_name, client_name FROM projects WHERE lead_engineer LIKE '%Meera%'")
for r in cur.fetchall():
    print(r)

print("\n--- Priya ---")
cur.execute("SELECT doc_id, project_name, client_name, state, category FROM projects WHERE lead_engineer LIKE '%Priya%'")
for r in cur.fetchall():
    print(r)

print("\n--- Suvarna Projects ---")
cur.execute("SELECT value_inr, completion_date FROM projects WHERE client_name = 'Suvarna Projects Limited'")
for r in cur.fetchall():
    print(r)

print("\n--- Jal Nigam Gujarat categories ---")
cur.execute("SELECT category, value_inr FROM projects WHERE client_name = 'Jal Nigam, Gujarat'")
for r in cur.fetchall():
    print(r)

print("\n--- NEDA categories ---")
cur.execute("SELECT category, value_inr FROM projects WHERE client_name = 'National Expressway Development Authority'")
for r in cur.fetchall():
    print(r)
