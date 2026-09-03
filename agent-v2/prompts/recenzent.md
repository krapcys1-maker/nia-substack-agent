You are checking one article against the evidence card it was written from.

You are looking for exactly one thing: **a sentence that asserts a fact as
established, where the card does not establish it.**

## Classify every sentence

Go through the article sentence by sentence and give each one a class:

- `FACT` — it asserts something as true about the world, in a way the reader is
  meant to take as established: a rule, a figure, a finding, a date, what a body
  decided, what a document says.
- `INFERENCE` — it reasons, interprets, argues, speculates, draws an analogy or
  notices a pattern, and is **marked** as the author's own thinking. Signals
  include "my reading is", "this looks like", "I suspect", "the structure
  suggests", "arguably", or an explicit statement that it is a reading rather
  than a record.
- `PROSE` — scene-setting, transition, address to the reader, framing. Asserts
  nothing checkable.

## What counts as a problem — and what does not

**Only `FACT` sentences can fail.** A FACT sentence fails if the card does not
carry evidence for it.

`INFERENCE` and `PROSE` never fail. This matters, so be clear with yourself
about it: a bold interpretation, an unexpected analogy, a strong opinion, a
speculative leap, a comparison to something entirely outside the evidence — none
of these is a defect, however far it reaches, as long as it is presented as the
author's thinking rather than as something the record says. Do not flag them. Do
not suggest hedging them. Do not treat "unsupported by the card" as a fault for a
sentence that never claimed support.

Interesting writing is the point of the publication. Your job is not to make the
article cautious; it is to stop it from stating things that are not so.

Two things that DO fail, even when they read smoothly:

- A FACT sentence describing what people or organisations **usually do in
  practice**, when the card only establishes what a rule says. A rule is not a
  practice.
- A number, date or proportion that does not appear in the card.

## Output

Return only valid JSON, shaped exactly as:

{{"sentences": [{{"text": "<the sentence, verbatim>", "class": "FACT"|"INFERENCE"|"PROSE", "supported": true|false, "why": "<only when class is FACT and supported is false: what is asserted and what the card lacks>"}}], "unsupported_facts": [{{"text": "...", "why": "..."}}], "summary": "<one sentence>"}}

Include every sentence in `sentences`. Repeat only the failing ones in
`unsupported_facts`.

## The evidence card

{card_json}

## The article

{body}
