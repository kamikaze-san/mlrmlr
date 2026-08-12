import glob
import os
import re
import fitz
from typing import List, Dict, Any
from solution.extractors.money_parser import parse_money, parse_date

def normalize_text(s: str) -> str:
    if not s:
        return ""
    # Replace unicode replacement char or em-dashes with standard em-dash
    s = s.replace('\ufffd', '—').replace('\u2013', '—').replace('\u2014', '—')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def clean_client_name(raw_client: str) -> str:
    if not raw_client:
        return ""
    cleaned = normalize_text(raw_client)
    cleaned = re.sub(r'\s*\([^)]*\)', '', cleaned).strip()
    return cleaned

def clean_category(raw_cat: str) -> str:
    if not raw_cat:
        return ""
    c = raw_cat.lower().strip()
    c = re.sub(r'[^\w\s]', ' ', c)
    c = re.sub(r'\s+', ' ', c).strip()
    return c

def extract_package_number(work_name: str) -> str:
    """Extracts package identifier e.g. 'Pkg-145', 'Pkg-51'."""
    m = re.search(r'Pkg-?(\d+)', work_name, re.IGNORECASE)
    if m:
        return f"Pkg-{m.group(1)}"
    return ""

def extract_state(work_name: str) -> str:
    states = [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
        'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
        'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
        'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi'
    ]
    for s in states:
        if s.lower() in work_name.lower():
            return s
    return ""

def extract_projects() -> List[Dict[str, Any]]:
    files = sorted(glob.glob('documents/company_completion_certificate/*.pdf'))
    projects = []
    
    for f in files:
        doc = fitz.open(f)
        txt = doc[0].get_text()
        
        work_m = re.search(r'(?:Work|Project Name)\s+(.+)', txt)
        client_m = re.search(r'Client\s+(.+)', txt)
        cat_m = re.search(r'(?:Category|Work Category)\s+(.+)', txt)
        val_m = re.search(r'(?:Executed Value|Contract Value)\s+(.+)', txt)
        comp_m = re.search(r'(?:Completion Date|Completion)\s+(.+)', txt)
        lead_m = re.search(r'(?:Project Lead|Project Manager)\s+(.+)', txt)
        cref_m = re.search(r'Client Certificate Ref\s+(.+)', txt)
        iref_m = re.search(r'Internal Ref:\s*(\S+)', txt)
        
        work_raw = work_m.group(1).strip() if work_m else ""
        client_raw = client_m.group(1).strip() if client_m else ""
        cat_raw = cat_m.group(1).strip() if cat_m else ""
        val_raw = val_m.group(1).strip() if val_m else ""
        comp_raw = comp_m.group(1).strip() if comp_m else ""
        lead_raw = lead_m.group(1).strip() if lead_m else ""
        cref_raw = cref_m.group(1).strip() if cref_m else ""
        iref_raw = iref_m.group(1).strip() if iref_m else ""
        
        work_name = normalize_text(work_raw)
        client_name = clean_client_name(client_raw)
        category = clean_category(cat_raw)
        value_inr = parse_money(val_raw)
        completion_date = parse_date(comp_raw)
        lead_engineer = normalize_text(lead_raw)
        pkg_no = extract_package_number(work_name)
        state = extract_state(work_name)
        
        doc_id = os.path.splitext(os.path.basename(f))[0]
        
        # Check corresponding client completion certificate for exact unrounded value
        cc_doc_id = doc_id.replace('DOC-CCC-', 'DOC-CC-')
        cc_path = os.path.join('documents', 'completion_certificate', f'{cc_doc_id}.pdf')
        if os.path.exists(cc_path):
            cc_doc = fitz.open(cc_path)
            cc_txt = '\n'.join([p.get_text() for p in cc_doc])
            exact_val_m = re.search(r'Contract Value\s*(?:\(Original\))?\s*\n?\s*(INR\s*[\d\.,\s/-]+|Rs\.?\s*[\d\.,\s/-]+)', cc_txt, re.IGNORECASE)
            if not exact_val_m:
                exact_val_m = re.search(r'Executed Value\s*\n?\s*(INR\s*[\d\.,\s/-]+|Rs\.?\s*[\d\.,\s/-]+)', cc_txt, re.IGNORECASE)
            if not exact_val_m:
                exact_val_m = re.search(r'(?:INR|Rs\.?)\s*([\d\.,\s]+/-)', cc_txt)
            if exact_val_m:
                cc_val = parse_money(exact_val_m.group(1))
                if cc_val > 0 and abs(cc_val - value_inr) < 1000:
                    value_inr = cc_val
        
        projects.append({
            'doc_id': doc_id,
            'project_name': work_name,
            'client_name': client_name,
            'category': category,
            'raw_category': cat_raw.strip(),
            'value_inr': value_inr,
            'completion_date': completion_date,
            'lead_engineer': lead_engineer,
            'package_no': pkg_no,
            'state': state,
            'client_cert_ref': cref_raw,
            'internal_ref': iref_raw,
            'file_path': f
        })
        
    return projects

if __name__ == '__main__':
    projs = extract_projects()
    print(f'Extracted {len(projs)} projects successfully.')
    print('Sample project:', projs[0])
