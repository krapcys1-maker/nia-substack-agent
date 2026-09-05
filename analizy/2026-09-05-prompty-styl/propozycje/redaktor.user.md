Read the article as an editor. Find specific places where its reasoning or expression fails the assignment. Return findings, not a rewritten article.

Editorial job:
{editorial_brief_json}

Evidence:
{evidence_json}

Article:
{body}

Check these questions:

1. Does the article answer its actual question? Identify a missing explanatory link only when you can state what the reader cannot understand without it.
2. Does a factual clause exceed the supplied evidence in scope, time, attribution, causality or certainty? Check factual clauses inside opinions and analogies too. "I think" does not exempt the premise that follows.
3. Is a passage redundant? Additional support is useful when it establishes a disputed link, explains an unfamiliar process or separates alternatives. Flag repetition only when removing it loses none of those functions.
4. Does the opening make a promise the body does not deliver? Familiar context is allowed when it gets the reader to a precise unfamiliar question. Novelty in the first sentence is not compulsory.
5. Does the ending follow from the argument? A quiet implication or an unresolved limit is allowed. Do not demand drama, a personal reader moment, a comparison or a third act.
6. Do words, syntax or attribution obstruct understanding? Name the actual obstruction. A dash, long sentence, technical term or lack of "you" is not a defect by itself.

Report only consequential issues. Every finding must quote the affected text exactly, explain the loss to the reader, and state the smallest adequate change. If a needed fact is absent, identify the missing evidence; do not invent replacement prose.

Also identify up to two passages whose specificity, explanation or rhythm should be preserved. Do not suggest rewriting a sound article merely to make it different.

Return:
{{"findings":[{{"quote":"...","kind":"unsupported_clause|missing_link|redundancy|opening_promise|ending|clarity","reader_cost":"...","change":"...","evidence_ids":[]}}],"preserve":[{{"quote":"...","reason":"..."}}]}}
