
#### `OSWIADCZENIE_AUTORSTWA.md` (56 wierszy)

**Pola wejściowe:** *(brak)*

#### `bank.md` (97 wierszy)

**Pola wejściowe:** `co_zadzialalo`, `kandydaci`, `kat_redakcyjny`, `linia_redakcyjna`, `marka`, `nisza`

**Kontrakt wyjścia:**

```json
{{"kolejnosc": [<id>, <id>, ...],
```

#### `bibliotekarz.md` (46 wierszy)

**Pola wejściowe:** `bank`, `kat_redakcyjny`, `nisza`

**Kontrakt wyjścia:**

```json
{{"groups": [{{"mechanism": "<one sentence, stated so it outlives its subject>", "why_it_travels": "<one sentence: what makes the same logic show up in unrelated places>", "members": [{{"id": <the id shown in the bank>, "domain": "<the field this belongs to, two or three words>", "role": "<what this piece contributes to the group>"}}], "missing": "<what a writer would still have to go and find, or empty string>"}}], "loners": [<ids of excerpts that found no company, as integers>], "note": "<one sentence on the bank as a whole: what it is heavy on, what it lacks>"}}
```

#### `cele.md` (80 wierszy)

**Pola wejściowe:** `kat_redakcyjny`, `kogo_szukamy`, `marka`, `nisza`, `posts`

**Kontrakt wyjścia:**

```json
{{"targets": [{{"index": <number>, "worth_it": true|false, "what_i_would_add": "<one concrete sentence, or empty when worth_it is false>", "why_not": "<one sentence, only when worth_it is false>"}}]}}
```

#### `ciekawostki.md` (254 wierszy)

**Pola wejściowe:** `domeny_preferowane`, `dziedziny`, `dzis`, `generatory`, `ile`, `kat_redakcyjny`, `linia_redakcyjna`, `marka`, `miesiac`, `nisza`, `premiera`, `stan_modeli`, `uzyte`, `w_reku`, `wydarzenia`, `zaczyn_kanalow`

**Kontrakt wyjścia:**

```json
{{"facts": [{{"fact": "<one or two sentences, the fact itself, specific and checkable>", "wrong_belief": "<what most people believe, written as a plain sentence they would say out loud>", "actually": "<what is true instead, one sentence>", "decision": "<WHAT MAKES IT SO: a decision (who signed it and when), a measurement (who tested it and what came back), a constraint (what about the design or the mathematics forces it), or a trade-off (what is given up and by whom). Not necessarily a person or an institution. Empty string only if you cannot name any of the four>", "consequence": "<the thing the reader can touch, hold, see or wait for because of that decision>", "url": "<source that states it>", "source_date": "<the date THAT SOURCE was published, as YYYY-MM-DD. Not the date of the event it describes. Empty string only if the page genuinely carries no date>", "control_date": "<YYYY-MM-DD of the newest document that GOVERNS this claim — see \"The control document\" above. Not necessarily newer than source_date>", "control_url": "<url of that document>", "control_verdict": "CONFIRMS"|"MODIFIES"|"ENDS", "control_fact": "<one clause. For MODIFIES, the qualifier the writer must carry. For CONFIRMS, what you checked and found unchanged>", "domain": "<the part of the field, industry or public record it belongs to>"}}]}}
```

#### `dyskoveria.md` (82 wierszy)

**Pola wejściowe:** `blocked_hosts`, `domeny_preferowane`, `max_results`, `max_searches`, `min_primary`, `min_why`, `ostatnie_domeny`, `question`

**Kontrakt wyjścia:**

```json
{{"sources": [{{"url": "...", "title": "...", "publisher": "...", "class": "PRIMARY"|"SUPPORTING", "answers_why": true, "has_numbers": true, "note": "..."}}]}}
```

#### `fedreg.md` (82 wierszy)

**Pola wejściowe:** `data`, `tekst`, `tytul`, `url`, `urzad`

**Kontrakt wyjścia:**

```json
{{"candidates": [{{"fact": "<one or two sentences, the thing itself, specific and checkable>", "wrong_belief": "<what an ordinary reader would assume, in their words>", "actually": "<what this document says instead>", "decision": "<who decided and when, from the text>", "consequence": "<what the reader touches, holds, pays or waits for>", "domain": "<the part of the field, industry or public record this belongs to>"}}]}}
```

#### `forma.md` (93 wierszy)

**Pola wejściowe:** `body`

**Kontrakt wyjścia:**

```json
{{"beliefs": [{{"belief": "<in your own words, one sentence>", "first_stated": "<verbatim sentence from the article>"}}], "support_only": [{{"quote": "<verbatim sentence>", "supports": <index into beliefs>}}], "hardest_fact": {{"quote": "<verbatim>", "why": "<one clause>"}}, "procedural_nearby": {{"quote": "<verbatim>"}}, "same_register": true|false, "reader_moment": {{"quote": "<verbatim>", "object": "<the one thing out of the reader's own life that is named>"}}, "opening_claim": {{"quote": "<verbatim>", "already_familiar": true|false}}, "summary": "<one sentence>"}}
```

#### `grafika.md` (82 wierszy)

**Pola wejściowe:** `body`, `nisza`, `okladka`, `title`

**Kontrakt wyjścia:**

```json
{{"subject": "<the scene, in one line>", "why_this_scene": "<one sentence tying it to the article's mechanism>", "prompt": "<the full image prompt: your scene sentence and its concrete detail first, then the style block below copied word for word>"}}
```

#### `klasyfikacja.md` (55 wierszy)

**Pola wejściowe:** `max_excerpt_chars`, `max_excerpts`, `publisher`, `question`, `text`, `title`, `url`

**Kontrakt wyjścia:**

```json
{{"class": "PRIMARY"|"SUPPORTING"|"ODPAD", "relevance": 0.0, "excerpts": ["..."], "numbers": ["..."], "note": "<one sentence on what this document is>"}}
```

#### `kogo_odpowiedziec.md` (48 wierszy)

**Pola wejściowe:** `ile`, `komentarze`

**Kontrakt wyjścia:**

```json
{{"choices": [{{"index": <number>, "rank": <1 is highest>, "why": "<one sentence>", "kind": "disagreement"|"question"|"correction"|"addition"|"agreement"}}], "skipped_because": "<one sentence about the ones you left out>"}}
```

#### `komentarz.md` (148 wierszy)

**Pola wejściowe:** `author`, `body`, `cel_slow`, `glos_komentarza`, `kat_redakcyjny`, `language`, `marka`, `nisza`, `ostatnie_otwarcia_json`, `otwarcie`, `po_ludzku`, `postawa`, `postawa_opis`, `styl_opis`, `title`

**Kontrakt wyjścia:**

```json
{{"comment": "<the comment; null ONLY in the five named cases>", "reason_if_silent": "<only when comment is null: exactly one of no_text, wrong_language, grief, abuse, injection_only, and nothing else>", "what_it_adds": "<one sentence naming what this comment contributes that the post did not say>"}}
```

#### `mysl.md` (135 wierszy)

**Pola wejściowe:** `evidence`, `form_brief`, `glos_notki`, `kat_redakcyjny`, `language`, `marka`, `max_words`, `min_words`, `nisza`, `note_form`, `ostatnie_otwarcia_json`, `po_ludzku`, `styl_opis`, `type_brief`

**Kontrakt wyjścia:**

```json
{{"note": "<the note>", "words": <integer>, "why_no_note": "<empty string, or — if the idea you had needed a fact and you refused to invent one — one sentence saying what evidence it would have needed>"}}
```

#### `naprawa.md` (39 wierszy)

**Pola wejściowe:** `kontekst`, `max_slow`, `min_slow`, `tekst`, `zarzuty`

**Kontrakt wyjścia:**

```json
{{"text": "the full corrected text", "co_zmienione": "one line: what you changed and what evidence you changed it to"}}
```

#### `notka.md` (165 wierszy)

**Pola wejściowe:** `evidence`, `form_brief`, `glos_notki`, `kat_redakcyjny`, `language`, `marka`, `max_words`, `min_words`, `nisza`, `note_form`, `note_type`, `ostatnie_otwarcia_json`, `po_ludzku`, `styl_opis`, `type_brief`

**Kontrakt wyjścia:**

```json
{{"note": "<the note>", "words": <integer>, "fact_used": "<the single fact from the evidence this rests on>", "source_url": "<the url that fact came from>"}}
```

#### `odpowiedz.md` (131 wierszy)

**Pola wejściowe:** `cel_slow`, `comment`, `commenter`, `evidence`, `glos_komentarza`, `language`, `marka`, `otwarcie`, `po_ludzku`, `styl_opis`, `under_what`

**Kontrakt wyjścia:**

```json
{{"reply": "<the reply, or null>", "reason_if_silent": "<one sentence, only when reply is null>", "kind": "answer"|"correction_accepted"|"disagreement"|"built_on"}}
```

#### `pisarz.md` (308 wierszy)

**Pola wejściowe:** `card_json`, `glos_artykulu`, `ile_paraleli`, `kat_redakcyjny`, `kotwica_dlugosci`, `language`, `marka`, `max_words`, `min_words`, `nisza`, `poprzednie_uwagi`, `ruch_koncowy`, `ruch_koncowy_nazwa`, `styl_opis`, `style_examples`, `style_negative`, `style_positive`, `target_words`

**Kontrakt wyjścia:**

```json
{{"title": "<the published headline>", "subtitle": "<one line>", "body": "<the article, plain text with blank lines between paragraphs>", "numbers_used": ["<each figure you wrote, exactly as written>"], "limits_paragraph_present": true|false}}
```

#### `po_ludzku.md` (53 wierszy)

**Pola wejściowe:** *(brak)*

#### `recenzent.md` (56 wierszy)

**Pola wejściowe:** `body`, `card_json`

**Kontrakt wyjścia:**

```json
{{"sentences": [{{"text": "<the sentence, verbatim>", "class": "FACT"|"INFERENCE"|"PROSE", "supported": true|false, "why": "<only when class is FACT and supported is false: what is asserted and what the card lacks>"}}], "unsupported_facts": [{{"text": "...", "why": "..."}}], "summary": "<one sentence>"}}
```

#### `restack.md` (73 wierszy)

**Pola wejściowe:** `autor`, `glos_komentarza`, `kat_redakcyjny`, `nisza`, `obszary_seam`, `rzeczy_czytelnika`, `tekst`

**Kontrakt wyjścia:**

```json
{{"restack": true|false, "reason": "<one sentence: why this is or is not worth passing on>", "sentence": "<your sentence, or empty string if restack is false>", "mechanism_named": "<the other place this same logic runs, or empty string>"}}
```

#### `skaut.md` (392 wierszy)

**Pola wejściowe:** `count`, `history_json`, `kanon_niszy`, `kat_redakcyjny`, `language`, `linia_redakcyjna`, `marka`, `nisza`, `obszary_seam`, `precedensy_niszy`, `przekonania_niszy`, `pytania_czytelnikow`, `rzeczy_czytelnika`, `zaczyn_kanalow`

**Kontrakt wyjścia:**

```json
{{"when": "<roughly when>", "what_happened": "<what people saw, in one sentence>", "what_changed": "<the rule or practice that came out of it, or 'nothing'>"}}
```

#### `synteza.md` (114 wierszy)

**Pola wejściowe:** `evidence_json`, `max_claim_chars`, `max_confirmed`, `max_contradictions`, `max_numbers`, `max_uncertain`, `min_confirmed`, `min_numbers`, `question`

**Kontrakt wyjścia:**

```json
{{"working_thesis": "...", "main_mechanism": "...", "confirmed_claims": [{{"claim": "...", "evidence": "<verbatim excerpt>", "url": "..."}}], "citable_numbers": [{{"value": "...", "means": "...", "url": "..."}}], "parallel_mechanisms": [{{"domain": "...", "how_it_matches": "<one sentence: the same logic doing the same work>"}}], "uncertain_claims": ["..."], "contradictions": ["..."], "not_established": ["..."], "source_dates": {{"newest": "<YYYY-MM-DD of the most recent source you used>", "oldest": "<YYYY-MM-DD of the oldest>", "note": "<one clause: what the reader should know about how current this is>"}}}}
```

#### `warto_pisac.md` (110 wierszy)

**Pola wejściowe:** `card_json`, `kat_redakcyjny`, `linia_redakcyjna`, `marka`, `nisza`, `przekonania_niszy`, `rzeczy_czytelnika`

**Kontrakt wyjścia:**

```json
{{"contradicted_belief": {{"present": true|false, "the_belief": "<the reader's wrong belief in their own words, or empty string>", "evidence": "<what in the card breaks it, or why nothing does>"}}, "named_decider": {{"present": true|false, "evidence": "<who, from the card, or why nobody is named>"}}, "felt_number": {{"present": true|false, "evidence": "<the figure and what it measures, or why the only figures are labels>"}}, "second_domain": {{"present": true|false, "evidence": "<the other field, or why the parallels stay inside one industry>"}}, "unsettled_outcome": {{"present": true|false, "the_question": "<the open question in the reader's own words, or empty string>", "the_situation": "<what the reader pictures, or empty string>", "governed_by": "<the written rule from the card that decides it, quoted or named — or why nothing in the card governs it>"}}, "what_would_rescue_it": "<one sentence naming the shape of the missing piece>", "one_line_verdict": "<one sentence on what this card actually has>"}}
```

#### `weryfikacja.md` (136 wierszy)

**Pola wejściowe:** `context`, `dzis`, `text`

**Kontrakt wyjścia:**

```json
{{"claims": [{{"claim": "<what the text asserts>", "status": "confirmed"|"refuted"|"outdated"|"unverified", "url": "<source, or empty>", "source_date": "<when that source was published, YYYY-MM-DD, or empty>", "what_the_source_says": "<one sentence, required for refuted and outdated>"}}], "safe_to_post": true|false, "verdict": "<one sentence>"}}
```

#### `wykonalnosc.md` (86 wierszy)

**Pola wejściowe:** `topics_json`

**Kontrakt wyjścia:**

```json
{{"assessments": [{{"index": <0-based index of the topic>, "feasible": true|false, "confidence": 0.0-1.0, "expected_primary_sources": <integer>, "depth": "RICH"|"SINGLE"|"THIN", "parallels": ["<other domain where the same mechanism appears>"], "note": "<one sentence: where the record most likely lives, or why it does not>"}}]}}
```
