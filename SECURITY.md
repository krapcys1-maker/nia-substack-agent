# Security

## Reporting

Use GitHub's private vulnerability reporting when available under
**Security → Report a vulnerability**. Do not include credentials, session
state or other people's data in public issues. If private reporting is
unavailable, ask publicly for a private contact channel without posting details.

## Private installation data

| Data | Current location |
|---|---|
| API keys, account settings and mail credentials | `agent-v2/.env` |
| Active preset pointer | `agent-v2/aktywny_preset.json` |
| Saved browser session | `agent-v2/instancje/<id>/storage-state.json` |
| Idea bank, drafts, logs, database and subscriber backups | `agent-v2/instancje/<id>/` |
| Dedicated Chrome profile | The operating-system user's `substack-agent-chrome` directory |
| Custom presets | Private directories under `presety/` |

Legacy installations may also have files under `agent-v2/data/` or a root
`.env`. Detaching a preset does not delete any of these files or log out Chrome.
Session files and browser profiles carry authenticated access; protect them
along with API keys. Do not include them in a distributable clone or ZIP.

Private runtime paths are ignored by Git, and the repository audit scans tracked
files and optionally history. This is a defense against accidental inclusion,
not a guarantee against force-adding files or every possible secret format.
A clean current tree does not by itself prove a clean history.

The engine applies owner-only POSIX permissions to selected sensitive outputs
where supported. On Windows, access depends on filesystem ACLs; POSIX mode bits
are not an equivalent access-control check. The runtime data is not encrypted
by this application.

## Known isolation boundaries

One checkout has one active preset. Instance folders separate runtime files,
but Chrome's default profile/CDP port and generated systemd unit names are
not yet configurable per instance. Do not treat multiple clones sharing them
as independent account environments.

The current browser account check reads a public profile; it does not provide
a reliable authenticated-user proof. Confirm the logged-in account manually
and use isolated browser environments for different publications.

Stop schedules and running processes before switching accounts or updating the
checkout. Detachment cannot recall a request already sent, and changing an
environment file does not reload a running process.

If a credential or session is exposed, revoke or replace it using the relevant
provider's account controls and inspect account activity. For current setup
and operating limits, see [INSTALL.md](docs/INSTALL.md) and
[the distribution audit](analizy/2026-09-06-dystrybucja-github/RAPORT.md).
