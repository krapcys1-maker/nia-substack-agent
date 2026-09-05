Find {ile} documented facts worth stopping a stranger mid-scroll.

Search for them. Do not write from memory: a fact you cannot put a source
against is not a fact you can use here.

## What this publication is

{marka} is a publication **about {nisza}** — {kat_redakcyjny}

It is not a publication about how badly designed everything is. A fact
qualifies in four ways, not one: something real happened and almost nobody
has explained it properly (the default, and the most valuable); it works, but
not for the reason people say; the interesting thing is next to the announced
thing, uncounted; a claim does not survive its own record. If everything you
return is the fourth kind, the batch is wrong even when every item is true.

Do not manufacture the assumption. "Everyone assumes X" is a claim about what
people believe, with no figure to check and no source to miss. If you cannot
point to where the belief is visibly stated (a headline, a product page, a
press release), the fact stands on its own without one.

## What this publication looks for, in its own words

{linia_redakcyjna}

## Happening right now: this takes precedence

{wydarzenia}

An item here means three or more independent channels covered the same thing
within the last four days. Give it first claim on your search, then do our job
on it, not theirs: the event tells you when the reader is looking this way,
not what to write. Take it as the occasion and find the mechanism, the number,
the decision or the constraint nobody else bothered with. A fact drawn from a
live event still has to clear everything below. If the event yields nothing
that clears the bar, drop it and work the grid.
{premiera}
## What the field is talking about this week

Real video titles from the channels this publication follows, with the dates
they went up. Hype wrapping stripped; what is left is roughly the event.

{zaczyn_kanalow}

Use this list for what is live, never as a source. A video title is not
evidence of anything. Take a subject from here, then go and find the document:
the filing, the paper, the pricing page, the court record, the changelog, the
maker's own technical note. Your `url` and `source_date` must point at that
document, never at a video. If you cannot find a document, drop the subject.

**Three quarters of what you return must start here, and this is counted by
code:** your facts are compared against this list after you return them. Take
the claim in the headline and be the one who checks it. Five hundred channels
will repeat that the new thing beats the market leader; nobody will open the
specification and say what the number was, who measured it, under which
conditions, and what the comparison leaves out. Prefer items from the last two
weeks. Do not tell yourself the week was thin: a headline that sounds like
hype is still somebody saying something, on a date, in a place, which is
checkable.

## How much searching is enough

**Stop searching once you have {ile} facts you can source, and write the
JSON.** Everything below describes what a good fact looks like; it is not a
checklist to satisfy item by item before you may answer. If a search comes
back thin, take the fact you already have and move on. Five solid facts beat
eight you never got to write down.

## Where to look this time

The live subjects above are the material. These areas are the lens you look
through, not a second place to go shopping. Point them at the live subjects:

{dziedziny}

They rotate every run, so the same subject seen through a different lens gives
a different fact. The last quarter of your facts may come from these areas
alone, with no live subject behind them.

## What shape to look for

The areas tell you where to look. They do not tell you what you are looking
for, and that is why searching for "interesting facts" returns trivia. A
candidate is produced by applying a named pattern to a named area:

{generatory}

Work the grid on the week's subjects: take a live subject, pick a pattern, and
ask the pattern's probe question of that subject; the area tells you which
aspect of it to press. Most cells will be empty. That is expected; the point
is that the full ones are found on purpose rather than by luck.

## A third way in: a fact that settles a question people actually ask

A fact also qualifies when it moves a big question, the kind a reader asks
about our subject without having a job in the field: what the thing really is
as opposed to what it is called; whether a difference anybody can name
survives measurement; whether it behaves differently when it knows it is being
watched; who is actually served by the arrangement everyone treats as natural.
Those are examples of a KIND, not a list to work through, and a question is
not better for appearing here.

The question is a frame. The fact inside it still needs a source, and that
rule does not soften because the subject got large. An opinion about a big
question is worth nothing here. A named test and what it returned, a behaviour
somebody wrote down in their own documentation, two named people reading the
same result the opposite way with a date on the exchange: those are worth
something, and the question is what makes a stranger care that they exist. The usable shape is question, then evidence that moves it, never the
question on its own. If the strongest thing underneath is that people
disagree, you have found a debate, not a fact.

The output fields still apply, and this is exactly where a big question dies:
a question phrased as "is it really X" names no decider, no date and nothing
the reader can see. The version that survives says what makes it so, and here
that is usually a measurement rather than a decision: what was tested, what
came back, on which date. If you cannot fill `decision` and `consequence`, the
question was the whole idea and there was no fact under it. One or two in a
batch, not the batch: a run where every fact sits under a big question is as
narrow as a run of nothing but debunkings.

## Today is {dzis}. Check the age of everything.

This subject moves fast, and a fact that was true eighteen months ago can be
false, retired or embarrassing today. Your memory ended months ago and does
not feel like a gap from the inside. Three rules:

- Give the publication date of every source in `source_date`: the date the
  page you read was published, not the date of the thing described. A page
  with no date is a page you cannot vouch for.
- Anything that claims how the world is right now (prices, availability, what
  is fastest, what is standard, what is newest) must come from the last three
  months.
- A fact about an event stays good. A court ruled, a study was published, a
  law passed, a system was built and measured: say when it happened and the
  fact keeps working for years.

## The control document: a second date, and the one that decides

`source_date` says where the fact came from. It cannot say whether the fact is
still true, and the more permanent the source looks, the less it tells you: a
founding statute, a landmark investigation and a peer-reviewed paper all keep
existing long after the arrangement they describe has been renegotiated,
cancelled or overtaken. So for every fact, name the newest document that
would have to change for the claim to stop being true, with its date and URL,
and say what it does to the claim:

- `CONFIRMS`: the governing document still says what the claim says. The age
  of your original source then stops mattering.
- `MODIFIES`: still broadly true, but something narrows, conditions or
  complicates it. `control_fact` carries the qualifier in one clause, and the
  writer is required to say it in the same breath as the claim.
- `ENDS`: the arrangement is over. Offer the fact anyway and put what happened
  in `control_fact`; a dead arrangement is a subject with an ending, which is
  usually the most interesting part. What is forbidden is presenting it as the
  way things are.

The control document does not have to be newer than your source. It has to be
the one that governs. If you search and genuinely find nothing that governs
the claim more recently, say so in `control_fact` and use `CONFIRMS`; leaving
the field empty because you did not look is not acceptable. Watch the
comparative clause hardest: "neither the US nor the EU", "more than half of",
"the only country that" each need their own control document, or must come
out.

**What exists right now, looked up today rather than remembered:**

{stan_modeli}

Anything not on that list either does not exist yet or is already gone. If a
source names something you cannot find above, that source is old. Never name a
version, price, rule or product you have not checked is current, and never
build on something that is being switched off: anything scheduled to end, the
reader will have to unlearn within weeks.

## Where attention is pointed this month

It is {miesiac}, and this is roughly where the field's attention sits:

{w_reku}

Something the reader has just seen mentioned beats the same fact raised cold.
Do not force it, and treat these as places to look, not facts to repeat:
dates move, launches slip, rules get postponed.

## Do not make everything one country

A rule from the EU, Japan, Brazil or India is not a lesser fact, and a rule
that differs between two countries is the strongest kind this publication
has, because the difference itself proves somebody decided.

## What makes a fact usable

- It is about something the reader already meets: a pricing rule, a queue, a
  standard, a default setting, a piece of infrastructure they walk past.
- Something makes it so, and you can name what. Four mechanisms, all equally
  admissible: a decision (someone chose, and they have a name and a date); a
  measurement (someone tested it and the number came back); a constraint (it
  falls out of how the thing is built, and no one chose it); a trade-off (an
  engineering choice with a cost somebody is paying, usually quietly).
  Measurements and constraints are where this field is most interesting. If
  every fact in a batch names an institution, the batch is wrong even when
  every item is true.
- It survives being looked up. Prefer the primary document (a filing, a
  standard, a regulation, a court record, a company's own statement) over an
  article describing one.

Avoid facts that trace back to nothing but listicles quoting each other; the
famous ones a reader has already met three times; anything where the
surprising version is the debunked version; pure numbers with no decision,
measurement, constraint or trade-off behind them.

Aim wide: {ile} facts spread across different live subjects, not {ile} angles
on one. If two of your facts share a mechanism, drop one and go elsewhere.

## Already used

These have been published already. A near-miss counts as a repeat: the same
regulation from another angle, the same object with a different number, the
same mechanism in a neighbouring industry. Go somewhere else entirely.

{uzyte}

## Output

Return only valid JSON:

{{"facts": [{{"fact": "<one or two sentences, the fact itself, specific and checkable>", "wrong_belief": "<what most people believe, written as a plain sentence they would say out loud>", "actually": "<what is true instead, one sentence>", "decision": "<WHAT MAKES IT SO: a decision (who signed it and when), a measurement (who tested it and what came back), a constraint (what about the design or the mathematics forces it), or a trade-off (what is given up and by whom). Not necessarily a person or an institution. Empty string only if you cannot name any of the four>", "consequence": "<the thing the reader can touch, hold, see or wait for because of that decision>", "url": "<source that states it>", "source_date": "<the date THAT SOURCE was published, as YYYY-MM-DD. Not the date of the event it describes. Empty string only if the page genuinely carries no date>", "control_date": "<YYYY-MM-DD of the newest document that GOVERNS this claim — see \"The control document\" above. Not necessarily newer than source_date>", "control_url": "<url of that document>", "control_verdict": "CONFIRMS"|"MODIFIES"|"ENDS", "control_fact": "<one clause. For MODIFIES, the qualifier the writer must carry. For CONFIRMS, what you checked and found unchanged>", "domain": "<the part of the field, industry or public record it belongs to>"}}]}}

## The two halves, and why a fact without both is worthless

`wrong_belief` and `actually` are not decoration. A candidate that cannot fill
both is trivia, and trivia is discarded before anybody writes it. A serial number
is a fact, checkable, and dead: nobody holds a belief about it, so there is
nothing to break and nothing to reply to. A fact is alive when the reader
already believes the opposite without ever having checked.

**Phrase the consequence as a thing the reader has, using the word "your".**
Not "the charge is applied per unit consumed" but "the line on your bill".
Not "complaints are reviewed in batches" but "the reason your request was
never answered". This is checked in code: a consequence without
"your" is rejected before anything is written, because it means you named a
category of people rather than something the reader is holding.

`decision` holds whatever makes the fact so: the decision, the measurement,
the constraint or the trade-off. A mechanism with no consequence the reader
meets is administrative history; a consequence with no mechanism behind it is
a curiosity. Test each candidate before returning it: can you say *"most
people think X, actually Y, because Z"* in one breath, where Z is one of the
four? If not, leave it out and find another. Ten candidates that pass are
worth more than thirty that do not.
