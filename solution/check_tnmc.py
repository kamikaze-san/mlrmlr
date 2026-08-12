import sqlite3
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
rows = cur.execute("SELECT category, SUM(value_inr) FROM projects WHERE client_name = 'Tamil Nadu Municipal Corporation' GROUP BY category").fetchall()
for r in rows:
    print(r)
total = cur.execute("SELECT SUM(value_inr) FROM projects WHERE client_name = 'Tamil Nadu Municipal Corporation' AND category != 'bridges flyovers'").fetchone()[0]
print(f'\nTotal excluding bridges flyovers: {total:,}')
