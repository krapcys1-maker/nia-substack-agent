# NIA roadmap

NIA is an early-stage project, first published in September 2026 and under
active development. This roadmap describes intended priorities, not release
dates or features already available. Feedback from real installations will
help determine the order.

## Available now

- Research, a persistent idea bank, articles and Notes.
- Source and editorial checks, saved drafts and recorded model costs.
- Browser publishing and configurable replies, comments, likes and restacks.
- Optional following and free subscriptions, disabled in the bundled presets.
- Reusable AI and Hidden Bill presets, a template and private instance data.
- Local CLI operation and a generator for Linux systemd services and timers.
- An inline [product film and published examples](docs/DEMO.md).

## Next priorities

| Priority | Planned improvement | What completion should demonstrate |
|---|---|---|
| **A clearer first run** | A guided setup/preflight command checking the preset, environment, model access and browser identity | A fresh installation can identify a missing prerequisite before attempting publication, with a specific next step |
| **More reliable unattended runs** | Better stage timeout behavior, recovery reports and visible publication outcomes | A deliberately failed stage leaves a useful result; later independent work proceeds when safe; retries do not duplicate a post |
| **Easier scheduling** | Simplify Linux browser/service setup and add a Windows task generator | A new user can create, inspect and disable the schedule using documented steps |
| **More editorial directions** | Community presets with source lists, original style examples and reviewed sample output | A new subject works in a clean instance without changes to engine code |

The existing [stage timeout report](https://github.com/krapcys1-maker/nia-substack-agent/issues/2)
and [preset contribution request](https://github.com/krapcys1-maker/nia-substack-agent/issues/1)
are useful starting points. Recovery should make failures understandable; it
should not silently bypass a publishing guard or account error.

## Exploring after that

- A small local dashboard for drafts, run status and costs.
- A reviewed container/server installation path, including browser login.
- Per-instance browser ports, profiles and service names for simultaneous accounts.
- An English command interface and evaluation of additional writing languages.
- Opt-in, reproducible run reports with source quality, costs and recovery results.

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
