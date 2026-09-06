# Contributing

Contributions can improve the engine or add a reusable editorial preset.
Use a development checkout without production sessions, keys or instance data.

## Add a preset

Start from `presety/SZABLON/` or copy an existing public preset. A modern preset
is a **directory** containing its TOML, prompt blocks and style assets.
The older single-file subject packs under `packs/` are not the complete
preset format used by the current installation guide.

Keep account placeholders in the public TOML. The user's real handle, brand and
keys come from `agent-v2/.env`. Include an explanation of the audience, source
selection, writing style, expected operating volumes and evaluation criteria.
Distinguish original style examples from factual evidence.

```bash
python narzedzia/presety.py sprawdz your-preset
python narzedzia/presety.py podglad your-preset
python agent-v2/tests/test_presety.py
```

Custom preset directories are ignored by default. For an accepted public preset,
update the explicit allowlist in both `.gitignore` and `narzedzia/audyt.py`,
then add it to the catalog and CI validation. Do not force-add private copies,
credentials, cookies or runtime files.

## Change the engine

Use Python 3.11+ and install `requirements-dev.txt`. Describe the concrete
before/after behavior and the checks relevant to the change. Preserve the
boundaries between shared presets, installation settings and instance data.

For affected generated documentation:

```bash
python narzedzia/mapa_funkcji.py
python agent-v2/dokumentacja-zrodla/sklej.py
python agent-v2/tests/test_liczby_w_dokumentach.py
```

For repository checks:

```bash
python narzedzia/zaleznosci.py --sprawdz
python narzedzia/audyt.py --historia
```

The audit runs generators and can rewrite generated documents. Run it in the
development checkout. Tests are standalone scripts; the
[CI workflow](.github/workflows/testy.yml) defines the full run, known exclusions
and history-dependent skips. Do not count an environment skip as a passing test.
Paid tests under `agent-v2/tests/platne/` require separate intentional use.

When changing a runtime boundary, test the failure case as well as success:
for example, two different accounts attempting to reuse one instance, or a
process trying to continue after detachment. Avoid duplicating configuration
values and distinguish unavailable evidence from a negative finding.

## Documentation and review

Keep the README focused on the product and first use. Detailed setup belongs in
[INSTALL.md](docs/INSTALL.md); the current preset contract is documented in
[PRESETY.md](docs/PRESETY.md). Historical investigations under `analizy/`
record the state at their stated date and are not installation instructions.

Use relative links in repository documents so they work on GitHub and after
cloning. Code identifiers and many technical comments are Polish; user-facing
setup documentation is primarily English.

Never include credentials or other users' personal data in a contribution.
For a security report, follow [SECURITY.md](SECURITY.md).
