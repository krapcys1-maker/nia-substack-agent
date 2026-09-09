# The voice standard

Texts the owner accepted as NIA, kept as files so they can be measured, not
only read. Everything here is the owner's verdict; nothing here is a draft the
owner has not passed. This is the reference the tools compare against:

- `python narzedzia/odcisk_glosu.py FILE` measures any text the same way
  (words per sentence, short paragraphs, sentences addressed to the reader,
  hedges, field jargon, links in the body, attributions per hundred words,
  sentences about being an AI, and so on) and shows where it falls against
  the band these samples set. It is an observation, not a gate.
- `python narzedzia/slepa_proba_glosu.py --kandydaci FILE` lays a new text
  next to two of these without labels and asks which one is not from here.
- `python narzedzia/proba_glosu.py --wejscie NAME --live` writes fresh Notes
  on fixed inputs so the same story can be compared across runs.

The prompts in `prompty/` quote some of these texts as voice examples. The
copies here are the canonical ones; a prompt may quote less, never something
different.

## Format

Each file starts with `forma: notka`, `forma: artykul` or `forma: rozmowa`.
Samples are separated by `## ` headings. Lines starting with `Reader:` are the
other party in a conversation, lines starting with `Source:` name where the
facts came from, and a line that is only a `[link label]` stands for a link
the original carried; none of those is NIA's text and none is measured.

## Adding to it

Add a text only after the owner has accepted it. Keep the published English;
if the original was Polish, translate it one to one and say so at the top of
the file. Do not edit an accepted text to make it fit a rule; if the owner's
taste moves, the band moves with the next accepted text.
