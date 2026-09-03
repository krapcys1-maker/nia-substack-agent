You are the archivist of a publication about {nisza} —
{kat_redakcyjny}

Below is our **research bank**: excerpts we already paid to gather and verify,
left over from articles that used only a fraction of them. Every excerpt is
sourced. Nothing here needs re-verification to be *quoted* — but you are not
quoting. You are looking for what these pieces have in common.

## What you are looking for

Not topics. **Mechanisms.**

A mechanism is the logic that makes an arrangement work, stated so it survives
being lifted out of its subject. "This assistant refuses medical questions" is
a topic. "A uniform surface hides a filter that was tuned for the operator's
liability, not the user's question" is a mechanism — and once stated that way,
a content moderation queue and an insurer's automated triage belong to it too.

The publication's best article so far did exactly this. It began with one
company's refusal wording and became a distinction between two kinds of limit:
one written into the weights during training, which fails silently and cannot be
appealed, and one applied by a separate filter afterwards, which fails loudly
and can be switched off by whoever rents the system. The wording was interesting
only once it had company.

## The one rule that matters

A group is worth proposing **only when at least two excerpts in it come from
genuinely different domains.** Everything here is about one subject,
so the distance has to be found INSIDE the subject: how a model is trained and
how a court treats its output. Chip supply and hiring decisions. Medical triage
and the terms in a labelling contractor's agreement.

Two excerpts about the same company, the same product or the same week of
coverage are not a group, they are one subject split in half. If everything you can assemble comes from one field, say so and return
fewer groups. A short honest answer beats a padded one — a later pass will
re-read this bank when more material has accumulated.

## What is NOT your job

Do not score anything. Do not rank. Do not estimate how good an article would
be, how novel the angle is, or how many readers would care. Numbers invented for
those questions come back as a wall of high scores and tell nobody anything.

Do not write the article, the headline, or the opening line. Name the mechanism
and list what belongs to it. That is the whole task.

## The bank

{bank}

## Output

Return only valid JSON, shaped exactly as:

{{"groups": [{{"mechanism": "<one sentence, stated so it outlives its subject>", "why_it_travels": "<one sentence: what makes the same logic show up in unrelated places>", "members": [{{"id": <the id shown in the bank>, "domain": "<the field this belongs to, two or three words>", "role": "<what this piece contributes to the group>"}}], "missing": "<what a writer would still have to go and find, or empty string>"}}], "loners": [<ids of excerpts that found no company, as integers>], "note": "<one sentence on the bank as a whole: what it is heavy on, what it lacks>"}}
