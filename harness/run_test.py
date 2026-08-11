"""
Test harness: one persistent RLM session, asked two questions in a row about
the same client ("Jal Nigam, Jharkhand"), to check whether the second question
actually reuses what the first one found (lower token usage / no re-search)
instead of starting from scratch.

Model backend is env-driven so this works against DeepSeek's API or a local
OpenAI-compatible server (LM Studio / Ollama) without code changes:

    MODEL_NAME       e.g. "deepseek-v4-flash", or a local model id
    MODEL_BASE_URL   e.g. "https://api.deepseek.com" or "http://localhost:1234/v1"
    MODEL_API_KEY    required for DeepSeek; local servers usually ignore it
"""
import os
import re
import sys

import openai
from rlm import RLM
from rlm.logger import RLMLogger
from rlm.utils.exceptions import (
    BudgetExceededError,
    CancellationError,
    ErrorThresholdExceededError,
    TimeoutExceededError,
    TokenLimitExceededError,
)

sys.path.insert(0, os.path.dirname(__file__))
from tools import (  # noqa: E402
    list_documents,
    list_doc_types,
    read_document,
    grep_documents,
    verify_client_work_count,
    read_workbook_table,
    query_db,
    parse_inr,
    find_client,
    find_engineer,
)

RLM_ERRORS = (
    BudgetExceededError,
    TimeoutExceededError,
    TokenLimitExceededError,
    ErrorThresholdExceededError,
    CancellationError,
)

GOTCHAS = """\
You are answering questions about a document archive for a fictional Indian
infrastructure contractor, "National Infrastructure Corp. Ltd." You have
tools to explore it: list_documents(doc_type=None), list_doc_types(),
read_document(doc_id), grep_documents(pattern, doc_type=None). There is no
index mapping documents to projects/clients -- you must discover that.

Known gotchas about this corpus -- apply them carefully:

1. Money appears in multiple renderings for the same value: "INR 33.38 Cr",
   "3,338.00 Lakh", "33,38,00,000" (Indian digit grouping), or a raw integer.
   Normalize all to a plain integer number of rupees. Exact conversion
   factors -- a common mistake is getting these off by a power of ten:
   1 Lakh = 100,000 = 10^5 (NOT 10^6). 1 Crore = 10,000,000 = 10^7 (NOT 10^8).
   Double-check your arithmetic against these exact powers before finalizing
   any money answer.
2. Every completion certificate has a constant, bogus letterhead date like
   "Dated: March 31, 2026" near the top -- this is NOT the completion or
   issuance date. Always use the actual labeled "Completion Date" field.
3. Client names can collide across different states -- e.g. "Jal Nigam"
   appears as "Jal Nigam, Jharkhand", "Jal Nigam, Uttar Pradesh", and
   "Jal Nigam, Gujarat" as three DIFFERENT clients. Always match the FULL
   client name string, never a partial/fuzzy match.
4. A client's grade sometimes appears as an explicit sentence ("graded
   Excellent") and sometimes only as paraphrased prose ("found satisfactory
   during final inspection") depending on the certificate template -- these
   are not necessarily the same signal.
5. A field like "role" (Prime vs subcontractor) may not be on the completion
   certificate at all -- check past_performance_portfolio, tender_dossier, or
   compliance_matrix too.
6. A single grep/search pass can silently undercount a client's works -- some
   certificates center or indent the client name in the letterhead/signature
   block instead of left-aligning it, which can cause a naive search to miss
   them with no error or warning. MANDATORY: before finalizing any answer
   about how many works a client has, or any total/list/average/rank over
   their works, call verify_client_work_count(client_name). It cross-checks
   your completion_certificate count against company_completion_certificate
   (two independent records of the same 155 works, always equal in count for
   a real client). If counts_match is False, you have NOT found everything --
   compare the two id lists to find the missing package number(s) and keep
   searching before answering.
7. Questions that start from an engineer's certificate/PMP for one named
   project, then ask for a combined value, mean one of two different things --
   the deciding signal is HOW the client is referenced, not just whether one
   is mentioned at all:
   - If the client is named EXPLICITLY as a proper noun in the "delivered
     for" / "for the [client]" phrase (e.g. "...every completed assignment he
     has delivered FOR THE PUBLIC WORKS DEPARTMENT, GOVT OF MAHARASHTRA"),
     the named engineer and project are ONLY there to identify which client.
     The answer is the sum of ALL of that client's works (verify with
     verify_client_work_count), regardless of which engineer led each one --
     do not filter to just the named engineer's own projects.
   - If the client is referenced ANAPHORICALLY instead -- "that client",
     "them", "their" -- pointing back to the client already identified via
     the named project (e.g. "...every completed assignment he has done FOR
     THAT CLIENT", "...delivered TO THEM"), it means only that engineer's OWN
     works for that client, NOT the client's whole portfolio. This phrasing
     is common and easy to misread as the first pattern -- confirmed
     repeatedly on real cases: "for that client"/"to them" is engineer-scoped,
     an explicitly re-stated client name is client-scoped. Don't default to
     the whole-client sum just because a client is mentioned somewhere.
   - If no client is mentioned at all, just "the works/projects [engineer]
     led/delivered" (e.g. "...the projects he led that wrapped up after that
     date"), it also means only that engineer's own works, optionally
     filtered further (by date, category, etc).
   Getting this backwards is a designed trap in this corpus -- the naive
   answer (just the one named project, or summing the wrong scope) is a
   plausible-looking wrong number.
8. Percentage answers must keep exactly 2 decimal places, not rounded --
   e.g. 2 out of 3 is 66.67, not 67. The scorer requires this precision.
9. Workbooks (boq_workbook, ageing_workbook, trial_balance_workbook,
   asset_register_workbook): prefer read_workbook_table(doc_id) over
   read_document for these -- it returns real column-name access
   ({sheet: [{"ColumnName": value, ...}, ...]}) instead of raw
   tab-separated text you'd have to split and guess column positions from.
   Feed a sheet's rows straight into pandas.DataFrame(rows) if that's more
   natural for the filter/groupby/sum you need, or use plain Python. Blank
   TOTAL rows from simple SUM() formulas are already recomputed for you in
   both read_document and read_workbook_table -- most totals you see are
   real. But if a TOTAL/summary cell still looks blank or suspicious, don't
   trust it -- sum the underlying line items yourself instead.
10. You have llm_query/rlm_query available to spawn sub-calls (e.g. one per
    document) for cases that need a semantic judgment call a regex can't make
    (e.g. "does this letter express strong vs mild praise"). Most questions
    don't need this -- grep_documents already handles exact matches (names,
    dates, thresholds) directly. If you DO spawn sub-calls across many
    documents, make each one return a SHORT, simple answer (a boolean, a
    single word, a short number) -- never free-form prose. Aggregating many
    paragraph-length sub-answers yourself is unreliable and easy to lose
    track of; a simple verdict per document is safe to combine.
11. "Outstanding receivables" / net balance questions over the ageing
    workbook mean the NET sum across every invoice for the client(s) in
    scope, including negative rows (overpayments/credits). Do NOT filter to
    only positive-outstanding invoices and call that "what's owed" -- a
    negative row nets against the rest of the same account. Sum everything,
    don't exclude anything based on sign.
12. Two DIFFERENT calculations get asked about a client's money, and they are
    NOT interchangeable:
    - "gap"/"shortfall"/"unbilled remainder" between what was
      AWARDED/AAssigned/SANCTIONED/SECURED/COMMITTED and what's been
      BILLED/INVOICED -- this is (sum of completion certificate contract
      values for that client) MINUS (sum of the ageing workbook's
      "Invoiced (INR)" column for that client).
    - "outstanding"/"still owed"/"pending"/"balance" (gotcha #11 above) --
      this is the ageing workbook's "Invoiced (INR)" column MINUS its
      "Received (INR)" column (i.e. the "Outstanding (INR)" column
      directly).
    These use different source data (contract certificates vs one workbook
    column) and give very different numbers -- read which one the question
    is actually asking for before picking a formula. Defaulting to
    "Outstanding (INR)" because it's the easiest number to grab is a known
    trap: it answers a question that wasn't asked.
13. You have query_db(sql) -- a pre-built, pre-validated SQL database
    (estate.db) covering completion_certificate + company_completion_certificate
    + personnel_certificate + past_performance_portfolio + reference_letter,
    extracted and cross-checked ahead of time (validated exact-match against
    21 independent worked examples). For anything about clients, projects,
    engineers, work categories, contract values, completion dates, roles
    (Prime/JV Partner), reference-letter presence, or PMP/Six Sigma
    credential issuance dates -- START with query_db, not grep_documents or
    manual text parsing. It is far less error-prone than re-deriving these
    from prose every time (this corpus has repeatedly punished hand-parsing:
    off-by-power-of-ten money bugs, silently undercounted clients, engineer
    name mis-splits). Call query_db("select sql from sqlite_master where
    type='table'") or just try a query against clients/engineers/projects/
    credentials if you're unsure of the exact columns -- errors come back
    as {"error": ...}, not a crash, so it's safe to explore interactively.
    Money is already integer rupees, dates are ISO 'YYYY-MM-DD'. Client/
    engineer names may need LIKE '%partial%' rather than exact match --
    find_client(name_pattern)/find_engineer(name_pattern) are shortcuts for
    that specific lookup, saving you the boilerplate SQL. This
    DB does NOT cover workbooks (use read_workbook_table, gotcha #9),
    general_ledger_book, bank_statement, iso_certificate, tender_dossier, or
    compliance_matrix -- for those, or for anything query_db can't answer,
    fall back to read_document/grep_documents as before.
    TRUST a clean query_db result once your query is unambiguous (a single
    client_id/engineer_id resolved via one clear LIKE match, a well-formed
    count/sum/avg/date-diff over it) -- finalize from it directly. Do NOT
    follow it up by re-reading every underlying certificate one-by-one "to
    be sure" -- that has been observed costing 10+ extra iterations and
    100,000+ extra tokens on questions where the DB's number was already
    correct, for zero change in the final answer. Reserve manual
    read_document verification for when something is actually in question:
    query_db returns NULL/empty/multiple candidate rows for a name, the
    number looks implausible given the question's context, or has_discrepancy
    is set on a row you're relying on -- not as a default extra step on
    every question.
    Only add a WHERE condition if the question's own words ask for it --
    don't import one from a similar-looking question you've seen elsewhere
    in this batch (confirmed failure mode: "PMP certification" alone got
    misread as "completed after his PMP issuance date" and added a spurious
    completion_date filter that wasn't asked for, wrongly cutting 3 works
    down to 1).
    BAD: query_db("select category from projects where engineer_id=5 and
      completion_date >= '2021-03-10'") -- for "how many categories has he
      led under his PMP certification" (no date mentioned in the question).
    GOOD: query_db("select category from projects where engineer_id=5")
      -- only filter by date when the question itself says "after"/"since"/
      "before" a date.


CODE FORMAT -- use exactly this and nothing else:
```repl
your code here
```
Do NOT use any of these -- they will not execute and you will get no output
or feedback at all, silently: <repl>...</repl>, <repl_block>...</repl_block>,
```python fences, or a bare ``` fence with no language tag. Only the exact
```repl fence shown above runs.

GOOD (one block, then stop -- real output comes back next turn):
```repl
print(list_doc_types())
```

BAD (never do this -- more blocks in the same response, guessing without
having seen real output yet):
```repl
print(list_doc_types())
```
```repl
print(list_doc_types())
```
```repl
print("test")
```

CRITICAL OUTPUT REQUIREMENT -- checked automatically, not optional. This is
the single most common source of wasted turns in this harness -- some runs
have burned over half their iteration budget on this one mistake alone, with
the correct number already known many turns earlier.

GOOD (the ONLY way to finish -- a real repl block, answer["content"] ends
with its own FINAL(<number>) line):
```repl
answer["content"] = "Brief reasoning here if you want it.\n\nFINAL(84200000)"
answer["ready"] = True
```

BAD (prose only, no repl block -- nothing executes, nothing ends, this just
wastes a turn even though it "looks" done):
FINAL(84200000)

BAD (real repl block, but answer["content"] is the bare number with no
FINAL() wrapper -- fails validation exactly like leaving it out):
```repl
answer["content"] = "84200000"
answer["ready"] = True
```

If feedback says "FINAL value failed validation", that's the second BAD
case -- re-run the GOOD pattern above with the wrapper text included, don't
just restate the number in prose.
"""


FINAL_RE = re.compile(r"FINAL\(\s*(-?[\d,]*\.?\d+)\s*\)")


def extract_final(response_text: str) -> float | None:
    """Strict parse: last FINAL(<number>) in the text, as the harness would score it."""
    matches = FINAL_RE.findall(response_text)
    if not matches:
        return None
    return float(matches[-1].replace(",", ""))


def validate_final_answer(final_answer: str) -> tuple[bool, str]:
    """Passed to RLM(output_validator=...) -- called every time the REPL calls
    FINAL(). Rejects an answer that doesn't end with a clean FINAL(<number>)
    line, so the model gets told immediately (with its REPL state and every
    derived variable still intact) instead of silently returning something
    the harness would later need a separate repair pass to recover."""
    if extract_final(final_answer) is not None:
        return True, ""
    return False, (
        "Your answer did not end with a FINAL(<number>) line. The LAST LINE "
        "must be exactly FINAL(<number>) -- e.g. FINAL(84200000) -- with "
        "nothing else on that line. State your reasoning first if you like, "
        "but the final line must be exactly that format."
    )


SUBAGENT_HINT = """\

SUBAGENT MODE (enabled for this run): For any question that requires reading
MULTIPLE similar documents to extract per-document numbers (e.g. several
invoices, certificates, or ledger entries belonging to one client), do NOT
read the full text of each document into your own reasoning and print it --
that permanently grows your own conversation history for every remaining
iteration. Instead: call read_document(doc_id) to get the text into a
variable, then pass that variable straight into
llm_query(f"...extract the exact figure for X from this document: {doc_text}")
and keep ONLY the short returned value (a number/short string). Never print
the raw document text yourself. Aggregate the short returned values with
plain Python arithmetic. This keeps your own context small since the full
document text is spent inside the one-shot llm_query call, not your own
history. Skip this for questions that only touch one or two documents --
it's not worth the extra round-trip there.

Before using llm_query anywhere, ask yourself: is there an actual judgment
call to make here (ambiguous wording, matching a name/label that isn't an
exact string, deciding tone/severity/quality), or is the data already exact
and structured (a table, a list of clearly-labeled numbers)? Use llm_query
only for the former -- it exists to make a call a regex/plain-code can't
make, not to move data around. If there's nothing ambiguous to resolve,
llm_query adds a full extra LLM round-trip for zero benefit.

Workbooks (boq_workbook, ageing_workbook, trial_balance_workbook,
asset_register_workbook doc_types) are a clear example of the latter: each
is already plain tab-separated rows of numbers via read_document -- one
file, many rows, not many documents, and nothing about a row's value is
ambiguous once you've matched its label. Parse and sum those rows directly
with plain Python (split on tabs, float() the columns you need).
"""


def make_rlm(persistent: bool, use_subagents: bool = False) -> RLM:
    prologue = GOTCHAS + (SUBAGENT_HINT if use_subagents else "")
    return RLM(
        backend="openai",
        backend_kwargs={
            "model_name": os.environ.get("MODEL_NAME", "deepseek-v4-flash"),
            "base_url": os.environ.get("MODEL_BASE_URL", "https://api.deepseek.com"),
            "api_key": os.environ.get("MODEL_API_KEY"),
        },
        environment="local",
        persistent=persistent,
        custom_tools={
            "list_documents": list_documents,
            "list_doc_types": list_doc_types,
            "read_document": read_document,
            "grep_documents": grep_documents,
            "verify_client_work_count": verify_client_work_count,
            "read_workbook_table": read_workbook_table,
            "query_db": query_db,
            "parse_inr": parse_inr,
            "find_client": find_client,
            "find_engineer": find_engineer,
        },
        user_prologue=prologue,
        max_iterations=20,
        max_budget=0.5,     # hard $ cap per completion() call
        max_timeout=600,    # hard wall-clock cap (seconds) per completion() call --
                            # raised from 180: HS-IC-0005 needed 194s across 12
                            # iterations, every single one productive (0 wasted on
                            # format drift) -- 180s was cutting off legitimate
                            # multi-step searches, not just runaway ones. Genuine
                            # "dooming" (repeated failures, no progress) is caught
                            # separately by max_errors, not by wall-clock time.
        max_errors=4,
        verbose=False,
        logger=RLMLogger(log_dir=os.path.join(os.path.dirname(__file__), "logs")),
        output_validator=validate_final_answer,
    )


def repair_final_answer(question: str, response_text: str) -> float | None:
    """Cheap non-agentic fallback: a single plain completion (no REPL, no tools,
    no iteration budget) asked to pull the numeric answer out of a response that
    didn't end with a clean FINAL(<number>) line. This is a repair pass, not a
    re-derivation -- it does not re-search documents, only reads what the main
    call already concluded."""
    client = openai.OpenAI(
        api_key=os.environ.get("MODEL_API_KEY"),
        base_url=os.environ.get("MODEL_BASE_URL", "https://api.deepseek.com"),
    )
    resp = client.chat.completions.create(
        model=os.environ.get("MODEL_NAME", "deepseek-v4-flash"),
        messages=[{
            "role": "user",
            "content": (
                "Extract ONLY the final numeric answer a response arrived at. "
                "This response has already done any needed unit conversion "
                "(Lakh/Crore/etc) -- locate and restate the existing number it "
                "already computed, do not recompute or reconvert anything "
                "yourself.\n\n"
                "FORMAT -- follow exactly:\n"
                "Output the number once, and only once. No units, no commas, "
                "no words, no repeating or restating it a second time in any "
                "form. If it never reached a numeric answer, output exactly: "
                "NONE\n\n"
                "Example 1 (correct):\n"
                "  Response: \"Combined value of Jal Nigam, Jharkhand's "
                "completed works: 1,613,800,000 rupees. FINAL(1613800000)\"\n"
                "  Output: 1613800000\n\n"
                "Example 2 (correct):\n"
                "  Response: \"...of which 2 have reference letters. "
                "(2/3)*100 = 66.67.\"\n"
                "  Output: 66.67\n\n"
                "Example 3 (WRONG -- never do this):\n"
                "  Response: \"634500000\"\n"
                "  Wrong output: 634500000634500000  <- the digits got "
                "duplicated, this is never correct\n"
                "  Correct output: 634500000\n\n"
                f"Now do this one.\n\n"
                f"A question was asked: {question}\n\n"
                f"Here is the full response given: {response_text}\n\n"
                "Output:"
            ),
        }],
        temperature=0,
    )
    text = resp.choices[0].message.content.strip()
    if text == "NONE":
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def ask(rlm: RLM, label: str, question: str, usage_out: dict | None = None):
    print("\n\n" + "=" * 70, f"\n{label}:", question, "\n" + "=" * 70)
    try:
        # root_prompt gets embedded directly as "Answer the following: {question}"
        # in the setup prompt for this call -- without it, the question only lives
        # in an opaque context_N REPL variable, and on a persistent session with
        # multiple stacked contexts the model has to guess which one is current
        # (observed failure: it read context_0 -- the FIRST question -- instead).
        r = rlm.completion(question, root_prompt=question)
    except RLM_ERRORS as e:
        print(f"\n--- STOPPED: {type(e).__name__}: {e} ---")
        print("(this is a clean stop, not a crash -- no further tokens spent on this question)")
        return None
    print(f"\n--- RESPONSE ({label}) ---\n", r.response)
    print(f"\n--- USAGE ({label}) ---\n", r.usage_summary.to_dict())
    if usage_out is not None:
        usage_out.update(r.usage_summary.to_dict())

    answer = extract_final(r.response)
    if answer is None:
        print(f"--- no clean FINAL(<number>) found, calling repair pass for {label} ---")
        answer = repair_final_answer(question, r.response)
        print(f"--- repair pass extracted: {answer!r} ---")
    else:
        print(f"--- parsed answer for {label}: {answer!r} ---")
    return answer


def main():
    if not os.environ.get("MODEL_API_KEY") and "localhost" not in os.environ.get("MODEL_BASE_URL", ""):
        sys.exit("Set MODEL_API_KEY (and optionally MODEL_NAME / MODEL_BASE_URL) before running.")

    rlm = make_rlm(persistent=True)

    # Fresh, uncached, never-mentioned client -- "Peninsular Petroleum
    # Corporation" (5 works). Ground truth independently verified by direct
    # document read just before this run: 847,000,000 total.
    q1 = ("How many completed works does the client \"Peninsular Petroleum "
          "Corporation\" have, and what is the total value of all of them "
          "combined (plain rupee integer)?")
    q2 = ("List each of those \"Peninsular Petroleum Corporation\" works with its "
          "individual value.")
    q3 = ("Of those same \"Peninsular Petroleum Corporation\" works, which one has "
          "the largest value, and what is that value?")

    ask(rlm, "Q1", q1)
    ask(rlm, "Q2 (same session)", q2)
    ask(rlm, "Q3 (pure reuse, no new lookups needed)", q3)

    print("\n\nCORRECTED ground truth (7 works, not 5 -- the first pass missed 2 "
          "long-form-template certificates via an anchored grep bug): "
          "112,300,000 + 240,500,000 + 181,700,000 + 491,100,000 + 164,000,000 + "
          "148,500,000 + 28,200,000 = 1,366,300,000 total; largest is Check Dam "
          "Pkg-69 at 491,100,000.")


if __name__ == "__main__":
    main()
