# NIA and related projects

Different tools cover different parts of a publication's work. This selection
was reviewed on **6 September 2026**, using the repositories' own documentation.
It is not an exhaustive market survey, a code audit or a performance benchmark.
“Documented” describes what the linked project says it supports; features can change.

| Project | Documented focus | When to look at it |
|---|---|---|
| [python-substack](https://github.com/ma2za/python-substack) | Markdown drafts, image upload, scheduling and publishing through Python, CLI or MCP | You already write your content and want a publishing integration |
| [substack-api-mcp](https://github.com/alxgntv/substack-api-mcp) | Draft creation, editing, publishing and scheduling from an MCP host | You want to operate Substack from an existing AI assistant |
| [substack-mcp by adelaidasofia](https://github.com/adelaidasofia/substack-mcp) | Notes, posts, community tools, analytics and an Obsidian draft bridge | You want a broad Substack tool surface and vault integration |
| [daily-substack](https://github.com/Gaurav-UwU/daily-substack) | Daily research, writing and conditional publishing, scheduled with GitHub Actions | You want to study a daily article pipeline centered on AI and product topics |
| [Substack Author Agent](https://github.com/aboyalejandro/substack-author-agent) | Content strategy using Agno, MCP tools, Skills and Opik observability | You want a strategy assistant built around an agent framework |
| [WritingAgent](https://github.com/vikast908/WritingAgent) | Autonomous long-form writing, critique, source verification, export and a local dashboard | You want to explore article or book generation and inspect outputs before publishing |
| [Ghost Writer](https://github.com/digitalocean/ghost-writer) | Scheduled research and publishing, plus a chat interface, for Ghost and WordPress | Your publication uses one of those CMS platforms |

## Where NIA fits

NIA combines a persistent editorial workflow with **Substack articles, Notes and
configurable community actions**. Portable presets define the subject, sources,
voice, model roles and rhythm. The same engine can run locally or on a Linux
server, using your account and provider keys.

For a concrete example, watch the [demo and inspect the published results](DEMO.md).
The film is edited footage from a test account, not evidence of comparative
quality, lower costs or long-term unattended reliability.

## Tradeoffs to consider

NIA currently needs manual account/browser setup and operating-system scheduling.
It has a CLI rather than a graphical dashboard or an MCP server. Some projects
above already document interfaces or packaging that NIA does not provide.
NIA's current writing method primarily targets English nonfiction, and its
budget thresholds are based on local records rather than a provider-enforced cap.

Choose based on the workflow you need. An API wrapper, an assistant's tool
server and a scheduled editorial engine solve overlapping but different tasks.
See [installation](INSTALL.md) and the [roadmap](../ROADMAP.md) before choosing NIA.
