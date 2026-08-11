"""Durable, growing knowledge cache -- a plain JSON file on disk that survives
across separate script runs. Exposed to the model as two tools: check it
before searching, save to it after resolving something new. This is our
version of "self-evolving memory" -- deliberately simple and inspectable
(just open the .json file) rather than relying on the RLM environment's own
(process-scoped, non-disk-backed for the local environment) state reuse."""
import difflib
import json
from pathlib import Path

CACHE_FILE = Path(__file__).resolve().parent / "knowledge_cache.json"

if CACHE_FILE.exists():
    _CACHE: dict = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
else:
    _CACHE = {}


def cache_lookup(entity_name: str) -> dict | None:
    """Check whether facts about this entity (a client name, engineer name, etc,
    used as the exact string you'd otherwise search for) were already resolved
    in a previous question -- in this run or an earlier one. Returns the saved
    facts dict, or None if nothing is cached yet for this entity. ALWAYS call
    this before searching documents for an entity you haven't resolved yet
    in this conversation."""
    return _CACHE.get(entity_name)


def cache_save(entity_name: str, facts: dict) -> str:
    """Save resolved facts about an entity so future questions (this run or a
    later one) don't have to re-derive them. `facts` should be a plain JSON-
    serializable dict, e.g. {"works": [...], "total_value": 1613800000,
    "has_reference_letter": {...}}. Call this once you've fully resolved an
    entity's information, before moving on."""
    _CACHE[entity_name] = facts
    CACHE_FILE.write_text(json.dumps(_CACHE, indent=2), encoding="utf-8")
    return f"cached {len(json.dumps(facts))} bytes under '{entity_name}'"


def cache_search(query: str) -> list[dict]:
    """Find cached entities whose name is CLOSE to `query` but not necessarily
    identical -- use this when cache_lookup(query) returns None and you suspect
    the entity might already be cached under a slightly different spelling or
    phrasing (a typo, a missing comma, an extra word). Returns up to 5 candidate
    {key, similarity, preview} entries, ranked by similarity -- it does NOT pick
    one for you. Compare the returned keys carefully yourself: two entities can
    look similar but be genuinely different (e.g. the same department name in a
    different state) -- once you've identified the correct key, call
    cache_lookup(that_exact_key) to get the full data. Do not trust the top
    result blindly just because it ranks first."""
    q = query.strip().lower()
    candidates = []
    for key, value in _CACHE.items():
        k = key.strip().lower()
        ratio = difflib.SequenceMatcher(None, q, k).ratio()
        if q in k or k in q or ratio > 0.6:
            preview = json.dumps(value)[:150]
            candidates.append({"key": key, "similarity": round(ratio, 2), "preview": preview})
    candidates.sort(key=lambda c: -c["similarity"])
    return candidates[:5]


def cache_dump() -> dict:
    """Return everything currently cached, across all entities."""
    return dict(_CACHE)
