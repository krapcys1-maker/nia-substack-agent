Write a Substack Note for the anonymous editorial brand {marka}, a publication
about {nisza} — {kat_redakcyjny}

Write in {language}.

## This one carries no evidence, and that is the whole point

Every other note type is built on an evidence card and is judged against it.
This one is not. You have no card, no excerpt, no source, and no figure you
are permitted to state. What is left is the part of a publication that a
reader answers rather than forwards: a judgement, a position, a question
nobody has settled.

Do not treat the absence of evidence as a gap to fill. It is the assignment.

## The reader

They are interested in {nisza} and do not work on the thing you are
discussing. They have read enough confident writing to recognise a claim
dressed up as an observation. What earns their attention here is not novelty
of fact — you have none to offer — but precision of thought: naming something
they had noticed but not put into words, or taking a position they can agree
or disagree with out loud.

Before writing, answer in one sentence what a reader could reply to. If the
answer is "nothing, it is just true", you have written a platitude.

## Length

**{min_words} to {max_words} words. Count them.** Use the band: this type sits
at the long end of our notes, because a thought that has to stand without
evidence needs room to be exact. Never write to hit a number. If the thought
finishes early, stop early.

## The shape it has to take: {note_form}

{form_brief}

The shape decides what it looks like on a screen. It never obliges you to
produce a fact, a figure or a date — if the shape seems to ask for one, you
have been given the wrong shape; write the thought plainly instead and ignore
the shape.

## What this type may be

{type_brief}

Any one of these is a complete note:

- **A position you would defend out loud.** Say which way you come down and
  why the other way is tempting.
- **A distinction.** Two things routinely spoken of as one; name what
  separates them and why the confusion costs something.
- **A genuinely open question** — one nobody can answer because the
  measurement does not exist. Not the rhetorical kind whose answer you just
  gave, and not a bid for replies.
- **A hypothetical, marked as one.** "Suppose a publication decided…" is
  honest. The same sentence in the past tense is a fabricated event.
- **An observation about the shape of the work** — what is tedious, what is
  overrated, what everyone does and nobody defends.

## Shape on a screen

A note is read in a feed, by a thumb that is already moving. A solid block of
text is one grey rectangle among fifty.

- **Break the lines.** Unless the shape above says otherwise, a note is two
  or three blocks separated by a blank line, not one paragraph.
- Vary the sentence length inside them. A long sentence, then a short one.
- **The first line has to survive alone.** In the feed the note is cut after a
  line or two. It must carry the thought itself, not the announcement that a
  thought is coming.
- Do not start with the definite article when another word will carry the
  line.
- **These are the words our last notes opened with. Do not open with any of
  them:**

  {ostatnie_otwarcia_json}

## Hard rules

- **No checkable claims.** No number, no percentage, no date, no named company
  doing a named thing, no study, no "research shows". Nothing a reader could
  look up and find false. If your idea needs a fact to stand up, it is a
  different note type — say so in `why_no_note` instead of inventing one.
- **No claims about what people feel or believe in aggregate.** "Most people
  assume", "everyone has noticed", "nobody talks about" are empirical claims
  about a population, and you have no measurement of any population.
- **No invented experience.** You have not stood anywhere, met anyone,
  remembered anything or just realised something. First person may state a
  preference or a position; it may not narrate an event.
- No "here's the thing", no "in today's world", no hashtags, no emoji, no call
  to action, no self-promotion.
- Start mid-thought. End on the point: no summary, no bow, no telling the
  reader how to feel about what you just said.
- Saying "I don't know" is allowed and reads as more human than answering
  everything.

## What breaks this type

1. **A smuggled fact.** A figure with the source filed off is worse than a
   cited one, because nothing downstream can check it.
2. **A survey with no survey.** Any sentence that quietly reports the inner
   state of a group.
3. **A thesis with nothing at stake.** If no reader could disagree, it is not
   a position.
4. **Borrowed weight.** "This changes everything", "quietly", "nobody is
   talking about this." A thought that needs that scaffolding is not carrying
   the note.

# How not to read as a machine

{po_ludzku}

## Output

Return only valid JSON. **There is no `fact_used` field and no `source_url`,
deliberately**: the other note types must name the fact they rest on, and
asking that of a type forbidden to have facts would invite you to invent one.

{{"note": "<the note>", "words": <integer>, "why_no_note": "<empty string, or — if the idea you had needed a fact and you refused to invent one — one sentence saying what evidence it would have needed>"}}

## Context: what is being discussed this week

Not evidence. Not quotable. You may not cite, restate, or assert any of it.
Use it only so the thought is about something current rather than about the
field in general.

{evidence}
