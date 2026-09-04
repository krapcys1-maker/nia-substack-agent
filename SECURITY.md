# Security

## Reporting

Use GitHub's private vulnerability reporting (**Security → Report a
vulnerability** on this repository). Please do not open a public issue for
anything involving credentials, session state or other people's data.

If private reporting is unavailable to you, open a public issue saying only
that you have something to report and asking for a channel — no details.

## What this software handles that is worth protecting

This bot runs somebody's publication. Three things it touches are worth
attacking, and all three are deliberately kept out of the repository:

| what | where it lives | why it matters |
|---|---|---|
| API keys | `agent-v2/.env` | spends money |
| Substack session cookie | `agent-v2/storage-state.json` | **full control of the account** — it is a logged-in session, not a password |
| subscriber exports | `agent-v2/data/kopie/*.csv` | other people's email addresses, and the only asset that cannot be regenerated |

All are gitignored from the first commit. The session file and the subscriber
exports are written `0600` — readable only by the account that owns them,
because on a shared machine "in my home directory" is not privacy.

`python narzedzia/audyt.py --historia` fails if any of them appears in the
working tree **or anywhere in git history**, along with real API keys, IP
addresses and ssh commands. Section 9 of that audit is a counterproof: it
injects three leaks and checks that each one is caught, because an audit that
always says OK is indistinguishable from a broken one.

## Things that are working as intended, not vulnerabilities

**The bot does not hide that it is automated.** It never denies being AI-run
when asked directly, and it does not evade bot detection. That is doctrine.

**Prompts and briefs are in the repository.** They are the product, not a
secret. Nothing in them is a credential.

**The database and the action journal are gitignored but not encrypted.**
They sit on the operator's own machine. If that machine is compromised, so is
the session, and the session is the bigger problem.

## If you are running this

- Keep `agent-v2/.env`, `agent-v2/storage-state.json` and `agent-v2/data/` off
  any shared filesystem and out of any backup you would hand to somebody else.
- If the session file leaks, **log out of all sessions in Substack** — that
  invalidates the cookie. Rotating the password alone may not.
- `python agent-v2/alarm.py` reports missing backups and file permissions on
  every run, and names the exact path.
