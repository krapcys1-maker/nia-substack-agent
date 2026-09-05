# Presets

A **preset** is one TOML file that describes an entire publication — subject,
voice, sources, model split, daily volumes, schedule and money — and that can
be plugged into the engine and unplugged again. Without an active preset the
engine refuses to run: there is no built-in subject to fall back to.

```bash
python narzedzia/presety.py lista            # what is here, and what is plugged in
python narzedzia/presety.py sprawdz ai       # errors and warnings, no paid calls
python narzedzia/presety.py podglad ai       # the prompts exactly as a model gets them
python narzedzia/presety.py podlacz ai       # activate (creates agent-v2/instancje/ai/)
python narzedzia/presety.py status
python narzedzia/presety.py odlacz           # deactivate; the instance data stays
```

- `presety/przyklady/` — shipped examples, tracked in git. `zgodnosc` is the
  engine's former built-in profile written out explicitly; `ai` is a full
  example: AI in English, two notes a day, one article a week.
- `presety/*.toml` — **your** presets. Gitignored, because a preset carries the
  account handle and the subject, which is exactly what should not be in a
  public repository. Start by copying an example.

The full description, in Polish, is in [docs/PRESETY.md](../docs/PRESETY.md):
what each section does, what happens on activation and deactivation, what is
isolated per instance and what is deliberately shared.
