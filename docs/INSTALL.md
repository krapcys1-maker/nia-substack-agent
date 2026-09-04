# Installation

Zero to running, in order. Every step says what it is for and how you know it
worked. Step 5 is the one no software can do for you.

Everything is run **from the repository root**, never from inside `agent-v2/`.
On Windows, set `PYTHONIOENCODING=utf-8` first.

---

## Before you start: what this actually needs

| requirement | why | optional? |
|---|---|---|
| Python 3.10+ | developed and measured on 3.12 | required |
| `DEEPSEEK_API_KEY` | **21 of the 26 model roles** | required |
| `ANTHROPIC_API_KEY` | notes, articles, the repair pass | required |
| `OPENAI_API_KEY` | article cover image only | optional |
| Playwright + Chromium | the whole Substack layer | required |
| **a real Chrome with a display** | Cloudflare fingerprints headless mode | required to publish |
| **a Substack account, logged in by hand** | Substack has no publishing API | required |
| SMTP mailbox | failure alerts | optional |

Budget: the bot ships with a hard ceiling of **$40/month**, a daily ceiling and
a per-run ceiling. A full article costs $0.75–0.78. A day of notes, comments and
replies costs roughly $0.30.

---

## 1. Get the code and the dependencies

```bash
git clone <this repository>
cd nia-substack-bot
pip install -r requirements-dev.txt
playwright install chromium
```

`requirements-dev.txt` pulls in `requirements.txt` plus `pytest`. If you only
want to run the bot and never the tests, `requirements.txt` is enough.

**Check it worked.** This must print a table and end with `OK`:

```bash
python narzedzia/zaleznosci.py --sprawdz
```

It derives the real dependency list from the syntax tree of every import and
compares it with `requirements.txt`. It exists because the first version of that
file, written from memory, listed two packages nothing imports.

---

## 2. Run the health check before anything else

```bash
python agent-v2/alarm.py
```

This is the only entry point that runs **with no session, no API keys and no
data**. It prints, line by line, what is missing: the session, the subscriber
backup, the reader snapshots, material in the idea bank.

For a fresh install this is the best to-do list you will get. Expect it to
complain about everything — that is correct at this point.

---

## 3. Run the test suite

```bash
for t in agent-v2/tests/test_*.py; do echo "$t"; python "$t"; done
```

**On a fresh clone some tests fail and none of those failures is a code
defect.** Three of them go away as you finish this guide; two cannot. Measured:

```
after pip install                    102 passed, 18 skipped, 4 failed
after playwright install chromium    103 passed, 18 skipped, 3 failed
after .env and the first run         104 passed, 18 skipped, 2 failed
```

What each one is:

| test | why it fails | fixable? |
|---|---|---|
| `test_artykul` | `playwright` browser not downloaded | **yes** — `playwright install chromium` |
| `test_czas` | needs real POSIX `SIGTERM` | no on Windows |
| `test_komplet_sciezek` | `agent-v2/data/` is empty | **yes** — resolves after the first run |
| `test_podlogi_playbook` | needs a production article file | no — gitignored |
| `test_zapora_platnych_wywolan` | no `.env` yet | yes — step 4 |
| 17 history tests | this copy has no original git history | no — see below |

Those 17 reproduce a counterproof out of a specific commit
(`git show <SHA>:agent-v2/file.py`) because the project's doctrine requires a
reference version pinned to a SHA, never to `HEAD`. In a copy whose history was
started fresh those commits do not exist, so they print what is missing and skip
with exit code 0 rather than crashing. That is honest, not a workaround: the
counterproof genuinely cannot be reproduced without the history.

---

## 4. Configure

### 4.1 Keys

```bash
cp .env.example agent-v2/.env
```

Then fill in:

```
ANTHROPIC_API_KEY=
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
DRY_RUN=true
KILL_SWITCH=false
ALARM_EMAIL_TO=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
```

Keep `DRY_RUN=true` until you have read step 6. It blocks model calls **and the
browser** — it used to block only model calls, and a "dry" run once wrote
nothing and still liked two strangers' posts.

For Gmail, `SMTP_PASSWORD` is an **app password**, not your account password.

### 4.2 Your account and your subject — one file

```bash
cp konfiguracja.example.toml agent-v2/konfiguracja.toml
```

27 fields: handle, publication name, readers' timezone, the subject and its
search terms, topic sources, the model split, daily volumes, budget ceilings and
the publishing rhythm. Every field carries the reasoning next to it, and the
constraints that tests enforce.

A bad value **or a mistyped field name stops the start** with a message naming
what was allowed — a config that silently ignores a typo is worse than no config.

Full walk-through of every field, with what it is for and what breaks if it is
wrong: **[PLUGGING_IN_AN_ACCOUNT.md](PLUGGING_IN_AN_ACCOUNT.md)**.

The handle used to live in two independent constants and changing one gave a bot
that published to one account and read the profile of another. It is one value
now, and a test enforces that. Likewise the publication name and the subject
reach all 24 prompts as injected fields — you do not edit a prompt to rename a
publication.

**Still hand-edited:** the two files in `style-profiles/` carry the publication
name in prose, and the worked examples inside the prompts are in English.

### 4.3 Two thresholds your subject has to clear

The repository ships with an **example niche** you must replace. Two of the
fields have hard minimums, and a too-thin configuration fails a test rather than
producing thin output three weeks later:

| field | minimum | enforced by |
|---|---|---|
| `temat.hasla_szukania` | **≥19 phrases**, spanning ≥3 areas | `test_szukanie_celow` |
| `temat.dziedziny` | grid `GENERATORY × dziedziny` **≥400 cells** — so ≥29 domains at 14 patterns | `test_generatory` |

Check them before going further:

```bash
python agent-v2/tests/test_szukanie_celow.py
python agent-v2/tests/test_generatory.py
```

`zrodla.kanaly_youtube` ships **empty** and empty is fine: the seed becomes
"(nothing fetched today)" and the domain grid carries the run.

### 4.4 Rebuild the generated documentation

```bash
python agent-v2/dokumentacja-zrodla/sklej.py
```

**Not optional.** `test_dokumentacja_zywa` fails after any configuration change
until the documentation is reassembled, because that document is generated from
the code and guarded against drift.

---

## 5. The Substack session — the step no software does for you

Substack has no publishing API. The bot **is a signed-in user**, and its whole
authority is one cookie: `substack.sid`, stored in
`agent-v2/data/storage-state.json`.

### Why it must be done by hand

There is an automated login path in `browser.py`. The code itself advises
against it — it loops on CAPTCHA. There is no way around this that does not mean
defeating Substack's own protections.

### Why headless is not enough

Measured on a live account, same session, same address, same server:
**publishing through a real Chrome returns 200; through headless Chromium the
note simply never appears.** Cloudflare fingerprints headless mode. So the
machine that publishes needs a real Chrome with a display — a virtual one is
fine.

### How to create the session

1. Start Chrome with a debugging port and **log in yourself**:

   ```bash
   chrome --remote-debugging-port=9222
   ```

2. With that Chrome open and logged in:

   ```bash
   python agent-v2/browser.py sesja
   ```

   It attaches over CDP, opens `substack.com/home`, checks it sees a signed-in
   view, and writes the session file. It prints how many days are left.

3. On a server, run the same Chrome as a service on a virtual display and log in
   through a remote desktop once.

### How long it lasts

The bot reads the expiry from the cookie itself — no constant is assumed. The
session **extends itself**: Substack refreshes the cookie on activity, and the
bot re-saves the state after every run, so regular use pushes the expiry
forward.

It is invalidated by logging out anywhere, by a password change, and by the
cookie expiring.

`agent-v2/alarm.py` warns by email when fewer than 14 days remain, when it has
expired, and when the file is missing.

### Check it

```bash
python agent-v2/browser.py serwer
```

Answers exactly one question: does the stored session still work from this
machine's address. Read-only — it publishes nothing.

---

## 6. First run

Nothing reaches the outside world without `--wyslij`.

```bash
python agent-v2/run.py --dzien          # the daily routine, publishing nothing
python agent-v2/artykul_z_puli.py       # one article, to disk
```

With no session, the daily run stops **before spending anything**:
`wymagaj_sesji()` sits in front of everything that costs money.

When you are ready:

```bash
python agent-v2/run.py --dzien --wyslij
python agent-v2/artykul_z_puli.py --wyslij
```

**Safety net worth knowing about:** if a file named `TO_JEST_KOPIA_TESTOWA`
sits next to `config.py`, `--wyslij` is refused. Put one in every copy that is
not your production install. Databases separate themselves automatically —
`DATA_DIR` derives from where `config.py` sits, so a second clone gets its own
database with no environment variable to forget.

---

## 7. Running it on a schedule

`agent-v2/systemd/` holds three services and three timers:

| unit | when | what |
|---|---|---|
| `nia-agent.timer` | five times a day | the daily routine |
| `nia-artykul.timer` | Tuesdays 14:00 UTC | the weekly article |
| `nia-alarm.timer` | daily 07:00 UTC | health check and alerts |

**Do not edit them by hand.** The three `.service` files carry an install path
(twice each — `WorkingDirectory` and the interpreter in `ExecStart`), a system
user, and your brand name in `Description=`. Editing six values across six files
is how one of them ends up wrong, and the failure looks like a Python error
rather than a configuration one.

```bash
python narzedzia/jednostki.py --katalog /srv/bot --uzytkownik bot
```

It writes `agent-v2/systemd/dla-tej-instalacji/`, takes the brand from
`konto.nazwa_marki`, and prints the three things that must exist on the server
before you copy anything. The files in `agent-v2/systemd/` stay as the source —
they are what the tests and `norma.py` read.

*On Windows in Git Bash*, a POSIX `--katalog` is rewritten by the shell before
the program sees it (`/srv/bot` arrives as `C:/Program Files/Git/srv/bot`). The
tool detects that and refuses; prefix the command with `MSYS_NO_PATHCONV=1`.

**One number appears in two files and must match**:
`config.LIMIT_CZASU_PRZEBIEGU_S` and `TimeoutStartSec=` in `nia-agent.service`.
If they diverge, the agent computes a different deadline than systemd enforces,
and runs get killed mid-flight.

The timers use `RandomizedDelaySec` deliberately: a run that starts at exactly
the same second every day is a machine signature.

**Deploy only when no run is in progress** (`flock -n agent-v2/data/agent.lock`).
Prompts are read from disk on every model call, so a `git pull` mid-run swaps
them under a live process.

---

## What to do when something breaks

[docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) — nine problems found while
mapping this codebase, each with the symptom, what it actually meant, and the
fix. Most of them are waiting for anyone who clones this.
