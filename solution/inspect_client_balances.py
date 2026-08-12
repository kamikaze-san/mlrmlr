import sqlite3

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("=== CLIENTS WITH NEGATIVE OR UNUSUAL BALANCES ===")
rows = cur.execute("SELECT client_name, total_awarded_inr, total_invoiced_inr, total_received_inr, total_outstanding_inr FROM clients").fetchall()
for r in rows:
    shortfall = r[1] - r[2] if r[1] and r[2] else 0
    out = r[4]
    if shortfall < 0 or (out is not None and out < 0):
        print(f"Client: {r[0]}")
        print(f"  Awarded: {r[1]:,} | Invoiced: {r[2]:,} | Received: {r[3]:,} | Outstanding: {r[4]:,}")
        print(f"  Shortfall (Awarded - Invoiced): {shortfall:,}")
        print()
