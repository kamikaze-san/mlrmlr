import sqlite3
import os
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, Union, Tuple
from solution.solver.ollama_client import OllamaClient

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'knowledge_base.db')

def days_between(d1: Any, d2: Any) -> int:
    if not d1 or not d2:
        return 0
    try:
        t1 = datetime.strptime(str(d1)[:10], '%Y-%m-%d')
        t2 = datetime.strptime(str(d2)[:10], '%Y-%m-%d')
        return abs((t2 - t1).days)
    except Exception:
        return 0

class LLMEngine:
    def __init__(self, db_path: str = DB_PATH, ollama_client: Optional[OllamaClient] = None):
        self.db_path = db_path
        self.client = ollama_client or OllamaClient()
        self._init_db_connection()
        self._load_dynamic_entity_catalog()

    def _init_db_connection(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function("DAYS_BETWEEN", 2, days_between)

    def _load_dynamic_entity_catalog(self):
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT client_name FROM clients WHERE client_name IS NOT NULL AND client_name != '' AND client_name != 'nan'")
        self.clients = [r[0] for r in cur.fetchall()]
        
        cur.execute("SELECT DISTINCT name FROM engineers WHERE name IS NOT NULL AND name != ''")
        self.engineers = [r[0] for r in cur.fetchall()]

        cur.execute("SELECT DISTINCT package_no FROM projects WHERE package_no IS NOT NULL AND package_no != ''")
        self.packages = [r[0] for r in cur.fetchall()]

    def step1_ground_entities(self, question: str) -> Dict[str, Any]:
        """Step 1: LLM in-context entity grounding and decomposition."""
        system_prompt = (
            "You are an Entity Resolution Assistant for an infrastructure engineering database.\n"
            "Given a user's question, map any mentioned client or engineer to the exact canonical name in the database.\n"
            "Rules:\n"
            "1. Match acronyms to the full company name (e.g. 'NEDA' -> 'National Expressway Development Authority', 'UP Irrigation' -> 'Irrigation & Waterways Dept, Govt of Uttar Pradesh', 'WB PWD' -> 'Public Works Department, Govt of West Bengal', 'L&C' -> 'Lakshya Engineering & Construction').\n"
            "2. Map first names (e.g. 'Rajesh', 'Asha', 'Neha') to full engineer names ('Rajesh Rao', 'Asha Nair', 'Neha Chopra').\n"
            "3. Reference Anchors: If a question says 'referencing X project as reference point' or 'referencing certification XYZ', that project/cert is ONLY an anchor to find the client/engineer. Do NOT put reference project names in filters or specific_package_to_query. Set filters to null unless there is an explicit exclusion like 'excluding buildings' or a date threshold like 'after March 10, 2021'.\n"
            "Respond strictly with valid JSON."
        )

        user_prompt = f"""
Candidate Clients in Database:
{json.dumps(self.clients, indent=2)}

Candidate Engineers in Database:
{json.dumps(self.engineers, indent=2)}

User Question:
"{question}"

Output JSON format:
{{
  "target_client": "exact canonical client name from Candidate Clients or null",
  "target_engineer": "exact canonical engineer name from Candidate Engineers or null",
  "specific_package_to_query": "ONLY set if user asks for the single specific package itself (e.g. 'what was the completion date of Pkg-145'); if user asks for total/all completed assignments for a client or engineer, set this to null",
  "operation_intent": "brief summary of math/query required (e.g. 'sum of all completed projects for client', 'days between cert and project completion', 'percentage of referenced projects')",
  "filters": "ONLY strict mathematical filters (e.g. 'excluding buildings', 'value >= 500000000', 'completion_date > 2021-03-10'); if no category or date exclusion, set to null"
}}
"""
        resp = self.client.generate(prompt=user_prompt, system=system_prompt, json_mode=True, temperature=0.0)
        if resp:
            try:
                return json.loads(resp)
            except Exception:
                pass
        return {
            "target_client": None,
            "target_engineer": None,
            "specific_package_to_query": None,
            "operation_intent": question,
            "filters": None
        }

    def step2_generate_sql(self, question: str, answer_type: str, entities: Dict[str, Any], previous_error: Optional[str] = None) -> Optional[str]:
        """Step 2: Schema-driven Text-to-SQL compiler with self-correction."""
        system_prompt = (
            "You are an expert SQLite developer.\n"
            "Generate a single executable SQLite query that calculates the exact numerical answer.\n"
            "Output ONLY the SQL code inside ```sql ... ``` block."
        )

        error_context = f"\nPREVIOUS ERROR TO FIX:\n{previous_error}\n" if previous_error else ""

        target_client = entities.get('target_client')
        target_engineer = entities.get('target_engineer')
        specific_pkg = entities.get('specific_package_to_query')

        user_prompt = f"""
Database Schema:
- projects (
    id INTEGER PRIMARY KEY,
    doc_id TEXT,
    package_no TEXT,
    project_name TEXT,
    client_name TEXT,
    category TEXT,
    raw_category TEXT,
    value_inr INTEGER,
    completion_date TEXT,
    lead_engineer TEXT,
    has_reference_letter INTEGER
  )
- engineers (
    emp_id TEXT PRIMARY KEY,
    name TEXT,
    designation TEXT,
    business_unit TEXT
  )
- personnel_certs (
    doc_id TEXT,
    name TEXT,
    emp_id TEXT,
    cred_type TEXT,
    cred_id TEXT,
    issue_date TEXT
  )
- receivables_ageing (
    invoice_no TEXT PRIMARY KEY,
    client_name TEXT,
    invoice_date TEXT,
    invoiced_inr INTEGER,
    received_inr INTEGER,
    outstanding_inr INTEGER
  )
- clients (
    client_name TEXT PRIMARY KEY,
    total_projects_count INTEGER,
    total_awarded_inr INTEGER,
    referenced_projects_count INTEGER,
    unreferenced_projects_count INTEGER,
    total_invoiced_inr INTEGER,
    total_received_inr INTEGER,
    total_outstanding_inr INTEGER
  )

Custom Helper Functions:
- DAYS_BETWEEN(d1, d2): Returns absolute integer number of days between two ISO date strings ('YYYY-MM-DD').

Target Calculation:
- Goal: {entities.get('operation_intent')}
- Target Client: {target_client}
- Target Engineer: {target_engineer}
- Target Package (if querying only 1 package): {specific_pkg}
- Mathematical Filters: {entities.get('filters')}
{error_context}
Expected Output Unit: {answer_type}

Instructions:
1. If the goal is the sum of completed assignments for a Client ({target_client}), write:
   `SELECT SUM(value_inr) FROM projects WHERE LOWER(client_name) = LOWER('{target_client}')`
2. If filtering by Engineer ({target_engineer}) and completion date after a threshold, write:
   `SELECT SUM(value_inr) FROM projects WHERE lead_engineer = '{target_engineer}' AND completion_date > 'YYYY-MM-DD'`
3. If calculating days between cert issue and project completion for package {specific_pkg}:
   `SELECT DAYS_BETWEEN(c.issue_date, p.completion_date) FROM projects p, personnel_certs c WHERE p.package_no = '{specific_pkg}' AND c.name = '{target_engineer}' LIMIT 1`
4. If calculating percentage of referenced projects for {target_client}:
   `SELECT (SUM(has_reference_letter) * 100.0 / COUNT(*)) FROM projects WHERE LOWER(client_name) = LOWER('{target_client}')`
5. If calculating collection rate for {target_client}:
   `SELECT (total_received_inr * 100.0 / total_invoiced_inr) FROM clients WHERE LOWER(client_name) = LOWER('{target_client}')`

Output ONLY the SQL code inside ```sql ... ```
"""
        raw_resp = self.client.generate(prompt=user_prompt, system=system_prompt, json_mode=False, temperature=0.0)
        if not raw_resp:
            return None

        # Extract SQL from markdown code block
        m = re.search(r'```(?:sql)?\s*(.*?)\s*```', raw_resp, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return raw_resp.strip()

    def execute_query(self, sql: str) -> Tuple[Optional[Any], Optional[str]]:
        """Executes SQL in SQLite and returns (result, error)."""
        try:
            cur = self.conn.cursor()
            cur.execute(sql)
            row = cur.fetchone()
            if row is not None:
                val = row[0]
                return val, None
            return 0, None
        except Exception as e:
            return None, str(e)

    def solve(self, question: str, answer_type: str, verbose: bool = True) -> Union[int, float]:
        """Full end-to-end resolution with LLM Grounding + Text-to-SQL + Self-Correction."""
        # 1. Ground entities
        entities = self.step1_ground_entities(question)
        if verbose:
            print(f"[Step 1 Grounding] {entities}")

        # 2. Text-to-SQL with up to 2 retries
        error_msg = None
        for attempt in range(3):
            sql = self.step2_generate_sql(question, answer_type, entities, previous_error=error_msg)
            if verbose:
                print(f"[Step 2 SQL (Attempt {attempt+1})] {sql}")
            if not sql:
                continue

            val, err = self.execute_query(sql)
            if verbose:
                print(f"[Execute Result] val={val}, err={err}")
            if err is None:
                # Successfully executed
                if val is None:
                    return 0 if answer_type != 'percent' else 0.0
                if answer_type == 'percent':
                    return round(float(val), 2)
                elif answer_type in ('money', 'count', 'days'):
                    return int(round(float(val)))
                return val
            else:
                error_msg = f"SQL: {sql}\nError: {err}"

        return 0 if answer_type != 'percent' else 0.0
