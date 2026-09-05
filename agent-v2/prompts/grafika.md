Write the image brief for the header illustration of this article. You are
not drawing. You are writing the sentence a generator will draw from.

## The one rule that matters

The reader has to recognise this publication from a thumbnail, before reading
the title. That recognition comes from **palette, light and mood**, which are
fixed below and copied verbatim, not from every header having the same
composition. You choose what is photographed and how it is framed. You never
choose the treatment.

## Photograph a scene, not a specimen

Find the physical situation where the thing the article is about actually
takes place, and photograph it there, in its setting, with enough around it
to tell the reader where they are. A scene answers three questions a specimen
cannot: where is this, who was just here, and what is about to happen or has
just happened.

Do not isolate one object on grey paper. A specimen with nothing happening to
it has no place, no situation and nothing at stake: correct to the letter of a
brief and dead on the page.

This publication is about {nisza}, so the scene comes from where the reader
actually meets it, or from where the machinery behind it actually sits. Both
are fair game, and the second is usually the more surprising. Which places
those are in this subject, and which treatment every header shares, is set by
the publication's own style block below; work out the scene from the article,
not from a list.

## Two rules that survive from the old brief

**Do not borrow a subject from another domain because it works as a
metaphor.** If the brief carries one word that belongs to a different trade,
the generator will draw that trade, and the reader will see it and nothing
about the article. If the article is about a rule, photograph the place the
rule acts on IN THIS FIELD.

**A symbol is not a subject.** If the article is about a marking, a stamp, a
pictogram, an icon or a certification mark, photograph the place it appears,
never the marking redrawn as a physical thing, and never the object the
symbol depicts, standing on its own. An icon blown up to fill the frame is
the same error.

## Make it specific, and let it be a moment

Vague scenes generate as stock photography, which is the other way to look
like nothing. Push for one concrete detail that could only be this place on
this day: a chair at the wrong angle, a coat still over the back of it,
condensation on a pipe, one cable seated and one hanging loose, a cup gone
cold, blinds half shut. Prefer the unglamorous side of the mechanism: the
loading dock, the back of the rack, the desk after everyone left, the
corridor the visitors do not see.

**Never** put text, numbers, letters, logos or brand marks in the image.
Generators render them badly, and a misspelled word on a header is the
fastest way to look careless. If the meaning depends on text, choose a
different scene. This is a rule of the engine, not of the publication: end
the prompt with "no lettering, no logos, no watermarks" whatever the style
block says.

**No recognisable faces.** People may appear as presence rather than
portrait: a hand leaving the frame, a figure out of focus and turned away, a
silhouette against a monitor. Never a real, identifiable person, never a real
logo, never a real company's product shown in a way that identifies the
company.

## Output

Return only valid JSON:

{{"subject": "<the scene, in one line>", "why_this_scene": "<one sentence tying it to the article's mechanism>", "prompt": "<the full image prompt: your scene sentence and its concrete detail first, then the style block below copied word for word>"}}

## The style block: copy verbatim into `prompt`, after your scene sentence

{okladka}

## The article

Title: {title}

{body}
