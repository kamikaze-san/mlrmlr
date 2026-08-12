import json, sqlite3, sys, os, re
from collections import Counter
import numpy as np

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker
from solution.solver.question_parser import classify_question
from solution.solver.query_engine import QueryEngine

with open('questions.json') as f:
    qs = json.load(f)['questions']

linker = EntityLinker('solution/db/knowledge_base.db')
engine = QueryEngine()
conn = sqlite3.connect('solution/db/knowledge_base.db')
cur = conn.cursor()

print("=" * 80)
print("COMPREHENSIVE AUDIT OF ALL 333 QUESTIONS")
print("=" * 80)

# Audit 1: Category Diff - verify extracted categories vs question text
print("\n--- AUDIT: CATEGORY DIFF (63 questions) ---")
cat_diff_issues = []
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'category_diff':
        qtxt = q['question']
        ent = linker.link(qtxt)
        client = ent.get('client_name')
        
        # Check all categories mentioned in question text
        CAT_MAP = {
            'bridges and flyovers': 'bridges flyovers',
            'large bridges': 'bridges flyovers',
            'bridges': 'bridges flyovers',
            'water supply': 'water treatment',
            'water treatment': 'water treatment',
            'roads and highways': 'roads highways',
            'roads maintenance': 'roads highways',
            'roads': 'roads highways',
            'small buildings': 'buildings',
            'buildings': 'buildings',
            'sewerage drainage': 'drainage',
            'sewerage': 'drainage',
            'expressways': 'expressways',
            'tunnels': 'tunnels',
            'industrial epc': 'industrial epc',
            'irrigation': 'irrigation',
            'drainage': 'drainage'
        }
        
        txt_l = qtxt.lower()
        found = []
        for cat in sorted(CAT_MAP.keys(), key=len, reverse=True):
            if cat in txt_l:
                start = txt_l.find(cat)
                if not any(start >= f_start and start < f_start + len(f_cat) for f_start, f_cat in found):
                    found.append((start, cat))
        found.sort()
        cats_found = [c for _, c in found]
        
        if len(cats_found) < 2:
            cat_diff_issues.append((q['qid'], f"Found only {len(cats_found)} categories: {cats_found}", qtxt))
        elif not client:
            cat_diff_issues.append((q['qid'], "Missing client", qtxt))

print(f"Category diff issues found: {len(cat_diff_issues)}")
for iss in cat_diff_issues:
    print(f"[{iss[0]}] {iss[1]}")
    print(f"  Q: {iss[2]}\n")

# Audit 2: Threshold Aggregate - verify parsed threshold amount
print("\n--- AUDIT: THRESHOLD AGGREGATE (21 questions) ---")
thresh_issues = []
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'threshold_aggregate':
        qtxt = q['question']
        ent = linker.link(qtxt)
        thresh = ent.get('threshold_inr')
        client = ent.get('client_name')
        if not thresh or thresh == 0:
            thresh_issues.append((q['qid'], "Missing threshold value", qtxt))
        if not client:
            thresh_issues.append((q['qid'], "Missing client", qtxt))

print(f"Threshold aggregate issues: {len(thresh_issues)}")
for iss in thresh_issues:
    print(f"[{iss[0]}] {iss[1]}")
    print(f"  Q: {iss[2]}\n")

# Audit 3: Exclusion Aggregate - verify parsed excluded category
print("\n--- AUDIT: EXCLUSION AGGREGATE (21 questions) ---")
excl_issues = []
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'exclusion_aggregate':
        qtxt = q['question']
        ent = linker.link(qtxt)
        excl = ent.get('excluded_category')
        client = ent.get('client_name')
        if not excl:
            excl_issues.append((q['qid'], "Missing excluded category", qtxt))
        if not client:
            excl_issues.append((q['qid'], "Missing client", qtxt))

print(f"Exclusion aggregate issues: {len(excl_issues)}")
for iss in excl_issues:
    print(f"[{iss[0]}] {iss[1]}")
    print(f"  Q: {iss[2]}\n")

# Audit 4: Rank Value - verify client has at least 2 projects
print("\n--- AUDIT: RANK VALUE (16 questions) ---")
rank_issues = []
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'rank_value':
        qtxt = q['question']
        ent = linker.link(qtxt)
        client = ent.get('client_name')
        if not client:
            rank_issues.append((q['qid'], "Missing client", qtxt))
        else:
            vals = cur.execute("SELECT value_inr FROM projects WHERE client_name = ? ORDER BY value_inr DESC", (client,)).fetchall()
            if len(vals) < 2:
                rank_issues.append((q['qid'], f"Client has only {len(vals)} projects", qtxt))

print(f"Rank value issues: {len(rank_issues)}")
for iss in rank_issues:
    print(f"[{iss[0]}] {iss[1]}")
    print(f"  Q: {iss[2]}\n")

# Audit 5: Temporal Chain - verify engineer cert issue date and post-cert projects
print("\n--- AUDIT: TEMPORAL CHAIN (21 questions) ---")
temp_issues = []
for q in qs:
    s = classify_question(q['question'], q['answer_type'])
    if s == 'temporal_chain':
        qtxt = q['question']
        ent = linker.link(qtxt)
        eng = ent.get('engineer')
        cert = ent.get('cert')
        client = ent.get('client_name')
        if not eng:
            temp_issues.append((q['qid'], "Missing engineer", qtxt))
        if not client:
            temp_issues.append((q['qid'], "Missing client", qtxt))

print(f"Temporal chain issues: {len(temp_issues)}")
for iss in temp_issues:
    print(f"[{iss[0]}] {iss[1]}")
    print(f"  Q: {iss[2]}\n")
