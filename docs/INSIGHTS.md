# Results, costs and research decisions

The **Results & research** tab reads the active instance's existing files and
SQLite ledger. Select 7 or 30 days, then refresh. It works while a workflow runs
and does not call a model, scrape Substack or publish anything. Switch the panel
between English and Polish using the language selector.

For a server or a JSON export, run from the repository root:

```bash
python agent-v2/insights.py --data-dir agent-v2/instancje/my-publication --days 7
```

Use your actual instance directory. The command opens an existing database in
read-only mode and does not create one when it is missing. Reports can contain
private publication metadata and source excerpts; review them before sharing.

## Read the numbers

| Field | Meaning |
|---|---|
| Recorded API estimate | Recorded costs of non-test attempts within the period, including failed attempts. This is not provider billing reconciliation. |
| Unresolved reservations | Pending or unknown usage still carrying a cost reservation. It is shown separately, not treated as a completed charge or a free request. |
| Test costs | Calls attached to runs explicitly marked `test`, excluded from the production cost ratio. Historical unmarked calls cannot be reliably reclassified. |
| Published | Successful, non-skipped entries in the publication journal during the period, deduplicated by confirmed ID when available. Generated drafts do not count. |
| Period cost / publication | Recorded costs for an activity divided by confirmed publications of that activity in the same period. Shared costs remain separate. An unresolved attempt suppresses the ratio. It is not a matched per-post cost. |
| 24/48-hour views | A measurement at the horizon or up to two hours before it, or a dated primary graph that reaches the horizon. A first reading after 48 hours cannot reconstruct the 24-hour result by itself. |
| Measured at 24h | Coverage: the number of publications with a comparable measurement divided by all confirmed publications. The mean uses only that measured subset. |

A dash means unavailable, including immature posts and absent reach cards.
A measured zero remains zero. Older records without sufficient timing data
cannot be backfilled by guessing. Existing collection schedules are unchanged;
missing measurements do not trigger extra scraping. Concurrent reads may omit
the newest in-flight entry until the next refresh.

## Follow topic choices

- **Note choices** show the persona writer's saved topic, selected source URLs
  and draft status. These are not proof of publication.
- **Latest feed selection and exclusions** records which candidates were offered
  to the writer and which were too old, already used, outside the ranked limit
  or rejected for unsafe source instructions. An offered topic is not necessarily
  the topic the writer eventually chooses.
- **Article selection history** records bank candidates, topic overlap and the
  decision whether a subject supports an article. It shows actual past choices;
  the current bank alone cannot guarantee which topic a future run will select.
- **Article evidence gaps** keeps the current question, unresolved items and up
  to 12 retrieved source excerpts. During an already-required second search,
  the researcher gets missing source counts, failed URLs and at most six short
  excerpts. This changes the existing retry, adds no model call and preserves
  the article question. The final evidence card updates the saved gaps. Gaps do
  not trigger a new background job or become confirmed claims.

Operational traces start with the version that introduced them. They live in
`editorial-decisions.jsonl` and `research-tasks/` inside the instance, separate
from persona memory and reusable presets. The report shows bounded recent lists;
the idea-bank and feed-cache sections are current snapshots, not historical
reconstructions of the selected period.

## Avoid repeating work

Confirmed comment/reply targets in the journal are filtered before writer
selection, including subsequent batches. Failed attempts and new reply parents
remain eligible. The publisher still checks live state before sending; this
filter cannot infer interactions absent from the local journal.

Each RSS/Atom URL has its own disk cache inside the active instance. Valid XML
is fresh for 30 minutes and can be reused during a network outage for at most
24 hours. Existing entry-date filters still apply. A failed request starts a
five-minute pause, doubling up to six hours, and honors a longer `Retry-After`.
Reading a backup does not reset the failure count or refresh its age. A valid
network response resets failures; another feed URL or instance cannot reuse
the old URL's state. These cached reads require no LLM call.

This release does not change writing prompts, personality assets, model choices,
publishing quotas or the scheduled workflow frequency. The report is diagnostic;
it does not automatically optimize future topics from small engagement samples.
