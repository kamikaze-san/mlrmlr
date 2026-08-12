import sqlite3
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
rows = cur.execute("SELECT project_name, category, value_inr FROM projects WHERE client_name = 'Arunodaya Infrastructure'").fetchall()
c1 = sum(r[2] for r in rows if r[1] == 'roads highways')
c2 = sum(r[2] for r in rows if r[1] == 'roads maintenance')
print('roads highways:', c1)
print('roads maintenance:', c2)
print('diff:', abs(c1 - c2))
