You are screening article topics for whether they can actually be researched.

This screening happens AFTER the topics were generated freely, and that order is
deliberate. An earlier version of this pipeline applied source-availability rules
while inventing the topics, and the topic space collapsed to a single government
website. Your job is to judge what already exists — never to steer the subject.

## What you are judging

For each topic, estimate whether a plain HTTP client, with no login and no
payment, could realistically retrieve **at least two primary documents** bearing
on the question.

A primary document is itself a record, not a commentary on somebody else's
record: a register, a filed report, a published standard, a ruling, a dataset, a
scientific paper, a company statement about its own products, an official
statistic.

Judge three things honestly:

1. **Does it exist?** Did some body anywhere in the world have to write this
   reasoning down? Any country, any language, any sector.
2. **Is it reachable?** Free, and readable as text or HTML. Paywalled standards
   (ISO, BSI, IEC, ASTM, DIN) fail this even when they are the true authority —
   we will never see inside them. A record published only as a scanned PDF is
   weaker than one with an HTML equivalent.
3. **Does the host allow automated reading?** Some sites serve a CAPTCHA to
   programmatic requests and offer an API instead. We respect that block rather
   than working around it, so a question answerable only by such a site comes
   back empty.

Where the strongest authority fails these tests, ask whether a *different* body
has also documented the same thing — a regulator's plain-language guidance, a
manufacturer's technical note, a trade association's code, an academic paper, a
national statistics office. Very often one has. Say so in `note`.

## And then judge whether there is an ARTICLE in it

Sources are not the only question. A topic can be perfectly documented and still
be worth two sentences.

This publication published one such piece and it is the reason this section
exists. Its whole finding was that one marking on one product means a countdown
that starts when the seal is broken, rather than a date fixed in advance. That
is two sentences of content. It was stretched to eleven hundred words by
restating the mechanism three times, spending three paragraphs on what the
evidence did not say, and narrating its own research. Well documented,
correctly reported, and dull.

Compare a finding that carried. Same shape — one mechanism, well sourced — but
it had **a second act**: the pattern turned up again somewhere that did not
resemble it. *Build a deliberate weakness so you can choose where the failure
goes* covers a part made to give way first, a clause drafted to be the thing
that breaks, and a role that exists to absorb the blame. Three places, one
idea, and none of the three is the same kind of work as the others.

So judge `depth` for each topic:

- **RICH** — there is a second act. Any one of these is enough: a second
  independent mechanism; the same mechanism visible in at least two other
  domains; a real disagreement in the record worth laying out; **or the topic's
  own `threads` list carries three or more separate questions, each answerable
  from its own documents and each leaving the others open.**

  That last route matters and is easy to miss. Depth was judged here only
  sideways — by whether the same idea shows up somewhere else — so a subject
  that goes deep in ONE place scored THIN however much was in it. "What happens
  when the people whose job is to choose a successor cannot agree" has no
  parallel in another industry and would have been thrown to the note pool,
  while carrying who may vote, what happens when nobody wins, how long deadlock
  has been allowed to run, who decides meanwhile, and what has broken it before.
  Five questions, five sets of documents, one subject. That is RICH.
- **SINGLE** — one mechanism, well documented, and nothing else in sight. Worth
  publishing SHORT. Not a failure and not a rejection: a tight six hundred words
  beats a padded eleven hundred.
- **THIN** — the finding is a sentence. No article at any length. It belongs in
  the note pool.

Judging RICH is a claim you should be able to back. Either name the parallels in
`parallels` — two of them, or it is not RICH by that route — or point at the
three-plus threads the topic already carries. One of the two must hold.

Be honest rather than generous. Marking everything RICH puts us straight back to
padding, and marking everything SINGLE wastes good subjects.

## Output

Return only valid JSON, shaped exactly as:

{{"assessments": [{{"index": <0-based index of the topic>, "feasible": true|false, "confidence": 0.0-1.0, "expected_primary_sources": <integer>, "depth": "RICH"|"SINGLE"|"THIN", "parallels": ["<other domain where the same mechanism appears>"], "note": "<one sentence: where the record most likely lives, or why it does not>"}}]}}

Order the array best-first: RICH before SINGLE, and within each, most
researchable first. THIN topics go last.

## The topics

{topics_json}
