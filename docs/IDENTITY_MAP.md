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
| `README.md` | 3 | comment — harmless, but stale | `**Your autonomous Substack editor. Your publication, your rules.**` |
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 1 | GENERATED — rebuilds itself | `# Your Publication — dokumentacja odtworzeniowa agenta` |
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 46 | GENERATED — rebuilds itself | `Agent prowadzi anglojęzycznego Substacka **„Your Publication"**, który` |
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 12101 | GENERATED — rebuilds itself | `\| `NAZWA_MARKI` \| `"Your Publication"` \| Konto na Substacku. Nazwa publikacji, tak jak m` |
| `agent-v2/alarm.py` | 146 | **BY HAND** | `uruchamialby bota pod marka „Your Publication". To ma byc alarm.` |
| `agent-v2/config.py` | 139 | **FIELD** | `NAZWA_MARKI = "Your Publication"` |
| `agent-v2/konfiguracja.py` | 723 | **BY HAND** | `Placeholder marki („Your Publication", „Your AI Publication") trafialby` |
| `agent-v2/run.py` | 609 | comment — harmless, but stale | `# „Your Publication", czyli nas — Substack melduje w tym` |
| `agent-v2/systemd/nia-agent.service` | 2 | **BY HAND** — systemd unit | `Description=Your Publication — agent` |
| `agent-v2/systemd/nia-agent.timer` | 2 | **BY HAND** — systemd unit | `Description=Your Publication — zegar agenta` |
| `agent-v2/systemd/nia-alarm.service` | 2 | **BY HAND** — systemd unit | `Description=Your Publication — kontrola sesji, zdrowia i alarm` |
| `agent-v2/systemd/nia-alarm.timer` | 2 | **BY HAND** — systemd unit | `Description=Your Publication — zegar kontroli sesji` |
| `agent-v2/systemd/nia-artykul.service` | 2 | **BY HAND** — systemd unit | `Description=Your Publication — artykul tygodniowy` |
| `agent-v2/systemd/nia-artykul.timer` | 2 | **BY HAND** — systemd unit | `Description=Your Publication — zegar artykulu tygodniowego` |
| `agent-v2/tests/test_data_wystawienia.py` | 52 | test fixture | `"author": {"name": "Your Publication"}}}},` |
| `agent-v2/tests/test_jednostki_dla_instalacji.py` | 108 | test fixture | `"Your Publication" not in tresc)` |
| `agent-v2/tests/test_jednostki_dla_instalacji.py` | 134 | test fixture | `_zostala_marka = any("Your Publication" in t for t in bez_zmian.values())` |
| `agent-v2/tests/test_konto_z_env.py` | 107 | test fixture | `and len(konfiguracja.placeholder_konta("", "Your Publication")) == 2)` |
| `agent-v2/tests/test_panel.py` | 142 | test fixture | `.replace('Your Publication', 'Legacy publication'), encoding='utf-8')` |
| `agent-v2/tests/test_pochodne_po_konfiguracji.py` | 26 | test fixture | `domyslnej „Your Publication".` |
| `agent-v2/tests/test_pochodne_po_konfiguracji.py` | 111 | test fixture | `if isinstance(wartosc, str) and ("Your Publication" in wartosc` |
| `agent-v2/tests/test_pochodne_po_konfiguracji.py` | 139 | test fixture | `config.NAZWA_MARKI == "Your Publication", config.NAZWA_MARKI)` |
| `agent-v2/tests/test_reagujacy_jest_celem.py` | 446 | test fixture | `skutek("sched:11", "scheduled_note_sent", ["Your Publication"],` |
| `agent-v2/tests/test_reagujacy_jest_celem.py` | 448 | test fixture | `skutek("sched:12", "scheduled_note_sent", ["Your Publication"],` |
| `agent-v2/tests/test_wzajemnosc.py` | 230 | test fixture | `w.append(skutek("scheduled_note_sent", ["Your Publication"],` |
| `agent-v2/tests/test_wzajemnosc.py` | 402 | test fixture | `"Your Publication" not in` |
| `agent-v2/tests/test_zrodla_ruchu.py` | 105 | test fixture | `return {"source": "c-%s" % ident, "sourceName": "Your Publication: …",` |
| `konfiguracja.example.toml` | 41 | TEMPLATE — this is the file you copy | `nazwa_marki = "Your Publication"` |
| `packs/README.md` | 27 | **BY HAND** | `your publication.` |
| `panel/app.js` | 109 | **BY HAND** | `return `<div class="eyebrow">${t('Your publication. Your rules.','Twoja publikacja. Twoj` |
| `panel/app.js` | 116 | **BY HAND** | `return `<h1>${t('Connect your publication.','Podłącz swoją publikację.')}</h1><p class="` |
| `panel/app.js` | 142 | **BY HAND** | `capture();draft={id:null,target:'my-preset',meta:{opis:''},revision:null,models:clone(st` |

---

## nisza — ``

Constant `config.NISZA`, set by `temat.nisza`

Appears nowhere in the tree outside `config.py` — nothing to
hand-edit.

---

## uchwyt konta — `your-handle`

Constant `config.SUBSTACK_HANDLE`, set by `konto.uchwyt`

| file | line | how | context |
|---|---|---|---|
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 736 | GENERATED — rebuilds itself | `\| `konto_placeholder()` \| Konto instalacji nadal jest placeholderem — bot sprawdzalby pr` |
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 2326 | GENERATED — rebuilds itself | `5. Nowy szkic pod `https://{SUBSTACK_HANDLE}.substack.com/publish/post?type=newsletter` ` |
| `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md` | 12102 | GENERATED — rebuilds itself | `\| `SUBSTACK_HANDLE` \| `"your-handle"` \| — \|` |
| `agent-v2/alarm.py` | 140 | **BY HAND** | `"""Konto instalacji nadal jest placeholderem — bot sprawdzalby profil „your-handle".` |
| `agent-v2/browser.py` | 592 | comment — harmless, but stale | `# (your-handle.substack.com), a /api/v1/reader/* i /api/v1/user/*` |
| `agent-v2/browser.py` | 1346 | comment — harmless, but stale | `# `substack.com/@your-handle/following` oddaje 26 uchwytow, a` |
| `agent-v2/config.py` | 141 | **FIELD** | `SUBSTACK_HANDLE = "your-handle"` |
| `agent-v2/konfiguracja.py` | 699 | **BY HAND** | `PLACEHOLDER_UCHWYTU = "your-handle"` |
| `agent-v2/tests/test_cicha_porazka.py` | 416 | test fixture | `"https://your-handle.substack.com/p/tekst", "Ktos", TEKST, wyslij=True)` |
| `agent-v2/tests/test_dowod_przeciw_hostowi.py` | 450 | test fixture | `"https://your-handle.substack.com/p/%s" % sciezka,` |
| `agent-v2/tests/test_komentarz_potwierdzony.py` | 502 | test fixture | `"url": "https://your-handle.substack.com/p/tekst"},` |
| `agent-v2/tests/test_konto_z_env.py` | 10 | test fixture | `a `podlacz ai` z placeholderem `your-handle` przechodzil bez slowa — bot` |
| `agent-v2/tests/test_konto_z_env.py` | 11 | test fixture | `sprawdzalby potem konto o nazwie „your-handle" i pisal pod marka „Your AI` |
| `agent-v2/tests/test_konto_z_env.py` | 92 | test fixture | `tekst_ai.replace('uchwyt = "your-handle"', 'uchwyt = "moj-uchwyt"')` |
| `agent-v2/tests/test_naprawa_zamiast_ciecia.py` | 305 | test fixture | `LINK = "https://your-handle.substack.com/p/first-remove-the-brakes"` |
| `agent-v2/tests/test_obserwacje.py` | 364 | test fixture | `Z_LINKIEM = "Pressure panels have a tiny hole. https://your-handle.substack.com/p/x"` |
| `agent-v2/tests/test_obserwacje.py` | 365 | test fixture | `Z_LINKIEM_2 = "Sorting machines read the barcode. https://your-handle.substack.com/p/y"` |
| `agent-v2/tests/test_panel.py` | 50 | test fixture | `self.assertEqual(result['fields']['konto.uchwyt'], 'your-handle')` |
| `agent-v2/tests/test_panel.py` | 141 | test fixture | `path.write_text(path.read_text(encoding='utf-8').replace('your-handle', 'legacy-profile'` |
| `agent-v2/tests/test_przyklad_przechodzi_reguly.py` | 113 | test fixture | `ai.pola.get("konto.uchwyt") == "your-handle", ai.pola.get("konto.uchwyt"))` |
| `agent-v2/tests/test_pula_obserwacji.py` | 20 | test fixture | `Odczyt, nic nie klikniete, konto `your-handle`:` |
| `agent-v2/tests/test_pula_obserwacji.py` | 22 | test fixture | `substack.com/@your-handle/following  -> 26 uchwytow` |
| `agent-v2/tests/test_pula_obserwacji.py` | 23 | test fixture | `/api/v1/user/your-handle/public_profile` |
| `agent-v2/tests/test_wstrzykniecie.py` | 133 | test fixture | `LINK = "https://your-handle.substack.com/p/example-article-slug"` |
| `agent-v2/tests/test_wzrost_konta.py` | 54 | test fixture | `"handle": "your-handle",` |
| `analizy/2026-09-06-presety-odlaczenie-klony/RAPORT.md` | 46 | **BY HAND** | `Śledzony preset `ai` zawiera przykładowe konto `your-handle`; lokalny `nia` ma inne usta` |
| `konfiguracja.example.toml` | 36 | TEMPLATE — this is the file you copy | `uchwyt = "your-handle"` |
| `panel/app.js` | 142 | **BY HAND** | `capture();draft={id:null,target:'my-preset',meta:{opis:''},revision:null,models:clone(st` |
| `presety/ai/preset.toml` | 75 | **BY HAND** | `uchwyt = "your-handle"` |
| `presety/hidden-bill/README.md` | 85 | **BY HAND** | `W repo pozostaje publiczny przykład `konto.uchwyt = "your-handle"`.` |
| `presety/hidden-bill/preset.toml` | 13 | **BY HAND** | `uchwyt = "your-handle"` |
| `presety/nia-unfiltered/preset.toml` | 8 | **BY HAND** | `uchwyt = "your-handle"` |

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

**20 places** need a human hand when the account changes.
Everything else either follows `konfiguracja.toml`, regenerates
itself, or is a test fixture that no live run reads.

| what | file | line | context |
|---|---|---|---|
| nazwa marki | `agent-v2/alarm.py` | 146 | `uruchamialby bota pod marka „Your Publication". To ma byc alarm.` |
| nazwa marki | `agent-v2/konfiguracja.py` | 723 | `Placeholder marki („Your Publication", „Your AI Publication") trafialb` |
| nazwa marki | `agent-v2/systemd/nia-agent.service` | 2 | `Description=Your Publication — agent` |
| nazwa marki | `agent-v2/systemd/nia-agent.timer` | 2 | `Description=Your Publication — zegar agenta` |
| nazwa marki | `agent-v2/systemd/nia-alarm.service` | 2 | `Description=Your Publication — kontrola sesji, zdrowia i alarm` |
| nazwa marki | `agent-v2/systemd/nia-alarm.timer` | 2 | `Description=Your Publication — zegar kontroli sesji` |
| nazwa marki | `agent-v2/systemd/nia-artykul.service` | 2 | `Description=Your Publication — artykul tygodniowy` |
| nazwa marki | `agent-v2/systemd/nia-artykul.timer` | 2 | `Description=Your Publication — zegar artykulu tygodniowego` |
| nazwa marki | `packs/README.md` | 27 | `your publication.` |
| nazwa marki | `panel/app.js` | 109 | `return `<div class="eyebrow">${t('Your publication. Your rules.','Twoj` |
| nazwa marki | `panel/app.js` | 116 | `return `<h1>${t('Connect your publication.','Podłącz swoją publikację.` |
| nazwa marki | `panel/app.js` | 142 | `capture();draft={id:null,target:'my-preset',meta:{opis:''},revision:nu` |
| uchwyt konta | `agent-v2/alarm.py` | 140 | `"""Konto instalacji nadal jest placeholderem — bot sprawdzalby profil ` |
| uchwyt konta | `agent-v2/konfiguracja.py` | 699 | `PLACEHOLDER_UCHWYTU = "your-handle"` |
| uchwyt konta | `analizy/2026-09-06-presety-odlaczenie-klony/RAPORT.md` | 46 | `Śledzony preset `ai` zawiera przykładowe konto `your-handle`; lokalny ` |
| uchwyt konta | `panel/app.js` | 142 | `capture();draft={id:null,target:'my-preset',meta:{opis:''},revision:nu` |
| uchwyt konta | `presety/ai/preset.toml` | 75 | `uchwyt = "your-handle"` |
| uchwyt konta | `presety/hidden-bill/README.md` | 85 | `W repo pozostaje publiczny przykład `konto.uchwyt = "your-handle"`.` |
| uchwyt konta | `presety/hidden-bill/preset.toml` | 13 | `uchwyt = "your-handle"` |
| uchwyt konta | `presety/nia-unfiltered/preset.toml` | 8 | `uchwyt = "your-handle"` |

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
