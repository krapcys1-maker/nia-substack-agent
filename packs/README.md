# Subject packs

A **subject pack** is one TOML file that answers the hardest part of setting
this bot up: *what is it about, and what should it go looking for.*

The technical setup takes a minute. Then the configurator asks for twenty-odd
search terms, twenty niche markers and twenty domains — and that is where
people stall, or type something plausible and end up with a bot searching for
the wrong thing. In the log that failure looks like a fussy model
(`worth commenting: 0/15`); it is actually a badly configured subject.

A pack is that material done once, properly, by somebody who knows the field.

```bash
python narzedzia/pakiety.py                      # what packs exist
python narzedzia/pakiety.py --pokaz ai           # read one
python narzedzia/kreator.py --wsad ai            # set up starting from it
```

Every value from a pack arrives as a **default you can overwrite**. It is still
your publication.

---

## What is in this directory

| pack | language | about |
|---|---|---|
| `everyday-things-and-regulation` | English | standards, tolerances, certification, liability, procurement — the configuration this bot actually ran on in production |
| `ai-and-machine-learning` | English | benchmarks, training data, inference economics, evaluation, and the rules being written around them |
| `how-things-work` | English | physics, materials, measurement and engineering in ordinary objects |
| `laws-and-public-money` | English | legislation, procurement, budgets and audit reports, read as documents |

---

## What a pack may and may not contain

A pack may set exactly two sections: **`[temat]`** (the subject) and
**`[zrodla]`** (sources). Plus a `[pack]` block describing itself.

It may **not** set the account handle, the money ceilings, the daily volumes,
the model split, or anything else. That is not a style preference — packs are
meant to arrive from strangers through pull requests, and a file from somebody
else must not be able to touch your account or your budget, not even by
mistake. A pack carrying any other section is **rejected at load time**, and
`agent-v2/tests/test_pakiety.py` fails the build if one gets in.

```toml
[pack]
name = "AI and machine learning"      # required
language = "English"                  # required
description = "one sentence"          # required
author = "your-github-handle"         # optional
added = "2026-09-04"                  # optional
source = "where the material came from"  # optional

[temat]
nisza = "..."             # one sentence, given to the model
jezyk = "English"
kat_redakcyjny = "..."    # the editorial angle: what this publication is for
znaki_niszy = [...]       # markers your search terms are graded against
hasla_szukania = [...]    # what the bot searches for to find people
dziedziny = [...]         # lenses, rotated every run — not destinations
puste_slowa = []          # words too common in your field; empty is correct

[zrodla]                  # optional
kanaly_youtube = { "Channel name" = "UC..." }
blokowane_hosty = [...]
```

**`znaki_niszy` is a yardstick, not a filter.** Nothing in the agent filters
posts by it — what counts as on-topic is decided by the model, from
`agent-v2/prompts/cele.md`. The markers exist so that your *own* search terms
can be checked for drift against your *own* subject. Four places in this
repository used to claim otherwise; they were wrong and are fixed.

---

## The three rules your pack has to pass

None of them is a taste judgment. Each has a measured consequence, and each is
derived from the code rather than from a number somebody typed once.

**1. The pool must be wider than one run draws.** Every run samples
`ILE_HASEL_NA_PRZEBIEG` search terms at random (5 by default), so a pool of
five or fewer is drawn whole every time and brings back the same handful of
accounts forever. Minimum: **three times the draw**.

**2. Every search term must carry at least one of your own niche markers.**
Otherwise the bot searches, finds posts, and the targeting rule rejects every
one of them as off-beat. The fix is either direction — add the shared stem to
`znaki_niszy`, or reword the term.

**3. The grid must have room to rotate.** Patterns × domains has to give at
least ten cells per note per day, or the same pattern in the same domain comes
back within the week.

Check yours before you open a pull request:

```bash
python narzedzia/pakiety.py --sprawdz
python agent-v2/tests/test_pakiety.py
```

Both are free: no network, no model calls, no API key.

---

## What makes a pack good rather than merely valid

The rules above stop a pack from being broken. They cannot make it good. From
the one that ran in production:

- **Search terms should point at people who publish, not at the topic.** The
  bot uses them to find accounts worth talking to. "materials testing" finds
  practitioners; "interesting facts" finds aggregators.
- **Domains are lenses, not destinations.** Write them as the *shape of a
  finding* — "a rating measured under conditions nobody encounters" — not as a
  category. The pipeline rotates them, so twenty specific lenses beat sixty
  vague ones.
- **Cover more than one side of the subject.** Twenty terms about one thing
  reach the same accounts as three. The production pack deliberately spans how
  a thing is made, who is protected, and who pays.
- **The editorial angle does the heaviest lifting.** It is the sentence that
  decides what this publication is *for*, and it is what keeps the bot from
  producing plausible nothing. Look at `laws-and-public-money.toml`: the angle
  forbids motive, party and prediction, and demands the document — which is the
  only reason that subject is safe to automate at all.

---

## Contributing one

1. Copy the closest existing pack and rewrite it. Do not start from an empty
   file — the shape matters more than it looks.
2. Run the two checks above until they are clean.
3. Open a pull request with the pack and nothing else in it.

Say in the PR description **what you know about the field** and where the
material came from. A pack is a claim that these are the right things to search
for; the review is about that claim, not about the syntax — the tests already
cover the syntax.

Packs in languages other than English are welcome. Set `language` honestly:
the gates in `agent-v2/gates.py` are English regular expressions and go quiet
in another language, which is documented in
[docs/CONFIGURATION_MAP.md](../docs/CONFIGURATION_MAP.md) and is a real
limitation rather than an oversight.
