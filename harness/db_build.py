"""
Phase 1 of the structured-knowledge-layer upgrade: build a validated
`projects` table from completion_certificate + company_completion_certificate
(the "core triangle" -- clients <-> projects <-> engineers), with a
soft-merge/flag policy on disagreement between the two independent records
of each work (never drop a row -- see conversation for why: dropping rows
breaks portfolio-wide SUM()s and absence/negative-proof questions).

Four known templates, confirmed by full-corpus survey (155/155 completion
certs, 155/155 company completion certs, zero unclassified):
  CC  TABLE_STYLE:  "Name of Work / Nature / Category / Contract Value
                      (Original) / Completion Date" labeled fields
  CC  PROSE_STYLE:  "...work of "X" (category)...completed...on DATE at a
                      gross executed value of VALUE..." sentence
  CCC RECORD_STYLE: "Work / Client / Category / Executed Value / Completion
                      / Project Lead" labeled fields
  CCC PROJECT_STYLE:"Project Name / Client / Work Category / Contract Value
                      / Completion Date / Project Manager" labeled fields
"""
import re
import sqlite3
from pathlib import Path

from tools import list_documents, parse_date_flexible, parse_inr, read_document

DB_PATH = Path(__file__).resolve().parent / "estate.db"


def _field(text: str, *labels: str) -> str | None:
    """Find the value on the same line as any of the given field labels
    (tries labels in order, first match wins)."""
    for label in labels:
        m = re.search(re.escape(label) + r"\s{2,}(.+)", text)
        if m:
            return m.group(1).strip()
    return None


def extract_cc(doc_id: str) -> dict:
    """Extract from a completion_certificate (either template)."""
    text = read_document(doc_id)
    flat = re.sub(r"\s+", " ", text)
    low = text.lower()

    if "particulars of the work" in low:
        name = _field(text, "Name of Work")
        cat = _field(text, "Nature / Category", "Nature/Category")
        val_raw = _field(text, "Contract Value (Original)", "Contract Value")
        date_raw = _field(text, "Completion Date")
    else:
        m = re.search(r'work of\s+"(.+?)"\s+\((.+?)\)', flat)
        name = m.group(1).strip() if m else None
        cat = m.group(2).strip() if m else None
        m = re.search(
            r"gross executed value of\s+(?:INR|Rs\.?)\s*([\d,.]+\s*(?:Cr|Crore|Lakh)?)",
            flat, re.IGNORECASE,
        )
        val_raw = m.group(1).strip() if m else None
        m = re.search(r"completed in all respects on\s+([\w /,\-]+?)\s+at", flat)
        date_raw = m.group(1).strip() if m else None

    # supervising engineer -- two known phrasings, either template
    eng = _field(text, "Contractor's Project Manager", "Project Manager")
    if not eng:
        m = re.search(r"supervised on the contractor's side by\s+([A-Z][a-zA-Z ]+?)\.", text)
        eng = m.group(1).strip() if m else None

    client = extract_client_letterhead(text)

    return {
        "doc_id": doc_id, "client_raw": client, "project_name": name,
        "category": cat, "value_raw": val_raw, "value": parse_inr(val_raw),
        "date_raw": date_raw, "date": parse_date_flexible(date_raw),
        "engineer_raw": eng,
    }


def extract_ccc(doc_id: str) -> dict:
    """Extract from a company_completion_certificate (either template)."""
    text = read_document(doc_id)
    low = text.lower()

    if "record of work completed" in low:
        name = _field(text, "Work")
        client = _field(text, "Client")
        cat = _field(text, "Category")
        val_raw = _field(text, "Executed Value")
        date_raw = _field(text, "Completion")
        eng = _field(text, "Project Lead")
    else:
        name = _field(text, "Project Name")
        client = _field(text, "Client")
        cat = _field(text, "Work Category")
        val_raw = _field(text, "Contract Value")
        date_raw = _field(text, "Completion Date")
        eng = _field(text, "Project Manager")

    if client:
        client = re.sub(r"\s*\(government\)\s*$", "", client, flags=re.IGNORECASE).strip()

    return {
        "doc_id": doc_id, "client_raw": client, "project_name": name,
        "category": cat, "value_raw": val_raw, "value": parse_inr(val_raw),
        "date_raw": date_raw, "date": parse_date_flexible(date_raw),
        "engineer_raw": eng,
    }


def extract_client_letterhead(text: str) -> str:
    """The client name in a CC letterhead can wrap across 2 lines (long
    department names don't fit the header width) and is sometimes followed
    on the SAME line by 'Government of India / State Authority...'
    boilerplate. Take everything up to that boilerplate marker, across
    however many lines, and collapse whitespace."""
    m = re.search(r"(.+?)(?:Government of India|Office of the Executive Engineer)",
                   text, re.DOTALL)
    chunk = m.group(1) if m else text.splitlines()[0]
    return re.sub(r"\s+", " ", chunk).strip()


def pkg_num(doc_id: str) -> str:
    """'DOC-CC-047' / 'DOC-CCC-047' -> '047' -- the shared pairing key."""
    return doc_id.rsplit("-", 1)[-1]


def build() -> list[dict]:
    cc_docs = {pkg_num(d["doc_id"]): d["doc_id"] for d in list_documents("completion_certificate")}
    ccc_docs = {pkg_num(d["doc_id"]): d["doc_id"] for d in list_documents("company_completion_certificate")}

    all_pkgs = sorted(set(cc_docs) | set(ccc_docs), key=lambda x: int(x))
    rows = []
    for pkg in all_pkgs:
        cc = extract_cc(cc_docs[pkg]) if pkg in cc_docs else None
        ccc = extract_ccc(ccc_docs[pkg]) if pkg in ccc_docs else None

        if cc and ccc:
            if cc["value"] is not None and ccc["value"] is not None and cc["value"] == ccc["value"]:
                value, has_discrepancy = cc["value"], False
            else:
                # tie-break: client-signed completion_certificate wins, flagged
                value = cc["value"] if cc["value"] is not None else ccc["value"]
                has_discrepancy = cc["value"] != ccc["value"]
        else:
            value = (cc or ccc)["value"]
            has_discrepancy = True  # missing one side is itself a discrepancy worth flagging

        # field-by-field fallback -- CC preferred (client-signed), CCC fills
        # in anything CC's own extraction missed, not just when CC is absent
        def pick(field):
            return (cc or {}).get(field) or (ccc or {}).get(field)

        rows.append({
            "package": pkg,
            "doc_id_cc": cc_docs.get(pkg), "doc_id_ccc": ccc_docs.get(pkg),
            "client": pick("client_raw"),
            "project_name": pick("project_name"),
            "category": pick("category"),
            "value": value, "has_discrepancy": has_discrepancy,
            "completion_date": pick("date"),
            "engineer": pick("engineer_raw"),
        })
    return rows


def reference_letter_packages() -> set[str]:
    """Package numbers (zero-padded to 3 digits, matching `package` field)
    that have a reference letter on file. NOTE: reference_letter doc_ids are
    NOT numbered by package (confirmed empirically -- DOC-REF-006 refers to
    Pkg-7, not Pkg-6, and it only gets worse from there) -- the actual
    package number has to be read out of each letter's own text."""
    pkgs = set()
    for d in list_documents("reference_letter"):
        text = read_document(d["doc_id"])
        m = re.search(r"Pkg-(\d+)", text)
        if m:
            pkgs.add(m.group(1).zfill(3))
    return pkgs


def extract_ppp_roles() -> dict[str, str]:
    """DOC-PPP-001's second section (155 numbered per-work detail entries,
    not the garbled index table at the top) is the only source with an
    explicit role. Verified against the full document: all 155/155 entries
    have a role annotation (no entries are missing one, despite the "role
    info is sparse" pattern seen elsewhere in this corpus), and only two
    distinct values actually occur -- "Prime" and "JV Partner" (no
    "Subcontractor" appears anywhere, despite that being a plausible third
    value). Verified 1:1 clean package-number pairing against the existing
    `projects` table (155/155, no dups, no orphans either direction) and
    spot-checked client/category/value against 5 packages -- exact matches."""
    text = read_document("DOC-PPP-001")
    roles = {}
    for m in re.finditer(r"PkG-(\d+)\s*\n\s*\nClient\s+.+?\(([^)]+)\)", text, re.IGNORECASE):
        pkg, role = m.group(1).zfill(3), re.sub(r"\s+", " ", m.group(2)).strip()
        roles[pkg] = role
    return roles


def extract_credentials() -> list[dict]:
    """personnel_certificate (48 docs) -- Phase 1's engineer side of the
    core triangle. Three templates, confirmed by full-corpus survey
    (48/48 classified, zero unclassified):
      "This is to certify that" style (PMI-2000XX PMP certs AND 6S-5001XX
        Six Sigma certs both use this template) -- name is reliably on the
        physical line exactly 2 rows below the "This is to certify that"
        line (NOT "skip a blank line" -- some renderings have a non-blank
        label-only line in between, e.g. row+1 = "Credential ID" with no
        trailing value, so counting physical rows is what's reliable, not
        counting non-blank rows). Some renderings interleave a
        left-column label on that name line too (e.g. "Issuing Authority
        Neha Chopra"), others don't (e.g. "          Amit Iyer" alone) --
        in BOTH cases the name is reliably the LAST whitespace-separated
        segment on that line, so splitting on 2+ spaces and taking the
        last segment handles both without needing to tell them apart.
        (An earlier version of this used a blank-line-skip regex instead
        of a fixed row+2 offset, and silently mis-captured the label text
        "Credential ID" as the name for every doc with no blank line in
        between -- caught by cross-checking unique-name counts against
        the corpus and finding a real engineer, Gautam Joshi, missing.)
      "This credential is conferred upon" style -- name is 2 lines below,
        cleanly alone, no interleaving.
    Credential type is derived from the credential-ID prefix ("PMI-" ->
    PMP, "6S-" -> Six Sigma Black Belt), NOT from which template rendered
    it -- both templates are used for both credential types.

    Some engineers hold 2 credentials (an original PMP cert plus a later
    Six Sigma one) -- this returns ALL of them, one row per document, the
    caller decides how to use them (e.g. "PMP issuance date" questions
    must filter to credential_type == 'PMP')."""
    rows = []
    for d in list_documents("personnel_certificate"):
        doc_id = d["doc_id"]
        text = read_document(doc_id)
        lines = text.split("\n")
        if "This is to certify that" in text:
            idx = next(i for i, l in enumerate(lines) if "This is to certify that" in l)
            raw_line = lines[idx + 2] if idx + 2 < len(lines) else None
            name = re.split(r"\s{2,}", raw_line.strip())[-1] if raw_line and raw_line.strip() else None
            cred = re.search(r"Credential ID:\s*(\S+)", text)
            issued_raw = re.search(r"Issued:\s*([\d-]+)", text)
        elif "This credential is conferred upon" in text:
            idx = next(i for i, l in enumerate(lines) if "This credential is conferred upon" in l)
            raw_line = lines[idx + 2] if idx + 2 < len(lines) else None
            name = raw_line.strip() if raw_line else None
            cred = re.search(r"Certificate No\.\s*(\S+)", text)
            issued_raw = re.search(r"Issued\s{2,}(.+)", text)
        else:
            name = cred = issued_raw = None

        cred_id = cred.group(1) if cred else None
        ctype = None
        if cred_id and cred_id.startswith("PMI-"):
            ctype = "PMP"
        elif cred_id and cred_id.startswith("6S-"):
            ctype = "Six Sigma Black Belt"

        rows.append({
            "doc_id": doc_id, "engineer_raw": name, "credential_id": cred_id,
            "credential_type": ctype,
            "issued_date": parse_date_flexible(issued_raw.group(1).strip()) if issued_raw else None,
        })
    return rows


def canonicalize(raw_names: list[str]) -> dict[str, str]:
    """Case-insensitive grouping -> {raw_name: canonical_name}. Canonical
    form is whichever variant is NOT all-uppercase (the letterhead ALL-CAPS
    rendering is the outlier, not the norm, in this corpus)."""
    groups: dict[str, list[str]] = {}
    for name in raw_names:
        groups.setdefault(name.lower(), []).append(name)
    mapping = {}
    for variants in groups.values():
        canonical = next((v for v in variants if not v.isupper()), variants[0])
        for v in variants:
            mapping[v] = canonical
    return mapping


def write_db(rows: list[dict]) -> None:
    credentials = extract_credentials()
    client_map = canonicalize([r["client"] for r in rows if r["client"]])
    # canonicalize project-engineer names AND credential-holder names together
    # so case-variants merge to one engineer_id, and engineers who hold a
    # credential but have no CC/CCC project credit under their name (e.g.
    # "Asha Bose", "Manoj Kapoor") still get an engineers row.
    engineer_map = canonicalize(
        [r["engineer"] for r in rows if r["engineer"]]
        + [c["engineer_raw"] for c in credentials if c["engineer_raw"]]
    )
    ref_pkgs = reference_letter_packages()
    ppp_roles = extract_ppp_roles()

    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE clients (
            client_id INTEGER PRIMARY KEY, canonical_name TEXT UNIQUE
        )""")
    conn.execute("""
        CREATE TABLE engineers (
            engineer_id INTEGER PRIMARY KEY, canonical_name TEXT UNIQUE
        )""")
    conn.execute("""
        CREATE TABLE projects (
            package TEXT PRIMARY KEY, doc_id_cc TEXT, doc_id_ccc TEXT,
            client_id INTEGER, project_name TEXT, category TEXT,
            value INTEGER, has_discrepancy INTEGER,
            completion_date TEXT, engineer_id INTEGER, has_reference_letter INTEGER,
            role TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(client_id),
            FOREIGN KEY(engineer_id) REFERENCES engineers(engineer_id)
        )""")
    conn.execute("""
        CREATE TABLE credentials (
            doc_id TEXT PRIMARY KEY, engineer_id INTEGER, credential_id TEXT,
            credential_type TEXT, issued_date TEXT,
            FOREIGN KEY(engineer_id) REFERENCES engineers(engineer_id)
        )""")

    client_ids = {name: i + 1 for i, name in enumerate(sorted(set(client_map.values())))}
    engineer_ids = {name: i + 1 for i, name in enumerate(sorted(set(engineer_map.values())))}
    conn.executemany("INSERT INTO clients VALUES (?,?)", [(v, k) for k, v in client_ids.items()])
    conn.executemany("INSERT INTO engineers VALUES (?,?)", [(v, k) for k, v in engineer_ids.items()])

    for r in rows:
        conn.execute(
            "INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["package"], r["doc_id_cc"], r["doc_id_ccc"],
             client_ids.get(client_map.get(r["client"])),
             r["project_name"], r["category"], r["value"],
             int(r["has_discrepancy"]), r["completion_date"],
             engineer_ids.get(engineer_map.get(r["engineer"])),
             int(r["package"] in ref_pkgs),
             ppp_roles.get(r["package"])),
        )
    for c in credentials:
        conn.execute(
            "INSERT INTO credentials VALUES (?,?,?,?,?)",
            (c["doc_id"], engineer_ids.get(engineer_map.get(c["engineer_raw"])),
             c["credential_id"], c["credential_type"], c["issued_date"]),
        )

    conn.commit()
    conn.close()
    print(f"wrote {DB_PATH}: {len(client_ids)} clients, {len(engineer_ids)} engineers, "
          f"{len(rows)} projects, {len(ppp_roles)} roles, {len(credentials)} credentials")


if __name__ == "__main__":
    rows = build()
    print(f"{len(rows)} packages processed")
    missing_value = [r for r in rows if r["value"] is None]
    missing_client = [r for r in rows if not r["client"]]
    missing_engineer = [r for r in rows if not r["engineer"]]
    missing_date = [r for r in rows if not r["completion_date"]]
    discrepancies = [r for r in rows if r["has_discrepancy"]]
    print(f"missing value: {len(missing_value)}  {[r['package'] for r in missing_value][:10]}")
    print(f"missing client: {len(missing_client)}  {[r['package'] for r in missing_client][:10]}")
    print(f"missing engineer: {len(missing_engineer)}  {[r['package'] for r in missing_engineer][:10]}")
    print(f"missing date: {len(missing_date)}  {[r['package'] for r in missing_date][:10]}")
    print(f"discrepancies: {len(discrepancies)}  {[r['package'] for r in discrepancies][:15]}")
    write_db(rows)
