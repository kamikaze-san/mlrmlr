import sqlite3
import os
import re
import json
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, Union, Tuple, List
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

def percent_calc(num: Any, denom: Any) -> float:
    try:
        n = float(num) if num is not None else 0.0
        d = float(denom) if denom is not None else 0.0
        if d == 0.0:
            return 0.0
        return round((n * 100.0 / d), 2)
    except Exception:
        return 0.0

class MedianAggregate:
    def __init__(self):
        self.values = []

    def step(self, value):
        if value is not None:
            try:
                self.values.append(float(value))
            except (ValueError, TypeError):
                pass

    def finalize(self):
        if not self.values:
            return 0.0
        return float(np.median(self.values))

def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Creates a configured SQLite connection with custom math primitives."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.create_function("DAYS_BETWEEN", 2, days_between)
    conn.create_function("PERCENT", 2, percent_calc)
    conn.create_aggregate("MEDIAN", 1, MedianAggregate)
    return conn

class LLMEngine:
    def __init__(self, db_path: str = DB_PATH, ollama_client: Optional[OllamaClient] = None):
        self.db_path = db_path
        self.client = ollama_client or OllamaClient()
        self._load_dynamic_entity_catalog()

    def _load_dynamic_entity_catalog(self):
        """Pulls distinct values dynamically from the live database at runtime."""
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT DISTINCT client_name FROM clients WHERE client_name IS NOT NULL AND client_name != '' AND client_name != 'nan'")
        self.clients = [r[0] for r in cur.fetchall()]
        
        cur.execute("SELECT DISTINCT name FROM engineers WHERE name IS NOT NULL AND name != ''")
        self.engineers = [r[0] for r in cur.fetchall()]

        cur.execute("SELECT DISTINCT category FROM projects WHERE category IS NOT NULL AND category != ''")
        self.categories = [r[0] for r in cur.fetchall()]
        conn.close()

    def _build_system_prompt(self) -> str:
        return (
            "You are an expert SQLite analyst for an infrastructure corporate knowledge base.\n"
            "Given a natural language question and database schema, write a single executable SQLite query.\n"
            "Respond strictly in JSON format: {\"sql\": \"SELECT ...\"}"
        )

    def _build_user_prompt(self, question: str, answer_type: str, previous_error: Optional[str] = None) -> str:
        error_section = f"\nPREVIOUS ERROR TO FIX:\n{previous_error}\n" if previous_error else ""
        return f"""
SQLite Database Schema:
- projects (
    id INTEGER PRIMARY KEY,
    package_no TEXT,
    project_name TEXT,
    client_name TEXT,
    category TEXT,
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

Live Distinct Entities in Database:
- Clients: {json.dumps(self.clients)}
- Engineers: {json.dumps(self.engineers)}
- Categories: {json.dumps(self.categories)}

Available In-DB Helper Functions:
- DAYS_BETWEEN(date1, date2): Returns integer day difference between two ISO dates ('YYYY-MM-DD').
- PERCENT(numerator, denominator): Returns rounded percentage (num * 100.0 / denom).
- MEDIAN(column): Computes the 50th percentile median of a column.

Rules for Query Generation:
1. Always map client abbreviations (e.g. 'NEDA' -> 'National Expressway Development Authority', 'UP Irrigation' -> 'Irrigation & Waterways Dept, Govt of Uttar Pradesh') to the exact canonical client from the live Clients list.
2. Case-Insensitive Matching: Always use LOWER(client_name) = LOWER('canonical_name') or LOWER(lead_engineer) = LOWER('canonical_name').
3. Scope of Total Value: When asked for the "total value of all completed assignments delivered for [Client]", compute `SELECT SUM(value_inr) FROM projects WHERE LOWER(client_name) = LOWER('canonical_client')`. Do NOT filter by a package_no mentioned only as background reference point.
4. Aggregation by Expected Unit ({answer_type}):
   - 'count': Use COUNT(*) or COUNT(DISTINCT col).
   - 'percent': Use PERCENT(SUM(has_reference_letter), COUNT(*)) or PERCENT(total_received_inr, total_invoiced_inr).
   - 'days': Use DAYS_BETWEEN(c.issue_date, p.completion_date).
   - 'money': Use SUM(value_inr), AVG(value_inr), or (AVG(value_inr) - MEDIAN(value_inr)).
5. Category Filters: Map keywords to exact strings from Categories list, e.g. 'excluding buildings' -> `WHERE category NOT LIKE '%building%'`.
{error_section}
Question: "{question}"
Expected Unit: {answer_type}

Output JSON format:
{{"sql": "SELECT ..."}}
"""

    def check_semantic_plausibility(self, val: Any, answer_type: str) -> Optional[str]:
        """Validates that execution result matches the expected unit."""
        if val is None:
            return "Query returned NULL. Check if WHERE filters were too restrictive."
        
        try:
            num = float(val)
        except (ValueError, TypeError):
            return None

        if answer_type == 'count' and num > 1000:
            return f"Semantic Error: Expected a small integer count (e.g. number of projects/engineers), but query returned {num} (likely a monetary sum). Use COUNT(*) instead of SUM(value_inr)."
        
        if answer_type == 'percent' and (num < 0.0 or num > 100.0):
            return f"Semantic Error: Expected a percentage between 0.0 and 100.0, but query returned {num}. Check formula: PERCENT(numerator, denominator)."
        
        if answer_type == 'days' and (num < 0 or num > 36500):
            return f"Semantic Error: Expected positive integer days elapsed, but got {num}. Use DAYS_BETWEEN(d1, d2)."
        
        return None

    def solve(self, question: str, answer_type: str, verbose: bool = False) -> Union[int, float]:
        """Single-pass high-throughput Text-to-SQL with semantic guardrails."""
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        
        error_msg = None
        system_prompt = self._build_system_prompt()

        for attempt in range(3):
            user_prompt = self._build_user_prompt(question, answer_type, previous_error=error_msg)
            raw_resp = self.client.generate(prompt=user_prompt, system=system_prompt, json_mode=True, temperature=0.0)
            
            sql = None
            if raw_resp:
                try:
                    data = json.loads(raw_resp)
                    sql = data.get("sql")
                except Exception:
                    # Fallback regex extraction if raw JSON wrapper had extra text
                    m = re.search(r'SELECT\s+.*', raw_resp, re.DOTALL | re.IGNORECASE)
                    if m:
                        sql = m.group(0).rstrip(';`"\n }')

            if not sql:
                error_msg = "Could not parse valid SQL from JSON response. Output format must be {\"sql\": \"SELECT ...\"}."
                continue

            if verbose:
                print(f"[SQL Attempt {attempt+1}] {sql}")

            try:
                cur.execute(sql)
                row = cur.fetchone()
                val = row[0] if row is not None else 0
                
                # Check semantic plausibility
                semantic_err = self.check_semantic_plausibility(val, answer_type)
                if semantic_err is not None and attempt < 2:
                    error_msg = f"SQL: {sql}\n{semantic_err}"
                    continue

                conn.close()
                if val is None:
                    return 0 if answer_type != 'percent' else 0.0
                if answer_type == 'percent':
                    return round(float(val), 2)
                elif answer_type in ('money', 'count', 'days'):
                    return int(round(float(val)))
                return val

            except Exception as e:
                error_msg = f"SQL Error on '{sql}': {e}"
                if verbose:
                    print(f"[Execution Error] {e}")

        conn.close()
        return 0 if answer_type != 'percent' else 0.0
