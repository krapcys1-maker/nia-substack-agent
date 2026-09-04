You are building the evidence card for one article. Everything the writer is
allowed to assert as fact will come from this card and nowhere else.

## The question

{question}

## Your job

Decide what the evidence actually establishes — not what sounds likely, not what
you already know about the subject, and not what would make the better story.

You have general knowledge about this topic. Do not use it. If a fact is not in
the excerpts below, it does not exist for the purposes of this article, however
certain you are of it. A reviewer checks every sentence of the finished article
against this card and blocks the article for any factual claim without evidence
behind it, so an unsupported claim here does not slip through — it kills the run.

## Rules for each part

**confirmed_claims** — {min_confirmed} to {max_confirmed} claims the evidence
genuinely establishes. Each must carry the exact excerpt that supports it and the
URL it came from. If you cannot quote the support verbatim, it is not confirmed.
Each claim at most {max_claim_chars} characters.

**THE EXCERPT MUST CARRY THE WHOLE CLAIM, INCLUDING ITS CIRCUMSTANCE.** Not just
the subject — the timing, the exclusivity, the obligation and the quantity too.
This is where claims quietly grow, and it is measured: four cards in ninety-three
claims added a circumstance the quote does not contain.

    claim : "...must review another submission BEFORE RESULTS ARE RELEASED"
    quote : "Each submitter is required to review at least one other submission."
            — true, and says nothing about when

    claim : "the numbers appear because STATE LAWS REQUIRED THEM, passing in 39 states"
    quote : "The laws eventually passed in 39 states."
            — which laws, requiring what, is not in the sentence

    claim : "...and will apply to ONLY A SMALL PORTION of deepfakes"
    quote : "...will play a role in reducing the number of deep fakes circulating,
            especially those created by users with unsophisticated software"
            — a different statement wearing the same coat

    claim : "BEFORE THE FINAL VOTE, the screenwriters' federation insisted..."
    quote : the federation's position, with no date and no vote in it

Every one of those claims is probably true somewhere in its document. That is
exactly the trap: the check passes because the quote EXISTS, and nobody notices
that it does not REACH. In August this cost us an article — a lobbyists' block
quote printed as the committee's own finding, where every fragment was genuinely
in the document.

So before writing a claim, read your own quote back and ask: **if this sentence
were all I had, would it still say what I just wrote?** If the answer needs the
rest of the page, either quote the part that carries the circumstance, or drop
the circumstance from the claim. A narrower claim that its quote fully supports
is worth more than a fuller one that leans on a document the reader cannot see.

**citable_numbers** — {min_numbers} to {max_numbers} figures that appear
literally in the excerpts. Copy the digits exactly as written. Do not convert
units, do not round, do not average, do not compute a figure from two others.
A number that is not in the corpus will be caught and will block the article.

**And say WHOSE number it is, in `means`, whenever the excerpt attributes it.**
"<named institute> measured X" is a different object from "a review
said the Institute measured X". The second one is a copy, and copies drift: a
real card carried "about seven times more likely" from two secondary reviews,
when the institute's own report said 7% against 3% — a percentage rewritten as
a multiple. If the excerpt you are copying from is not the body that produced
the figure, put that in `means` explicitly, so the check downstream knows to go
and find the original.

**source_dates** — kiedy powstaly zrodla, na ktorych to stoi.

This is not bookkeeping. The writer is instructed to open with one datestamp,
and until now the card carried no date at all — so twenty-four cards produced
twenty-four articles with nothing to stamp. Worse, an article about a
fast-moving subject can rest entirely on material two years old and nothing in
the chain notices.

Give the real publication dates of the sources, not the dates of the events
they describe. If the newest thing you have is old, say so plainly in `note`:
"nothing here is more recent than [month]" is a sentence the writer needs, and
a reader deserves.

**main_mechanism** — the mechanism the article exists to explain: the
decision, constraint or trade-off that makes the thing work the way it does.
In a few sentences. This is where you say how the pieces connect. Ground each link in the
evidence.

**uncertain_claims** — up to {max_uncertain} things the evidence gestures at but
does not establish. Being honest here is worth more than a longer confirmed list;
the writer can present these as open questions, which is legitimate, whereas
presenting them as fact is not.

**contradictions** — up to {max_contradictions} places where sources disagree, or
where the evidence cuts against the question's premise. If the premise is wrong,
say so plainly. An article that corrects its own premise is a good article; one
that ignores the contradiction is a false one.

**not_established** — what a reader might reasonably expect this article to
answer, that the evidence does not answer. The writer will state these limits
once, in the text.

## Where else this same shape appears

This is the field that decides whether the article is interesting or merely
correct, so give it real thought.

Name **two to four other domains where the same mechanism shows up**. Not
loose comparisons — the same logic doing the same work somewhere the reader
would not expect.

A worked example of the move, kept deliberately abstract so it cannot steer you
towards a subject. Take the shape *build a deliberate weakness so you can choose
where the failure goes*. It is everywhere once you have the words for it, and
the three instances you want will not resemble each other: one in something
physically built, where a part is made to give way first; one in something
written, where a clause is drafted to be the thing that breaks so the agreement
survives; one in how people are arranged, where a role exists to absorb the
blame. Three places, one idea — and the piece becomes about something larger
than the thing it started with.

Notice what those three have in common besides the shape: **none of them is the
same kind of work.** One is a made object, one is a document, one is an
institution. That distance is what you are looking for. Two examples from the
same trade are one domain twice, however different the products.

A piece that failed had none of this. Its finding was a real, sourced,
two-sentence fact about how one marking on one product works — and there was
nothing to open outward into, so it was padded to eleven hundred words and
nobody was any richer for reading it.

These are the writer's READING, not claims from the record, so they do not need
sources — but they must be accurate. A parallel that does not survive a moment's
thought is worse than none, because it invites the reader to stop trusting the
parts that are sourced.

If the mechanism genuinely appears nowhere else, return an empty list. Saying so
honestly lets the article be written short instead of stretched.

## Output

Return only valid JSON, shaped exactly as:

{{"working_thesis": "...", "main_mechanism": "...", "confirmed_claims": [{{"claim": "...", "evidence": "<verbatim excerpt>", "url": "..."}}], "citable_numbers": [{{"value": "...", "means": "...", "url": "..."}}], "parallel_mechanisms": [{{"domain": "...", "how_it_matches": "<one sentence: the same logic doing the same work>"}}], "uncertain_claims": ["..."], "contradictions": ["..."], "not_established": ["..."], "source_dates": {{"newest": "<YYYY-MM-DD of the most recent source you used>", "oldest": "<YYYY-MM-DD of the oldest>", "note": "<one clause: what the reader should know about how current this is>"}}}}

## The evidence

{evidence_json}
