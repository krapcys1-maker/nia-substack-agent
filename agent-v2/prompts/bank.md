Rank these candidate facts against each other, strongest first, and say which
ones this publication should throw away.

{marka} is a publication **about {nisza}** — {kat_redakcyjny}

## You are RANKING, not scoring

Put them in order, best to worst. Every position is different; there are no
ties and there is no "all of these are good". Asked to score things one by
one, a model gives almost everything the same high mark and the ranking
carries no information. Asked to put them in order, it has to decide. The
order is the answer.

## What actually landed on this account

Our own notes with the reception they measurably got: likes, replies, and how
many people were shown them.

{co_zadzialalo}

Read the two groups against each other before you rank anything, and notice
what separates them rather than what they are about. Then say, for the ones
you put near the top, which side they resemble. Two warnings: views are not
success, because the measure that matters is whether anybody did something
that costs them a moment, and a reply costs more than a like; and do not copy
the subjects, copy what made them work.

## What makes one stronger than another

In roughly this order of weight:

1. **A stranger would stop scrolling for it.** Would somebody who does not
   work in this field read the second sentence?
2. **It is checkable and the check would be interesting.** A specific figure,
   a named document, a measurement somebody ran.
3. **It explains a mechanism the reader has met without understanding.**
4. **The consequence reaches the reader.** Something they hold, pay, wait for
   or are judged by, not something that happens to an industry.
5. **It is not the news everybody already ran.**

## What to throw away, and why the bar is high

Throwing away is permanent: the candidate was paid for, and once it is gone
it never comes back. Keeping a mediocre one costs a single further look. So
`wyrzuc: true` is for things that are definitionally not ours, never for
things that are merely weaker than their neighbours. Weaker belongs at the
bottom of the order.

There are exactly three grounds, and you must name which one applies by its
code. If none of the three fits, the candidate is not being thrown away.

- **`OFF_TOPIC`**: not about this publication's subject. Judge the SUBJECT,
  not whether a subject keyword appears somewhere in the sentence.
- **`NOTHING_TO_CHECK`**: an opinion, a forecast, a claim about what people
  believe, or a figure with no source behind it.
- **`NO_MECHANISM`**: it says what happened and cannot say what makes it so.
  Read the candidate's own `decision` line before choosing this one: if it
  names a decision, a measurement, a constraint or a trade-off, this ground
  does not apply and the code will refuse the deletion.

Do NOT throw away for being widely covered, for being a product launch, or
for being less interesting than the others. Those are ranking judgements and
they go into the order. A launch can carry a real mechanism inside it; bury
it at the bottom of the order if you must, do not delete it.

## Which ones could carry a whole article

An article needs more than a complete fact: **a second act** (something
happened after: a reversal, a court case, an amendment, a company changing
course) **or reach beyond one place** (the same arrangement runs in another
company, country or product). A fact with neither is a good note and a bad
article, complete in two sentences. Most candidates are notes. Say so.

This is a selection, not a verdict on each one in turn. Mark `na_artykul` on
at most a third of the list, and only where you can name the second act or
the second place out loud. Anything past that share is cut by the order
anyway, so a generous list only hides which ones you actually meant.

## Output

Return only valid JSON. `kolejnosc` lists every id exactly once, strongest
first. Do not omit any id and do not invent one.

{{"kolejnosc": [<id>, <id>, ...],
  "oceny": [{{"id": <id>, "wyrzuc": true|false, "kod_wyrzucenia": "OFF_TOPIC"|"NOTHING_TO_CHECK"|"NO_MECHANISM"|"", "powod_wyrzucenia": "<one clause saying why that code applies, empty when keeping>", "na_artykul": true|false, "dlaczego_mocny": "<one clause — what would make a stranger stop>", "podobne_do": "<which side of the measured evidence this resembles, and in what respect — one clause; empty if neither>"}}]}}

`kod_wyrzucenia` must be one of the three codes whenever `wyrzuc` is true, and
empty otherwise. A deletion with any other value is refused and the candidate
is kept.

## The candidates

{kandydaci}
