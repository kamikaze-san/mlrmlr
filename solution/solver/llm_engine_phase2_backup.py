import sqlite3
import os
import re
import json
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, Union, Tuple, List
from solution.solver.ollama_client import OllamaClient
from solution.solver.entity_resolver import EntityResolver

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
        self.resolver = EntityResolver(db_path)

    def _build_system_prompt(self) -> str:
        return """You are an expert SQLite analyst for an infrastructure corporate knowledge base.
Given a natural language question, a database schema, and a pre-resolved entities section, write a
single executable SQLite query. The entities section has already identified which real clients,
engineers, categories and projects the question refers to -- use those exact values, don't re-derive
them from the raw question text yourself.
Respond strictly in JSON format: {"sql": "SELECT ..."}

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
- equipment_assets (
    asset_id INTEGER PRIMARY KEY,
    asset_type TEXT,
    make TEXT,
    acquired_year INTEGER,
    cost_inr INTEGER,
    condition TEXT,
    location TEXT,
    ownership TEXT,
    safety_certified INTEGER
  )

Available In-DB Helper Functions:
- DAYS_BETWEEN(date1, date2): Returns integer day difference between two ISO dates ('YYYY-MM-DD').
- PERCENT(numerator, denominator): Returns rounded percentage (num * 100.0 / denom).
- MEDIAN(column): Computes the 50th percentile median of a column.

Rules for Query Generation:
1. Use the exact canonical names given in the "Resolved Entities" section below -- never guess a
   spelling or abbreviation yourself, the resolution has already been done.
2. If a "Resolved Entities" field lists MULTIPLE tied candidates for the same entity (meaning the
   question's wording alone doesn't disambiguate which one is meant), write the query with
   `WHERE col IN (...)` over all of them, GROUP BY that column, and apply whatever other filters the
   question also states (other resolved entities, categories, thresholds). The correct one should be
   whichever group satisfies every constraint the question actually gives -- don't just pick the
   first tied candidate arbitrarily.
3. Case-Insensitive Matching: Always use LOWER(client_name) = LOWER('canonical_name') or
   LOWER(lead_engineer) = LOWER('canonical_name').
4. Scope of Total Value: When asked for the total value of all completed assignments delivered for a
   client, and any specific package/project mentioned is only background context establishing which
   client is meant (not the actual thing being asked about), sum over the WHOLE client, not just that
   one project -- and the same applies to an engineer mentioned only as scaffolding to identify the
   client: `SELECT SUM(value_inr) FROM projects WHERE LOWER(client_name) = LOWER('canonical_client')`.
5. Aggregation by Expected Unit:
   - 'count': Use COUNT(*) or COUNT(DISTINCT col).
   - 'percent': Use PERCENT(SUM(has_reference_letter), COUNT(*)) or PERCENT(total_received_inr, total_invoiced_inr).
   - 'days': Use DAYS_BETWEEN(c.issue_date, p.completion_date).
   - 'money': Use SUM(value_inr), AVG(value_inr), or (AVG(value_inr) - MEDIAN(value_inr)).
"""

    def _build_resolved_entities_section(self, question: str) -> Tuple[str, Dict[str, Any]]:
        """Runs the deterministic resolver (no LLM call) and formats what it
        found for the prompt. Returns the text block plus the raw resolution
        info, so callers/tests can inspect what was actually resolved."""
        info: Dict[str, Any] = {}
        lines = []

        client_res = self.resolver.resolve_client(question)
        if client_res.matched:
            lines.append(f"- Client: {client_res.matched} (resolved via {client_res.method})")
            info['client'] = client_res.matched
        elif client_res.tied:
            lines.append(f"- Client: AMBIGUOUS from wording alone -- candidates: {json.dumps(client_res.tied)}")
            info['client_tied'] = client_res.tied

        scope_client = client_res.matched
        eng_res = self.resolver.resolve_engineer(question)
        if eng_res.matched:
            lines.append(f"- Engineer: {eng_res.matched} (resolved via {eng_res.method})")
            info['engineer'] = eng_res.matched
        elif eng_res.tied:
            lines.append(f"- Engineer: AMBIGUOUS from wording alone -- candidates: {json.dumps(eng_res.tied)}")
            info['engineer_tied'] = eng_res.tied

        cred_res = self.resolver.resolve_cred_type(question)
        if cred_res.matched:
            lines.append(f"- Credential type: {cred_res.matched}")
            info['cred_type'] = cred_res.matched

        proj_res = self.resolver.resolve_project(
            question,
            scope_engineer=eng_res.matched,
            scope_client=scope_client,
        )
        if proj_res.matched:
            lines.append(f"- Project referenced: {proj_res.matched} (resolved via {proj_res.method})")
            info['project'] = proj_res.matched
        elif proj_res.tied:
            lines.append(f"- Project referenced: AMBIGUOUS -- candidates: {json.dumps(proj_res.tied)}")
            info['project_tied'] = proj_res.tied

        # Category resolution goes last and masks out every other already-
        # resolved entity's own words (client, engineer, project) -- a
        # project name like "Ring Road" would otherwise leak "roads" into
        # matching the "roads highways" category even when the question
        # never actually asks about categories at all.
        mask = [v for v in (client_res.matched, eng_res.matched, proj_res.matched) if v]
        cats = self.resolver.resolve_categories(question, top_n=3, mask=mask)
        if cats:
            lines.append(f"- Categories mentioned: {json.dumps(cats)}")
            info['categories'] = cats

        if not lines:
            lines.append("- No entities confidently resolved from the question text; use the live lists below directly.")

        # Only fall back to the full live lists for whichever entity types
        # the resolver genuinely couldn't pin down at all -- showing them
        # unconditionally, even when resolution already succeeded, just
        # bloats the prompt with redundant information for the common case
        # and measurably hurt a small model's accuracy in testing (diluted
        # focus, not missing information).
        if 'client' not in info and 'client_tied' not in info:
            lines.append(f"- All known clients: {json.dumps(self.resolver.clients)}")
        if 'engineer' not in info and 'engineer_tied' not in info:
            lines.append(f"- All known engineers: {json.dumps(self.resolver.engineers)}")
        if 'categories' not in info:
            lines.append(f"- All known categories: {json.dumps(self.resolver.categories)}")

        return "Resolved Entities (deterministic pre-match, done before this prompt was built):\n" + "\n".join(lines), info

    def _build_user_prompt(self, question: str, answer_type: str, previous_error: Optional[str] = None) -> str:
        error_section = f"PREVIOUS ERROR TO FIX:\n{previous_error}\n\n" if previous_error else ""
        entities_section, _info = self._build_resolved_entities_section(question)
        return f"""{error_section}{entities_section}

Question: "{question}"
Expected Unit: {answer_type}

Output JSON format:
{{"sql": "SELECT ..."}}"""

    def check_semantic_plausibility(self, val: Any, answer_type: str) -> Optional[str]:
        """Validates that execution result matches the expected unit. Bounds
        are kept intentionally loose and, where possible, derived from the
        live database rather than hardcoded -- a hardcoded upper bound is
        itself a dataset-specific assumption (e.g. percent-change answers
        can legitimately exceed 100 or go negative, unlike percent-share
        answers, so only an absurd magnitude is flagged, not a fixed range)."""
        if val is None:
            return "Query returned NULL. Check if WHERE filters were too restrictive."

        try:
            num = float(val)
        except (ValueError, TypeError):
            return None

        if answer_type == 'count':
            max_plausible = self._max_row_count()
            if num > max_plausible:
                return (f"Semantic Error: Expected a small integer count, but query returned {num}, "
                        f"which exceeds the largest table's actual row count ({max_plausible}) -- "
                        f"this looks like a monetary SUM was used instead of COUNT(*).")

        if answer_type == 'percent' and abs(num) > 100000:
            return f"Semantic Error: {num} is an implausible magnitude for a percentage. Check the PERCENT() arguments."

        if answer_type == 'days' and (num < 0 or num > 36500):
            return f"Semantic Error: Expected positive integer days elapsed, but got {num}. Use DAYS_BETWEEN(d1, d2)."

        if answer_type == 'money' and abs(num) > 1_000_000_000_000:
            return f"Semantic Error: {num} is an implausible magnitude for a rupee value in this dataset. Check for an unintended CROSS JOIN inflating the sum."

        return None

    def _max_row_count(self) -> int:
        if not hasattr(self, '_cached_max_rows'):
            conn = get_db_connection(self.db_path)
            cur = conn.cursor()
            counts = []
            for table in ('projects', 'engineers', 'personnel_certs', 'receivables_ageing', 'equipment_assets', 'clients'):
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    counts.append(cur.fetchone()[0])
                except sqlite3.Error:
                    pass
            conn.close()
            self._cached_max_rows = max(counts) if counts else 100000
        return self._cached_max_rows

    def solve(self, question: str, answer_type: str, verbose: bool = False) -> Union[int, float]:
        """Deterministic entity resolution first (no LLM, no cost), then a
        single-pass Text-to-SQL call using the already-resolved entities,
        with semantic guardrails on retry."""
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
