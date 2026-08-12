"""
Cross-check: for each question that mentions a state-specific entity (Rajasthan / UP / WB / Jharkhand),
confirm our linked client contains the same state keyword as the question.
"""
import json
import re
import sys
sys.path.insert(0, '.')
from solution.solver.entity_linker import EntityLinker
from solution.solver.question_parser import classify_question

with open('questions.json') as f:
    qs = {q['qid']: q for q in json.load(f)['questions']}

linker = EntityLinker('solution/db/knowledge_base.db')

STATE_KEYWORDS = ['rajasthan', 'uttar pradesh', 'west bengal', 'jharkhand', 'gujarat',
                  'odisha', 'maharashtra', 'madhya pradesh', 'tamil nadu', 'delhi']

mismatches = []
for qid, q in qs.items():
    qtxt = q['question']
    qtxt_l = qtxt.lower()
    ent = linker.link(qtxt)
    linked_client = ent.get('client_name', '') or ''
    linked_l = linked_client.lower()
    
    # Find state mentioned in question
    q_states = [s for s in STATE_KEYWORDS if s in qtxt_l]
    c_states = [s for s in STATE_KEYWORDS if s in linked_l]
    
    # If question mentions a specific state but linked client has a different state
    if q_states and c_states and set(q_states) != set(c_states):
        # Only flag if the client name pattern matches (same org type, different state)
        mismatches.append({
            'qid': qid,
            'shape': classify_question(qtxt, q['answer_type']),
            'q_states': q_states,
            'c_states': c_states,
            'linked': linked_client,
            'q': qtxt[:120]
        })

print(f"State mismatch (question state != linked client state): {len(mismatches)}")
for m in mismatches:
    print(f"\n[{m['qid']}] ({m['shape']})")
    print(f"  Question mentions: {m['q_states']}")
    print(f"  Linked client state: {m['c_states']}  ->  {m['linked']}")
    print(f"  Q: {m['q']}")
