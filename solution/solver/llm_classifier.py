import json
import os
import urllib.request

# The competition's provided LLM endpoint (OpenAI-compatible vLLM server).
# No external APIs or self-hosted generative models are permitted -- this is
# the only generative model this pipeline is allowed to call.
DEFAULT_MODEL = 'qwen3.6-35b-a3b-nvfp4'

MONEY_SHAPES = [
    'hop_aggregate', 'temporal_chain', 'exclusion_aggregate', 'category_diff',
    'threshold_aggregate', 'mean_vs_median', 'avg_work_size', 'rank_value',
    'annual_diff', 'outstanding_balance', 'billing_shortfall', 'gap_to_threshold',
]

SYSTEM_PROMPT = """You classify a question about an infrastructure company's completed projects into exactly ONE of these 12 shapes.

- hop_aggregate: sum of ALL completed work for one client, no date filter, no threshold, no exclusion.
- temporal_chain: sum of completed work for one client, but ONLY counting projects completed AFTER a specific stated date (e.g. after a certification/PMP issue date). Requires an explicit "after this date" condition — do not choose this just because a date or credential is mentioned.
- exclusion_aggregate: sum of a client's work MINUS one named category (e.g. "excluding water treatment", "leaving out bridges", "take out the X projects"). Requires ONE specific category being subtracted out.
- category_diff: the VALUE DIFFERENCE between TWO named categories for a client (e.g. "expressways vs water treatment", "difference between bridges and roads"). Two categories being compared, not one being removed.
- threshold_aggregate: sum of only the projects at or above a specific stated CRORE or LAKH amount (e.g. "at or over 40 crore"). Requires an actual numeric currency threshold to be present. Do NOT choose this just because a word contains the letters "cr" or "line" (e.g. "across", "deadline") — there must be a real crore/lakh amount.
- mean_vs_median: the rupee gap between the average (mean) and median contract value for a client's works.
- avg_work_size: the average/mean/typical contract value across a client's completed work (a single average, not a mean-vs-median gap).
- rank_value: the difference in value between the LARGEST completed project and the SECOND-largest, for a client.
- annual_diff: how much a client's total value changed between two specific stated years.
- outstanding_balance: the total UNPAID/PENDING/remaining amount a client still owes against what's been billed/invoiced.
- billing_shortfall: the gap between a client's total AWARDED/contract value and what's actually been INVOICED (not about payment status, about awarded-vs-billed).
- gap_to_threshold: how much MORE value is needed to reach/hit a target threshold.

Question: {question}"""

# Structured output is constrained during decoding by the server, so a
# response in this schema always parses -- this also rules out the
# label-hallucination failure mode seen from weaker models during testing
# (answering with something outside the valid shape list entirely).
RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "shape_classification",
        "schema": {
            "type": "object",
            "properties": {
                "shape": {"type": "string", "enum": MONEY_SHAPES},
            },
            "required": ["shape"],
        },
    },
}


def classify_llm(question_text: str, atype: str, base_url: str = None,
                  model: str = DEFAULT_MODEL, timeout: int = 60):
    """Classify a MONEY-type question via the competition's provided LLM
    endpoint. Returns a valid shape name, or None on any failure
    (endpoint not configured/unreachable, timeout, malformed response) so
    the caller falls through to the next tier rather than trust a bad
    result. Never calls any model other than the one provided.
    """
    if atype != 'money':
        return None
    base_url = base_url or os.environ.get('LLM_BASE_URL')
    if not base_url:
        return None

    prompt = SYSTEM_PROMPT.format(question=question_text)
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        # Reasoning model: it spends budget on a hidden trace before the
        # actual answer, so max_tokens needs headroom or the response comes
        # back truncated (finish_reason "length", content null).
        "max_tokens": 2048,
        "temperature": 0,
        "response_format": RESPONSE_SCHEMA,
    }
    try:
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
        shape = json.loads(content).get('shape')
        return shape if shape in MONEY_SHAPES else None
    except Exception:
        return None
