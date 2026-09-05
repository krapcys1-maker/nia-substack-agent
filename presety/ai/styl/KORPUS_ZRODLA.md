# Style corpus of the `ai` cartridge: sources and licences

(PL) Korpus stylu tego kartridza sklada sie z akapitow tekstow w domenie publicznej albo na
licencjach pozwalajacych na kopiowanie z podaniem zrodla. Nic tu nie pochodzi z zadnego
dawnego konta ani z cudzej publicystyki bez licencji. Ten plik to atrybucja wymagana przez
te licencje; `korpus.txt` obok zawiera same akapity, oddzielone pusta linia.

`korpus.txt` is a set of paragraphs used only as **examples of rhetorical moves** for the
article writer (see `style.py`: at most five short paragraphs reach a prompt, chosen by
`przypiecia.json`). Every paragraph is copied from a source that is either in the public
domain or published under a licence that permits copying with attribution. Paragraph numbers
below are zero-based indexes of the blank-line-separated blocks in `korpus.txt`, the same
numbers `narzedzia/przypnij_styl.py --pokaz` prints. Fetched on 2026-09-06.

| Paragraphs | Source | Licence |
|---|---|---|
| 0, 1, 2, 3, 4, 5, 6 | Epoch AI, Gradient Updates: “An update on AI’s most important number” (2026) — https://epoch.ai/gradient-updates/an-update-on-ais-most-important-number | CC BY 4.0 |
| 7, 8, 9, 10, 11, 12, 13 | Epoch AI, Gradient Updates: “Will financing bottleneck AI compute? An Anthropic case study” (2026) — https://epoch.ai/gradient-updates/will-financing-bottleneck-ai-compute | CC BY 4.0 |
| 14, 15, 16, 17, 18 | Epoch AI, Gradient Updates: “9 big questions benchmarks can help answer” (2026) — https://epoch.ai/gradient-updates/9-big-questions-benchmarks-can-help-answer | CC BY 4.0 |
| 19, 20, 21, 22, 23, 24, 25, 26, 27 | Max Roser, “AI timelines: What do experts in AI expect for the future?”, Our World in Data (2022) — https://ourworldindata.org/ai-timelines | CC BY 4.0 |
| 28, 29 | Max Roser, “AI is transforming our world — it is on all of us to make sure that it goes well”, Our World in Data (2022) — https://ourworldindata.org/ai-impact | CC BY 4.0 |
| 30, 31, 32 | Max Roser, “The brief history of AI: the world has changed fast — what might be next?”, Our World in Data (2022) — https://ourworldindata.org/brief-history-of-ai | CC BY 4.0 |
| 33, 34, 35, 36, 37 | Michael Atleson, “Keep your AI claims in check”, U.S. Federal Trade Commission Business Blog (27 Feb 2023) — https://www.ftc.gov/business-guidance/blog/2023/02/keep-your-ai-claims-check | public domain (U.S. government work) |
| 38 | Michael Atleson, “The Luring Test: AI and the engineering of consumer trust”, U.S. Federal Trade Commission Business Blog (1 May 2023) — https://www.ftc.gov/business-guidance/blog/2023/05/luring-test-ai-engineering-consumer-trust | public domain (U.S. government work) |
| 39, 40, 41 | Cory Breaux and Emin Dinlersoz, “How Many U.S. Businesses Use AI?”, U.S. Census Bureau, America Counts (28 Nov 2023) — https://www.census.gov/library/stories/2023/11/businesses-use-ai.html | public domain (U.S. government work) |
| 42, 43, 44, 45, 46 | NIST, “NIST Identifies Types of Cyberattacks That Manipulate Behavior of AI Systems” (4 Jan 2024) — https://www.nist.gov/news-events/news/2024/01/nist-identifies-types-cyberattacks-manipulate-behavior-ai-systems | public domain (U.S. government work) |
| 47 | NIST, “There’s More to AI Bias Than Biased Data, NIST Report Highlights” (16 Mar 2022) — https://www.nist.gov/news-events/news/2022/03/theres-more-ai-bias-biased-data-nist-report-highlights | public domain (U.S. government work) |
| 48, 49, 50, 51, 52, 53, 54, 55, 56 | Mata v. Avianca, Inc., No. 22-cv-1461 (PKC), Opinion and Order on Sanctions (S.D.N.Y. 22 June 2023), Judge P. Kevin Castel — https://storage.courtlistener.com/recap/gov.uscourts.nysd.575368/gov.uscourts.nysd.575368.54.0.pdf | public domain (U.S. federal court opinion) |
| 57, 58, 59, 60 | U.S. Copyright Office, “Copyright and AI, Part 2: Copyrightability” (Jan 2025) — https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf | public domain (U.S. government work) |
| 61, 62, 63, 64, 65 | UK Competition and Markets Authority, “AI Foundation Models: Initial Report”, short version (18 Sep 2023) — https://www.gov.uk/government/publications/ai-foundation-models-initial-report | Open Government Licence v3.0 (Crown copyright) |
| 66, 67, 68, 69, 70 | Shivalika Singh et al., “The Leaderboard Illusion”, arXiv:2504.20879 (2025) — https://arxiv.org/abs/2504.20879 | CC BY-SA 4.0 |
| 71, 72, 73 | Ilia Shumailov et al., “AI models collapse when trained on recursively generated data”, Nature 631, 755–759 (2024) — https://www.nature.com/articles/s41586-024-07566-y | CC BY 4.0 |
| 74, 75, 76 | NTIA, “AI Accountability Policy Report”, Overview (Mar 2024) — https://www.ntia.gov/issues/artificial-intelligence/ai-accountability-policy-report/overview | public domain (U.S. government work) |
| 77, 78, 79 | NTIA, “AI Accountability Policy Report”, Recommendations (Mar 2024) — https://www.ntia.gov/issues/artificial-intelligence/ai-accountability-policy-report/recommendations | public domain (U.S. government work) |
| 80 | Laurie A. Harris, “AI: Overview, Recent Advances, and Considerations for the 118th Congress”, Congressional Research Service R47644 (4 Aug 2023) — https://crsreports.congress.gov/product/pdf/R/R47644 | public domain (U.S. government work) |

## What was changed in the copied text

Nothing in the wording. The only edits are mechanical: footnote markers glued to the end of a
sentence were removed; the numbering of findings in the court opinion and of paragraphs in the
CMA report was dropped; hyphens lost at PDF line breaks were restored (well-resourced,
real-world, use-specific, docket number 98-7926); one LaTeX arrow from the arXiv HTML was
rendered as a plain arrow; the Copyright Office paragraph that began mid-sentence after a page
break starts at its first full sentence. Where a source title spells out the field in two words,
the table writes it as “AI”; the linked page carries the exact title.

## Licence notes

- Works of the U.S. federal government (FTC, Census Bureau, NIST, NTIA, Copyright Office, CRS)
  and opinions of U.S. federal courts are not subject to copyright in the United States.
- Epoch AI, Our World in Data and the Nature article are published under Creative Commons
  Attribution 4.0 (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/
- “The Leaderboard Illusion” is published under CC BY-SA 4.0:
  https://creativecommons.org/licenses/by-sa/4.0/ — its paragraphs are quoted unchanged.
- The CMA report is Crown copyright under the Open Government Licence v3.0:
  https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

If you replace this corpus with your own texts, delete this file or rewrite it for your sources.
