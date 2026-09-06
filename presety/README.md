# Presets — the cartridge

The engine in `agent-v2/` provides the research and writing workflows.
A **preset** is a reusable package of subject, sources, style and operating
settings. Your account comes from the installation's `.env`; runtime data
belongs to an instance. Detaching disables the active preset and preserves
that instance for later use. Start with [the installation guide](../docs/INSTALL.md).

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
  style profiles and editorial blocks. Your account comes from `agent-v2/.env`.
- `presety/hidden-bill/` — The Hidden Bill: everyday purchase conditions,
  fees, subscriptions, repairs and digital ownership. A complete English
  preset with six verified feeds, its own style corpus and launch research.
  See [its guide](hidden-bill/README.md).
- `presety/SZABLON/` — the empty cartridge with every field explained.
  `<<...>>` placeholders make it impossible to plug in unfinished.
- other preset directories are **yours** and gitignored. Use a private copy
  when changing editorial settings; choosing a public preset for your own
  account does not require a copy or an edit to the shared package.

The full description, in Polish, is in [docs/PRESETY.md](../docs/PRESETY.md).

## Detaching, and what "a clean engine" means

- `odlacz` removes the pointer. Model calls and account writes check it before
  proceeding. Stop processes and schedules before switching: an in-flight
  request cannot be recalled, and reattaching the same fingerprint/instance
  does not yet enforce a new activation generation.
- `AGENT_V2_PRESET=<path>` is a preview: prompts render, tests run, but no
  paid calls and no publishing. Production needs the pointer.
- An instance directory has an owner (`wlasciciel.json`: preset and account
  handle). A different preset or account on the same `--instancja` is refused;
  `--przejmij` takes it over deliberately and logs the takeover.
- Without a cartridge the engine does not read the legacy
  `agent-v2/konfiguracja.toml` (tests and `AGENT_V2_KONFIGURACJA_TOML=1` excepted).
- An empty `styl.korpus` never loads the engine's old corpus. A directory
  preset instead points to its own `styl/korpus.txt`, which can still load
  if present. Style paths resolve inside the package; a shared repository
  file is chosen explicitly: `repo:style-profiles/X.md`.
- The fingerprint covers fields, prompt blocks and the style files' contents,
  with relative paths: copying a cartridge keeps it, editing a profile changes it.

## Your account is not in the preset

A preset is meant to be shared: the same `ai` can run on many accounts. The
account is yours, so it lives in `agent-v2/.env`:

```
SUBSTACK_HANDLE=your-real-handle
NAZWA_MARKI=Your real publication name
```

Both override `[konto]` in the preset. The presets in this repository keep the
placeholder on purpose, and `podlacz` refuses to activate while the handle or
the name is still one; `sprawdz` only warns, so a preset can be judged without
an account. The instance directory records the handle that was actually used.

