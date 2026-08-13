import json
import sqlite3
import urllib.request
import re
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'knowledge_base.db')

PROMPT_TEMPLATE = """You are an expert SQL assistant for an infrastructure company knowledge base.
Translate the user's natural language question into a single valid SQLite SELECT query.

Database Schema:
1. projects (doc_id TEXT, project_name TEXT, client_name TEXT, state TEXT, category TEXT, value_inr INTEGER, completion_date TEXT (YYYY-MM-DD), lead_engineer TEXT, package_no TEXT, has_reference_letter INTEGER (1 or 0))
2. engineers (emp_id TEXT, name TEXT, designation TEXT, experience_years INTEGER, qualification TEXT, date_of_joining TEXT)
3. personnel_certs (doc_id TEXT, cred_type TEXT, name TEXT, cred_id TEXT, issue_date TEXT, valid_through TEXT, emp_id TEXT)
4. clients (client_name TEXT, total_awarded_inr INTEGER, total_invoiced_inr INTEGER, total_received_inr INTEGER, total_outstanding_inr INTEGER)
5. receivables_ageing (invoice_no TEXT, client_name TEXT, invoiced_inr INTEGER, received_inr INTEGER, outstanding_inr INTEGER, days_bucket TEXT)

Key Business Rules:
- If asked for "shortfall" or "gap between awarded/secured and invoiced/billed", calculate `total_awarded_inr - total_invoiced_inr` from `clients`.
- If asked for "unpaid balance", "amount still owed", "pending charges", or "remaining balance across billed amounts", select `total_outstanding_inr` from `clients`.
- If asked for "collection rate" or "% received against billed", calculate `(CAST(total_received_inr AS FLOAT) / total_invoiced_inr) * 100.0` from `clients`.
- If asked for "lack reference letter", "no reference letter", or "unreferenced works", select `COUNT(*)` from `projects` where `has_reference_letter = 0`.
- If asked for "% with reference letter" or "endorsements cleared", calculate `(CAST(SUM(has_reference_letter) AS FLOAT) / COUNT(*)) * 100.0` from `projects`.
- If asked for days elapsed between cert date and completion date, use `ABS(JULIANDAY(completion_date) - JULIANDAY('YYYY-MM-DD'))`.
- For categories difference, calculate `ABS(SUM(CASE WHEN category = 'cat1' THEN value_inr ELSE 0 END) - SUM(CASE WHEN category = 'cat2' THEN value_inr ELSE 0 END))` from `projects`.
- For mean vs median gap, calculate `AVG(value_inr) - (SELECT value_inr FROM projects ...)` or use standard average minus median.

Output ONLY the raw SQLite query inside a ```sql ... ``` code block. No explanation.

Question: {question}
Answer Type: {answer_type}
"""

class LLMRouter:
    """Last-resort SQL generator using the competition's provided LLM
    endpoint (the only generative model this pipeline is permitted to
    call). Never a hard dependency -- every method fails safe (empty
    string / None) if the endpoint isn't configured or unreachable."""

    def __init__(self, model_name: str = 'qwen3.6-35b-a3b-nvfp4', base_url: str = None):
        self.model_name = model_name
        self.base_url = base_url or os.environ.get('LLM_BASE_URL')
        self.is_available = bool(self.base_url)

    def generate_sql(self, question: str, answer_type: str) -> str:
        if not self.is_available:
            return ""
        prompt = PROMPT_TEMPLATE.format(question=question, answer_type=answer_type)
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "temperature": 0,
        }
        try:
            req = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/chat/completions",
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                text = (res['choices'][0]['message'].get('content') or '').strip()
                if "```sql" in text:
                    return text.split("```sql")[1].split("```")[0].strip()
                elif "```" in text:
                    return text.split("```")[1].split("```")[0].strip()
                return text
        except Exception:
            return ""
            
    def execute_llm_query(self, question: str, answer_type: str, db_path: str = DB_PATH):
        sql = self.generate_sql(question, answer_type)
        if not sql:
            return None
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(sql)
            res = cur.fetchone()
            if res and res[0] is not None:
                val = res[0]
                if answer_type == 'percent':
                    return round(float(val), 2)
                elif answer_type in ['money', 'days', 'count']:
                    return int(round(float(val)))
        except Exception:
            return None
        return None
