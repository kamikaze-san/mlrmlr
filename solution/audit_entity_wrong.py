"""
Check for subtle entity linking issues - where a client IS resolved
but might be resolved to the WRONG client name.
Also check question shape misclassifications.
"""
import json
import sqlite3
import re
import sys, os
sys.path.insert(0, '.')
from solution.solver.entity_linker import EntityLinker
from solution.solver.question_parser import classify_question

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()
all_clients = {r[0].lower(): r[0] for r in cur.execute("SELECT client_name FROM clients").fetchall()}
linker = EntityLinker('solution/db/knowledge_base.db')

# Look for questions where the question text mentions a client name
# but we linked to a different one (fuzzy match gone wrong)
print("=== CHECKING FOR WRONG ENTITY LINKS (linked to wrong client) ===\n")

# Extract client keywords from question text and verify they match the linked client
client_keywords = {
    'meridian': 'Meridian Constructors & Co.',
    'peninsular petroleum': 'Peninsular Petroleum Corporation',
    'arunodaya': 'Arunodaya Infrastructure',
    'mega infrastructure': 'Mega Infrastructure Authority',
    'trishakti': 'Trishakti Power Generation Corporation',
    'suvarna': 'Suvarna Projects Limited',
    'subarnarekha': 'Subarnarekha Valley Corporation',
    'national expressway': 'National Expressway Development Authority',
    'lakshya': 'Lakshya Engineering & Construction',
    'mahanadi': 'Mahanadi Steel Corporation',
    'jal nigam, jharkhand': 'Jal Nigam, Jharkhand',
    'jal nigam, uttar pradesh': 'Jal Nigam, Uttar Pradesh',
    'jal nigam up': 'Jal Nigam, Uttar Pradesh',
    'jal nigam jharkhand': 'Jal Nigam, Jharkhand',
    'irrigation & waterways': 'Irrigation & Waterways Dept, Govt of West Bengal',
    'irrigation waterways.*rajasthan': 'Irrigation & Waterways Dept, Govt of Rajasthan',
    'irrigation waterways.*west bengal': 'Irrigation & Waterways Dept, Govt of West Bengal',
    'irrigation waterways.*up': 'Irrigation & Waterways Dept, Govt of Uttar Pradesh',
    'jharkhand municipal': 'Jharkhand Municipal Corporation',
    'maharashtra municipal': 'Maharashtra Municipal Corporation',
    'tamil nadu municipal': 'Tamil Nadu Municipal Corporation',
    'central works': 'Central Works & Buildings Bureau',
    'national special': 'National Special Projects Office',
    'maharashtra pwd': 'Public Works Department, Govt of Maharashtra',
    'gujarat pw': 'Public Works Department, Govt of Gujarat',
    'phed.*odisha': 'Public Health Engineering Dept, Odisha',
    'phed.*gujarat': 'Public Health Engineering Dept, Gujarat',
    'phed.*west bengal': 'Public Health Engineering Dept, West Bengal',
}

mismatches = []
for qid, q in qs.items():
    qtxt = q['question']
    qtxt_l = qtxt.lower()
    atype = q['answer_type']
    shape = classify_question(qtxt, atype)
    ent = linker.link(qtxt)
    linked_client = ent.get('client_name')
    
    if not linked_client:
        continue
    
    for kw, expected_client in client_keywords.items():
        if re.search(kw, qtxt_l) and linked_client != expected_client:
            mismatches.append({
                'qid': qid, 'shape': shape,
                'keyword_matched': kw,
                'expected': expected_client,
                'got': linked_client,
                'q': qtxt[:110]
            })
            break

print(f"Potential wrong entity links: {len(mismatches)}")
for m in mismatches:
    print(f"\n[{m['qid']}] ({m['shape']})")
    print(f"  Keyword: '{m['keyword_matched']}'")
    print(f"  Expected client: {m['expected']}")
    print(f"  Got:             {m['got']}")
    print(f"  Q: {m['q']}")

# Also check for shape misclassification on the tricky question types
print("\n\n=== CHECKING QUESTION SHAPE CLASSIFICATION ===")
print("Scanning for questions that might be misclassified...\n")

shape_counts = {}
for qid, q in qs.items():
    s = classify_question(q['question'], q['answer_type'])
    shape_counts[s] = shape_counts.get(s, 0) + 1

print("Shape distribution:")
for s, c in sorted(shape_counts.items(), key=lambda x: -x[1]):
    print(f"  {s:30s} : {c:3d}")
