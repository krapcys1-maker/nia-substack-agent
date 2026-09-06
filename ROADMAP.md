# NIA roadmap

NIA is an early-stage project, first published in September 2026 and under
active development. This roadmap describes intended priorities, not release
dates or features already available. Feedback from real installations will
help determine the order.

## Available now

- Research, a persistent idea bank, articles and Notes.
- Source and editorial checks, bounded factual repairs and saved rejected drafts.
- API attempt accounting, unknown-usage reservations and a read-only cost/research/memory report.
- Operation deadlines, server retry pauses, reusable results and idea recovery after drafting errors.
- Browser publishing and configurable replies, comments, likes and restacks.
- Optional following and free subscriptions, disabled in the bundled presets.
- Reusable AI and Hidden Bill presets, a template and private instance data.
- Local CLI operation and a generator for Linux systemd services and timers.
- An inline [product film and published examples](docs/DEMO.md).

## Next priorities

| Priority | Planned improvement | What completion should demonstrate |
|---|---|---|
| **A clearer first run** | A guided setup/preflight command checking the preset, environment, model access and browser identity | A fresh installation can identify a missing prerequisite before attempting publication, with a specific next step |
| **Recovery across restarts** | Recover interrupted work after a process or machine stops, with clear publication outcomes | Restarting preserves paid work and resolves uncertain publication state before another send |
| **Easier scheduling** | Simplify Linux browser/service setup and add a Windows task generator | A new user can create, inspect and disable the schedule using documented steps |
| **More editorial directions** | Community presets with source lists, original style examples and reviewed sample output | A new subject works in a clean instance without changes to engine code |

Recent [execution and accounting improvements](https://github.com/krapcys1-maker/nia-substack-agent/pull/3)
and [memory and research fixes](https://github.com/krapcys1-maker/nia-substack-agent/pull/4)
have shipped. The next reliability work extends that recovery across process
restarts. The [preset contribution request](https://github.com/krapcys1-maker/nia-substack-agent/issues/1)
is another starting point for contributors.

## Exploring after that

- A small local dashboard for drafts, run status and costs.
- A reviewed container/server installation path, including browser login.
- Per-instance browser ports, profiles and service names for simultaneous accounts.
- An English command interface and evaluation of additional writing languages.
- Shareable, redacted evaluation reports comparing source quality, costs and recovery across repeated runs.

These ideas are **not implemented features**. Today, multiple clones on one
machine still require browser and service isolation, and server setup is manual.
See the [installation guide](docs/INSTALL.md) for the supported paths.

## How to influence the next release

Open a [bug report, feature request or preset proposal](https://github.com/krapcys1-maker/nia-substack-agent/issues/new/choose).
For setup feedback, include the operating system, preset, command and the step
that failed. Remove keys, cookies, personal identifiers and private publication
content. A small reproducible case is especially helpful.

See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and the preset format, and
[releases](https://github.com/krapcys1-maker/nia-substack-agent/releases) for
changes that have actually shipped.
