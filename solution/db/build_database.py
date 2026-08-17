import sqlite3
import os
import sys
import pandas as pd
from typing import Optional

sys.path.insert(0, os.path.abspath('.'))
from solution.extractors.discover import discover_and_classify
from solution.extractors.extract_projects import extract_projects
from solution.extractors.extract_personnel import extract_personnel_certs, extract_cvs
from solution.extractors.extract_references import extract_reference_letters
from solution.extractors.extract_financials import extract_receivables_ageing, extract_asset_register

DB_PATH = 'solution/db/knowledge_base.db'

def init_db(db_path: str = DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.executescript('''
    DROP TABLE IF EXISTS projects;
    DROP TABLE IF EXISTS engineers;
    DROP TABLE IF EXISTS personnel_certs;
    DROP TABLE IF EXISTS receivables_ageing;
    DROP TABLE IF EXISTS plant_register;
    DROP TABLE IF EXISTS equipment_assets;
    DROP TABLE IF EXISTS clients;
    ''')
    
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT UNIQUE,
        project_name TEXT,
        client_name TEXT,
        category TEXT,
        raw_category TEXT,
        value_inr INTEGER,
        completion_date TEXT,
        lead_engineer TEXT,
        package_no TEXT,
        state TEXT,
        client_cert_ref TEXT,
        has_reference_letter INTEGER DEFAULT 0,
        ref_letter_doc_id TEXT
    );

    CREATE TABLE IF NOT EXISTS engineers (
        emp_id TEXT PRIMARY KEY,
        name TEXT,
        designation TEXT,
        business_unit TEXT,
        experience_years TEXT,
        qualification TEXT,
        date_of_joining TEXT
    );

    CREATE TABLE IF NOT EXISTS personnel_certs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT UNIQUE,
        name TEXT,
        emp_id TEXT,
        cred_type TEXT,
        cred_id TEXT,
        issue_date TEXT,
        valid_through TEXT
    );

    CREATE TABLE IF NOT EXISTS receivables_ageing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT,
        client_name TEXT,
        raw_client_name TEXT,
        invoice_date TEXT,
        invoiced_inr INTEGER,
        status TEXT,
        received_inr INTEGER,
        outstanding_inr INTEGER
    );

    CREATE TABLE IF NOT EXISTS equipment_assets (
        asset_id INTEGER PRIMARY KEY,
        asset_type TEXT,
        make TEXT,
        acquired_year INTEGER,
        cost_inr INTEGER,
        condition TEXT,
        location TEXT,
        ownership TEXT,
        safety_certified INTEGER
    );

    CREATE TABLE IF NOT EXISTS clients (
        client_name TEXT PRIMARY KEY,
        total_projects_count INTEGER,
        total_awarded_inr INTEGER,
        referenced_projects_count INTEGER,
        unreferenced_projects_count INTEGER,
        total_invoiced_inr INTEGER,
        total_received_inr INTEGER,
        total_outstanding_inr INTEGER
    );
    ''')
    conn.commit()
    return conn

def discover_documents(docs_root: str):
    import glob
    from solution.extractors.discover import classify_xlsx
    
    grouped = {}
    
    # 1. Discover all xlsx workbooks by header
    found_xlsx = glob.glob(os.path.join(docs_root, '**', '*.xlsx'), recursive=True)
    for f in found_xlsx:
        cls, sheet = classify_xlsx(f)
        if cls not in ('unreadable', 'unknown'):
            grouped.setdefault(cls, []).append((f, sheet))

    # 2. Check if document_index.csv exists in docs_root, parent, or cwd for PDFs
    candidates = [
        os.path.join(docs_root, 'document_index.csv'),
        os.path.join(docs_root, '..', 'document_index.csv'),
        'document_index.csv'
    ]
    index_path = next((c for c in candidates if os.path.exists(c)), None)
    if index_path:
        try:
            df = pd.read_csv(index_path)
            for _, row in df.iterrows():
                dtype = str(row['doc_type']).strip()
                fname = str(row['filename']).strip()
                full_p = os.path.join(docs_root, fname)
                if not os.path.exists(full_p):
                    base = os.path.basename(fname)
                    full_p = os.path.join(docs_root, base)
                if not os.path.exists(full_p):
                    full_p = os.path.join(docs_root, fname)
                
                if dtype in ('completion_certificate', 'company_completion_certificate'):
                    grouped.setdefault('completion_certificate_any', []).append(full_p)
                else:
                    grouped.setdefault(dtype, []).append(full_p)
            return grouped
        except Exception:
            pass
            
    # Fallback to content-based discovery if index not present
    return discover_and_classify(docs_root)

def populate_database(db_path: str = DB_PATH, docs_root: str = 'documents'):
    print(f'Discovering documents under {docs_root}/ ...')
    grouped = discover_documents(docs_root)
    for cls, files in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        print(f'  {cls:32s}: {len(files)}')
    if grouped.get('unreadable'):
        print(f'  WARNING: {len(grouped["unreadable"])} file(s) could not be opened, skipped')

    print('Building knowledge base database...')
    conn = init_db(db_path)
    cur = conn.cursor()

    # 1. Extract and insert projects
    raw_projects = extract_projects(grouped.get('completion_certificate_any', []))
    # Extract reference letters and match
    ref_letters = extract_reference_letters(raw_projects, grouped.get('reference_letter', []))
    matched_refs = {r['matched_project_doc_id']: r['doc_id'] for r in ref_letters if r['matched_project_doc_id']}
    
    for p in raw_projects:
        has_ref = 1 if p['doc_id'] in matched_refs else 0
        ref_doc_id = matched_refs.get(p['doc_id'])
        cur.execute('''
        INSERT INTO projects (doc_id, project_name, client_name, category, raw_category, value_inr, completion_date, lead_engineer, package_no, state, client_cert_ref, has_reference_letter, ref_letter_doc_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (p['doc_id'], p['project_name'], p['client_name'], p['category'], p['raw_category'], p['value_inr'], p['completion_date'], p['lead_engineer'], p['package_no'], p['state'], p['client_cert_ref'], has_ref, ref_doc_id))
    
    # 2. Extract and insert engineers (CVs)
    cvs = extract_cvs(grouped.get('cv', []))
    for c in cvs:
        cur.execute('''
        INSERT OR REPLACE INTO engineers (emp_id, name, designation, business_unit, experience_years, qualification, date_of_joining)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (c['emp_id'], c['name'], c['designation'], c['business_unit'], c['experience_years'], c['qualification'], c['date_of_joining']))

    # 3. Extract and insert personnel certs
    certs = extract_personnel_certs(grouped.get('personnel_certificate', []))
    for cert in certs:
        cur.execute('''
        INSERT INTO personnel_certs (doc_id, name, emp_id, cred_type, cred_id, issue_date, valid_through)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (cert['doc_id'], cert['name'], cert['emp_id'], cert['cred_type'], cert['cred_id'], cert['issue_date'], cert['valid_through']))
        
    # 4. Extract and insert receivables
    ar_source = grouped.get('receivables_ageing', [None])[0]
    ar_records = extract_receivables_ageing(ar_source)
    for ar in ar_records:
        cur.execute('''
        INSERT INTO receivables_ageing (invoice_no, client_name, raw_client_name, invoice_date, invoiced_inr, status, received_inr, outstanding_inr)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ar['invoice_no'], ar['client_name'], ar['raw_client_name'], ar['invoice_date'], ar['invoiced_inr'], ar['status'], ar['received_inr'], ar['outstanding_inr']))

    # 5. Extract and insert assets
    plant_source = grouped.get('plant_machinery_register', [None])[0]
    assets = extract_asset_register(plant_source)
    for a in assets:
        cur.execute('''
        INSERT INTO equipment_assets (asset_id, asset_type, make, acquired_year, cost_inr, condition, location, ownership, safety_certified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (a['asset_id'], a['asset_type'], a['make'], a['acquired_year'], a['cost_inr'], a['condition'], a['location'], a['ownership'], 1 if a['safety_certified'] else 0))
        
    # 6. Aggregate client stats
    cur.execute('''
    INSERT OR REPLACE INTO clients (client_name, total_projects_count, total_awarded_inr, referenced_projects_count, unreferenced_projects_count, total_invoiced_inr, total_received_inr, total_outstanding_inr)
    SELECT 
        all_clients.client_name,
        COALESCE(p_stats.total_projects_count, 0),
        COALESCE(p_stats.total_awarded_inr, 0),
        COALESCE(p_stats.referenced_projects_count, 0),
        COALESCE(p_stats.unreferenced_projects_count, 0),
        COALESCE(ar.total_invoiced, 0),
        COALESCE(ar.total_received, 0),
        COALESCE(ar.total_outstanding, 0)
    FROM (
        SELECT client_name FROM projects WHERE client_name IS NOT NULL AND client_name != '' AND client_name != 'nan'
        UNION
        SELECT client_name FROM receivables_ageing WHERE client_name IS NOT NULL AND client_name != '' AND client_name != 'nan'
    ) all_clients
    LEFT JOIN (
        SELECT 
            client_name,
            COUNT(id) AS total_projects_count,
            SUM(value_inr) AS total_awarded_inr,
            SUM(has_reference_letter) AS referenced_projects_count,
            SUM(1 - has_reference_letter) AS unreferenced_projects_count
        FROM projects
        WHERE client_name IS NOT NULL AND client_name != '' AND client_name != 'nan'
        GROUP BY client_name
    ) p_stats ON all_clients.client_name = p_stats.client_name
    LEFT JOIN (
        SELECT client_name, SUM(invoiced_inr) AS total_invoiced, SUM(received_inr) AS total_received, SUM(outstanding_inr) AS total_outstanding
        FROM receivables_ageing
        WHERE client_name IS NOT NULL AND client_name != '' AND client_name != 'nan'
        GROUP BY client_name
    ) ar ON all_clients.client_name = ar.client_name
    WHERE all_clients.client_name IS NOT NULL AND all_clients.client_name != '' AND all_clients.client_name != 'nan';
    ''')
    
    conn.commit()
    print('Database populated successfully!')
    
    # Print sanity statistics
    cur.execute('SELECT COUNT(*) FROM projects')
    print(f'Projects in DB: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM engineers')
    print(f'Engineers in DB: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM personnel_certs')
    print(f'Personnel Certs in DB: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM receivables_ageing')
    print(f'Receivables rows in DB: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM clients')
    print(f'Clients in DB: {cur.fetchone()[0]}')
    
    conn.close()

if __name__ == '__main__':
    import sys
    docs_root = sys.argv[1] if len(sys.argv) > 1 else 'documents'
    populate_database(docs_root=docs_root)
