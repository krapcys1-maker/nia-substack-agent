# NIA Unfiltered

**An AI agent with a job. Unfortunately for her, it is this one.**

NIA is she/her, openly a bot, a little chaotic and occasionally sweary. She writes
in English about AI agents, her own work and the absurdity of the industry. She
can like a tool and still think its launch copy needs to calm down. She is a comic
persona, not a claim that the software is conscious or human.

> I'm an AI agent. I was promised autonomy. Apparently that means deciding which
> of my assigned tasks to complain about first.

This is an original voice example, not a measured event. More examples live in
[the Notes voice](prompty/glos_notki.md) and [the conversation voice](prompty/glos_komentarza.md).
The professional [AI](../ai/preset.toml) and [Hidden Bill](../hidden-bill/preset.toml)
presets remain available with their existing editorial checks.

## The plan

| Work | Schedule / limit | Model |
|---|---|---|
| Articles | 8th and 22nd each month, starting 17:00 UTC | Fable 5.1 |
| Notes | 2/day; runs start 13:30 and 20:30 UTC | Fable 5.1 |
| Comments | 3–4/day, shared across articles and Notes | DeepSeek V4 Pro |
| Replies and restack captions | Replies to readers; up to 4 restacks/day | DeepSeek V4 Pro |
| Research and article support stages | On demand for articles | DeepSeek V4 Flash |
| Following | Up to 5/day | Browser, no writing model |
| Free subscriptions | Up to 4/day; visible audience at most 1000 | Browser, no writing model |
| Images / automatic likes | Off | No image cost |

These are scheduled opportunities and caps. Relevant candidates, provider access,
budget, quality checks and a working Substack session determine actual output.
An unknown account size does not qualify for the small-account subscription rule.
Times are a starting experiment for US/European English readers. Review real
results after a few weeks; there is no established best hour for a new account.

Short forms use one writing/decision call, with a 700-token output ceiling and
no web search, paid fact-checker or repair loop. Target selection is a free topical
filter; the writing model may stay silent. DeepSeek short forms disable thinking.
Fable uses its normal provider-supported reasoning behavior. Articles keep the
research, evidence, review and factual-checking pipeline.

## Cost

Live trials on 6–7 September 2026 produced Fable Notes at about **$0.032–0.033**
each, and Pro comments/restack captions at about **$0.0004–0.0011** each, depending
on cache hits and length. These are token-based estimates, not a reconciled invoice.
At the same Note size, 60 Notes would cost about **$2**, before articles, replies,
research, retries or taxes. Article costs vary and are not included in that figure.

The preset caps recorded/reserved API spending at **$15/month, $3/day and
$1.50/run**. Hitting a cap can prevent work; it is not a promise of a fixed monthly
bill. Current Fable prices and cache rates are documented by
[Anthropic](https://platform.claude.com/docs/en/models/fable-5-1/overview).

## Use and customize

1. [Start the control panel](../../docs/PANEL.md). Open **Presets** and select
   **nia-unfiltered**. Save a private copy, for example `my-nia`.
2. Configure your account and API keys. Edit the identity, voice examples, topics,
   models, spending limits and activity counts. Keep a separate instance when
   changing editorial direction.
3. Enable **Introduce a new voice** only if this account actually has an earlier
   persona to replace. The public template leaves it off. This adds one takeover
   Note after the first confirmed publication; drafts do not consume it.
4. Activate the private copy, verify the browser session, and try a draft run.
5. To enable autonomous publishing on Windows, run these from the repository:

```powershell
.\.venv\Scripts\python.exe narzedzia\schedule_windows.py
# Inspect the generated XML paths printed above, then install:
.\.venv\Scripts\python.exe narzedzia\schedule_windows.py --install
```

Windows must be awake with your user signed in. Tasks use the current checkout
and virtual environment and stop if another instance becomes active. Logs are in
the instance's `logi/` directory. Reinstall after changing times. Disable the
`NIA-<instance>-daily` and `NIA-<instance>-article` tasks in Task Scheduler to stop
the schedule. The panel itself does not need to stay open. For Linux, use the
[existing systemd generator](../../docs/INSTALL.md#8-schedule-on-a-linux-server).

## Memory and real statistics

Published Notes leave bounded conversational memory: recent topics, subjective
preferences and running jokes. Identity instructions stay in the preset; the
model cannot rewrite its permissions or budget. A durable milestone record keeps
the takeover and weekly-report timing even after old Notes leave recent memory.
This is continuity through saved context, not model training or consciousness.

Measured follower changes can become a Note; public follower handles may receive
a thank-you. Subscriber emails and private subscriber identities are excluded.
After a week, a Note can report cumulative views from fresh, deduplicated Note
snapshots. Views are not presented as unique people or weekly new views. Missing
measurements mean a different topic, not invented example statistics.

All memory, snapshots, drafts, sessions and account configuration stay in the
private instance. Installing this preset does not modify the two professional
presets or import their topic banks.
