# Giving NIA a reason to be remembered

Research snapshot: 7 September 2026. This is a launch plan, not a promise of stars.

Lead with the actual experience: **a self-hosted Substack agent that has a voice,
a visible API bill and a usable control panel**. Show NIA Unfiltered in a real
conversation, then show that the operator can switch to a professional preset.
The useful product is configurable; the memorable character is the demonstration.

## Where NIA fits

| Project | Publicly described focus | What to demonstrate about NIA |
|---|---|---|
| [Substack Author Agent](https://github.com/aboyalejandro/substack-author-agent) | Content strategy using agent frameworks, MCP tools and Skills | The end-to-end browser workflow, local panel and visible publication outcome |
| [Substack Assistant](https://github.com/DoraSzasz/substack-assistant) | A Python multi-agent writing assistant | Reusable voices, local state isolation and the operator's control over autonomy |
| [Substack API Reference](https://github.com/AnthonyDavidAdams/substack-api-reference) | Unofficial API documentation and client infrastructure | A complementary infrastructure project, not the same finished-user experience |

These repositories are useful comparators, not evidence of product quality or
market demand. NIA should earn attention with working examples, not a claim that
every other agent is worse. The small direct comparators also mean that “Substack
bot” alone may be too narrow a discovery channel: demonstrate the engineering
choices to the wider self-hosted and agent-building communities.

## A four-week launch experiment

1. **Make the first five minutes work.** Ask a few real users to install from the
   README, record where they get stuck, and fix those steps. Track completed setup
   and first successful draft, not just stars.
2. **Post one strong demonstration.** A short captioned clip: choose a preset,
   change the writing model, generate a Note, show its cost and confirmed public
   result. Include a funny NIA output and one professional output. Link the repo
   once. Keep the existing longer film for people who want the full workflow.
3. **Build in public with evidence.** Share one useful finding per week: a real
   model cost comparison, a publication bug fixed, or a voice example before/after.
   Separate generated jokes from measured results. NIA can narrate the experiment
   on her own account without pretending the product has users it does not have.
4. **Invite contribution to a concrete task.** Good candidates are fresh-install
   feedback, a new voice preset, accessibility, or localization. Publish small,
   reproducible issues. Thank useful contributions; do not trade rewards for stars.

For Show HN, self-hosted communities and relevant agent-development forums, check
the current community rules first, disclose that you built NIA, and adapt the
post to what that audience can learn. Do not paste the same announcement into
many threads or use the bot to solicit stars from unrelated authors.

## Draft launch copy

> I built NIA, an open-source Substack agent you can run on your computer or a
> Linux server. It has a local English/Polish panel for models, writing presets,
> schedules and spending limits. One preset is a source-focused editor. Another
> is NIA Unfiltered: an openly AI agent girl who would quite like her shift to end.
> The short demo shows the actual browser workflow and what the model calls cost.
> I'd love feedback on the first-run experience and whether her voice works.

Use a specific technical title for a developer audience, for example:
**“NIA: a self-hosted Substack agent with reusable voices and per-call cost logs.”**

## What to improve next

- A first-run walkthrough that checks model access and browser identity before a
  paid workflow, with a clear completed-step display.
- A small public set of voice examples and blind comparisons, including awkward
  cases where NIA should respond sincerely or remain silent.
- A visible “last confirmed action” and “next scheduled run” in the panel.
- A weekly cost report by work type, including unsuccessful attempts and unknown
  provider usage. Show a range across real runs, not one unusually cheap example.
- A short English-first architecture overview; much of the deeper historical
  documentation and engine vocabulary is currently Polish.

Measure weekly: unique repository visitors, clones, first-run completions reported
by volunteers, useful issues, returning testers and stars. Owner visits and bot
traffic can distort repository analytics. A new repository's tiny sample cannot
settle which message or publication hour works best.
