# Testing NIA's voice

NIA Unfiltered shares one identity across Notes, replies, restacks and articles.
The identity lives in `prompty/linia_redakcyjna.md`; each format adds its own
instructions. Rubrics suggest angles rather than enforcing a mood or sentence
formula. The professional presets keep their own voices.

Evaluate the English original. A translation can strengthen a swear word or
introduce grammatical gender that was absent in English. It is not reliable
evidence of the writer model's exact wording.

To test the **installed** persona, run from the project directory:

```sh
python narzedzia/proba_glosu.py --live --samples 3
```

Use your installation's Python environment (`.venv/bin/python` on Linux or
`.venv\Scripts\python.exe` on Windows). This makes paid calls through the same
Note generator as the scheduler, with its actual sources, memory, models and
prompts. It does not publish or remember the samples as published work. Calls
are recorded as a test run. `--slot 1` selects the second configured Note slot
when one exists. There are no hidden prompt or length overrides.

Read every sample, including the weak ones. Look for a clear point of view,
humour within the observation, adult language, a specific comparison and an
ending that earns its place. Warmth can still sound like NIA. Do not grade by
counting swear words or assume one good example guarantees the next result.

Each paid short-form answer is retained under the private instance's
`persona-drafts` directory with a unique ID, timestamp, preset fingerprint,
exact request, request hash, raw answer and validation status. Repeated inputs
and different models no longer overwrite one another. Confirmed publication
memory links back to the draft ID and request hash. These records include
source and account context; they belong to the private installation, not Git.

The scheduler generates a fresh Note. Running a preview does not queue that
exact wording for publication. Never present a successful preview as proof that
the next independently generated Note will contain the same wording. The saved
request hashes let you distinguish input changes from output variation.

The persona path uses one writing call per attempt. It has no paid stylistic
rewrite or fact-check loop. A malformed or rejected answer is retained for
diagnosis and does not trigger another paid attempt. Articles retain their
separate evidence checks. Unit tests verify text and draft integrity; judging
whether the voice is good still requires reading real outputs.

## Memory and news inputs

Confirmed Notes, comments, replies and restacks enter the private persona
memory with their text, topic and originating draft. Failed or skipped actions
do not. Restacks need a detected publication ID. Conversation memories do not
advance Note milestones or displace Notes from the recent-theme rotation.
Older publications provide continuity; the current preset defines her voice.

News Notes receive dated RSS excerpts, not full articles. The feed window
excludes old, future and invalid dates; an empty window leaves NIA free to write
a personal thought. Feed caches are isolated by instance and configured sources.
Changing a preset also changes YouTube sources and topic-comparison stopwords.

The writer can identify a chosen supplied source using its private `source_ids`
field. Only IDs from the actual input resolve to URLs. After confirmed publication,
these URLs enter memory and are excluded from subsequent news inputs while retained
there. This tracks exact URLs, not every article about the same event. Missing IDs
do not invent provenance or trigger an extra paid call. IDs stay out of public text.

These controls use no extra model calls. Voice previews now finalize their run cost
from recorded calls on success and failure. Paid previews require explicit approval
of the model, call count and estimated cost before anyone runs the command.

Mixed news feeds prioritize the preset's subject terms and actual excerpts before
filling the short Note input, taking turns across channels within each tier.
Explicitly sponsored feed categories are excluded. Show HN supplies
small-builder stories, but link/vote metadata is not a description: an empty
excerpt is marked as headline-only. When a submission contains the author's
own account, its source is the HN discussion, not the project interface. This
does not independently verify the author's claims or guarantee a warm Note.

The RSS pool is not the article bank. If the bank is empty, the scheduled article
run searches for candidates and leases an admitted candidate through the same
path as an existing bank. Its topic is not selected before that run. Recent
persona Notes inform topic avoidance. Feed leads have a 14-day window and carry
their original URLs into research; the chosen lead is fetched even if discovery
omits it. Unfetched claims remain in the private archive but are excluded from
the writer's evidence. Explicit article-body markup takes precedence over generic
page extraction so navigation cannot substitute for an empty article body.

Warmth has a repetition failure of its own: praise can repeatedly start with
"no keynote" or "no grand prophecy". The Note prompt now names that pattern and
asks for humour from the actual work. This instruction is not a measured claim
that the tic has disappeared; an offline contract test cannot assess comic quality.

## Scoring a run, so "the voice is uneven" becomes a number

`proba_glosu.py` scores every sample it generates. Reading three Notes and
arguing about taste never settles anything; a hit rate does. Ten samples on one
input is the smallest run that separates a half-working rule from a working one.

Four checks, each written down only after it failed measurably:

| check | what it looks for |
|---|---|
| `addressed` | the last line is aimed **at** somebody — an order or an accusation, not an observation that one thing resembles another |
| `no_review` | none of the reviewer words (`sensible`, `useful`, `worth noting`) that turn a Note into a review of the news |
| `strong_word` | swearing when the piece is angry. `pissed off` does not count; it is a status update |
| `length` | 60–90 words |

`addressed` comes from the five Notes the owner accepted as the target: **all
five end with an order or an accusation**, and none of the rejected ones do.
"Credit the woman whose homework you copied." "Say who mopped." "Some of you
need a satellite network before you'll listen to a woman."

### Measured on gpt-5.6-sol, ten samples per run, one identical input

| | before | after |
|---|---|---|
| addressed | 5/10 | **8/10** |
| no_review | 10/10 | 10/10 |
| strong_word | 0/10 | **5/10** |
| length 60–90 | 2/10 | **10/10** |
| **all three of addressed + no_review + length** | **2/10** | **8/10** |

What each number cost to learn:

**Permission is not an expectation.** The prompt said "You can say fuck, shit or
bullshit" and three different models — Fable, Opus and Sol — produced zero
swearing across dozens of samples. Stating it as what she does when angry moved
it to 5/10.

**A range with an escape hatch is read as the escape hatch.** "Roughly 40–100
words, a complete shorter thought is welcome" produced 36–68 word Notes, 2/10
inside the band. A floor with a reason produced 10/10.

**A banned punchline shape needs naming.** Four of the first ten samples ended
with the identical construction — "That's not [their charitable word]. That's
[damning picture]." The prompt already forbade repeating an opening or a
punchline; it did not forbid repeating a *construction*, and that construction
addresses nobody, which is what held `addressed` at 5/10.

`same_input` in the summary reports whether every sample shared one
`request_sha256`. If they did not, the comparison is void and the tool says so
rather than averaging two different questions.

## Shared writing instructions and offline preview

With `osobowosc.wlaczona = true`, every writing format receives the same system
blocks, in this order:

1. `prompty/linia_redakcyjna.md`: identity, values and factual boundaries.
2. `styl.opis`: the preset's concise style description.
3. `prompty/glos_wspolny.md`: shared voice and approved style examples.
4. The form's block: `glos_artykulu.md`, `glos_notki.md` or `glos_komentarza.md`.

Comments, replies and restack captions share the interaction block. They respond
to the supplied post and can remain silent. Notes receive their subject and
available news or measured statistics. Published memory provides continuity;
old text is not a higher-priority style instruction.

Articles use `agent-v2/prompts/pisarz_persona.md` for the assignment and evidence.
It leaves the structure and ending to the writer and keeps factual attribution
and uncertainty. The generic `pisarz.md` remains the route for professional
presets without a persona. A persona without an identity anchor retains the
generic article fallback.

The approved examples are references for rhythm and attitude, not factual
sources or jokes to copy. A qualification may sound like NIA while still
stating exactly what is unknown. A joke must not erase that distinction.

## Preview and verify without model calls

Run from the repository root, using your installed Python environment:

```sh
python narzedzia/presety.py podglad nia-unfiltered
python agent-v2/tests/test_personality.py
python agent-v2/tests/test_artykul_wie_kto_pisze.py
python agent-v2/tests/test_presety.py
```

Preview chooses the active article template and short-form system instructions.
It labels short-form context as supplied at runtime; it is not a replay of a
particular generation. Tests capture actual writing calls with model responses
stubbed and network connections blocked, check shared voice priority and verify
that the configured path without factual rewriting preserves the article body.

These checks establish routing and preservation, not the literary quality of a
model's next answer. Evaluate actual samples across anger, warmth, explanation
and disagreement before claiming voice quality. Paid trials require the
operator's permission. Models are selected per role in the preset; using the
same voice does not require silently changing those selections.

The public preset is a reusable configuration, not a record of a running
installation. A local private preset can also differ from the server's private
preset. When reporting model usage, identify the host and active instance,
read its resolved `MODEL_FOR`, and check its call history. Historical call
counts can include trials; they are not counts of published Notes. Never infer
the production writer from a different checkout's preset file.

If you edit an active private preset, update that preset too and reactivate it
with `python narzedzia/presety.py podlacz NAME --instancja INSTANCE`. Its
fingerprint includes prompt files. Running processes retain loaded settings;
new processes read the reactivated version.

The historical scoring heuristics above are diagnostics for their particular
trials, not mandatory shapes or swear-word quotas for every new piece.
