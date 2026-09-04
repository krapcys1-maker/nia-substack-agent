# Contributing

Two kinds of contribution are genuinely wanted here, and they are very
different in effort.

---

## 1. A subject pack — the easy one, and the most useful

A pack is one TOML file that tells the bot what a publication is *about*:
what to search for, what counts as on-topic, what lenses to look through. It is
the part of setup where people stall, and the part where somebody who knows a
field can save everybody else an hour.

**No Python. No account. No API key.** Copy the closest existing pack, rewrite
it, run two free checks:

```bash
python narzedzia/pakiety.py --sprawdz
python agent-v2/tests/test_pakiety.py
```

[packs/README.md](packs/README.md) says what a pack may contain, the three
rules it has to pass and — more usefully — what separates a pack that is merely
valid from one that is good.

In the pull request, say **what you know about the field**. A pack is a claim
that these are the right things to search for; that claim is what gets
reviewed. The syntax is already covered by the tests.

---

## 2. Code

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) first, and
[docs/REPO_MAP.md](docs/REPO_MAP.md) for where things live.

### Before you open a pull request

```bash
python narzedzia/audyt.py                 # identity, secrets, generated docs
python narzedzia/zaleznosci.py --sprawdz  # imports match requirements.txt
for t in agent-v2/tests/test_*.py; do python "$t" >/dev/null || echo "FAILED: $t"; done
```

All of it is free: no network, no model calls, no API key. Two tests fail on a
fresh Windows checkout for environmental reasons — `test_czas` needs POSIX
signals, `test_zapora_platnych_wywolan` needs a real key. Both are listed in
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) with their cause.

If you touched anything the generated documents describe:

```bash
python narzedzia/mapa_funkcji.py
python agent-v2/dokumentacja-zrodla/sklej.py
python agent-v2/tests/test_liczby_w_dokumentach.py --popraw
```

CI runs all of this, so it will tell you anyway — this just saves a round trip.

### What review will actually ask you

This project has a few habits that are not style preferences. They came from
bugs that cost real money and real time, and a pull request that ignores them
will get the same question every time:

**Write down the reason, not just the change.** Comments here carry *why*:
the measured number, the incident that forced a rule, what was tried and
rejected. A diff that changes a threshold without saying what measurement moved
it is not reviewable.

**Every check needs a counterproof.** A check that has never fired is
indistinguishable from a broken one. If you add a guard, add the case that
makes it fail — most test files here have a section called
`KONTRDOWOD` doing exactly that.

**No number that nothing recomputes.** A count in a document is a claim; if
no test derives it from the tree, it will drift and lie. See
`test_liczby_w_dokumentach.py` for how the existing ones are pinned.

**Distinguish "we did not measure it" from "the answer is zero."** An empty
set is not a zero percent. Several audits in this repository used to report a
failure on a perfectly correct fresh install because `max(1, len(...))` turned
a missing measurement into a bad result.

**Don't add a second copy of a value.** Two copies of one number always
diverge — it happened here with a date (five copies), a stopword list (four),
a section heading (eight) and an article length (two, already out of sync).
Derive it instead.

### The language

Documents are in English. Code — identifiers, comments, test names — is in
Polish, and that is not going to change; the reasoning behind decisions lives
in those comments and a translation pass would quietly lose it. You can
contribute code without reading Polish, but you will get more out of the review
if you can at least follow the comment above the line you are changing.

---

## What is out of scope

**Detection evasion.** The account does not hide that it is automated, does
not deny it when asked, and does not work around anti-bot measures. This is
doctrine, not a setting — see "Lines this agent does not cross" in the
[README](README.md).

**Reciprocity farming**, unfollow-after-silence and similar. Measured here:
of twelve accounts given a subscription, zero reciprocated. It also breaches
the platform's terms.

**Anything that puts secrets in the repository.** `.env`, session state,
subscriber exports and the database are gitignored from the first commit, and
`narzedzia/audyt.py` fails the build if one appears — including in git history.

---

## Reporting a security issue

See [SECURITY.md](SECURITY.md). Please do not open a public issue for anything
involving credentials or other people's data.
