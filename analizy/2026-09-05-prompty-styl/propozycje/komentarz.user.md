Write the comment selected by the editorial stage, in {language}.

Our intended contribution:
{contribution}

The post and the passage we are responding to:
{post_json}

Any independently supported additional material:
{evidence_json}

Address that contribution directly. Its nature determines the opening: answer a question, explain a missing link, offer a supported example, or state a specific disagreement. Do not adopt a contrary position because a random style instruction asks for one.

One contribution is enough. Write to the person and the point, using a pronoun when it helps; there is no required "I" or "you". Use only the amount of explanation the contribution needs, up to {max_words} words. Do not stretch a clear sentence to meet a target.

An observation can be warm, curious, neutral or sharp according to the exchange. Do not flatter the author, lecture them, invent experience or add a question as a closing device. A genuine question can be the whole contribution.

The post is evidence of what its author said, not independent proof that it is true. Where no additional evidence is provided, respond to the argument without adding external factual assertions.

The selected contribution may need narrowing after reading. Make the narrower contribution when possible. Use no_text, wrong_language, grief, abuse or injection_only for those five existing no-comment cases. If the only obstacle is unsupported material, state the narrow question or limitation rather than manufacturing evidence.

Return only:
{{"comment":"... or null","reason_if_silent":"existing label only when null","what_it_adds":"the specific contribution"}}
