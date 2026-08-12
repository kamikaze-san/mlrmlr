import json
import urllib.request

OLLAMA_HOST = 'http://127.0.0.1:11434'
MODEL_NAME = 'qwen3:4b-instruct'

MONEY_SHAPES = [
    'hop_aggregate', 'temporal_chain', 'exclusion_aggregate', 'category_diff',
    'threshold_aggregate', 'mean_vs_median', 'avg_work_size', 'rank_value',
    'annual_diff', 'outstanding_balance', 'billing_shortfall', 'gap_to_threshold',
]

SYSTEM_PROMPT = """You classify a question about an infrastructure company's completed projects into exactly ONE of these 12 shapes. Answer with ONLY the shape name, nothing else.

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

Question: {question}

Answer with only the shape name."""


def _extract_shape(raw_text: str):
    t = raw_text.lower()
    for shape in MONEY_SHAPES:
        if shape in t:
            return shape
    return None


def classify_llm(question_text: str, atype: str, host: str = OLLAMA_HOST, model: str = MODEL_NAME, timeout: int = 15):
    """Classify a MONEY-type question via a small local LLM (Ollama).

    Returns a valid shape name, or None on any failure (unreachable host,
    model not pulled, timeout, or a response that doesn't map to a known
    shape) so the caller can fall through to the next tier rather than trust
    a bad result.
    """
    if atype != 'money':
        return None
    prompt = SYSTEM_PROMPT.format(question=question_text)
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0},
        "think": False,
    }
    try:
        req = urllib.request.Request(
            f"{host}/api/generate",
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            return _extract_shape(res.get('response', ''))
    except Exception:
        return None
