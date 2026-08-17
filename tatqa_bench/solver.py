"""TAT-QA adapter: same architecture bet as the hackathon pipeline -- the
LLM's job is narrowly to identify which spans/numbers in the given table and
paragraphs answer the question; any arithmetic (subtraction, percent change,
sum, average) is computed in Python, not trusted to the model.

    python solver.py --split dev --model qwen3.5:4b --limit 20
"""
import argparse
import json
import os
import re
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(HERE, '..', 'tat-qa', 'dataset_raw')

DEFAULT_BASE_URL = 'http://localhost:11434/v1'
DEFAULT_MODEL = 'qwen3.5:4b'

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "tatqa_answer",
        "schema": {
            "type": "object",
            "properties": {
                "answer_type": {"type": "string", "enum": ["span", "multi-span", "count", "arithmetic"]},
                "spans": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "For span/multi-span: the exact text span(s) copied verbatim from the table or paragraphs that answer the question. For count: the items being counted (its length is the count).",
                },
                "operands": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "For arithmetic only: the raw numeric value(s) from the table/text needed to compute the answer, in the order the operation needs them.",
                },
                "operation": {
                    "type": "string",
                    "enum": ["none", "subtract", "percent_change", "sum", "average", "divide", "multiply"],
                    "description": "For arithmetic only. percent_change = (operands[0]-operands[1])/operands[1]*100.",
                },
                "scale": {
                    "type": "string",
                    "enum": ["", "thousand", "million", "billion", "percent"],
                    "description": "Unit scale of the answer, if the question/table implies one beyond the raw number.",
                },
            },
            "required": ["answer_type", "spans", "operands", "operation", "scale"],
        },
    },
}

PROMPT = """You are answering a question about ONE financial table and its surrounding text, taken from a company filing.

Table:
{table}

Relevant text:
{paragraphs}

Question: {question}

Identify the answer using ONLY the fields in the schema:
- If the question asks to copy/identify text or a single value stated directly (answer_type "span") or several such items (answer_type "multi-span"), put the exact text as it appears in `spans`.
- If the question asks "how many" of something, use answer_type "count" and list the counted items in `spans`.
- If the question requires a calculation (change, percentage change, sum, average, difference, ratio), use answer_type "arithmetic": put the raw numeric values needed in `operands` (in the order the operation needs), and set `operation`. Do NOT do the arithmetic yourself -- just supply the numbers and the operation.
- Set `scale` to the unit implied (thousand/million/billion/percent) if relevant, else "".
"""


def format_table(table):
    rows = table.get('table', table) if isinstance(table, dict) else table
    lines = []
    for row in rows:
        lines.append(' | '.join(str(c) for c in row))
    return '\n'.join(lines)


def format_paragraphs(paragraphs):
    ordered = sorted(paragraphs, key=lambda p: p.get('order', 0))
    return '\n'.join(p['text'] for p in ordered)


def compute_arithmetic(operands, operation):
    if not operands:
        return None
    try:
        if operation == 'subtract' and len(operands) >= 2:
            return operands[0] - operands[1]
        if operation == 'percent_change' and len(operands) >= 2 and operands[1] != 0:
            return round((operands[0] - operands[1]) / operands[1] * 100, 2)
        if operation == 'sum':
            return sum(operands)
        if operation == 'average':
            return round(sum(operands) / len(operands), 2)
        if operation == 'divide' and len(operands) >= 2 and operands[1] != 0:
            return round(operands[0] / operands[1], 4)
        if operation == 'multiply':
            r = 1
            for o in operands:
                r *= o
            return r
    except (ZeroDivisionError, TypeError):
        return None
    return operands[0] if operands else None


def call_llm(prompt, base_url, model, timeout=60):
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "response_format": SCHEMA,
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res = json.loads(resp.read().decode('utf-8'))
    content = res['choices'][0]['message'].get('content')
    if not content:
        return None
    return json.loads(content)


def solve_question(doc, question, base_url, model):
    table_txt = format_table(doc['table'])
    para_txt = format_paragraphs(doc['paragraphs'])
    prompt = PROMPT.format(table=table_txt, paragraphs=para_txt, question=question['question'])
    try:
        fields = call_llm(prompt, base_url, model)
    except Exception as e:
        return None, str(e)
    if not fields:
        return None, 'empty response'

    atype = fields.get('answer_type')
    scale = fields.get('scale') or ''
    if atype == 'count':
        spans = fields.get('spans') or []
        return [str(len(spans))], scale
    if atype in ('span', 'multi-span'):
        spans = fields.get('spans') or []
        return spans, scale
    if atype == 'arithmetic':
        result = compute_arithmetic(fields.get('operands') or [], fields.get('operation') or 'none')
        if result is None:
            return None, 'arithmetic computation failed'
        return [result], scale
    return None, f'unrecognized answer_type {atype}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--split', default='dev', choices=['dev', 'test'])
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--base-url', default=DEFAULT_BASE_URL)
    ap.add_argument('--limit', type=int, default=None, help='Only answer the first N questions (for smoke testing)')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    path = os.path.join(DATASET_DIR, f'tatqa_dataset_{args.split}.json')
    with open(path, encoding='utf-8') as f:
        docs = json.load(f)

    out_path = args.out or os.path.join(HERE, f'predictions_{args.split}.json')

    predictions = {}
    n = 0
    t0 = time.time()
    errors = 0
    for doc in docs:
        for q in doc['questions']:
            if args.limit and n >= args.limit:
                break
            uid = q['uid']
            answer, scale_or_err = solve_question(doc, q, args.base_url, args.model)
            if answer is None:
                errors += 1
                print(f'[{n+1}] ERROR {uid}: {scale_or_err}', flush=True)
                predictions[uid] = [[''], '']
            else:
                predictions[uid] = [answer, scale_or_err]
                print(f'[{n+1}] {uid}: {answer} ({scale_or_err})', flush=True)
            n += 1
        if args.limit and n >= args.limit:
            break

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(predictions, f, indent=2)

    elapsed = time.time() - t0
    print(f'\nAnswered {n} questions in {elapsed:.1f}s ({errors} errors). Wrote {out_path}')


if __name__ == '__main__':
    main()
