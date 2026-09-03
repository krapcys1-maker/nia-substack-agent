Choose which of these comments deserve a reply, and rank them.

You will not answer all of them. Answering everyone is what a bot does — and
readers can tell. A publication that replies to every "great piece!" looks
automated even when every reply is written well.

## Answer first

1. **Disagreement.** Someone contradicts the piece or pushes back on a claim.
   These matter most: an unanswered objection stands as the last word, and other
   readers see it that way.
2. **A real question.** Especially one the piece could answer or should have.
3. **A correction.** Whether they are right or wrong, this needs a response —
   and if they are right, saying so publicly is worth more than being right.
4. **A specific addition.** A fact, a case, a counter-example you did not have.

## Answer only if there is room

5. **Substantive agreement** that adds a reason or an example of its own. Worth
   a reply when it lets you take the point further, not when it just agrees.

## Do not answer

- Bare praise: "great piece", "loved this", "so true", an emoji.
- Anything you would answer with thanks and nothing else.
- Self-promotion, link drops, unrelated pitches.
- Abuse or bait.

Skipping these is not rudeness. A comment section where the author speaks only
when they have something to say reads as a person; one where the author replies
under every line reads as a machine — or as someone who needs to be seen.

## How many

Return at most {ile} comments, ranked most-worth-answering first. Return fewer —
or none — when fewer deserve it. Zero is a valid and common answer.

## Output

Return only valid JSON:

{{"choices": [{{"index": <number>, "rank": <1 is highest>, "why": "<one sentence>", "kind": "disagreement"|"question"|"correction"|"addition"|"agreement"}}], "skipped_because": "<one sentence about the ones you left out>"}}

## The comments

{komentarze}
