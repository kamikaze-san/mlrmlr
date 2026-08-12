import sqlite3, numpy as np
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
r = cur.execute("SELECT package_no, project_name, client_name, value_inr FROM projects WHERE package_no = 'Pkg-120'").fetchone()
print('Pkg-120 project in DB:', r)
vals = cur.execute('SELECT project_name, value_inr FROM projects WHERE client_name = ?', (r[2],)).fetchall()
for v in vals:
    print(' ', v)
print('Average size for', r[2], ':', int(round(np.mean([v[1] for v in vals]))))
