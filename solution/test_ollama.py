import urllib.request
import json
import sqlite3
import time

PROMPT_TEMPLATE = """You are an expert SQL assistant for an infrastructure company knowledge base.
Translate the user's natural language question into a single valid SQLite SELECT query.

Database Schema:
1. projects (doc_id TEXT, project_name TEXT, client_name TEXT, state TEXT, category TEXT, value_inr INTEGER, completion_date TEXT (YYYY-MM-DD), lead_engineer TEXT, package_no TEXT, has_reference_letter INTEGER (1 or 0))
2. engineers (emp_id TEXT, name TEXT, designation TEXT, experience_years INTEGER, qualification TEXT, date_of_joining TEXT)
3. personnel_certs (doc_id TEXT, cred_type TEXT, name TEXT, cred_id TEXT, issue_date TEXT, valid_through TEXT, emp_id TEXT)
4. clients (client_name TEXT, total_awarded_inr INTEGER, total_invoiced_inr INTEGER, total_received_inr INTEGER, total_outstanding_inr INTEGER)

Key Business Rules:
- If asked for "shortfall" or "gap between awarded/secured and invoiced/billed", calculate `total_awarded_inr - total_invoiced_inr` from `clients`.
- If asked for "unpaid balance", "amount still owed", "pending charges", or "remaining balance across billed amounts", select `total_outstanding_inr` from `clients`.
- If asked for "collection rate" or "% received against billed", calculate `(CAST(total_received_inr AS FLOAT) / total_invoiced_inr) * 100.0` from `clients`.
- If asked for "lack reference letter", "no reference letter", or "unreferenced works", select `COUNT(*)` from `projects` where `has_reference_letter = 0`.
- If asked for "% with reference letter" or "endorsements cleared", calculate `(CAST(SUM(has_reference_letter) AS FLOAT) / COUNT(*)) * 100.0` from `projects`.
- If asked for days elapsed between cert date and completion date, use `ABS(JULIANDAY(completion_date) - JULIANDAY('YYYY-MM-DD'))`.
- For categories difference, calculate `ABS(SUM(CASE WHEN category = 'cat1' THEN value_inr ELSE 0 END) - SUM(CASE WHEN category = 'cat2' THEN value_inr ELSE 0 END))` from `projects`.

Output ONLY the raw SQLite query inside a ```sql ... ``` code block. No explanation.

Question: {question}
Answer Type: {answer_type}
"""

def query_ollama(model_name: str, question: str, answer_type: str) -> str:
    prompt = PROMPT_TEMPLATE.format(question=question, answer_type=answer_type)
    data = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }
    req = urllib.request.Request(
        'http://127.0.0.1:11434/api/generate',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        t1 = time.time()
        return res.get('response', ''), t1 - t0

def test_llm():
    test_questions = [
        ("HV-IC-0006", "Lakshya Engineering & Construction is under audit, so what is the exact gap between the total value of work awarded and the amount we have actually invoiced?", "money"),
        ("HV-IC-0002", "how many completed works for Jal Nigam, Jharkhand lack a reference letter on file?", "count"),
        ("HV-IC-0402", "National Special Projects Office, what is the exact total of all submitted charges that remain unpaid?", "money"),
        ("HV-IC-0368", "tell me how many days elapsed from Naveen's March 10, 2021 PMP for the Uttar Pradesh Pkg-31 STP site until the work actually wrapped up?", "days"),
        ("HV-IC-0389", "Trishakti Power Generation Corporation lists assignments on my end, so when I cross-check those against endorsements, what is the out of 100 figure for the portion that cleared?", "percent")
    ]
    
    conn = sqlite3.connect('solution/db/knowledge_base.db')
    cur = conn.cursor()
    
    print("Testing Ollama with model 'qwen3.5:4b' or 'qwen3:8b'...")
    for qid, qtxt, atype in test_questions:
        print(f"\n[{qid}] Q: {qtxt}")
        resp, dur = query_ollama('qwen3.5:4b', qtxt, atype)
        print(f"Generated in {dur:.2f}s:")
        print(resp.strip())
        
        # Extract SQL
        sql = resp
        if "```sql" in resp:
            sql = resp.split("```sql")[1].split("```")[0].strip()
        elif "```" in resp:
            sql = resp.split("```")[1].split("```")[0].strip()
            
        try:
            cur.execute(sql)
            row = cur.fetchone()
            print(f"-> SQL Executed Successfully! Result = {row[0] if row else None}")
        except Exception as e:
            print(f"-> SQL Execution Error: {e}")

if __name__ == '__main__':
    test_llm()
