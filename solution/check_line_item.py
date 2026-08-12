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

print("=== CHECKING ALL QUESTIONS WITH 'LINE ITEM' ===")
for q in qs:
    if 'line item' in q['question'].lower():
        s = classify_question(q['question'], q['answer_type'])
        print(f"[{q['qid']}] Shape: {s:20s}")
        print(f"  Q: {q['question']}\n")
