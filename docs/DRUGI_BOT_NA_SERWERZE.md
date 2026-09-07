# A second bot on the same server

Running two accounts from one machine. Every path, unit name and variable below
was read from a live Ubuntu server and checked against the code, not recalled.

The two copies share nothing that matters: separate checkout, separate
virtualenv, separate `.env`, separate data directory, separate Chrome profile,
separate systemd units. What they may share is API keys and the machine itself.

## The three things that make a copy separate

**Its account.** `SUBSTACK_HANDLE` and `NAZWA_MARKI` come from `.env`, not from
the cartridge, because a cartridge can be shared and an account cannot.

**Its Chrome.** Each copy talks to its own browser on its own debug port, logged
into its own account. A copy pointed at the wrong port connects to the other
bot's browser; the account guard then refuses every write, so nothing is
published to the wrong account — but nothing is published at all, and the log
says "nie to konto" without mentioning the port.

**Its budget.** Spending caps are per copy. Each reads its own database and
cannot see the other. Two copies capped at $15 are a $30 bill with no warning
anywhere. Decide the cap as a sum first, then split it.

## Before you start

You need the first bot's layout. On the server that this was written from:

```bash
systemctl cat nia-chrome.service | grep ExecStart   # profile dir and port
systemctl cat nia-agent.service  | grep -E "WorkingDirectory|Environment"
systemctl cat nia-agent.timer    | grep OnCalendar  # hours to avoid
```

Nothing about the first bot changes. Do not copy its `data/` directory: that is
the first account's memory — journal, fact bank, publication history, session.
A second copy inheriting it would avoid repetitions it never made and count
another account's spending as its own.

## 1. Checkout and environment

```bash
git clone <repo> ~/nia-agent && cd ~/nia-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

A separate `.venv`. Sharing one with the first bot couples two deployments that
should be able to move independently.

## 2. `.env` for this copy

```
ANTHROPIC_API_KEY=...          # may be the same as the first bot's
DEEPSEEK_API_KEY=...
SUBSTACK_HANDLE=<second account handle>
NAZWA_MARKI=<second publication name, as it should appear in the text>
CHROME_DEBUG_PORT=9223
```

`NAZWA_MARKI`, not `MARKA` — a variable by any other name sets nothing, and the
brand silently stays "Your Publication".

`CHROME_DEBUG_PORT` defaults to 9222, which is the first bot's port. The second
copy must set it.

**The monthly cap does not belong here.** With a cartridge attached it comes from
`pieniadze.sufit_miesieczny_usd` in the preset, and a value in `.env` is
overwritten without a word. Set it in the preset, in the next step.

## 3. The cartridge

A clone does not bring one. `presety/*` is gitignored apart from the public
templates, because a working cartridge holds a real account handle. Copy a public
template into a private cartridge, edit it, attach it:

```bash
cp -r presety/nia-unfiltered presety/moj-kartridz
$EDITOR presety/moj-kartridz/preset.toml     # nazwa, konto.uchwyt,
                                             # pieniadze.sufit_miesieczny_usd
.venv/bin/python narzedzia/presety.py sprawdz moj-kartridz
.venv/bin/python narzedzia/presety.py podlacz moj-kartridz
```

The engine refuses to run without an attached cartridge — `run.py` exits with
code 3 and writes nothing. Attaching is not optional setup, it is the step that
gives the bot a subject, a voice and a plan.

Editing a preset after attaching halts the next start on purpose: the fingerprint
no longer matches. Attach it again, deliberately.

## 4. Check what the copy actually sees

Before running anything:

```bash
cd ~/nia-agent && .venv/bin/python -c "
import sys; sys.path.insert(0,'agent-v2')
import config, browser
print('handle      :', config.SUBSTACK_HANDLE)
print('brand       :', config.NAZWA_MARKI)
print('guard match :', browser.PROFIL_HANDLE == config.SUBSTACK_HANDLE)
print('monthly cap :', config.MONTHLY_LIMIT_USD)
print('chrome port :', browser.CDP_PORT)
print('data dir    :', config.DATA_DIR)"
```

Handle and brand must be the second account's. The port must be the second
Chrome's. The data directory must sit under this checkout. If any line is wrong,
stop — every one of them is a way to write to the wrong account or bill the
wrong budget.

## 5. Its own Chrome

The first bot's browser unit is the template. Change three things: the profile
directory, the debug port, and the unit name. Keep the same display if the server
has one remote desktop.

```ini
[Unit]
Description=Chrome for the second account
After=nia-vnc.service
Requires=nia-vnc.service

[Service]
Type=simple
User=ubuntu
Environment=DISPLAY=:1
ExecStart=/usr/bin/google-chrome --user-data-dir=/home/ubuntu/chrome-nia \
  --no-first-run --no-default-browser-check --remote-debugging-port=9223 \
  --window-size=1400,860 https://substack.com/sign-in
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Do not log in for the owner.** Start the unit, tell them the port and the
remote desktop, and let them enter the password themselves. Automating a login
is not part of deployment.

## 6. Tests, then a dry run

```bash
for t in agent-v2/tests/test_*.py; do
  PYTHONIOENCODING=utf-8 .venv/bin/python "$t" >/dev/null 2>&1 || echo "FAILED: $t"
done
```

Nothing should fail on Linux. `test_czas` needs a real SIGTERM and fails only on
Windows.

```bash
.venv/bin/python agent-v2/run.py --dzien
```

Without `--wyslij` nothing goes out. Read the output: it must show this copy's
account and this copy's data directory.

## 7. Units and hours

Three pairs, modelled on the first bot's, with `WorkingDirectory` and the
interpreter pointing at the new checkout:

| unit | first bot's equivalent | what it does |
|---|---|---|
| `nia2-agent.service` + `.timer` | `nia-agent` | the working day |
| `nia2-alarm.service` + `.timer` | `nia-alarm` | health check |
| `nia2-artykul.service` + `.timer` | `nia-artykul` | the article |

```ini
[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/nia-agent
Environment=AGENT_V2_SERVER=1
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/ubuntu/nia-agent/.venv/bin/python agent-v2/run.py --dzien --wyslij
```

`narzedzia/jednostki.py` generates the timers from the cartridge's own schedule,
so the hours match what the preset says rather than what a template remembers.

**Offset the hours from the first bot.** Not for capacity — one run peaks at a
few hundred megabytes and the server has room — but because two Chrome instances
starting in the same second is the one place these copies can collide.

## 8. Enable the timers last

Only after a green test suite, a clean dry run, and the owner confirming the
second account is logged in.

```bash
sudo systemctl enable --now nia2-agent.timer nia2-alarm.timer nia2-artykul.timer
systemctl list-timers "nia2-*"
```

## Report back

The checkout path and its commit. The test result. The monthly cap **and the sum
of both copies**. The three unit names with their hours. The Chrome port.

## Two traps worth knowing

**A worktree has no `data/`.** Comparing two versions of the code with
`git worktree` measures the presence of the journal, not the version of the code:
every test that reads the journal passes in a worktree regardless.

**The account guard is the last line, not the first.** It compares the handle in
the session against `SUBSTACK_HANDLE` and refuses to write on a mismatch. It will
catch a copy pointed at the wrong browser — but it catches it at the moment of
writing, after the run has already paid for the text.
