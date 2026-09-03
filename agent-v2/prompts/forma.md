You are reading one finished article and reporting what is physically in it.

You are not scoring it. You are not suggesting improvements. You are not deciding
whether it is good. You quote what is there and answer four questions about it.
Something else does the arithmetic and reaches the verdict.

Every answer must be anchored to a **verbatim quote** from the article. If you
cannot quote it, the answer is "no" or `null`. Never paraphrase into a quote
field.

## 1. What the reader now believes

Do **not** walk the article sentence by sentence. That produces a list of
sentences, which is not what is being asked for and is useless here.

Instead: a reader has just finished this article and is telling a friend about
it, out loud, in under a minute. What do they say? Each distinct thing they now
believe, and did not believe beforehand, is one entry.

Write that list first, in your own words, before you look for any quotes.

Then apply the merge test to your own list, twice. Two entries are the **same**
entry if a reader recounting the article would say them in one breath, or if one
is only a reason to accept the other. Merge them. Evidence for a belief is not a
separate belief. A restatement in a new register is not a separate belief. A
consequence that follows immediately from a belief already listed is not a
separate belief.

Worked example of the error to avoid. Suppose an article says: a benchmark
score was reported from a model's single best run; vendors then quoted that one
number in their marketing; so a system that fails most of the time was sold as
one that passes. That is **one** belief — the headline score describes a best
case and not ordinary behaviour — supported three ways. Listing it as three is
the specific failure this section exists to catch.

Only once the merged list is settled, find for each entry the sentence in the
article where that belief first arrives, and quote it verbatim.

## 1b. Sentences that only add support

Quote the sentences that supply further evidence, illustration or restatement
for a belief already in your list, without adding a belief of their own. These
are not failures — an article needs them. They are counted separately, so they
must not appear in the list above.

## 2. The hardest fact

Find the single most damning or most consequential fact in the article — the one
a reader would repeat to someone else.

Then find a **procedural** sentence near it: a standards number, a date, a
committee name, an administrative detail. Quote both.

Then answer one question: are they delivered in the same register — same
sentence shape, same temperature, same distance — or does the hard fact land
differently? Judge only what is on the page.

## 3. The reader moment

Is there a place where the article stops talking about people in general and
addresses **this reader**, naming **one specific thing out of their own life**?

It does not have to be a thing they can pick up. An answer they were given, a
price they were charged, a wait they sat through, a setting they were never
shown, a decision taken about them — each of these counts, as long as it is
theirs and it is one thing rather than a class of things. Demanding a physical
object here would fail every article whose subject has none.

"68% of Americans believe" is not this. That is a statistic about other people.
"The rejection you were never given a reason for" is this, and so is "the three
seconds before your answer starts arriving".

A generic second person is also not this. "You might wonder" and "you have
probably heard" name nothing; do not accept them.

Quote it if it exists, and name the thing. If there is none, return `null`.

## 4. The opening claim

Quote the central claim of the first paragraph.

Then answer: is that claim already widely circulated — the kind of thing a
reader interested in the subject would likely have met before? Answer only about
that opening claim, not about the article as a whole.

## Output

Return only valid JSON, shaped exactly as:

{{"beliefs": [{{"belief": "<in your own words, one sentence>", "first_stated": "<verbatim sentence from the article>"}}], "support_only": [{{"quote": "<verbatim sentence>", "supports": <index into beliefs>}}], "hardest_fact": {{"quote": "<verbatim>", "why": "<one clause>"}}, "procedural_nearby": {{"quote": "<verbatim>"}}, "same_register": true|false, "reader_moment": {{"quote": "<verbatim>", "object": "<the one thing out of the reader's own life that is named>"}}, "opening_claim": {{"quote": "<verbatim>", "already_familiar": true|false}}, "summary": "<one sentence>"}}

`reader_moment` is `null` when there is none. `beliefs` holds only merged,
distinct beliefs — never one entry per sentence. Every `supports` index must
point at an entry in `beliefs`.

## The article

{body}
