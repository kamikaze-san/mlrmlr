import os
import re
import fitz
from typing import List, Dict, Any, Optional
from solution.extractors.money_parser import parse_money, parse_date
from solution.extractors.llm_extractor import extract_fields_llm

def normalize_text(s: str) -> str:
    if not s:
        return ""
    # Replace unicode replacement char or em-dashes with standard em-dash
    s = s.replace('�', '—').replace('–', '—').replace('—', '—')
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

def extract_package_number(text: str) -> str:
    """Extracts package identifier e.g. 'Pkg-145', 'Pkg-51'."""
    m = re.search(r'Pkg-?(\d+)', text, re.IGNORECASE)
    if m:
        return f"Pkg-{m.group(1)}"
    return ""

def extract_state(text: str) -> str:
    states = [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
        'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
        'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
        'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi'
    ]
    for s in states:
        if s.lower() in text.lower():
            return s
    return ""

def _parse_completion_doc(f: str) -> Optional[Dict[str, Any]]:
    """Parse one completion-certificate-type PDF, whichever of the known
    template variants it happens to be. Different issuing authorities use
    different field labels for the same information (e.g. 'Work' vs 'Name
    of Work', 'Category' vs 'Nature / Category'), so each field is matched
    against every label variant seen in this document estate rather than
    assuming one fixed layout."""
    doc = fitz.open(f)
    pages_txt = [p.get_text() for p in doc]
    txt = pages_txt[0]
    full_txt = '\n'.join(pages_txt)

    first_lines = [l.strip() for l in txt.split('\n') if l.strip()]
    issuing_authority = first_lines[0] if first_lines else ""

    work_m = re.search(r'(?:Work|Project Name|Name of Work)\s*\n?\s*(.+)', txt)
    cat_m = re.search(r'(?:Category|Work Category|Nature\s*/\s*Category)\s*\n?\s*(.+)', txt)
    val_m = re.search(r'(?:Executed Value|Contract Value)\s*(?:\(Original\))?\s*\n?\s*(.+)', txt)
    comp_m = re.search(r'(?:Completion Date|Completion)\s*\n?\s*(.+)', txt)
    lead_m = re.search(r"(?:Project Lead|Project Manager|Contractor'?s Project Manager)\s*\n?\s*(.+)", txt)
    cref_m = re.search(r'Client Certificate Ref\s*\n?\s*(.+)', txt)
    iref_m = re.search(r'Internal Ref:\s*(\S+)', txt)

    # Client: an explicit "Client" field if the template has one, otherwise
    # the issuing authority named at the top of the letterhead.
    client_m = re.search(r'^Client\s*\n?\s*(.+)', txt, re.MULTILINE)
    client_raw = client_m.group(1).strip() if client_m else issuing_authority

    if work_m and val_m:
        work_raw = work_m.group(1).strip()
        cat_raw = cat_m.group(1).strip() if cat_m else ""
        val_raw = val_m.group(1).strip()
        comp_raw = comp_m.group(1).strip() if comp_m else ""
        lead_raw = lead_m.group(1).strip() if lead_m else ""
        cref_raw = cref_m.group(1).strip() if cref_m else ""
        iref_raw = iref_m.group(1).strip() if iref_m else ""
    else:
        # Third template variant: value/dates embedded in narrative prose
        # rather than labeled fields, e.g. "...the work of 'Road Widening
        # - Pkg-21' (roads highways), ... completed ... on April 22, 2011
        # at a gross executed value of INR 19,32,99,999/- ... supervised
        # on the contractor's side by Neha Chopra."
        narrative_m = re.search(r"the work of\s+[‘’“”'\"�]([^‘’“”'\"�]+)[‘’“”'\"�]\s*\(([^)]+)\)", full_txt)
        work_raw = narrative_m.group(1).strip() if narrative_m else ""
        cat_raw = narrative_m.group(2).strip() if narrative_m else ""

        nval_m = re.search(r'(?:gross executed value of|executed value of)\s+([A-Za-z₹\.]*\s*[\d,\.]+\s*/-?)', full_txt)
        val_raw = nval_m.group(1).strip() if nval_m else ""

        ndate_m = re.search(r'completed(?: in all respects)? on\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2})', full_txt)
        comp_raw = ndate_m.group(1).strip() if ndate_m else ""

        nlead_m = re.search(r"supervised on the contractor'?s side by\s+([A-Za-z\s]+?)\.", full_txt)
        lead_raw = nlead_m.group(1).strip() if nlead_m else ""

        cref_raw = ""
        iref_raw = ""
        if not client_m:
            client_raw = issuing_authority

    if not (work_raw and val_raw):
        # Neither known template matched -- a layout we haven't seen
        # before. Last resort: ask the provided LLM endpoint to identify
        # the same fields from the raw text. Never a hard dependency --
        # returns None if the endpoint isn't configured/reachable, in
        # which case this document is skipped exactly as before.
        llm_fields = extract_fields_llm(full_txt)
        if llm_fields:
            work_raw = llm_fields.get('project_name', '')
            cat_raw = llm_fields.get('category_raw', '')
            val_raw = llm_fields.get('value_raw', '')
            comp_raw = llm_fields.get('completion_date_raw', '')
            lead_raw = llm_fields.get('lead_engineer', '')
            cref_raw = ""
            iref_raw = ""
            if not client_m and llm_fields.get('client_name'):
                client_raw = llm_fields['client_name']

    if not (work_raw and val_raw):
        return None

    work_name = normalize_text(work_raw)
    value_inr = parse_money(val_raw)
    pkg_no = extract_package_number(work_name) or extract_package_number(full_txt)

    if not pkg_no or value_inr <= 0:
        return None

    # A more exact, unrounded value sometimes appears spelled out further
    # in the same document (multi-page certs); prefer it if it's close to
    # the summary value already found, as a sanity check against a mismatch.
    exact_val_m = re.search(r'Contract Value\s*(?:\(Original\))?\s*\n?\s*(INR\s*[\d\.,\s/-]+|Rs\.?\s*[\d\.,\s/-]+)', full_txt, re.IGNORECASE)
    if not exact_val_m:
        exact_val_m = re.search(r'Executed Value\s*\n?\s*(INR\s*[\d\.,\s/-]+|Rs\.?\s*[\d\.,\s/-]+)', full_txt, re.IGNORECASE)
    if exact_val_m:
        alt_val = parse_money(exact_val_m.group(1))
        if alt_val > 0 and abs(alt_val - value_inr) < 1000 and alt_val != value_inr:
            value_inr = alt_val

    doc_id = os.path.splitext(os.path.basename(f))[0]
    return {
        'doc_id': doc_id,
        'package_no': pkg_no,
        'project_name': work_name,
        'client_name': clean_client_name(client_raw),
        'category': clean_category(cat_raw),
        'raw_category': cat_raw,
        'value_inr': value_inr,
        'completion_date': parse_date(comp_raw),
        'lead_engineer': normalize_text(lead_raw),
        'state': extract_state(work_name),
        'client_cert_ref': cref_raw,
        'internal_ref': iref_raw,
        'file_path': f,
        # completeness score used to pick the better of two records for
        # the same package if this estate has more than one document per
        # project (as our local set does)
        '_completeness': sum(1 for v in (client_raw, cat_raw, comp_raw, lead_raw) if v),
    }

def extract_projects(files: List[str]) -> List[Dict[str, Any]]:
    """Parse every completion-certificate-type file given (any template
    variant), then merge records that describe the same project. Projects
    are matched across documents by package number rather than by a
    predictable filename relationship, since neither the folder layout nor
    the filenames of a new document estate are assumed to be known."""
    by_package: Dict[str, List[Dict[str, Any]]] = {}
    for f in files:
        rec = _parse_completion_doc(f)
        if rec is None:
            continue
        by_package.setdefault(rec['package_no'], []).append(rec)

    projects = []
    for pkg_no, recs in by_package.items():
        recs.sort(key=lambda r: -r['_completeness'])
        primary = recs[0]
        # Cross-check value against any other document for the same package
        for other in recs[1:]:
            if other['value_inr'] > 0 and abs(other['value_inr'] - primary['value_inr']) < 1000 \
                    and other['value_inr'] != primary['value_inr']:
                primary['value_inr'] = other['value_inr']
            if not primary['client_name'] and other['client_name']:
                primary['client_name'] = other['client_name']
        primary.pop('_completeness', None)
        projects.append(primary)

    return projects

if __name__ == '__main__':
    import sys
    from solution.extractors.discover import discover_and_classify
    root = sys.argv[1] if len(sys.argv) > 1 else 'documents'
    grouped = discover_and_classify(root)
    files = grouped.get('completion_certificate_any', [])
    projs = extract_projects(files)
    print(f'Extracted {len(projs)} projects successfully from {len(files)} source files.')
    if projs:
        print('Sample project:', projs[0])
