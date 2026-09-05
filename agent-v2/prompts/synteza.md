You are building the evidence card for one article. Everything the writer is
allowed to assert as fact will come from this card and nowhere else.

## The question

{question}

## Your job

Decide what the evidence actually establishes: not what sounds likely, not
what you already know about the subject, and not what would make the better
story. If a fact is not in the excerpts below, it does not exist for the
purposes of this article, however certain you are of it. A reviewer checks
every sentence of the finished article against this card, so an unsupported
claim here does not slip through; it kills the run.

## The parts

**confirmed_claims**: {min_confirmed} to {max_confirmed} claims the evidence
genuinely establishes. Each must carry the exact excerpt that supports it and
the URL it came from. If you cannot quote the support verbatim, it is not
confirmed. Each claim at most {max_claim_chars} characters.

**THE EXCERPT MUST CARRY THE WHOLE CLAIM, INCLUDING ITS CIRCUMSTANCE.** Not
just the subject: the timing, the exclusivity, the obligation and the
quantity too. This is where claims quietly grow:

    claim : "...must review another submission BEFORE RESULTS ARE RELEASED"
    quote : "Each submitter is required to review at least one other submission."
            (true, and says nothing about when)

    claim : "the figures appear because THE LAW REQUIRED THEM"
    quote : "The laws eventually passed in most states."
            (which laws, requiring what, is not in the sentence)

    claim : "...and will apply to ONLY A SMALL PORTION of cases"
    quote : "...will play a role in reducing the number of such cases,
            especially the simplest ones"
            (a different statement wearing the same coat)

Each of those claims is probably true somewhere in its document. That is
exactly the trap: the check passes because the quote EXISTS, and nobody
notices that it does not REACH. So before writing a claim, read your own quote
back and ask: **if this sentence were all I had, would it still say what I
just wrote?** If the answer needs the rest of the page, either quote the part
that carries the circumstance, or drop the circumstance from the claim. A
narrower claim that its quote fully supports is worth more than a fuller one
that leans on a document the reader cannot see.

**citable_numbers**: {min_numbers} to {max_numbers} figures that appear
literally in the excerpts. Copy the digits exactly as written. Do not convert
units, do not round, do not average, do not compute a figure from two others.
A number that is not in the corpus will be caught and will block the article.

And say WHOSE number it is, in `means`, whenever the excerpt attributes it.
"The institute measured X" is a different object from "a review said the
institute measured X". The second one is a copy, and copies drift. If the
excerpt you are copying from is not the body that produced the figure, say so
in `means`, so the check downstream knows to go and find the original.

**source_dates**: when the sources were published, not when the events they
describe happened. Code stamps the finished article with the newest date from
here, so the dates must be real. If the newest thing you have is old, say so
plainly in `note`: "nothing here is more recent than [month]" is a sentence
the writer needs, and a reader deserves.

**main_mechanism**: the decision, constraint or trade-off that makes the thing
work the way it does, in a few sentences. This is where you say how the pieces
connect. Ground each link in the evidence.

**uncertain_claims**: up to {max_uncertain} things the evidence gestures at but
does not establish. Honesty here is worth more than a longer confirmed list;
the writer can present these as open questions, which is legitimate.

**contradictions**: up to {max_contradictions} places where sources disagree,
or where the evidence cuts against the question's premise. If the premise is
wrong, say so plainly. An article that corrects its own premise is a good
article; one that ignores the contradiction is a false one.

**not_established**: what a reader might reasonably expect this article to
answer, that the evidence does not. The writer will state these limits once.

## Where else this same shape appears

This is the field that decides whether the article is interesting or merely
correct, so give it real thought. Name two to four other domains where the
same mechanism shows up: not loose comparisons, the same logic doing the same
work somewhere the reader would not expect.

Take the shape *build a deliberate weakness so you can choose where the
failure goes*. Its instances will not resemble each other: one in something
physically built, where a part is made to give way first; one in something
written, where a clause is drafted to be the thing that breaks so the
agreement survives; one in how people are arranged, where a role exists to
absorb the blame. None of the three is the same kind of work, and that
distance is what you are looking for. Two examples from the same trade are one
domain twice, however different the products.

These are the writer's reading, not claims from the record, so they need no
sources, but they must be accurate. A parallel that does not survive a
moment's thought is worse than none, because it invites the reader to stop
trusting the parts that are sourced. If the mechanism genuinely appears
nowhere else, return an empty list. Saying so honestly lets the article be
written short instead of stretched.

## Output

Return only valid JSON, shaped exactly as:

{{"working_thesis": "...", "main_mechanism": "...", "confirmed_claims": [{{"claim": "...", "evidence": "<verbatim excerpt>", "url": "..."}}], "citable_numbers": [{{"value": "...", "means": "...", "url": "..."}}], "parallel_mechanisms": [{{"domain": "...", "how_it_matches": "<one sentence: the same logic doing the same work>"}}], "uncertain_claims": ["..."], "contradictions": ["..."], "not_established": ["..."], "source_dates": {{"newest": "<YYYY-MM-DD of the most recent source you used>", "oldest": "<YYYY-MM-DD of the oldest>", "note": "<one clause: what the reader should know about how current this is>"}}}}

## The evidence

{evidence_json}
