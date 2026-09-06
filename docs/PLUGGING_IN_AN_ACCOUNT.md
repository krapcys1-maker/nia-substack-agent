# Account and preset customization

For the installation sequence use [INSTALL.md](INSTALL.md). This document
explains which settings belong to the user and which belong to a reusable preset.

## Your account belongs to the installation

Copy the root `.env.example` to `agent-v2/.env` and fill in:

```dotenv
SUBSTACK_HANDLE=your-real-handle
NAZWA_MARKI=Your publication name
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
DRY_RUN=true
```

Use your profile handle without `@`. The environment values override
`[konto]` in the preset, so a hundred users can select the same public preset
without editing it. Account identity, API keys and SMTP configuration do not
belong in a shared preset. Use only the keys required by its model roles.

The loading order is: exported process variables, `agent-v2/.env`, root
`.env`, then preset values for fields not overridden by the environment.
The preset command shows the effective account during activation. Inspect it;
a stale exported variable can hide your new file value.

`sprawdz` warns about placeholders and missing keys. `podlacz` refuses an
unresolved account placeholder. Neither checks your provider subscription or
authenticates your Substack account. Establish the browser session **after**
activation, then verify the logged-in account manually.

## Customize a preset

If only the account differs, select the public preset directly. If you want to
change output volumes, models, sources or writing style, copy the **whole
directory** into a private preset.

Linux/macOS:

```bash
cp -R presety/hidden-bill presety/moj-preset
```

Windows PowerShell:

```powershell
Copy-Item presety/hidden-bill presety/moj-preset -Recurse
```

Choose a destination that does not already exist. In
`presety/moj-preset/preset.toml`, set `preset.nazwa = "moj-preset"` and edit the
editorial settings. Keep account overrides in the installation's `.env`.
The new directory is ignored by Git; the shared `hidden-bill` package remains
unchanged.

| What to change | Where |
|---|---|
| Subject, language, editorial angle and search vocabulary | `[temat]` |
| RSS/Atom feeds, YouTube sources and preferred domains | `[zrodla]` |
| Notes, articles, comments, likes and other activity | `[wolumeny]` |
| Run times and article days/time | `[harmonogram]` |
| Publication window, note mix and quiet days | `[publikowanie]` |
| Monthly, daily and per-run thresholds | `[pieniadze]` |
| Model assignment per role and optional images | `[modele]` |
| Voice description, profiles and corpus paths | `[styl]` |
| Editorial direction and voice for each form | `prompty/*.md` |
| Positive/negative profiles, corpus and pins | `styl/` |

The [template](../presety/SZABLON/preset.toml) lists the supported fields.
`sprawdz` validates relationships between volumes, schedules and required topic
material. Do not rely on old fixed counts copied from a previous publication.

A role accepts only a model supported by the implemented adapters. The current
text transport supports Claude and DeepSeek families; the OpenAI path is for
images. Choosing a different text provider requires code and validation, not
just a new key or model string. Token ceilings and reasoning settings are not
fully exposed by the preset schema.

When editing a corpus, regenerate its pins with
`narzedzia/przypnij_styl.py`; see the selected preset's guide. Keep paths
relative to that preset. Files intended to come from the shared repository use
an explicit `repo:` prefix.

```bash
python narzedzia/presety.py sprawdz moj-preset
python narzedzia/presety.py pokaz moj-preset
python narzedzia/presety.py podglad moj-preset
```

After stopping the existing scheduler and workflows:

```bash
python narzedzia/presety.py podlacz moj-preset --instancja moja-redakcja
```

Changes to fields, loaded prompt blocks or style assets alter the preset
fingerprint and require reactivation. Preview renders prompts without paid
calls; it is not a live writing-quality benchmark. Read the full style profiles
as well: the preview does not display every profile in full.

## Start another publication

Prefer a **fresh clone from GitHub**, not a filesystem copy of a used install.
A filesystem copy can bring its `.env`, activation pointer, old session, draft
queue and costs along with it.

Give the new clone its own environment and activate with a new instance ID.
If using the same machine for multiple accounts, also solve browser and service
isolation as described in [INSTALL.md](INSTALL.md#5-browser-session). Separate
instance directories do not change the shared Chrome port/profile or systemd
unit names.

## Detach versus erase

`python narzedzia/presety.py odlacz` removes the local activation pointer.
It preserves the instance's data for later resumption. It does not clear API
keys, browser login, old banks or anything already published.

For a fresh subject, stop processes, detach, then attach with a **new instance
ID**. Reusing an old ID means continuing that instance. The owner marker rejects
a different preset/account during attachment unless `--przejmij` is explicitly
used; takeover is not a clean start and does not empty the data.

Keep the same-account Substack history in mind: the bot can read previous
activity from the account even when its local instance is new. A genuinely new
publication also needs the appropriate account/publication setup on Substack.

## Bring changes back to the project

Normal users do not need push access to this repository. Running the bot never
submits their environment or preset choices to GitHub.

To contribute a new public preset, prepare a standalone package with account
placeholders, its own usable style assets and no runtime data. Maintainers must
add it to both the public allowlist in `.gitignore` and the tracked-file audit.
Review it in a development checkout and run the preset checks before publishing.

`presety.py eksportuj` exports normalized TOML only. Transfer the entire preset
directory when prompts and style assets are needed; that command is not a
complete package exporter.

The legacy `agent-v2/konfiguracja.toml` is a migration input, not the setup path
for new installations. It is not automatically restored after detaching a
preset. See [PRESETY.md](PRESETY.md) for the precise boundaries.
