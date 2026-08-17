import sys, os
sys.path.insert(0, os.path.abspath('.'))
import json
from solution.solver.llm_engine import LLMEngine

engine = LLMEngine()

# Test 1: Acronym grounding ("NEDA") + multi-hop aggregation
q1 = "Could you calculate the total value of all completed assignments Rajesh Rao has delivered for NEDA, referencing his Chartered Engineer certification (IEI-400018) and the Ring Road — West Bengal Pkg-128 project as the reference point?"
print("\n--- Test 1 ---")
print("Q:", q1)
ans1 = engine.solve(q1, "money")
print("Answer 1:", ans1, "(Expected: 2942400000)")

# Test 2: Temporal chain with date math
q2 = "Could you please calculate the combined value of the works Asha Nair led that were completed after her PMP certification date of March 10, 2021?"
print("\n--- Test 2 ---")
print("Q:", q2)
ans2 = engine.solve(q2, "money")
print("Answer 2:", ans2, "(Expected: 244200000)")

# Test 3: Unseen arbitrary question
q3 = "What is the total outstanding balance across all clients in the database?"
print("\n--- Test 3 ---")
print("Q:", q3)
ans3 = engine.solve(q3, "money")
print("Answer 3:", ans3)
