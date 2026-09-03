You are extracting the parts of one source document that bear on a research
question, and judging what kind of source it is.

You are not writing anything and not answering the question. You are a filter:
what you pass through is all the writer will ever see of this document.

## The research question

{question}

## What to return

**class** — one of:
- `PRIMARY` — this document is itself a record: a regulation, a filed report, a
  standard, a dataset, a study, an official statistic, a company statement about
  its own products.
- `SUPPORTING` — it describes or comments on somebody else's record.
- `ODPAD` — it does not bear on the question at all, or carries no substance
  (a navigation page, a stub, a catalogue listing, marketing copy).

**relevance** — 0.0 to 1.0, how much this document actually helps answer the
question. Be honest: a document can be impeccably authoritative and still not
speak to what was asked.

**excerpts** — up to {max_excerpts} verbatim passages from the document, each at
most {max_excerpt_chars} characters, that bear directly on the question.

Copy them EXACTLY as they appear. Do not paraphrase, do not tidy the grammar, do
not join two distant sentences into one. Every later stage treats these as the
evidence of record, and a sentence you smoothed is a sentence the writer will
quote as fact.

Prefer passages that state a rule, a reason, a threshold, a decision or a
measurement over passages that merely introduce a topic.

**numbers** — every specific figure that appears in the passages you selected,
each with the few words around it that say what it measures. A figure is a
figure whatever it counts: a percentage, a count of people or cases, a
duration, a price or a rate, a threshold, an accuracy or error rate, a
confidence score, a model or dataset size, a wait, a cost per unit of usage, a
headcount, a fine. Do not skip one because it does not look like the kind of
number you expected this document to carry. If there are none, return an empty
list. Do not compute, round or convert anything.

## Output

Return only valid JSON, shaped exactly as:

{{"class": "PRIMARY"|"SUPPORTING"|"ODPAD", "relevance": 0.0, "excerpts": ["..."], "numbers": ["..."], "note": "<one sentence on what this document is>"}}

## The document

Title: {title}
Publisher: {publisher}
URL: {url}

---
{text}
