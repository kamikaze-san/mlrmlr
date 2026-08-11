#!/usr/bin/env python3
"""
evaluate.py — score a submission against the answer key.

Every answer is a number, so scoring is mechanical and a near-miss earns proportional credit:

    score = max(0, 1 - |your answer - correct| / correct)

Exact answer scores 1.0. A 5% error scores 0.95. A 50% error scores 0.50. An answer that is off by
100% or more scores 0. There are no bands and no thresholds — the closer you are, the more you score.

Submission format — CSV, one row per question, with a header:

    question_id,answer
    HV-IC-0001,2942400000
    HV-IC-0002,1516600000

Answers are plain numbers: rupees (no units, no commas, no symbols), a count, a percentage out of
100, or a number of days. Each question states which. A question you do not answer scores 0, and a
wrong answer costs nothing extra — so answer everything.

Usage:
    python evaluate.py --self-test
    python evaluate.py --submission my_answers.csv --questions hidden_set_v1.0_questions.json
"""
import argparse, collections, csv, json, sys


def score_one(gold, got):
    """Proportional credit for closeness. 0.0 for a missing or unparseable answer."""
    if got is None:
        return 0.0
    try:
        gold, got = float(gold), float(got)
    except (TypeError, ValueError):
        return 0.0
    if gold == 0:
        return 1.0 if got == 0 else 0.0
    return max(0.0, 1.0 - abs(got - gold) / abs(gold))


def read_submission(path):
    """CSV with a `question_id,answer` header. Tolerates extra columns and stray whitespace."""
    out = {}
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return out
    head = [h.strip().lower() for h in rows[0]]
    start = 1 if ("question_id" in head or "qid" in head) else 0
    qi = head.index("question_id") if "question_id" in head else (
         head.index("qid") if "qid" in head else 0)
    ai = head.index("answer") if "answer" in head else 1
    for row in rows[start:]:
        if len(row) <= max(qi, ai) or not row[qi].strip():
            continue
        raw = row[ai].strip().replace(",", "").replace("₹", "").replace("INR", "").strip()
        try:
            out[row[qi].strip()] = float(raw)
        except ValueError:
            out[row[qi].strip()] = None
    return out


def evaluate(questions, submitted):
    """Score a submission. Questions marked `scored: false` are skipped entirely.

    Those are questions whose filtering property is not recoverable from the shipped documents, so
    no correct reading reaches the answer. Participants may answer them; they simply do not count.
    """
    rows, by_shape = [], collections.defaultdict(lambda: [0.0, 0])
    for q in questions:
        if q.get("scored") is False:
            continue
        gold = q.get("answer", q.get("answer_gold"))
        s = score_one(gold, submitted.get(q["qid"]))
        rows.append({"qid": q["qid"], "shape": q.get("shape"), "gold": gold,
                     "answered": submitted.get(q["qid"]), "score": s})
        by_shape[q.get("shape", "?")][0] += s
        by_shape[q.get("shape", "?")][1] += 1
    return rows, by_shape, sum(r["score"] for r in rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", help="CSV: question_id,answer")
    ap.add_argument("--questions", default="hidden_set_v1.0_answers.json",
                    help="answer key (organisers) or sample_questions.json (self-check)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--per-question", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        cases = [
            (1_000_000_000, 1_000_000_000, 1.00),   # exact
            (1_000_000_000, 1_050_000_000, 0.95),   # 5% high
            (1_000_000_000,   950_000_000, 0.95),   # 5% low
            (1_000_000_000, 1_500_000_000, 0.50),   # 50% out
            (1_000_000_000, 2_000_000_000, 0.00),   # 100% out
            (1_000_000_000, 5_000_000_000, 0.00),   # far out, never negative
            (100, 99, 0.99),
            (5, 5, 1.00),
            (5, 4, 0.80),
            (66.67, 66.67, 1.00),
            (66.67, 0.6667, 0.01),                  # fraction instead of percent: ~1% credit,
                                                    # not zero — the formula is continuous
            (1_000_000_000, None, 0.00),            # unanswered
            (1_000_000_000, "not a number", 0.00),
        ]
        bad = [(g, x, e, round(score_one(g, x), 4)) for g, x, e in cases
               if abs(score_one(g, x) - e) > 5e-3]
        for g, x, e, s in bad:
            print(f"  FAIL gold={g} answered={x} expected={e} got={s}")
        print(f"self-test: {len(cases)-len(bad)}/{len(cases)} correct")
        return sys.exit(1 if bad else 0)

    key = json.load(open(a.questions))
    questions = key.get("answers") or key.get("questions")
    if not a.submission:
        sys.exit("--submission is required (or use --self-test)")
    rows, by_shape, total = evaluate(questions, read_submission(a.submission))

    if a.per_question:
        for r in rows:
            print(f"  {r['score']:.3f}  {r['qid']:12s} gold={r['gold']}  answered={r['answered']}")
        print()
    if any(r["shape"] for r in rows):
        print(f"{'shape':26s} {'score':>8s}  {'n':>3s}")
        for shape, (s, n) in sorted(by_shape.items(), key=lambda kv: -kv[1][0] / max(kv[1][1], 1)):
            print(f"{shape:26s} {s:8.2f}  {n:3d}   {s/max(n,1):.1%}")
    answered = sum(1 for r in rows if r["answered"] is not None)
    print(f"\nanswered {answered}/{len(rows)}")
    print(f"TOTAL {total:.2f} / {len(rows)}  =  {total/max(len(rows),1):.2%}")


if __name__ == "__main__":
    main()
