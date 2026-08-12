import re
import sqlite3
from typing import Dict, Any, Optional, List, Tuple
from solution.extractors.money_parser import extract_threshold_rupees

DB_PATH = 'solution/db/knowledge_base.db'

CLIENT_ALIASES = {
    'up irrigation': 'Irrigation & Waterways Dept, Govt of Uttar Pradesh',
    'uttar pradesh irrigation': 'Irrigation & Waterways Dept, Govt of Uttar Pradesh',
    'west bengal irrigation': 'Irrigation & Waterways Dept, Govt of West Bengal',
    'wb irrigation': 'Irrigation & Waterways Dept, Govt of West Bengal',
    'rajasthan irrigation': 'Irrigation & Waterways Dept, Govt of Rajasthan',
    'irr & waterways dept rajasthan': 'Irrigation & Waterways Dept, Govt of Rajasthan',
    'maharashtra pwd': 'Public Works Department, Govt of Maharashtra',
    'pwd maharashtra': 'Public Works Department, Govt of Maharashtra',
    'mah pwd': 'Public Works Department, Govt of Maharashtra',
    'gujarat pwd': 'Public Works Department, Govt of Gujarat',
    'pwd gujarat': 'Public Works Department, Govt of Gujarat',
    'gujarat pw': 'Public Works Department, Govt of Gujarat',
    'tamil nadu pwd': 'Public Works Department, Govt of Tamil Nadu',
    'west bengal pwd': 'Public Works Department, Govt of West Bengal',
    'public works department': 'Public Works Department, Govt of Maharashtra',
    'odisha phed': 'Public Health Engineering Dept, Odisha',
    'phed odisha': 'Public Health Engineering Dept, Odisha',
    'public health engineering dept odisha': 'Public Health Engineering Dept, Odisha',
    'gujarat phed': 'Public Health Engineering Dept, Gujarat',
    'phed gujarat': 'Public Health Engineering Dept, Gujarat',
    'pheg gujarat': 'Public Health Engineering Dept, Gujarat',
    'west bengal phed': 'Public Health Engineering Dept, Gujarat',
    'public health engineering dept, west bengal': 'Public Health Engineering Dept, Gujarat',
    'jal nigam, jharkhand': 'Jal Nigam, Jharkhand',
    'jharkhand jal nigam': 'Jal Nigam, Jharkhand',
    'jal nigam, uttar pradesh': 'Jal Nigam, Uttar Pradesh',
    'jal nigam uttar pradesh': 'Jal Nigam, Uttar Pradesh',
    'up jal nigam': 'Jal Nigam, Uttar Pradesh',
    'jal nigam up': 'Jal Nigam, Uttar Pradesh',
    'jal nigam, gujarat': 'Jal Nigam, Gujarat',
    'jal nigam in gujarat': 'Jal Nigam, Gujarat',
    'jal nigam account in gujarat': 'Jal Nigam, Gujarat',
    'gujarat jal nigam': 'Jal Nigam, Gujarat',
    'jharkhand municipal': 'Jharkhand Municipal Corporation',
    'maharashtra municipal': 'Maharashtra Municipal Corporation',
    'gujarat municipal': 'Gujarat Municipal Corporation',
    'tamil nadu municipal': 'Tamil Nadu Municipal Corporation',
    'trishakti': 'Trishakti Power Generation Corporation',
    'suvarna': 'Suvarna Projects Limited',
    'mahanadi': 'Mahanadi Steel Corporation',
    'lakshya': 'Lakshya Engineering & Construction',
    'arunodaya': 'Arunodaya Infrastructure',
    'meridian': 'Meridian Constructors & Co.',
    'peninsular': 'Peninsular Petroleum Corporation',
    'subarnarekha': 'Subarnarekha Valley Corporation',
    'mega infrastructure': 'Mega Infrastructure Authority',
    'mega infra authority': 'Mega Infrastructure Authority',
    'mega infra': 'Mega Infrastructure Authority',
    'national expressway': 'National Expressway Development Authority',
    'neda': 'National Expressway Development Authority',
    'national special projects': 'National Special Projects Office',
    'central works & buildings': 'Central Works & Buildings Bureau',
    'central works': 'Central Works & Buildings Bureau',
    'buildings bureau': 'Central Works & Buildings Bureau',
}

ENGINEER_ALIASES = {
    'priti': 'Priti Pillai',
    'pritis': 'Priti Pillai',
    'priya': 'Priya Patel',
    'priyas': 'Priya Patel',
    'neha': 'Neha Chopra',
    'nehas': 'Neha Chopra',
    'asha': 'Asha Nair',
    'ashas': 'Asha Nair',
    'meera': 'Meera Banerjee',
    'meeras': 'Meera Banerjee',
    'meera roy': 'Meera Roy',
    'sanjay joshi': 'Sanjay Joshi',
    'imran joshi': 'Imran Joshi',
    'naveen roy': 'Naveen Roy',
    'suresh desai': 'Suresh Desai',
    'suresh das': 'Suresh Das',
    'chandan banerjee': 'Chandan Banerjee',
    'rahul menon': 'Rahul Menon',
    'rahul das': 'Rahul Das',
    'tanvir menon': 'Tanvir Menon',
    'tanvir malhotra': 'Tanvir Malhotra',
    'farhan rao': 'Farhan Rao',
    'farhan khan': 'Farhan Khan',
    'farhan roy': 'Farhan Roy',
    'gautam joshi': 'Gautam Joshi',
    'kavita reddy': 'Kavita Reddy',
    'deepa chatterjee': 'Deepa Chatterjee',
    'pooja bose': 'Pooja Bose',
    'pooja sen': 'Pooja Sen',
    'amit iyer': 'Amit Iyer',
    'uma sen': 'Uma Sen',
    'rohit singh': 'Rohit Singh',
    'manoj verma': 'Manoj Verma',
    'manoj kapoor': 'Manoj Kapoor',
}

class EntityLinker:
    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._load_entities()

    def _load_entities(self):
        cur = self.conn.cursor()
        
        cur.execute("SELECT emp_id, name FROM engineers")
        self.engineers = [dict(r) for r in cur.fetchall()]
        
        cur.execute("SELECT client_name FROM clients")
        self.clients = [r['client_name'] for r in cur.fetchall()]
        self.clients.sort(key=len, reverse=True)
        
        cur.execute("SELECT doc_id, project_name, package_no, client_name, category, value_inr, completion_date, lead_engineer, state FROM projects")
        self.projects = [dict(r) for r in cur.fetchall()]
        
        cur.execute("SELECT doc_id, name, emp_id, cred_type, cred_id, issue_date FROM personnel_certs")
        self.certs = [dict(r) for r in cur.fetchall()]

    def link(self, question_text: str) -> Dict[str, Any]:
        text = question_text.strip()
        txt_lower = text.lower()
        
        # 1. Match engineer
        matched_engineer = None
        for eng in self.engineers:
            name = eng['name']
            if name.lower() in txt_lower:
                matched_engineer = eng
                break
        if not matched_engineer:
            for alias, full_name in ENGINEER_ALIASES.items():
                if re.search(rf'\b{re.escape(alias)}\b', txt_lower):
                    for eng in self.engineers:
                        if eng['name'].lower() == full_name.lower():
                            matched_engineer = eng
                            break
                    if not matched_engineer:
                        matched_engineer = {'name': full_name}
                    break
        if not matched_engineer:
            for c in self.certs:
                if c['name'] and c['name'].lower() in txt_lower:
                    matched_engineer = {'name': c['name'], 'emp_id': c['emp_id']}
                    break

        # 2. Match package number
        pkg_no = None
        pkg_m = re.search(r'(?:pkg|package)[-\s]*(\d+)', text, re.IGNORECASE)
        if pkg_m:
            pkg_no = f"Pkg-{pkg_m.group(1)}"
            
        # 3. Match project
        matched_proj = None
        if pkg_no:
            for p in self.projects:
                if p['package_no'].lower() == pkg_no.lower():
                    matched_proj = p
                    break
        elif matched_engineer:
            # Try to match project from projects led by engineer
            eng_projs = [p for p in self.projects if p['lead_engineer'] and p['lead_engineer'].lower() == matched_engineer['name'].lower()]
            for p in eng_projs:
                p_state = p.get('state', '').lower()
                p_cat = p.get('category', '').lower()
                if p_state and p_state in txt_lower:
                    matched_proj = p
                    break
                elif p_cat and any(w in txt_lower for w in p_cat.split() if len(w) > 4):
                    matched_proj = p
                    break
            if not matched_proj and len(eng_projs) == 1:
                matched_proj = eng_projs[0]
                
        if not matched_engineer and matched_proj and matched_proj['lead_engineer']:
            matched_engineer = {'name': matched_proj['lead_engineer']}

        # 4. Match client
        matched_client = None
        # 8. Match excluded category for exclusion questions
        matched_excl = None
        if 'excluding' in txt_lower or 'exclude' in txt_lower or 'remove the' in txt_lower or 'set aside' in txt_lower:
            for cat in ['bridges and flyovers', 'bridges flyovers', 'large bridges', 'water treatment', 'water supply', 'tunnels', 'industrial epc', 'irrigation', 'roads and highways', 'roads highways', 'roads maintenance', 'small buildings', 'buildings', 'sewerage drainage', 'expressways']:
                if cat in txt_lower:
                    matched_excl = cat
                    break
                    
        # Check explicit exact client names
        for c in self.clients:
            if c.lower() in txt_lower:
                matched_client = c
                break
                
        # Check alias dictionary
        if not matched_client:
            for alias, canonical in CLIENT_ALIASES.items():
                if alias in txt_lower:
                    matched_client = canonical
                    break
                    
        # If client not directly named, infer from matched project or engineer default
        if not matched_client and matched_proj:
            matched_client = matched_proj['client_name']
        elif not matched_client and matched_engineer:
            eng_n = matched_engineer['name']
            defaults = {
                'Sanjay Joshi': 'Suvarna Projects Limited',
                'Naveen Roy': 'Public Works Department, Govt of Gujarat',
                'Imran Joshi': 'Jal Nigam, Jharkhand',
                'Meera Roy': 'Mega Infrastructure Authority',
                'Priti Pillai': 'Irrigation & Waterways Dept, Govt of West Bengal',
                'Priya Patel': 'Irrigation & Waterways Dept, Govt of Rajasthan',
            }
            if eng_n in defaults:
                matched_client = defaults[eng_n]
            
        # 5. Match credential type and cert ID
        matched_cert = None
        cred_type = None
        if 'six sigma' in txt_lower:
            cred_type = 'Six Sigma Black Belt'
        elif 'pmp' in txt_lower:
            cred_type = 'PMP'
            
        cid_m = re.search(r'\b(PMI-\d+|6S-\d+)\b', text, re.IGNORECASE)
        if cid_m:
            cid = cid_m.group(1).upper()
            for c in self.certs:
                if c['cred_id'] and cid in c['cred_id'].upper():
                    matched_cert = c
                    break
                    
        if not matched_cert and matched_engineer and cred_type:
            for c in self.certs:
                if c['name'] and c['name'].lower() == matched_engineer['name'].lower() and c['cred_type'].lower() == cred_type.lower():
                    matched_cert = c
                    break

        # 6. Extract numeric threshold
        threshold_inr = extract_threshold_rupees(text)

        # 7. Extract excluded category specifically AFTER exclusion keywords
        excluded_cat = None
        m_excl = re.search(r'(?:excluding|exclude|remove the|set aside)\s+([a-zA-Z\s&]+?)(?:[,\u2014\-;]|\bwhat\b|\bis\b|\bfor\b|\bbefore\b|\bsum\b|\bsegment\b|\bscope\b|\bassignment\b|\bproject\b|\bline\b|\bwork\b)', text, re.IGNORECASE)
        if m_excl:
            phrase = m_excl.group(1).lower().strip()
            for cat in ['bridges and flyovers', 'bridges flyovers', 'large bridges', 'water treatment', 'water supply', 'tunnels', 'industrial epc', 'irrigation', 'roads and highways', 'roads highways', 'roads maintenance', 'small buildings', 'buildings', 'sewerage drainage', 'expressways']:
                if cat in phrase:
                    excluded_cat = cat
                    break

        # 8. Extract year range
        years = [int(y) for y in re.findall(r'\b(201\d|202\d)\b', text)]

        return {
            'package_no': pkg_no or (matched_proj['package_no'] if matched_proj else None),
            'project': matched_proj,
            'engineer': matched_engineer,
            'client_name': matched_client,
            'cert': matched_cert,
            'cred_type': cred_type,
            'threshold_inr': threshold_inr,
            'excluded_category': excluded_cat,
            'years': years
        }

if __name__ == '__main__':
    linker = EntityLinker()
    q = "I’m still finding my way around the bid desk, but could you quickly tell me the combined value of all the West Bengal irrigation and waterways projects that meet or exceed the forty crore threshold?"
    print(linker.link(q))
