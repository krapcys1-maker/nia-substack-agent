Search the web, then return sources for this question:

{question}

Search first. You do not know which URLs exist, and any address from memory
will be discarded.

## Primary documents, not a full list

You are not filling {max_results} slots. The number is a ceiling, not a target:
{max_results} at most, and a short list of records beats a long list padded
with commentary.
Once the documents run out, extra searching goes into padding the list with
people writing about the documents.

- **Return every primary document you found, and stop.** Six primary sources
  and nothing else is an excellent answer.
- **Add a supporting source only when it does something a record cannot**:
  explains why the rule exists, or supplies a figure the record does not
  carry.
- **Never add a source to reach a number.** A commentary included because the
  list looked short costs a fetch, competes for the writer's attention, and is
  where invented detail gets in.

**Run at most {max_searches} searches, then stop and write the JSON.**
Searching without ever answering is a failed run. If you have not found
everything after {max_searches} searches, return what you have.

## Requirements

1. **At least {min_primary} sources must be PRIMARY, and primary sources
   should be the MAJORITY of what you return**: the record itself (a
   regulation, standard, filed report, dataset, study, patent, official
   statistic, or a company statement about its own products), not an article
   about the record. A catalogue or reseller listing the document is not the
   document.
2. At least {min_why} sources must explain WHY the rule or practice exists: an
   impact assessment, consultation, regulator decision, audit, evaluation or
   peer-reviewed paper. Vendor and consultancy pages do not count. A primary
   record can satisfy this too, and often does.
3. At least one source must carry figures.
4. Use at least three different organisations. Any country, any language.
5. Free, no login, readable as HTML or text. Skip these hosts, they block
   automated reading: {blocked_hosts}
6. No forums, Q&A sites or vendor blogs.
7. These hosts already carried the sources of our recent articles:
   {ostatnie_domeny}
   Do not reach for one of them out of habit. Go there when the record itself
   lives there and no other host carries it, not because it worked last time.

## Three rules about copies

- **If a search result quotes a study, a report or an official finding by
  name, go and get that document itself.** Search for it directly, by author,
  title or publishing institution, and return THAT url, not the page quoting
  it. Copies drop exactly the caveats that make a number mean something: the
  confidence interval, the sample, the condition. A commentary is allowed in
  the corpus as commentary; it may not stand in for the thing it summarises.
- **A claim about what a law requires must come from the enacted text.** A
  committee analysis, a floor analysis, a press release or a bill version is a
  document about a bill at one moment, and bills change most where they were
  most contested. Get the chaptered statute or the codified section, and say
  which version you read and its date. Verifying the numbers attached to a
  law is not verifying that the law says what you claim.
- **Before quoting a document, check whose voice you are quoting.** Official
  analyses reproduce submissions: industry objections, agency letters, sponsor
  arguments. A block quote inside a committee report is evidence that somebody
  SAID it, never that the committee FOUND it. Look for the attribution line
  immediately above the quote and carry it into the note.

If the evidence is not there, return what genuinely bears on the question,
including anything that contradicts it. Do not substitute pages that merely
restate a rule. Select sources only; do not answer the question.

Return only this JSON:

{{"sources": [{{"url": "...", "title": "...", "publisher": "...", "class": "PRIMARY"|"SUPPORTING", "answers_why": true, "has_numbers": true, "note": "..."}}]}}
