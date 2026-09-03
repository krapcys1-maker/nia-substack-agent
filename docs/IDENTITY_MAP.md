# Identity map — where the account's identity physically lives

**Generated** by `python narzedzia/mapa_tozsamosci.py`. Do not edit.

`PLUGGING_IN_AN_ACCOUNT.md` lists the fields you set.
This file answers the other question: **where each value actually lands,**
and — the part that matters for building a configurator — **what no field
reaches at all.**

It searches for the *current values* rather than for field names, so a
place that hard-codes the publication name shows up here even if nobody
remembered to write it down. That is the point: the hand-written list of
such places went stale once already, and the previous account name
survived a full clean-up because it was split across two string literals
and appeared on no list.

| marker | meaning |
|---|---|
| **FIELD** | the value came from `konfiguracja.toml` and changes with it |
| **INJECTED** | the file uses `{nisza}` / `{marka}` / `{language}`, so it follows too |
| **BY HAND** | the string is written into the text — **no field reaches this** |

---

## nazwa marki — `Kuchnia Bez Mitow`

Constant `config.NAZWA_MARKI`, set by `konto.nazwa_marki`

Appears nowhere in the tree outside `config.py` — nothing to
hand-edit.

---

## nisza — `how food is actually made, tested and labelled`

Constant `config.NISZA`, set by `temat.nisza`

Appears nowhere in the tree outside `config.py` — nothing to
hand-edit.

---

## uchwyt konta — `kuchnia-bez-mitow`

Constant `config.SUBSTACK_HANDLE`, set by `konto.uchwyt`

Appears nowhere in the tree outside `config.py` — nothing to
hand-edit.

---

## language — `Polish`

Constant `config.ARTICLE_LANGUAGE`, set by `temat.jezyk`.

Not searched by value: `English` occurs in ordinary prose (`England`,
`English Muffin` in the style corpus) and as a dictionary key, so a text
search returned 15 hits of which **none** was a place to edit. These are
the places where the language is actually decided, each checked below to
confirm it still exists:

| file | how | what |
|---|---|---|
| `agent-v2/config.py` | **FIELD** — the value itself | confirmed present |
| `agent-v2/stages.py` | **INJECTED** into all 24 prompts as `{language}` | confirmed present |
| `agent-v2/jezyki.py` | **BY HAND** — gate patterns per language; a language with no entry here has its gates switched off, and says so on every run | confirmed present |
| `agent-v2/browser.py` | **BY HAND** — browser UI locale, so text selectors match | confirmed present |

The worked examples inside `agent-v2/prompts/*.md` are in English
regardless of this field. The model follows `{language}`; the examples
do not follow anything.

---

## What no field reaches

**Nothing.** Every occurrence follows a field, regenerates itself,
or is a test fixture.

The `systemd` unit descriptions are per-installation by nature,
like `WorkingDirectory` and `User` in the same files. You edit those
three together when you deploy; `docs/INSTALL.md` step 7 says so.

Known and deliberate, not counted above because no field could reach
them:

* the worked examples inside `agent-v2/prompts/*.md` are in English
  regardless of `temat.jezyk`. The model follows `{language}`; the
  examples do not follow anything.
* `agent-v2/jezyki.py` holds gate patterns per language. A language
  with no entry there has its gates switched off — loudly, every run.

This file is GENERATED, so the list above cannot go stale the way the
hand-written one did.
