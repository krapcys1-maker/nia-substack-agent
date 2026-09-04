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

## nazwa marki — `Your Publication`

Constant `config.NAZWA_MARKI`, set by `konto.nazwa_marki`

| file | line | how | context |
|---|---|---|---|
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 1 | GENERATED — rebuilds itself | `# Your Publication — dokumentacja odtworzeniowa agenta` |
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 46 | GENERATED — rebuilds itself | `Agent prowadzi anglojęzycznego Substacka **„Your Publication"**, który` |
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 12747 | GENERATED — rebuilds itself | `\| `NAZWA_MARKI` \| `"Your Publication"` \| Konto na Substacku. Nazwa publikacji, tak jak m` |
| `agent-v2/config.py` | 116 | **FIELD** | `NAZWA_MARKI = "Your Publication"` |
| `agent-v2/run.py` | 564 | comment — harmless, but stale | `# „Your Publication", czyli nas — Substack melduje w tym` |
| `agent-v2/systemd/nia-agent.service` | 2 | **BY HAND** — systemd unit | `Description=Your Publication — agent` |
| `agent-v2/systemd/nia-artykul.service` | 2 | **BY HAND** — systemd unit | `Description=Your Publication — artykul tygodniowy` |
| `agent-v2/tests/test_data_wystawienia.py` | 52 | test fixture | `"author": {"name": "Your Publication"}}}},` |
| `agent-v2/tests/test_reagujacy_jest_celem.py` | 446 | test fixture | `skutek("sched:11", "scheduled_note_sent", ["Your Publication"],` |
| `agent-v2/tests/test_reagujacy_jest_celem.py` | 448 | test fixture | `skutek("sched:12", "scheduled_note_sent", ["Your Publication"],` |
| `agent-v2/tests/test_wzajemnosc.py` | 231 | test fixture | `w.append(skutek("scheduled_note_sent", ["Your Publication"],` |
| `agent-v2/tests/test_wzajemnosc.py` | 383 | test fixture | `"Your Publication" not in` |
| `agent-v2/tests/test_zrodla_ruchu.py` | 105 | test fixture | `return {"source": "c-%s" % ident, "sourceName": "Your Publication: …",` |
| `konfiguracja.example.toml` | 41 | TEMPLATE — this is the file you copy | `nazwa_marki = "Your Publication"` |

---

## nisza — `how everyday things are made and regulated`

Constant `config.NISZA`, set by `temat.nisza`

| file | line | how | context |
|---|---|---|---|
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 12886 | GENERATED — rebuilds itself | `\| `NISZA` \| `"how everyday things are made and regulated"` \| HASLA, KTORYMI AGENT SZUKA ` |
| `agent-v2/config.py` | 2165 | **FIELD** | `NISZA = "how everyday things are made and regulated"` |
| `agent-v2/stages.py` | 1271 | **INJECTED** — follows the field | `"You find documented facts about how everyday things are made and regulated for an anony` |
| `agent-v2/stages.py` | 6934 | **INJECTED** — follows the field | `"You rank candidate facts for a publication about how everyday things are made and regul` |
| `konfiguracja.example.toml` | 53 | TEMPLATE — this is the file you copy | `nisza = "how everyday things are made and regulated"` |

---

## uchwyt konta — `your-handle`

Constant `config.SUBSTACK_HANDLE`, set by `konto.uchwyt`

| file | line | how | context |
|---|---|---|---|
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 2084 | GENERATED — rebuilds itself | `5. Nowy szkic pod `https://{SUBSTACK_HANDLE}.substack.com/publish/post?type=newsletter` ` |
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 12748 | GENERATED — rebuilds itself | `\| `SUBSTACK_HANDLE` \| `"your-handle"` \| — \|` |
| `agent-v2/browser.py` | 507 | comment — harmless, but stale | `# (your-handle.substack.com), a /api/v1/reader/* i /api/v1/user/*` |
| `agent-v2/browser.py` | 1246 | comment — harmless, but stale | `# `substack.com/@your-handle/following` oddaje 26 uchwytow, a` |
| `agent-v2/config.py` | 118 | **FIELD** | `SUBSTACK_HANDLE = "your-handle"` |
| `agent-v2/tests/test_dowod_przeciw_hostowi.py` | 448 | test fixture | `"https://your-handle.substack.com/p/%s" % sciezka,` |
| `agent-v2/tests/test_naprawa_zamiast_ciecia.py` | 302 | test fixture | `LINK = "https://your-handle.substack.com/p/first-remove-the-brakes"` |
| `agent-v2/tests/test_obserwacje.py` | 330 | test fixture | `Z_LINKIEM = "Pressure panels have a tiny hole. https://your-handle.substack.com/p/x"` |
| `agent-v2/tests/test_obserwacje.py` | 331 | test fixture | `Z_LINKIEM_2 = "Eggs are refrigerated in America. https://your-handle.substack.com/p/y"` |
| `agent-v2/tests/test_pula_obserwacji.py` | 20 | test fixture | `Odczyt, nic nie klikniete, konto `your-handle`:` |
| `agent-v2/tests/test_pula_obserwacji.py` | 22 | test fixture | `substack.com/@your-handle/following  -> 26 uchwytow` |
| `agent-v2/tests/test_pula_obserwacji.py` | 23 | test fixture | `/api/v1/user/your-handle/public_profile` |
| `agent-v2/tests/test_wstrzykniecie.py` | 133 | test fixture | `LINK = "https://your-handle.substack.com/p/the-hole-in-your-airplane-window"` |
| `agent-v2/tests/test_wzrost_konta.py` | 54 | test fixture | `"handle": "your-handle",` |
| `konfiguracja.example.toml` | 36 | TEMPLATE — this is the file you copy | `uchwyt = "your-handle"` |

---

## language — `English`

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

**2 places** need a human hand when the account changes.
Everything else either follows `konfiguracja.toml`, regenerates
itself, or is a test fixture that no live run reads.

| what | file | line | context |
|---|---|---|---|
| nazwa marki | `agent-v2/systemd/nia-agent.service` | 2 | `Description=Your Publication — agent` |
| nazwa marki | `agent-v2/systemd/nia-artykul.service` | 2 | `Description=Your Publication — artykul tygodniowy` |

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
