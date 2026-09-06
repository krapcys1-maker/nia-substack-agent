Check every numbered segment against the evidence card. The numbers are stable
identifiers, not part of the article. Return one decision per identifier.

FACT asserts a checkable event, quantity, rule, practice, statement or finding.
INFERENCE expresses an interpretation or opinion. PROSE makes no checkable claim.
Check the factual premises inside an inference too: "I think the company removed
the right to resell" still asserts that a right was removed. A hedge does not
make an unsupported premise acceptable. Free opinion and analogy are welcome
when they introduce no unestablished factual premises.

Evidence of a rule does not establish how people usually behave. Evidence of an
effect does not establish a motive. Preserve scope, jurisdiction, date and the
conditions of numerical comparisons. Style examples are never factual evidence.
The card's parallel_mechanisms are research leads, not verified facts. A factual
comparison with another industry needs its own source and supporting excerpt;
a plausible mechanism written into that field alone does not establish it.

Return only JSON:
{{"sentences":[{{"index":1,"class":"FACT","supported":true,"why":""}}],"summary":"one sentence"}}

Include every identifier exactly once. Use supported=false for an unsupported
fact or factual premise, and explain only that problem in at most 25 words.
Do not copy the article or repeat failures in a second list. Do not rewrite it.

Evidence card:
{card_json}

Numbered article:
{body}
