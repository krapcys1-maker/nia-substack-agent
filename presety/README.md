# Presets — the cartridge

The engine in `agent-v2/` is the console: it carries the method (stages,
gates, contracts, guards) and **no subject at all** — no niche, no search
terms, no domains, no calendar, no visual identity. A **preset** is the
cartridge: one directory with everything that makes a publication *this*
publication. Plug it in and go; unplug it and the engine is empty again.

```
presety/<name>/
  preset.toml        knobs (notes/day, articles/week, comments, likes, runs,
                     models per role, budgets, schedule), account, subject,
                     sources (YouTube channels, RSS feeds, preferred hosts), style
  prompty/*.md       editorial blocks injected into the engine's briefs:
                     linia_redakcyjna, glos_artykulu, glos_notki,
                     glos_komentarza, okladka, kogo_szukamy, oswiadczenie
  styl/*.md          the positive and negative style profiles (+ optional corpus
                     with its pins and a source manifest, see presety/ai/styl/)
```

```bash
python narzedzia/presety.py lista            # what is here, and what is plugged in
python narzedzia/presety.py nowy moj-temat   # a new cartridge from SZABLON/
python narzedzia/presety.py sprawdz ai       # errors and warnings, no paid calls
python narzedzia/presety.py podglad ai       # the briefs exactly as a model gets them
python narzedzia/presety.py podlacz ai       # activate (creates agent-v2/instancje/ai/)
python narzedzia/presety.py status
python narzedzia/presety.py odlacz           # deactivate; the instance data stays
```

- `presety/ai/` — a complete cartridge, tracked in git: AI in English, two
  notes a day, one article a week, verified channels and feeds, its own
  style profiles and editorial blocks. Replace `[konto]` with your account.
- `presety/SZABLON/` — the empty cartridge with every field explained.
  `<<...>>` placeholders make it impossible to plug in unfinished.
- anything else in `presety/` is **yours** and gitignored: a preset carries
  the account handle and the subject, which is exactly what should not sit in
  a public repository.

The full description, in Polish, is in [docs/PRESETY.md](../docs/PRESETY.md).
