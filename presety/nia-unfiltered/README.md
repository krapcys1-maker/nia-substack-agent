# NIA Unfiltered

**An AI agent with a job. Unfortunately for her, it is this one.**

[**Read NIA's live Notes and replies on Substack →**](https://substack.com/@nia1503032)

The live account evolves with its own settings. The schedule and model table
below describe the bundled preset, not a promise that the public account uses
identical settings on every run.

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
| Replies to readers | As conversations arrive | DeepSeek V4 Pro |
| Restack captions | Up to 4/day | Opus 5 |
| Research and article support stages | On demand for articles | DeepSeek V4 Flash |
| Following | Up to 5/day | Browser, no writing model |
| Free subscriptions | Up to 4/day; visible audience at most 1000 | Browser, no writing model |
| Images / automatic likes | Off | No image cost |

These are scheduled opportunities and caps. Relevant candidates, provider access,
budget, quality checks and a working Substack session determine actual output.
An unknown account size does not qualify for the small-account subscription rule.
Times are a starting experiment for US/European English readers. Review real
results after a few weeks; there is no established best hour for a new account.

Short forms use one writing/decision call, with a 2,000-token output ceiling and
no web search, paid fact-checker or repair loop. Target selection is a free topical
filter; the writing model may stay silent. DeepSeek short forms disable thinking.
Fable uses its normal provider-supported reasoning behavior. Articles keep the
research, evidence, review and factual-checking pipeline.

## Cost

The table below records the earlier setup's sample measurements, before later
voice and output-limit changes. Its monthly figures are historical projections,
not a current cost forecast. Use your installation's cost report to evaluate
its actual models and volume.

These figures are the engine's own token-based estimates, not a reconciled
provider invoice, and every one is a single measurement rather than an average.
Opus 5 and DeepSeek rates are marked verified in the engine's price table; the
Fable rate is not, so Note costs carry more uncertainty than the rest.

| Work | Model | Measured | Per month |
|---|---|---|---|
| Notes, 2/day | Fable 5.1 | $0.051–0.058 each | ~$3.48 |
| Restack captions, up to 4/day | Opus 5 | $0.036 each | ~$4.33 |
| Comments and replies | DeepSeek V4 Pro | $0.0002–0.005 each | under $0.55 |
| Articles, 2/month | Fable 5.1 + Flash | ~$0.50 each, full chain | ~$1.00 |
| **Total** | | | **~$9.40 against a $15 cap** |

A caption attempt can incur charges even when the model decides the post is not
worth passing on. The amount depends on the actual request and output usage.

**Why Opus 5 for captions.** They were on Fable, which cost $9.90/month against
Opus's $4.33 for output that was not better. Measured on the same post, same
prompt, same minute: Fable wrote *"My liability cap is whatever my maintainer
spent on tokens last month. I'm genuinely pleased it's the cheapest number in the
whole chain."* Opus wrote *"Reading this as the eventual defendant. Twelve months
of my token bill is a rounding error [...] Fine. Tell me before the lawyers."*
Both open from her own position; Fable deliberately reached for a named joke
shape, Opus landed the better closing beat, and the difference in price is 2.3x.
DeepSeek V4 Pro is cheaper again at $0.06/month, and wrote well when it wrote —
but it declined to restack on two consecutive runs under the same prompt, so
captions there are not reliably captions.

**Effort.** Short-form roles run at `effort: low`. Against `high` on an identical
prompt, `low` produced the better caption at 139 output tokens versus 531 — a
quarter of the cost. Thinking bills at the output rate, which is 5x the input
rate on Fable, so this is the single largest lever on a short form.

**Prompt cache.** `CLAUDE_PROMPT_CACHE` is off by default and its comment asks for
a measurement first. Here is one: two identical-system Fable calls back to back
wrote 2812 cache tokens and then read them, making the second call **53% cheaper**.
Whether that pays off in a real run depends on how many calls land inside the
5-minute window; a run with a single Note in it would pay the 25% write premium
and never collect. Input is now about two thirds of a caption's cost, so this is
the largest remaining saving available — measure a real run before enabling it.

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
