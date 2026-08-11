# Technical briefing — the document estate

Supplementary detail for teams who want to understand the corpus before building against it. The
[README](README.md) is the task; this is the terrain.

---

## 1. Why this is not a table-parsing exercise

The obvious approach — OCR everything, find the tables, load them into a dataframe — will get you
some of the way and then stop. Three properties of the corpus are there specifically to break it.

**Layout varies between documents of the same type.** The 155 completion certificates were issued by
62 different client organisations over 15 years. They are not one template. Different issuing bodies
use different section orders, different headings for the same field, and different seals. Some are
dense tables; some are two paragraphs of prose with the value in the middle of a sentence.

**Financial statements change format across eras.** The reporting layout shifts over the period
covered, the way a real company's accounts do when standards change. A parser tuned to the newest
statements will misread the oldest.

**Some questions turn on facts that appear in no table anywhere.** The client's written assessment of
a work — the grading, the remark about co-operation, the name of the officer who signed — lives in
sentences. There is no field for it. Roughly one reasoning pattern in the hidden set depends on
reading those judgements and then aggregating over the works they apply to.

---

## 2. How money is written

Every monetary figure in the corpus is rendered the way Indian business documents render it, not as a
raw integer. A contract worth **333,800,000 rupees** may appear as:

| Rendering | Where you'll see it |
|---|---|
| `INR 33.38 Cr` | certificates, portfolios, narrative prose |
| `3,338.00 Lakh` | some ledgers and statements |
| `33,38,00,000` | Indian digit grouping, in tables |
| `333800000` | rarely — mostly in workbook cells |

This is lossless: no precision is discarded in the rendering, and a sum of five works reconstructed
from crore-denominated documents lands exactly on the true total. Reading money back out is a parsing
problem with a correct answer, not an approximation you have to tolerate.

**Practical consequence:** a naive integer search for a contract value finds it in about 1 document in
8. Handle the renderings and you find them all.

---

## 3. What links to what

Nothing in the bundle tells you which document concerns which project. That mapping exists — we hold
it internally, and it is how the questions were verified answerable — but reconstructing it is the
core of the task.

The joins you will need to rediscover, roughly:

```
personnel_certificate ──▶ engineer ──▶ works they led ──▶ client ──▶ that client's whole portfolio
                                              │
                                              ├──▶ completion_certificate  (value, dates, grading)
                                              ├──▶ reference_letter        (present or absent)
                                              ├──▶ performance_bond        (guarantees)
                                              └──▶ ledger entries          (invoiced, received)
```

Most questions walk four to six of these steps. The last step is usually an aggregate over a *set*
that only becomes identifiable after the earlier steps — which is why answering the single document a
question names is almost never the answer.

**A worked example.** Take: *"Starting from Sunita Joshi's Six Sigma Black Belt on the Ring Road —
Uttar Pradesh Pkg-107 project, what is the combined value of every completed work for the National
Expressway Development Authority?"*

1. Find the personnel certificate — establishes Sunita Joshi holds a Six Sigma Black Belt.
2. Find Ring Road — Uttar Pradesh Pkg-107 — its completion certificate names the client.
3. Find **every other** work for that client — this is the step that requires the corpus, not the
   named document.
4. Read each of those works' contract values out of their own certificates.
5. Add them.

The answer is not the value on the certificate the question names. A system that stops at step 2
returns a plausible, wrong number — and several questions are built specifically so that the naive
answer differs from the correct one.

---

## 4. The workbooks

Nine `.xlsx` files carry structured detail that does not appear in the PDFs:

- **BOQ workbooks** (6) — bill-of-quantity line items with rates and measured quantities
- **Ageing workbook** — receivables by bucket
- **Trial balance workbook** — account balances
- **Asset register workbook** — plant and equipment with acquisition costs

They contain live formulas (`=SUM(...)`) and Notes sheets. If your pipeline only ingests PDFs you
will miss them, and some values are reachable nowhere else.

---

## 5. Absence, and why it matters

132 reference letters cover 155 works. The gap is deliberate and it is queryable: *"how many of this
client's completed works have no reference letter on file?"*

This is the failure mode that separates a retrieval system from a reasoning one. To answer it you
must establish the client's complete portfolio **and** confirm the absence of a document for some of
them. A system that reasons over whatever it retrieved will report zero, confidently, because it
never saw the missing thing. Proving a negative requires knowing the boundary of the set.

Several hidden questions are of this kind.

---

## 6. Scale, and what "reading everything" costs

687 documents, ~39 MB, roughly 3.5 million characters of extractable text. That is small enough to
process exhaustively — you are not being asked to solve retrieval at scale. The difficulty is not
volume; it is that the right four documents for a given question are scattered across four different
type folders with no index connecting them.

One practical note on extraction: the layout-preserving text extractors handle these documents
considerably better than the default ones. On a table-heavy certificate, a default extraction can
silently return a fraction of the page — the text is there, but the extractor drops it and reports no
error. Check what your pipeline actually recovers from a few documents before trusting it across 687.

---

## 7. On the synthetic nature of the corpus

The company is generated, but the *questions* come from the shape of real government tender
requirements — what a bidder is actually asked to prove about their past performance, credentials,
financial standing and personnel. So the query distribution is realistic even though the company is
not.

Every answer is computed from the underlying structured data by an executable query, then verified to
be reachable from the documents alone before the question was accepted. There are no judgement calls
in the gold answers and no questions whose answer depends on interpretation.
