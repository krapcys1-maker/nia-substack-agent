# Installation

**Prefer a visual interface?** Use the [control panel guide with screenshots](PANEL.md)
or [instrukcja po polsku](PANEL_PL.md). Windows: install Python and Chrome,
extract the repository, then double-click `Install-NIA.cmd`. Later use
`Start-NIA.cmd`. Existing environments can run `python narzedzia/panel.py`.

Run commands from the repository root. This guide uses the preset workflow:
**download → local environment → choose preset → activate → log in → run →
schedule**. A normal user does not need to edit engine code or shared presets.

## 1. Requirements

- Python **3.11+**, preferably 3.12, and Git (or a downloaded repository ZIP).
- A Substack account and publication that you can access manually.
- API access for the roles in the selected preset. Both bundled presets use
  Anthropic and DeepSeek for text. AI also enables optional OpenAI images;
  Hidden Bill starts with images disabled.
- Playwright's Chromium and a separately installed Google Chrome for the
  interactive browser session.
- For unattended Linux operation: a service user, systemd, and a working browser
  session on that server. Browser/display setup is currently manual.

The setup is not an all-in-one installer. Model names in a preset are
configuration, not a guarantee that your provider account can access them.
There is no fixed cost per article or guaranteed monthly output.

## 2. Download and install

```bash
git clone https://github.com/krapcys1-maker/nia-substack-agent.git
cd nia-substack-agent
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = "utf-8"
```

If PowerShell prevents environment activation, invoke
`.\.venv\Scripts\python.exe` in place of `python` in the following commands.

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python narzedzia/zaleznosci.py --sprawdz
```

On Linux, install Chromium's system dependencies with
`python -m playwright install-deps chromium` if required by Playwright.
On Windows, also run `python -m pip install tzdata`: preset validation uses
IANA timezone data, which a standard Windows Python installation may not have.
The root `requirements.txt` is the installation entry point used here and in
CI. It currently uses minimum versions, so it is not a reproducible lockfile.

## 3. Set your account and keys

Linux/macOS:

```bash
cp .env.example agent-v2/.env
```

Windows PowerShell:

```powershell
Copy-Item .env.example agent-v2/.env
```

Do this only for a fresh installation; preserve an existing environment file.
Edit the local `agent-v2/.env`:

```dotenv
SUBSTACK_HANDLE=your-real-handle
NAZWA_MARKI=Your publication name
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
DRY_RUN=true
KILL_SWITCH=false
```

Replace the handle and name with your own values, and fill in the required
keys. The handle is the profile name without `@`, not a publication URL.
Keys never go in `preset.toml`. Keep one environment file per installation.
Exported process variables take precedence, followed by `agent-v2/.env`,
then the root `.env` fallback. An old exported handle can therefore override a
new value in the file.

Optional email alerts are configured in the same local file. They are not
needed for preset validation.

## 4. Select and activate a preset

```bash
python narzedzia/presety.py lista
python narzedzia/presety.py sprawdz hidden-bill
python narzedzia/presety.py pokaz hidden-bill
python narzedzia/presety.py podglad hidden-bill
python narzedzia/presety.py podlacz hidden-bill --instancja moja-publikacja
python narzedzia/presety.py status
```

Replace `hidden-bill` with `ai` for the AI publication. Validation and preview
do not call models or publish. Missing API keys are warnings, not a successful
provider connection test. Activation rejects unresolved account placeholders.

The shared preset stays unchanged. Activation creates a local pointer and
instance directory, records its preset/account owner, and selects its data
paths. **Activate before saving the browser session.** For this example it
belongs at `agent-v2/instancje/moja-publikacja/storage-state.json`, not the
legacy `agent-v2/data/storage-state.json`.

To change editorial settings, use a
[private preset copy](PLUGGING_IN_AN_ACCOUNT.md#customize-a-preset).
Do not create `agent-v2/konfiguracja.toml` for a new preset installation.

## 5. Browser session

Start a dedicated Chrome profile with the debugging port expected by the bot.
For one publication on this computer, examples are:

Windows PowerShell, for the standard Chrome installation:

```powershell
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' --remote-debugging-port=9222 --user-data-dir="$env:USERPROFILE\substack-agent-chrome" https://substack.com/home
```

Linux with a graphical session:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/substack-agent-chrome" https://substack.com/home
```

Log in manually to the intended account and verify the publication in Chrome.
Keep that browser available, then save the session:

```bash
python agent-v2/browser.py sesja
```

Read the result and verify that the session path belongs to your active instance.
The legacy session-save command uses a page-content heuristic; a saved file by
itself is not proof of the correct authenticated account. The publishing guard
checks the authenticated user in Substack's page bootstrap data and matches
both handle and ID to the target profile. The panel's **Verify and save session**
uses that guard before saving. Confirm the intended account in Chrome as part
of setup; an expired session needs a fresh login.

The CLI command `browser.py zaloguj` is a legacy automated login path and is
not the setup route recommended by the code.

**Multiple publications:** separate folders do not separate a Chrome already
listening on port 9222. The port and default browser profile are currently
fixed in code. Use separate machines or suitably isolated operating-system
environments for simultaneous accounts until per-instance browser configuration
is implemented. Do not assume a second clone has a second browser identity.

## 6. First workflow

With `DRY_RUN=true`, model calls are skipped and Substack writes are blocked.
This can check parts of the wiring but cannot produce a meaningful quality
sample; some stages need real model responses. Network reads and local file
writes may still occur.

For actual generation, set `DRY_RUN=false` in your local environment file.
A new process reads the updated value. Commands **without** `--wyslij` can
already incur model costs:

```bash
python agent-v2/run.py --dzien
python agent-v2/artykul_z_puli.py
```

Inspect the resulting files, source support, style and recorded costs in the
active instance. The article workflow may first need ideas and research
material; the launch guide does not seed its bank automatically.

When you intend to publish and interact from that account:

```bash
python agent-v2/run.py --dzien --wyslij
python agent-v2/artykul_z_puli.py --wyslij
```

A new clone has no active preset or session and does not run by itself.
Do not treat a successful prompt preview as a completed publication test.

## 7. Schedule on your computer

On Windows, Task Scheduler must currently be configured manually. For a daily
workflow task set:

| Task Scheduler field | Value |
|---|---|
| Program | Absolute path to this clone's `.venv\Scripts\python.exe` |
| Arguments | `agent-v2/run.py --dzien --wyslij` |
| Start in | Absolute path to the repository root |
| Trigger | Each time in the preset's `harmonogram.godziny_przebiegow_utc`, converted to the scheduler's timezone |
| Account/session | The operating-system user whose dedicated Chrome profile is logged in |
| Existing task | Do not start another instance of the same task |

Create the weekly article task using `agent-v2/artykul_z_puli.py --wyslij`
and the preset's article days/time. An optional health task runs
`agent-v2/alarm.py`. Disable the article task when the preset has zero articles.

For interactive Chrome, use a logged-in desktop session. The computer must be
awake, online and able to reach Chrome when the task starts. The repository does
not yet generate Windows tasks, handle timezone conversion or manage wake-up
settings. Linux desktop users can use the systemd setup below.

## 8. Schedule on a Linux server

Create a dedicated service user and a clone owned by that user, for example at
`/srv/substack-agent`. Repeat environment setup and **activate on the server**.
Create the virtual environment at `/srv/substack-agent/.venv`, which is the path
expected by generated services.

The server also needs a working Chrome session. The code prefers Chrome on
the local CDP port when available. Otherwise, server mode attempts headless
Chromium using the saved instance session; that fallback is not a guarantee of
successful Substack publishing. For the intended server setup, provision a
graphical or virtual display and Chrome under the service user's identity,
then log in manually through your chosen remote desktop.

The repository currently does **not** ship a complete installer/service set
for Chrome, the display and remote login. The Python timers alone are insufficient.
If transferring a saved session from another machine, put it in the active
server instance, restrict access to its owner and verify it works from that
server. Do not copy `.venv` or the activation pointer between machines.

From the server clone, as its service user:

```bash
python agent-v2/browser.py sesja
python agent-v2/browser.py serwer
```

The second command is a read check, not a publication test; read its printed
result. It may attach to the live Chrome rather than testing only the saved file.
After account verification and an intentionally enabled first workflow, generate
the timers from the active preset:

```bash
python narzedzia/jednostki.py --katalog /srv/substack-agent --uzytkownik substack-agent
```

Use your actual install path and existing service user. Inspect
`agent-v2/systemd/dla-tej-instalacji/` and follow the installation commands
printed by the generator. It generates the run and article schedules from the
active preset, not a fixed five-runs-per-day plan. Timers invoke publishing
commands, so activate them only when `DRY_RUN` and your account setup match
your intended operating mode.

**One installation per set of unit names:** the current names are
`nia-agent`, `nia-artykul` and `nia-alarm`. A second installation on the
same systemd host can overwrite the first one's units. A new output directory
does not change those service names.

## 9. Stop, switch and update

Stop the scheduler and running workflows first. On a server, stop the enabled
`nia-*.timer` units and any active corresponding services; on Windows, disable
the relevant tasks and end their running workflows. Changing `.env` alone does
not interrupt a process that has already loaded it.

```bash
python narzedzia/presety.py odlacz
python narzedzia/presety.py podlacz ai --instancja ai-start
```

A new instance starts with new local data; an old instance resumes its history.
Recheck the account/browser session and rebuild the schedule before restarting.
Detaching does not erase the previous bank, keys, browser login or published
Substack content.

After a preset change, stop obsolete timers and services as well. In particular,
changing to zero articles omits new article units but does not uninstall the
previous ones. Generate into a fresh output directory with `--wynik` when
replacing a deployment, then install only the intended files.

Update only while stopped, with a backup of private data:

```bash
git status --short
git pull --ff-only
```

Recheck the selected preset, read changes to public presets and reactivate if
its fingerprint changed. Regenerate schedules where required. Updating upstream
public preset files can change your next run; use a private copy or pin a release
when you need a stable editorial configuration.

See [architecture and clean instances](PRESETY.md) and the
[current distribution audit](../analizy/2026-09-06-dystrybucja-github/RAPORT.md).
