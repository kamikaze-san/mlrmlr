import os
import re
import fitz
from typing import List, Dict, Any

def extract_reference_letters(projects: List[Dict[str, Any]], ref_files: List[str]) -> List[Dict[str, Any]]:
    pkg_to_proj = {p['package_no'].lower(): p for p in projects if p.get('package_no')}
    ref_letters = []
    
    for f in ref_files:
        doc = fitz.open(f)
        txt = doc[0].get_text()
        
        doc_id = os.path.splitext(os.path.basename(f))[0]
        
        # Match project by package number
        pkg_m = re.search(r'Pkg-?(\d+)', txt, re.IGNORECASE)
        matched_pkg = f"Pkg-{pkg_m.group(1)}" if pkg_m else ""
        matched_proj = pkg_to_proj.get(matched_pkg.lower())
        
        # Client name from letter header
        lines = [line.strip() for line in txt.split('\n') if line.strip()]
        client_name = lines[0] if lines else ""
        
        ref_letters.append({
            'doc_id': doc_id,
            'client_name': client_name,
            'package_no': matched_pkg,
            'matched_project_doc_id': matched_proj['doc_id'] if matched_proj else None,
            'matched_project_name': matched_proj['project_name'] if matched_proj else None,
            'file_path': f
        })
        
    return ref_letters

if __name__ == '__main__':
    import sys
    from solution.extractors.discover import discover_and_classify
    from solution.extractors.extract_projects import extract_projects
    root = sys.argv[1] if len(sys.argv) > 1 else 'documents'
    grouped = discover_and_classify(root)
    projs = extract_projects(grouped.get('completion_certificate_any', []))
    refs = extract_reference_letters(projs, grouped.get('reference_letter', []))
    print(f'Extracted {len(refs)} reference letters.')
    matched_count = sum(1 for r in refs if r['matched_project_doc_id'] is not None)
    print(f'Matched to projects: {matched_count}/{len(refs)}')
