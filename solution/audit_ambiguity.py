import json
import sqlite3
import pandas as pd
import sys, os
import re

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.entity_linker import EntityLinker, CLIENT_ALIASES

linker = EntityLinker('solution/db/knowledge_base.db')

with open('questions.json') as f:
    qs = json.load(f)['questions']

print("=== CHECKING BARE / AMBIGUOUS CLIENT AND ENGINEER RESOLUTION ===")

ambiguous_matches = []
for q in qs:
    qid = q['qid']
    qtxt = q['question']
    txt_l = qtxt.lower()
    
    # Check if 'public works department' or 'pwd' or 'phed' or bare first names occur
    ent = linker.link(qtxt)
    client = ent.get('client_name')
    eng = ent.get('engineer')
    
    # Check if multiple clients could match
    matched_clients = [c for c in linker.clients if c.lower() in txt_l]
    
    # Check if state disambiguation could point to a different client
    states_in_q = [s for s in ['gujarat', 'maharashtra', 'west bengal', 'odisha', 'jharkhand', 'delhi', 'uttar pradesh', 'madhya pradesh', 'rajasthan'] if s in txt_l]
    
    if client:
        # Check if the resolved client state conflicts with state in question
        if 'public works department' in txt_l or 'phed' in txt_l or 'jal nigam' in txt_l:
            client_l = client.lower()
            mismatched_states = [s for s in states_in_q if s in client_l]
            if states_in_q and not mismatched_states and any(s in c.lower() for s in states_in_q for c in linker.clients if any(w in c.lower() for w in ['public works', 'phed', 'jal nigam'])):
                ambiguous_matches.append((qid, client, states_in_q, qtxt))

print(f"Total potential state/client mismatches found: {len(ambiguous_matches)}")
for m in ambiguous_matches:
    print(f"[{m[0]}] Resolved Client: {m[1]} | States in Q: {m[2]}")
    print(f"  Q: {m[3]}\n")
