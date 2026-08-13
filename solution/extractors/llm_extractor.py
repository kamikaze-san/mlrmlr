import json
import os
import urllib.request

DEFAULT_MODEL = 'qwen3.6-35b-a3b-nvfp4'

# Ask for each field as raw text exactly as written in the document, not a
# converted number -- unit conversion (crore/lakh -> rupees) and date
# parsing stay deterministic via our own parse_money/parse_date, the same
# functions used on regex-captured text. The LLM's job is narrowly "which
# span of text is the client name", not arithmetic.
EXTRACTION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "completion_certificate_fields",
        "schema": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "the work/project name, including any package reference like Pkg-47"},
                "client_name": {"type": "string", "description": "the client or issuing authority this work was done for"},
                "category_raw": {"type": "string", "description": "the work category exactly as written, e.g. 'Bridges Flyovers'"},
                "value_raw": {"type": "string", "description": "the contract/executed value exactly as written, e.g. 'INR 19.33 Cr' or 'Rs 4,50,000'"},
                "completion_date_raw": {"type": "string", "description": "the completion date exactly as written in the document"},
                "lead_engineer": {"type": "string", "description": "name of the project manager / lead engineer / contractor's site lead, if stated"},
                "package_no": {"type": "string", "description": "package identifier like Pkg-47, if present anywhere in the document"},
            },
            "required": ["project_name", "client_name", "value_raw", "package_no"],
        },
    },
}

PROMPT = """This is the text of a completion certificate for a completed infrastructure project, issued by a client to a contractor.

IMPORTANT distinctions, found to matter in testing:
- The CLIENT's specific name is normally the very first line of the document (a specific company or department name, e.g. "Meridian Constructors & Co." or "Trishakti Power Generation Corporation"). Do NOT extract a generic descriptor line like "Government of India / State Authority - <State> - IN" that may appear directly below it -- that line only describes the authority's tier/state, it is not the client's name itself.
- The CONTRACTOR is a different party, the one that PERFORMED the work (named after "awarded to" or "M/s ... GSTIN ..."). This is NOT the client -- never extract the contractor as the client.

Extract the fields below exactly as they appear in the document -- do not convert units or reformat values, just identify and copy the relevant text.

Document text:
{text}"""


def extract_fields_llm(document_text: str, base_url: str = None, model: str = DEFAULT_MODEL, timeout: int = 60):
    """Fallback field extraction via the competition's provided LLM
    endpoint, used only when a document has already been classified as a
    completion certificate but doesn't match any known template's regex
    (a layout we haven't seen before). Returns a dict of raw field strings
    to be parsed by our own parse_money/parse_date/etc., or None on any
    failure -- never a hard dependency."""
    base_url = base_url or os.environ.get('LLM_BASE_URL')
    if not base_url:
        return None
    prompt = PROMPT.format(text=document_text[:8000])
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0,
        "response_format": EXTRACTION_SCHEMA,
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
        fields = json.loads(content)
        if not fields.get('project_name') or not fields.get('value_raw'):
            return None
        return fields
    except Exception:
        return None
