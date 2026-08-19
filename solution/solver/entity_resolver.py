"""Deterministic entity resolution: exact match -> acronym match -> fuzzy
word-overlap match -> margin-based abstention. No LLM call anywhere in this
module. Candidates always come from the live database (loaded fresh each
run), never a hardcoded per-dataset list, so this generalizes to any new
document estate with different client/engineer/category/project names.

Ambiguous cases (no clear single winner) are returned as a small tied
candidate set rather than a guess -- the caller decides whether to resolve
the tie using other constraints from the same question (see query_engine's
use of this for content-based disambiguation) or escalate to an LLM.
"""
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional

STOPWORDS = {
    'of', 'the', 'and', '&', 'govt', 'government', 'department', 'dept',
    'authority', 'corporation', 'office', 'ltd', 'limited', 'co', 'company',
}

# Words too generic to count as a real acronym letter on their own -- avoids
# 'Department' contributing a 'D' to every single client's acronym.
ACRONYM_STOPWORDS = STOPWORDS - {'authority', 'corporation', 'office'}


def _words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z]+", text or '')


def normalize_words(text: str) -> set:
    """Lowercased, stopword-stripped, trailing-'s'-stemmed word set --
    used for word-overlap scoring so 'bridge/bridges' etc. count the same."""
    out = set()
    for w in _words(text):
        wl = w.lower()
        if wl in STOPWORDS or len(wl) <= 2:
            continue
        if wl.endswith('s') and len(wl) > 3:
            wl = wl[:-1]
        out.add(wl)
    return out


def compute_acronyms(full_name: str) -> List[str]:
    """Derives plausible acronym forms from a real, already-extracted name --
    never from question text. Generalizes to any name on any future document
    estate automatically, since it's a pure function of the name itself."""
    words = _words(full_name)
    variants = set()
    all_initials = ''.join(w[0].upper() for w in words if w)
    if len(all_initials) >= 2:
        variants.add(all_initials)
    sig_initials = ''.join(w[0].upper() for w in words if w.lower() not in ACRONYM_STOPWORDS)
    if len(sig_initials) >= 2:
        variants.add(sig_initials)
    return list(variants)


@dataclass
class ResolveResult:
    matched: Optional[str] = None          # single confident match, else None
    confidence: float = 0.0                # 0-1, margin-adjusted
    tied: List[str] = field(default_factory=list)   # candidates left when ambiguous
    method: str = 'none'                   # 'exact' | 'acronym' | 'fuzzy' | 'none'


def resolve(query_text: str, candidates: List[str], min_score: float = 0.3,
            min_margin: float = 0.15) -> ResolveResult:
    """Runs the full cascade against one candidate list. Returns a single
    confident match, or the tied top candidates if the top score doesn't
    clearly separate from the runner-up (abstention, not a guess)."""
    if not candidates:
        return ResolveResult()
    txt_lower = (query_text or '').lower()

    # 1. Exact / substring match -- cheapest, and itself can produce a tie
    # (e.g. "Public Works Department" is a literal substring of all four
    # state-qualified variants), which is exactly the right signal to carry
    # forward rather than silently picking one.
    exact_hits = [c for c in candidates if c.lower() in txt_lower or txt_lower.strip() and c.lower() == txt_lower.strip()]
    if len(exact_hits) == 1:
        return ResolveResult(matched=exact_hits[0], confidence=1.0, method='exact')
    if len(exact_hits) > 1:
        return ResolveResult(tied=exact_hits, confidence=1.0, method='exact')

    # 2. Acronym match -- algorithmic, computed from the real name, not from
    # having seen this abbreviation used anywhere before.
    query_tokens = set(re.findall(r'\b[A-Z]{2,}\b', query_text or ''))
    if query_tokens:
        acro_hits = []
        for c in candidates:
            if query_tokens & set(compute_acronyms(c)):
                acro_hits.append(c)
        if len(acro_hits) == 1:
            return ResolveResult(matched=acro_hits[0], confidence=0.95, method='acronym')
        if len(acro_hits) > 1:
            return ResolveResult(tied=acro_hits, confidence=0.95, method='acronym')

    # 3. Fuzzy word-overlap -- scored against every candidate, margin-checked,
    # and rarity-weighted. A word shared by many candidates in the SAME list
    # (e.g. "project" happening to sit inside two different institution
    # names) is weak evidence and shouldn't count as much as a word unique
    # to one candidate -- otherwise an everyday word used in its ordinary
    # sense ("the projects she led") can spuriously match an institution
    # whose name happens to contain that word, even though nothing in the
    # question actually names it. This is the within-candidate-set analogue
    # of IDF: rarity is measured against this specific candidate list, not
    # general English frequency.
    q_words = normalize_words(query_text)
    if not q_words:
        return ResolveResult()

    candidate_word_sets = {c: normalize_words(c) for c in candidates}
    doc_freq: Dict[str, int] = {}
    for c_words in candidate_word_sets.values():
        for w in c_words:
            doc_freq[w] = doc_freq.get(w, 0) + 1

    def word_weight(w: str) -> float:
        return 1.0 / doc_freq.get(w, 1)

    scores = {}
    for c, c_words in candidate_word_sets.items():
        if not c_words:
            continue
        shared = q_words & c_words
        if not shared:
            continue
        # Require either multiple distinct shared words, or a single shared
        # word that's actually unique to this one candidate. One shared word
        # that also sits inside some other candidate's name (e.g. "project"
        # appearing in two unrelated institutions) is too weak a signal on
        # its own -- it's an everyday word used in its ordinary sense, not
        # necessarily a reference to either institution.
        if len(shared) < 2 and doc_freq.get(next(iter(shared)), 1) > 1:
            continue
        weighted_overlap = sum(word_weight(w) for w in shared)
        c_total_weight = sum(word_weight(w) for w in c_words)
        frac = weighted_overlap / c_total_weight if c_total_weight else 0.0
        scores[c] = (weighted_overlap, frac)

    if not scores:
        return ResolveResult()
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1][0], -kv[1][1]))
    top_c, (top_overlap, top_frac) = ranked[0]
    if top_frac < min_score:
        return ResolveResult()

    runner_overlap = ranked[1][1][0] if len(ranked) > 1 else 0.0
    if abs(top_overlap - runner_overlap) < 1e-9:
        tied = [c for c, (ov, _fr) in ranked if abs(ov - top_overlap) < 1e-9]
        return ResolveResult(tied=tied, confidence=top_frac, method='fuzzy')

    runner_frac = ranked[1][1][1] if len(ranked) > 1 else 0.0
    if top_frac - runner_frac < min_margin:
        tied = [c for c, (_ov, fr) in ranked if top_frac - fr < min_margin]
        return ResolveResult(tied=tied, confidence=top_frac, method='fuzzy')
    return ResolveResult(matched=top_c, confidence=top_frac, method='fuzzy')


class EntityResolver:
    """Loads live candidate catalogs fresh from the DB each run and resolves
    question text against them. No hardcoded per-dataset aliases anywhere."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._load()

    @staticmethod
    def _dedup_case_insensitive(values: List[str]) -> List[str]:
        """Some ingested tables carry the same real-world name in more than
        one casing (a data-entry inconsistency, not a real distinct entity)
        -- keep one canonical form per case-insensitive key rather than
        surfacing it to the resolver as a spurious ambiguity."""
        seen: Dict[str, str] = {}
        for v in values:
            key = v.lower()
            if key not in seen:
                seen[key] = v
        return list(seen.values())

    def _load(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT DISTINCT client_name FROM clients WHERE client_name IS NOT NULL AND client_name != '' AND client_name != 'nan'")
        self.clients = self._dedup_case_insensitive([r[0] for r in cur.fetchall()])

        cur.execute("SELECT DISTINCT name FROM engineers WHERE name IS NOT NULL AND name != ''")
        self.engineers = self._dedup_case_insensitive([r[0] for r in cur.fetchall()])

        cur.execute("SELECT emp_id, name FROM engineers WHERE name IS NOT NULL AND name != ''")
        self.engineer_emp_ids: Dict[str, str] = {}
        for row in cur.fetchall():
            self.engineer_emp_ids.setdefault(row['name'].lower(), row['emp_id'])

        cur.execute("SELECT DISTINCT category FROM projects WHERE category IS NOT NULL AND category != ''")
        self.categories = self._dedup_case_insensitive([r[0] for r in cur.fetchall()])

        cur.execute("SELECT DISTINCT cred_type FROM personnel_certs WHERE cred_type IS NOT NULL AND cred_type != ''")
        self.cred_types = self._dedup_case_insensitive([r[0] for r in cur.fetchall()])

        cur.execute("SELECT doc_id, project_name, package_no, client_name, lead_engineer FROM projects")
        self.projects = [dict(r) for r in cur.fetchall()]

        conn.close()

    def resolve_client(self, text: str) -> ResolveResult:
        return resolve(text, self.clients)

    def resolve_engineer(self, text: str) -> ResolveResult:
        return resolve(text, self.engineers)

    def resolve_categories(self, text: str, top_n: Optional[int] = None,
                            mask: Optional[List[str]] = None) -> List[str]:
        """Categories can be multiply mentioned in one question (e.g. a
        category_diff question names two) -- score all candidates by raw
        shared-word count (same length-invariance reasoning as `resolve`),
        return strongest matches first. Returns scored, ranked candidates
        rather than everything above a flat threshold, so the caller can
        take the top-1 or top-2 as the question actually needs instead of
        being handed weaker partial matches mixed in with real ones.

        `mask` should be any already-resolved entity strings (client name,
        engineer name, project name) whose own words should be excluded
        first -- otherwise a word like "Expressway" sitting inside a
        client's own name ("National Expressway Development Authority")
        can be mistaken for a mention of the "expressways" category."""
        masked_words = set()
        for m in (mask or []):
            masked_words |= normalize_words(m)
        q_words = normalize_words(text) - masked_words
        hits = []
        for cat in self.categories:
            cat_words = normalize_words(cat)
            if not cat_words:
                continue
            overlap = len(q_words & cat_words)
            if overlap == 0:
                continue
            frac = overlap / min(len(q_words), len(cat_words))
            if frac >= 0.4:
                hits.append((cat, overlap, frac))
        hits.sort(key=lambda t: (-t[1], -t[2]))
        names = [c for c, _ov, _fr in hits]
        return names[:top_n] if top_n else names

    def resolve_cred_type(self, text: str) -> ResolveResult:
        return resolve(text, self.cred_types)

    def resolve_project(self, text: str, scope_engineer: Optional[str] = None,
                         scope_client: Optional[str] = None) -> ResolveResult:
        """Project retrieval scoped by an already-resolved engineer/client
        first (keeps the candidate pool small and accurate regardless of
        total dataset size), then fuzzy-matched by name/package within that
        narrowed scope -- not a blind scan of every project in the DB."""
        pkg_m = re.search(r'\b(?:pkg|package)[-\s]*(\d+)\b', text, re.IGNORECASE)
        if pkg_m:
            pkg_no = f"Pkg-{pkg_m.group(1)}"
            for p in self.projects:
                if p['package_no'] and p['package_no'].lower() == pkg_no.lower():
                    return ResolveResult(matched=p['project_name'], confidence=1.0, method='exact')

        pool = self.projects
        if scope_engineer:
            pool = [p for p in pool if p['lead_engineer'] and p['lead_engineer'].lower() == scope_engineer.lower()]
        elif scope_client:
            pool = [p for p in pool if p['client_name'] and p['client_name'].lower() == scope_client.lower()]
        if not pool:
            return ResolveResult()

        names = [p['project_name'] for p in pool]
        return resolve(text, names, min_score=0.3, min_margin=0.15)
