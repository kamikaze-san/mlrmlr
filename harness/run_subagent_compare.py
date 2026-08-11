"""
Token-cost comparison: does nudging the model to route multi-document
extraction through llm_query() (so full document text never permanently
enters its own growing conversation history) actually reduce total tokens,
without hurting accuracy?

llm_query() usage flows through the same lm_handler as the root loop, so
r.usage_summary already includes sub-call tokens -- a real win has to show up
in that same total, not be hidden off-book.

Baseline (direct reads, no subagent hint) is NOT re-run here -- we already
have real, clean numbers from prior live runs on disk, and re-spending on a
control we already trust would waste calls for no reason:
  HV-IC-0001: 12 calls, 102,925 in / 12,991 out tokens -- correct (2942400000)
  HV-IC-0003: 13 calls, 688,528 in / 15,086 out tokens -- correct (90.19)
    (this is the expensive one -- 6 works across 6 separate documents to
    aggregate for a collection %, the exact shape subagent mode targets)

This script runs the SAME two questions again with use_subagents=True and
prints usage + parsed answer so the two can be compared directly.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_test import make_rlm, ask  # noqa: E402

BASELINE = {
    "HV-IC-0001": {"calls": 12, "in": 102925, "out": 12991, "gold": 2942400000.0},
    "HV-IC-0003": {"calls": 13, "in": 688528, "out": 15086, "gold": 90.19},
}

Q_0001 = (
    "Starting with Rajesh Rao's Six Sigma Black Belt (6S-500161) work on the "
    "Material Handling Plant -- Uttar Pradesh Pkg-47 project with the "
    "National Expressway Development Authority, what is the combined value "
    "of every completed assignment he has done for that client right now to "
    "lock the submission?"
)

Q_0003 = (
    "Regarding the Ring Road -- West Bengal Pkg-128 assignment under PMP, "
    "with Amit Iyer as the assigned contact, could you please confirm the "
    "collection figure out of 100 for all amounts billed to the client?"
)


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY before running.")

    for label, question in [("HV-IC-0001", Q_0001), ("HV-IC-0003", Q_0003)]:
        rlm = make_rlm(persistent=True, use_subagents=True)
        answer = ask(rlm, f"{label} (subagent mode)", question)
        base = BASELINE[label]
        match = (answer is not None and abs(answer - base["gold"]) < 1e-6)
        print(f"\n--- {label} COMPARISON ---")
        print(f"  baseline (direct reads): {base['calls']} calls, "
              f"{base['in']} in / {base['out']} out tokens -> {base['gold']}")
        print(f"  subagent mode:           see USAGE above -> {answer}")
        print(f"  gold: {base['gold']}  match: {match}")


if __name__ == "__main__":
    main()
