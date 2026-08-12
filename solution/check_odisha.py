import sqlite3
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
rows = cur.execute("SELECT doc_id, project_name, value_inr, has_reference_letter FROM projects WHERE client_name = 'Public Health Engineering Dept, Odisha'").fetchall()
print(f"Total projects for Odisha PHED: {len(rows)}")
for r in rows:
    print(" ", r)
unref = [r for r in rows if not r[3]]
print(f"Unreferenced projects count: {len(unref)}")
