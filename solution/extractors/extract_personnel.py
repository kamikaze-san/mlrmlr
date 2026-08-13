import os
import re
import fitz
from typing import List, Dict, Any, Tuple
from solution.extractors.money_parser import parse_date

def extract_personnel_certs(files: List[str]) -> List[Dict[str, Any]]:
    certs = []
    
    for f in files:
        doc = fitz.open(f)
        txt = doc[0].get_text()
        
        name, emp_id, cred_type, cred_id, issue_date, valid_through = None, None, None, None, None, None
        
        # Credential Type
        if 'SIX SIGMA' in txt.upper():
            cred_type = 'Six Sigma Black Belt'
        elif 'PMP' in txt.upper():
            cred_type = 'PMP'
        else:
            cred_type = 'Other'
            
        # Format 1
        if 'This is to certify that' in txt:
            m_name = re.search(r'This is to certify that\s*\n\s*(.+)', txt)
            if m_name: name = m_name.group(1).strip()
            m_emp = re.search(r'Employee ID:\s*(EMP-\d+)', txt)
            if m_emp: emp_id = m_emp.group(1).strip()
            m_cid = re.search(r'Credential ID:\s*(\S+)', txt)
            if m_cid: cred_id = m_cid.group(1).strip()
            m_iss = re.search(r'Issued:\s*(\S+)', txt)
            if m_iss: issue_date = parse_date(m_iss.group(1).strip())
            m_val = re.search(r'Valid Through\s*\n?\s*(.+)', txt)
            if m_val: valid_through = parse_date(m_val.group(1).strip())
        
        # Format 2
        elif 'This credential is conferred upon' in txt:
            m_name = re.search(r'This credential is conferred upon\s*\n\s*(.+)', txt)
            if m_name: name = m_name.group(1).strip()
            m_cid = re.search(r'Certificate No\.\s*\n\s*(\S+)', txt)
            if m_cid: cred_id = m_cid.group(1).strip()
            m_iss = re.search(r'Issued\s*\n\s*(.+)', txt)
            if m_iss: issue_date = parse_date(m_iss.group(1).strip())
            m_val = re.search(r'Valid Through\s*\n\s*(.+)', txt)
            if m_val: valid_through = parse_date(m_val.group(1).strip())
            
        doc_id = os.path.splitext(os.path.basename(f))[0]
        certs.append({
            'doc_id': doc_id,
            'name': name,
            'emp_id': emp_id,
            'cred_type': cred_type,
            'cred_id': cred_id,
            'issue_date': issue_date,
            'valid_through': valid_through,
            'file_path': f
        })
        
    return certs

def extract_cvs(files: List[str]) -> List[Dict[str, Any]]:
    cvs = []
    
    for f in files:
        doc = fitz.open(f)
        txt = doc[0].get_text()
        name_m = re.search(r'Name\s+(.+)', txt)
        emp_m = re.search(r'Employee ID\s+(EMP-\d+)', txt)
        desig_m = re.search(r'Designation\s+(.+)', txt)
        bu_m = re.search(r'Business Unit\s+(.+)', txt)
        exp_m = re.search(r'Total Experience\s+(.+)', txt)
        qual_m = re.search(r'Qualification\s+(.+)', txt)
        doj_m = re.search(r'Date of Joining\s+(.+)', txt)
        
        doc_id = os.path.splitext(os.path.basename(f))[0]
        cvs.append({
            'doc_id': doc_id,
            'name': name_m.group(1).strip() if name_m else "",
            'emp_id': emp_m.group(1).strip() if emp_m else "",
            'designation': desig_m.group(1).strip() if desig_m else "",
            'business_unit': bu_m.group(1).strip() if bu_m else "",
            'experience_years': exp_m.group(1).strip() if exp_m else "",
            'qualification': qual_m.group(1).strip() if qual_m else "",
            'date_of_joining': parse_date(doj_m.group(1).strip()) if doj_m else "",
            'file_path': f
        })
        
    return cvs

if __name__ == '__main__':
    import sys
    from solution.extractors.discover import discover_and_classify
    root = sys.argv[1] if len(sys.argv) > 1 else 'documents'
    grouped = discover_and_classify(root)
    certs = extract_personnel_certs(grouped.get('personnel_certificate', []))
    cvs = extract_cvs(grouped.get('cv', []))
    print(f'Extracted {len(certs)} certs and {len(cvs)} CVs.')
