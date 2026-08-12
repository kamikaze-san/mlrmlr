import json
import sqlite3
import re

with open('questions.json') as f:
    qs = json.load(f)['questions']

print("=== CHECKING QUESTION PATTERNS & INTENT TRAPS ===")

for q in qs:
    qid = q['qid']
    qtxt = q['question']
    atype = q['answer_type']
    txt = qtxt.lower()
    
    # Check threshold triggers
    if ('crore or higher' in txt or 'crore or more' in txt or 'crore mark' in txt or 'hitting' in txt or 'valued at' in txt or 'clearing the' in txt or 'exceeding' in txt) and atype == 'money':
        if 'gap' not in txt and 'variance' not in txt:
            # Check if threshold value can be parsed
            words = {'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'twenty-one': 21, 'twenty-two': 22, 'twenty-three': 23, 'twenty-four': 24, 'twenty-five': 25, 'twenty-six': 26, 'twenty-seven': 27, 'twenty-eight': 28, 'twenty-nine': 29, 'thirty': 30, 'thirty-one': 31, 'thirty-two': 32, 'thirty-three': 33, 'thirty-four': 34, 'thirty-five': 35}
            found_num = False
            for w in words:
                if w in txt:
                    found_num = True
            if re.search(r'\b\d+\s*crore', txt):
                found_num = True
            print(f"[{qid}] Threshold Candidate: \"{qtxt}\" (Found num: {found_num})")

