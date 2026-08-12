import sqlite3
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
print('Projects for Meera Roy:')
for r in cur.execute("SELECT package_no, project_name, completion_date, lead_engineer FROM projects WHERE lead_engineer LIKE '%Meera Roy%'").fetchall():
    print(r)

print('\nCerts for Meera Roy:')
for r in cur.execute("SELECT * FROM personnel_certs WHERE name LIKE '%Meera Roy%'").fetchall():
    print(r)
