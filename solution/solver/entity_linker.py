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
    'west bengal phed': 'Public Health Engineering Dept, West Bengal',
    'public health engineering dept, west bengal': 'Public Health Engineering Dept, West Bengal',
    'public health engineering dept west bengal': 'Public Health Engineering Dept, West Bengal',
    'phed west bengal': 'Public Health Engineering Dept, West Bengal',
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
    # NOTE: bare first names are intentionally NOT hardcoded here when more
    # than one engineer shares that first name (e.g. Priya Patel / Priya
    # Gupta, Asha Nair / Asha Bose, Meera Roy / Meera Chatterjee / Meera
    # Banerjee) — a hardcoded guess would silently resolve to the wrong
    # person. Unambiguous first names are resolved generically at runtime
    # via EntityLinker.unique_first_names (built from the DB in
    # _load_entities), which only fires when exactly one engineer has that
    # first name. Full names below are safe regardless.
    'priti': 'Priti Pillai',
    'pritis': 'Priti Pillai',
    'neha': 'Neha Chopra',
    'nehas': 'Neha Chopra',
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

        # Real work categories, derived from the data itself rather than a
        # hand-typed list — guarantees every category that actually exists
        # in the documents is recognized, with no risk of one being missed.
        cur.execute("SELECT DISTINCT category FROM projects WHERE category IS NOT NULL AND category != ''")
        self.real_categories = [r[0] for r in cur.fetchall()]

        # First name -> full name, but only kept when exactly one engineer
        # in the whole roster has that first name. This generalizes the
        # first-name shortcut to everyone (not just names someone happened
        # to hardcode) while refusing to guess when it's genuinely ambiguous.
        first_name_counts: Dict[str, List[str]] = {}
        for eng in self.engineers:
            first = eng['name'].split()[0].lower()
            first_name_counts.setdefault(first, []).append(eng['name'])
        self.first_name_groups = first_name_counts
        self.unique_first_names = {
            fn: names[0] for fn, names in first_name_counts.items() if len(names) == 1
        }

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
            # Generic first-name fallback — only for first names that
            # belong to exactly one engineer in the roster (see
            # unique_first_names in _load_entities). Ambiguous first names
            # are deliberately left unresolved here so a stronger signal
            # (credential ID, package number) gets a chance to decide it,
            # rather than silently guessing.
            for first, full_name in self.unique_first_names.items():
                if re.search(rf'\b{re.escape(first)}\b', txt_lower):
                    for eng in self.engineers:
                        if eng['name'].lower() == full_name.lower():
                            matched_engineer = eng
                            break
                    if not matched_engineer:
                        matched_engineer = {'name': full_name}
                    break
        if not matched_engineer:
            # Ambiguous first name (2+ candidates share it) — try to
            # disambiguate by matching the question's project/location
            # wording against each candidate's own projects. Only resolves
            # when exactly one candidate has a real match; otherwise stays
            # unresolved rather than guessing which one is meant.
            for first, full_names in self.first_name_groups.items():
                if len(full_names) < 2 or not re.search(rf'\b{re.escape(first)}\b', txt_lower):
                    continue
                strong_candidates = []
                for full_name in full_names:
                    cand_projs = [p for p in self.projects if p['lead_engineer'] and p['lead_engineer'].lower() == full_name.lower()]
                    best = 0
                    for p in cand_projs:
                        p_name = p['project_name'].lower().replace('–', ' ').replace('-', ' ')
                        words = [w for w in p_name.split() if len(w) > 2 and w not in ['package', 'pkg']]
                        best = max(best, sum(1 for w in words if w in txt_lower))
                    if best >= 2:
                        strong_candidates.append(full_name)
                if len(strong_candidates) == 1:
                    for eng in self.engineers:
                        if eng['name'].lower() == strong_candidates[0].lower():
                            matched_engineer = eng
                            break
                    if not matched_engineer:
                        matched_engineer = {'name': strong_candidates[0]}
                break
        if not matched_engineer:
            for c in self.certs:
                if c['name'] and c['name'].lower() in txt_lower:
                    matched_engineer = {'name': c['name'], 'emp_id': c['emp_id']}
                    break

        # 1b. A credential ID (PMI-xxxxx / 6S-xxxxx) uniquely identifies one
        # person. It's a stronger signal than a name/alias guess, so if it
        # disagrees with whatever was matched above, it wins.
        matched_cert = None
        cid_m = re.search(r'\b(PMI-\d+|6S-\d+)\b', text, re.IGNORECASE)
        if cid_m:
            cid = cid_m.group(1).upper()
            for c in self.certs:
                if c['cred_id'] and cid in c['cred_id'].upper():
                    matched_cert = c
                    break
            if matched_cert and (not matched_engineer or matched_engineer['name'].lower() != matched_cert['name'].lower()):
                resolved = None
                for eng in self.engineers:
                    if eng['name'].lower() == matched_cert['name'].lower():
                        resolved = eng
                        break
                matched_engineer = resolved or {'name': matched_cert['name'], 'emp_id': matched_cert.get('emp_id')}

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
            # A package number is unique to one project/engineer — if it
            # disagrees with whatever was matched above, the package wins.
            if matched_proj and matched_proj['lead_engineer'] and (
                not matched_engineer or matched_engineer['name'].lower() != matched_proj['lead_engineer'].lower()
            ):
                resolved = None
                for eng in self.engineers:
                    if eng['name'].lower() == matched_proj['lead_engineer'].lower():
                        resolved = eng
                        break
                matched_engineer = resolved or {'name': matched_proj['lead_engineer']}
        elif matched_engineer:
            # Try to match project from projects led by engineer using keyword relevance
            eng_projs = [p for p in self.projects if p['lead_engineer'] and p['lead_engineer'].lower() == matched_engineer['name'].lower()]
            best_score = 0
            for p in eng_projs:
                p_name = p['project_name'].lower().replace('–', ' ').replace('-', ' ')
                words = [w for w in p_name.split() if len(w) > 2 and w not in ['package', 'pkg']]
                score = sum(1 for w in words if w in txt_lower)
                if score > best_score:
                    best_score = score
                    matched_proj = p
            if best_score < 2:
                matched_proj = None
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
                    
        # If client not directly named, infer from the matched project. No
        # hardcoded engineer->client answer table: when a question names
        # only the engineer, with no client and no identifiable project,
        # the client genuinely cannot be determined from the text, and
        # matched_client is correctly left unresolved rather than guessed.
        if not matched_client and matched_proj:
            matched_client = matched_proj['client_name']


        # 5. Match credential type (matched_cert may already be set by 1b above)
        cred_type = None
        if 'six sigma' in txt_lower:
            cred_type = 'Six Sigma Black Belt'
        elif 'pmp' in txt_lower:
            cred_type = 'PMP'

        if not matched_cert and matched_engineer and cred_type:
            for c in self.certs:
                if c['name'] and c['name'].lower() == matched_engineer['name'].lower() and c['cred_type'].lower() == cred_type.lower():
                    matched_cert = c
                    break

        # 6. Extract numeric threshold
        threshold_inr = extract_threshold_rupees(text)

        # 7. Extract excluded category. Rather than requiring one exact
        # sentence shape (trigger word, then category, then one of a fixed
        # set of closing words \u2014 brittle to rewording), scan the whole
        # question for any real category (derived from the DB, so it can't
        # be missing one), matching by word-overlap with crude trailing-'s'
        # stemming so "bridge/bridges", "highway/highways" etc. count as the
        # same word. The matched client's own name is masked out first, so a
        # category-like word sitting inside a client's name (e.g. "irrigation"
        # in "Irrigation & Waterways Dept") can never be mistaken for the
        # thing actually being excluded.
        excluded_cat = None

        def _norm_word(w: str) -> str:
            return w[:-1] if w.endswith('s') and len(w) > 3 else w

        scan_text = txt_lower
        if matched_client:
            scan_text = scan_text.replace(matched_client.lower(), ' ')
        scan_words = set(_norm_word(w) for w in re.findall(r'[a-z]+', scan_text))

        cat_matches = []
        for cat in self.real_categories:
            cat_words = [_norm_word(w) for w in cat.lower().split()]
            if all(w in scan_words for w in cat_words):
                cat_matches.append(cat)
        if cat_matches:
            excluded_cat = max(cat_matches, key=lambda c: len(c.split()))

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
