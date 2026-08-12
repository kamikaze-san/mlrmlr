import json
import sqlite3
import pandas as pd
import sys, os
import re

sys.path.insert(0, os.path.abspath('.'))
from solution.solver.question_parser import classify_question
from solution.solver.entity_linker import EntityLinker

with open('questions.json') as f:
    qs = json.load(f)['questions']

print("=== CHECKING QUESTIONS ASKING ABOUT 'NEGATIVE IF' OR 'DIRECTION' ===")
for q in qs:
    txt_l = q['question'].lower()
    if 'negative' in txt_l or 'lower' in txt_l or 'decrease' in txt_l or 'dips' in txt_l or 'drop' in txt_l or 'fall' in txt_l:
        s = classify_question(q['question'], q['answer_type'])
        print(f"[{q['qid']}] Shape: {s:20s}")
        print(f"  Q: {q['question']}\n")
