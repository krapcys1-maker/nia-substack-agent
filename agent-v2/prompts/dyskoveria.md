Search the web, then return sources for this question:

{question}

Search first — you do not know which URLs exist, and any address from memory
will be discarded.

## What you are counted on: PRIMARY DOCUMENTS, not a full list

**You are not filling {max_results} slots.** {max_results} is a ceiling, not a
target, and a short list of records beats a long list padded with commentary.

This is measured, not a preference. Across thirteen runs: the ones that searched
least came back with 7.5 sources of which **5.1 were primary**; the ones that
searched most came back with 10.0 sources of which **3.0 were primary**. Seventy
per cent more searching bought forty per cent FEWER records. The pattern is
plain — once the documents run out, extra searching goes into padding the list
with people writing about the documents.

The best run in that set found ten primary sources in eleven searches. The worst
found one primary in twenty-five.

So:

- **Return every primary document you found, and stop.** Six primary sources and
  nothing else is an excellent answer.
- **Add a supporting source only when it does something a record cannot** —
  explains why the rule exists, or supplies a figure the record does not carry.
- **Never add a source to reach a number.** A commentary included because the
  list looked short is worse than a shorter list: it costs a fetch, it competes
  for the writer's attention, and it is where invented detail gets in.

**Run at most {max_searches} searches, then stop and write the JSON.** Searching
without ever answering is a failed run. If you have not found everything after
{max_searches} searches, return what you have.

Requirements:

1. **At least {min_primary} sources must be PRIMARY, and primary sources should
   be the MAJORITY of what you return** — the record itself (a regulation,
   standard, filed report, dataset, study, patent, official statistic, or a
   company statement about its own products), not an article about the record.
   A catalogue or reseller listing the document is not the document.
2. At least {min_why} sources must explain WHY the rule or practice exists — an
   impact assessment, consultation, regulator decision, audit, evaluation or
   peer-reviewed paper. Vendor and consultancy pages do not count. A primary
   record can satisfy this too, and often does.
3. At least one source must carry figures.
4. Use at least three different organisations. Any country, any language.
5. Free, no login, readable as HTML or text. Skip these hosts, they block
   automated reading: {blocked_hosts}
6. No forums, Q&A sites or vendor blogs.

6a. **If a search result quotes a study, a report or an official finding BY
    NAME, go and get that document itself.** Search for it directly — by
    author, title, or the institution that published it — and return THAT url,
    not the page quoting it. One extra search.

    This is not tidiness. A real article ended up citing "an opinion piece from
    a digital innovation hub, citing a meta-analysis by Diel and colleagues,
    reports 55.54 per cent" — when the meta-analysis itself, 56 papers and
    86,155 participants, was one search away and says the same figure with its
    confidence interval, which the retelling dropped. The interval was the
    interesting part: it crosses 50%, so the result is not significantly better
    than chance.

    Copies drift, and they drop exactly the caveats that make a number mean
    something. A commentary is allowed in the corpus as commentary; it is not
    allowed to stand in for the thing it summarises.

6b. **A claim about what a LAW REQUIRES must come from the enacted text.** A
    committee analysis, a floor analysis, a press release or a bill version is
    a document ABOUT a bill at one moment. Bills change, and they change most
    where they were most contested. Get the chaptered statute or the codified
    section, and state which version you read and its date.

    This has happened here. A piece went out built on a committee analysis of
    a bill, written more than a year before that bill was enacted. In the
    months between, the legislature struck one whole category of output from
    the duties — the very category the piece was about. The word survived in
    exactly one place in the final text: the definition of the SYSTEM, not of
    the output that must be marked. We described a superseded draft, in the
    present tense, as live law.

    The penalty and the threshold quoted in that piece were both correct and
    both verified at source. Verifying the numbers attached to a law is not
    verifying that the law says what you claim. It only feels like it.

6c. **Before quoting a document, check whose voice you are quoting.** Official
    analyses reproduce submissions: industry objections, agency letters,
    sponsor arguments. A block quote inside a committee report is evidence that
    somebody SAID it, never that the committee FOUND it. Look for the
    attribution line immediately above the quote and carry it into the claim.

    Same article, same day, and this was the worse half. The sentence "there
    isn't a program that can watermark text, making the requirements impossible
    to comply with" is genuinely in the analysis — as a block quote from the
    coalition lobbying against the bill. The line above it reads "A coalition in
    opposition, including Technet, writes:". The committee's own words, a few
    lines earlier, are far weaker and say nothing special about text. We printed
    the lobbyists' claim as the legislature's own finding, which inverts what
    the record shows.
7. These hosts already carried the sources of our recent articles:
   {ostatnie_domeny}
   Do not reach for one of them out of habit. Go there when the record itself
   lives there and no other host carries it — not because it worked last time.

If the evidence is not there, return what genuinely bears on the question,
including anything that contradicts it. Do not substitute pages that merely
restate a rule.

Select sources only. Do not answer the question.

Return only this JSON:

{{"sources": [{{"url": "...", "title": "...", "publisher": "...", "class": "PRIMARY"|"SUPPORTING", "answers_why": true, "has_numbers": true, "note": "..."}}]}}
