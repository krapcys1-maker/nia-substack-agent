# Contributing

Contributions can improve the engine or add a reusable editorial preset.
Use a development checkout without production sessions, keys or instance data.

You can also help without writing code: describe where installation gets stuck,
review a sample article in your field, or propose an editorial preset. Start with
the [issue forms](https://github.com/krapcys1-maker/nia-substack-agent/issues/new/choose)
and [roadmap](ROADMAP.md). A public or redacted example is enough; never include
account sessions or private drafts.

## Pick a first contribution

**Help build a small, self-hosted publishing project whose voice can be its own.**
Writers, subject experts, designers, translators and Python developers are welcome.
These are open tasks, checked against the repository on 8 September 2026:

| Task | Useful skills | First deliverable |
|---|---|---|
| [Fresh installation #31](https://github.com/krapcys1-maker/nia-substack-agent/issues/31) | Trying software, clear reporting | One OS, one confusing step and a proposed guide correction |
| [Panel access and language #32](https://github.com/krapcys1-maker/nia-substack-agent/issues/32) | Accessibility, UI or English/Polish | A keyboard walkthrough or wording fix for one flow |
| [Editorial preset #1](https://github.com/krapcys1-maker/nia-substack-agent/issues/1) | Knowledge of a subject, writing | An audience and a small source list; a full preset can follow |
| [Voice evaluation #33](https://github.com/krapcys1-maker/nia-substack-agent/issues/33) | Writing, evaluation, optional Python | Source packets and a rubric that cover more than one mood |
| [Repeated news #34](https://github.com/krapcys1-maker/nia-substack-agent/issues/34) | Python, information retrieval | Fixtures showing duplicates and useful follow-ups |
| [Saved-draft view #35](https://github.com/krapcys1-maker/nia-substack-agent/issues/35) | Python and browser UI | A read-only list/detail view for one active instance |
| [Provider timeouts #2](https://github.com/krapcys1-maker/nia-substack-agent/issues/2) | Python, API adapters | Offline cases for model changes and output-limit overrides |

Comment on the issue with the part you would like to take and your proposed first
step. Check existing comments and PRs before starting. A small contribution is
easier to review; you do not need to deliver the whole roadmap. If you only have
time to review sources or test a screen, say so.

The installation and panel-review tasks are labelled **good first issue**.
More involved runtime changes use **help wanted**. The issues include starting
files, completion criteria and test boundaries. No paid generation or access to
the project's live Substack session is needed for these first deliverables.

## A free development check

Use a fresh checkout and Python 3.11+. After creating and activating a virtual
environment as described in [INSTALL.md](docs/INSTALL.md), run:

```bash
python -m pip install -r requirements-dev.txt
python narzedzia/presety.py sprawdz nia-unfiltered
python agent-v2/tests/test_personality.py
```

These commands install development dependencies, validate the public preset and
run isolated tests. They do not generate content or publish. Missing account/key
warnings from preset validation are expected in a clean development checkout.
For a documentation or design report, running Python is optional.

Paid comparisons are separate: agree on the model, number of calls and estimated
cost before running them. Never make a paid benchmark a prerequisite for a source
list, usability report or offline regression test.

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
