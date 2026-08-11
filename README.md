# BITS Hackathon — Bid Intelligence over a Document Estate

You are given the complete document archive of a construction company. **There is no database.**
Your task is to build a system that reads those documents and answers precise numerical questions
about the business.

---

## The company

**National Infrastructure Corp. Ltd.** — an Indian infrastructure contractor, founded 2005, head
office in Salt Lake, Kolkata. It builds highways, water treatment plants, flyovers, drainage,
tunnels and power infrastructure for state and central government bodies.

| | |
|---|---|
| Completed works | 155, delivered 2010 – 2025 |
| Clients | 62 government departments and authorities |
| Employees on record | 486 |
| Business units | 6 |
| Total delivered value | ~₹5,530 crore |

Everything about this company is synthetic. It has never existed, and the identifiers in these
documents (CIN, GST, PAN) are deliberately invalid — see *Rules* below.

---

## What you are given

**687 documents, 20 types, ~39 MB.** 678 PDFs and 9 Excel workbooks, in `documents/`, grouped by
type.

| Document type | Count | What it holds |
|---|---:|---|
| `completion_certificate` | 155 | Client's sign-off on a finished work: value, dates, and the client's **written grading** of our performance |
| `company_completion_certificate` | 155 | Our own record of the same work |
| `reference_letter` | 132 | Client testimonials — note that not every work has one |
| `performance_bond` | 60 | Bank guarantees issued against contracts |
| `personnel_certificate` | 48 | PMP, Six Sigma and other credentials held by staff |
| `cv` | 39 | Engineer profiles: which works they led |
| `compliance_matrix` | 40 | Tender compliance checklists |
| `general_ledger_book` | 8 | Full journal — invoices, receipts, credit notes |
| `bank_statement` | 8 | Cash movements |
| `financial_statement` | 7 | Statutory accounts, several reporting eras |
| `ra_bill` / `final_ra_bill` | 12 | Running-account bills with BOQ detail |
| `tender_dossier` | 6 | Bids submitted |
| `iso_certificate` | 5 | Quality and safety accreditations |
| `annual_report` | 2 | Narrative reports with registers and tables |
| `past_performance_portfolio` | 1 | Consolidated credentials pack |
| **workbooks** (`.xlsx`) | 9 | BOQ, ageing, trial balance, asset register — with live formulas |

Plus:

- `document_index.csv` — `doc_id`, `doc_type`, `filename`, `size_bytes`. **It deliberately does not
  tell you which document is about which project or client.** Working that out is part of the task.
- `questions.json` — **the 371 questions you must answer.**
- `sample_questions.json` — 23 worked examples with answers and reasoning, to calibrate against.
- `evaluate.py` — the exact scorer we will run, so you can measure yourself.
- `sample_submission.csv` — the submission format.

### What you are deliberately NOT given

No database, no knowledge graph, no schema, no extracted fact table, and no mapping from documents to
entities. If we handed you a database this would be a SQL exercise. The interesting problem is
getting structured, queryable knowledge **out of** 687 unstructured documents — so that is the part
we left for you.

---

## What you have to build

A system that takes a question in plain English and returns a number.

The questions are written the way people on a bid desk actually ask them — sometimes a formal note,
sometimes a hurried message before a deadline. They are not templated, and no two are phrased alike.

Answering them generally requires **several documents at once**. A typical question names an
engineer's certificate, expects you to find which project that engineer led, work out which client
commissioned it, gather *every* project for that client, and total their values — where each value
must be read out of that project's own certificate. Four documents minimum, often more.

**Three things make this harder than it first looks:**

1. **Money is written the way people write it.** A contract worth 333,800,000 rupees appears in
   documents as `INR 33.38 Cr`, or `3,338.00 Lakh`, or `33,38,00,000` in Indian digit grouping. Your
   extraction has to handle all of it. (The rendering is lossless — no precision is hidden from you.)

2. **Some facts exist only in prose.** Names, dates and written observations appear in the text of a
   certificate and nowhere else — no table holds them.
   *(Questions that filter on a client's written **grading** have been withdrawn from this release:
   the gradings are not stated consistently across the certificates. Reported by a participant.)*

3. **Absence is a real answer.** "How many completed works have no reference letter on file?"
   requires proving something is *missing* across a client's whole portfolio. A system that
   hallucinates connections will confidently say zero.

---

## What the questions look like

All 23 examples are in `sample_questions.json`, with answers and a step-by-step derivation. Three of
them:

> **Regarding Asha Nair’s PMP work on the Cable Stayed Bridge — Jharkhand Pkg-115, what is the defensible average size across all completed projects for the commissioning client?**
> → `537933333`

> **Cross-checking the completion date against Asha Nair's PMP for 2021-03-10, what number of days passed from issuance to finish for School Building — Madhya Pradesh Pkg-145?**
> → `1569`

> **Jal Nigam, Jharkhand is our starting point for the audit, so what whole number out of one hundred represents the defensible share of completed assignments that carry formal verification on file?**
> → `33.33`

Each sample carries `reasoning_steps` showing the path from question to answer, and the individual
values that had to be read out of documents along the way. Use them to calibrate — they are the same
kinds of question you will be scored on, only easier.

**Answers are always a plain number**: rupees (no units, no commas), a count, a percentage out of
100, or a number of days. Every question states which.

---

## The questions to answer

`questions.json` contains **371 questions**. Answer every one of them.

```json
{"qid": "HV-IC-0001", "question": "Starting with Rajesh Rao's Six Sigma Black Belt ...", "answer_type": "money"}
```

`answer_type` tells you the unit expected: `money` (rupees), `count`, `percent` (a number out of
100), or `days`.

---

## How to submit

A **CSV file** with a header row, one row per question:

```
question_id,answer
HV-IC-0001,2942400000
HV-IC-0002,1516600000
HV-IC-0003,90.19
```

- **`question_id`** — exactly as given in `questions.json` (e.g. `HV-IC-0001`)
- **`answer`** — a plain number. No commas, no currency symbols, no units, no text.
  - money → `2942400000`, not `INR 294.24 Cr` or `2,942,400,000`
  - percent → `90.19`, not `0.9019` or `90.19%`
  - count → `5`
  - days → `1388`
- Decimals are fine where the answer needs them. Round percentages to two places.
- **Answer all 371.** An unanswered question scores 0, and a wrong answer costs nothing extra —
  there is no penalty for guessing.
- Row order does not matter. Extra columns are ignored.

---

## Scoring

Each question is scored on how close you are:

```
score = max(0, 1 - |your answer - correct answer| / correct answer)
```

Your final score is the average across all 371 questions.

| your answer is | score |
|---|---|
| exact | **1.00** |
| 1% off | 0.99 |
| 5% off | 0.95 |
| 25% off | 0.75 |
| 50% off | 0.50 |
| 100% off or worse | 0.00 |

There are no bands and no cut-offs — every bit closer earns more. A system that reasons correctly
and misses one contributing document still scores well; one that guesses does not.

Check your own submission format before you send it:

```bash
python evaluate.py --self-test                                   # confirm the scorer
python evaluate.py --submission my_answers.csv \
                   --questions sample_questions.json             # score against the samples
```

---

---

## Tie-breaker

The top ten teams on the leaderboard will be asked to submit the code for their harness. We will run
that harness against a further set of hidden questions, and the final leaderboard will be published
on those results.

## Rules

- **The corpus is synthetic.** The company, people, clients and projects were generated. Searching
  the internet for "National Infrastructure Corp" will not help you, and any real company by a
  similar name is unrelated.
- **Identifiers are intentionally invalid.** The CIN, GST and PAN numbers fail their check digits by
  design. Do not use them to look anything up.
- **Everything you need is in `documents/`.** Every value required by every question was verified to
  be readable from the shipped documents before the question was accepted. If you cannot find
  something, it is a retrieval problem, not a missing file.
- Use any tools, models or libraries you like.

---

## Getting started

1. Read three or four completion certificates by hand. Notice how the value, dates, client and
   grading are laid out, and how much the layout varies between documents.
2. Open `sample_questions.json` and follow one `reasoning_steps` chain through the actual PDFs.
3. That will tell you what your extraction has to produce. Build that, then build the reasoning on
   top of it.

Good luck.
