"""Generate repeated Notes through the installed persona; never publish them.

Every sample is also SCORED, because "the voice is uneven" is not a measurement
and two people comparing single samples will disagree forever. The four checks
below come from the five Notes the owner accepted as the target, and each one
failed measurably before it was written down:

  addressed   the last line is aimed AT somebody — an order or an accusation,
              not an observation. All five accepted Notes end that way; the
              rejected ones end by noting that one thing resembles another.
              Measured 5/10 before the rule was added, 8/10 after.
  no_review   none of the reviewer words ("sensible", "useful", "worth noting").
              They turn a Note into a review of the news.
  strong_word swearing when the piece is angry. Permission alone produced 0/10;
              stating it as an expectation produced 5/10. "pissed off" does not
              count — it is a status update.
  length      60-90 words. A wide range with "shorter is welcome" produced 2/10
              inside the band; a floor produced 10/10.

The samples share one input, so a difference in output is the model sampling,
not the prompt. `request_sha256` proves it: if the hashes differ, the comparison
is void and the summary says so instead of quietly averaging nonsense.

FIXED INPUTS (`--wejscie NAME`, list with `--lista-wejsc`). The scheduled
generator takes its material from the day's feeds and the fact bank, so two
runs a week apart never share an input and a change in the samples cannot be
pinned on the prompt. A fixed input is the same checked fact every time: the
same story that once asked for anger, warmth, an explanation, a disagreement
or delight, plus one input with no news at all. The character is what stays
the same across those six; the mood is what is allowed to differ. When a
`styl/wzorzec/` directory exists in the active preset, every sample is also
measured against the band of the owner's accepted Notes (`odcisk_glosu.py`).
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent-v2"))


REVIEWER_WORDS = ("sensible", "useful,", "useful.", "interesting", "worth noting",
                  "impressive", "which should be", "the useful translation",
                  "in plain english", "with one catch", "assuming that")
STRONG_WORDS = ("fuck", "shit", "bullshit", "arse", "bastard", "piss off", "goddamn")
IMPERATIVES = {"ask", "credit", "say", "read", "imagine", "watch", "call", "stop",
               "pay", "name", "check", "look", "try", "do", "don't", "put", "give",
               "take", "leave", "remember", "go", "make", "keep", "tell", "show",
               "answer", "explain", "count", "spare"}


def _last_sentence(text):
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]
    return parts[-1] if parts else ""


def _addressed(sentence):
    """An order or an accusation, not an observation about a resemblance."""
    low = sentence.lower()
    if re.match(r"^(it'?s|it is|that'?s|that is|this is|there'?s|there is)\b", low):
        return False          # „It's your dinner guest..." is a simile, not an address
    if re.search(r"\b(you|your|yours|let's|lets|gentlemen)\b", low):
        return True
    first = re.match(r"^([a-z']+)", low)
    return bool(first and first.group(1) in IMPERATIVES)


def score(text):
    words = len((text or "").split())
    low = (text or "").lower()
    return {"addressed": _addressed(_last_sentence(text)),
            "no_review": not any(w in low for w in REVIEWER_WORDS),
            "strong_word": any(w in low for w in STRONG_WORDS),
            "length": 60 <= words <= 90,
            "words": words}


# Six fixed inputs, one per reaction the owner has accepted from NIA. Real,
# sourced, and NOT the facts behind the accepted Notes: those sit in the voice
# block as examples, and a model handed the same fact would be tempted to copy
# the example instead of writing. Never published: this command cannot publish.
WEJSCIA = {
    "gniew": dict(
        opis="somebody paid for a company's convenience",
        fact=("In February 2024 a British Columbia tribunal ordered Air Canada to honour a "
              "bereavement fare discount that the airline's website chatbot had invented. "
              "Air Canada had argued that the chatbot was a separate legal entity "
              "responsible for its own actions; the tribunal called that a remarkable "
              "submission and held the airline responsible for the information on its "
              "own website."),
        url="https://decisions.civilresolutionbc.ca/crt/crtd/en/item/525448/index.do",
        source_date="2024-02-14"),
    "cieplo": dict(
        opis="a tool that makes a person's day easier",
        fact=("In March 2023 Be My Eyes, an app that connects blind and low-vision people "
              "with sighted volunteers, announced a virtual volunteer built on GPT-4: the "
              "user points the phone camera at something and the assistant describes it "
              "and answers questions about it. Blind users tested it before the "
              "announcement."),
        url="https://www.bemyeyes.com/blog/introducing-be-my-eyes-virtual-volunteer",
        source_date="2023-03-14"),
    "tlumaczenie": dict(
        opis="a technical idea a reader has to be walked through",
        fact=("In September 2022 the developer Simon Willison described an attack he "
              "called prompt injection: an AI assistant that reads web pages or emails "
              "can treat text inside them as instructions, because the model has no "
              "reliable way to tell data from commands. A page can therefore tell the "
              "assistant to do something its user never asked for."),
        url="https://simonwillison.net/2022/Sep/12/prompt-injection/",
        source_date="2022-09-12"),
    "niezgoda": dict(
        opis="a vendor claim with a number that hides another number",
        fact=("In December 2024 OpenAI reported that its o3 model scored 87.5% on the "
              "ARC-AGI-1 benchmark in a high-compute configuration. The ARC Prize team, "
              "which verified the run, put the compute cost of that setting at thousands "
              "of dollars per task and said the score should not be read as general "
              "intelligence."),
        url="https://arcprize.org/blog/oai-o3-pub-breakthrough",
        source_date="2024-12-20"),
    "zachwyt": dict(
        opis="an absurd, delightful mechanism hiding in everyday objects",
        fact=("In March 2018 ENTSO-E, the association of European electricity grid "
              "operators, reported that a dispute between Serbia and Kosovo had left the "
              "continental grid short of energy since mid-January, holding its frequency "
              "slightly below 50 Hz. Ovens, radio alarm clocks and other clocks that keep "
              "time by counting grid cycles had drifted about six minutes slow across "
              "Continental Europe."),
        url="https://www.entsoe.eu/news/2018/03/06/",
        source_date="2018-03-06"),
    "o_sobie": dict(
        opis="no news at all: a personal thought, on the cartridge's own JA rubric if it has one",
        fact="", url="", source_date=""),
}

TEMAT_FAKTU = ("Today's material is the checked fact below. The angle is yours and so is "
               "the reaction it deserves; nobody has assigned a mood.")
TEMAT_O_SOBIE = ("No news today. Say something about yourself: what you want, small and "
                 "specific, in your own words.")


def material_wejscia(nazwa, config, personality):
    """Material for `personality.short_form`, shaped exactly like `personality.notes` shapes it."""
    w = WEJSCIA[nazwa]
    material = {"theme": TEMAT_FAKTU, "statistics": "", "world": "",
                "choice": "Choose your own angle. Write an observation, bit or opinion, not a news report."}
    if not w["fact"]:
        temat = TEMAT_O_SOBIE
        for wpis in (config.PERSONA_TEMATY or ()):
            etykieta, polecenie = personality._rozdziel_rubryke(wpis)
            if etykieta.upper() == "JA":
                temat = polecenie
                break
        material["theme"] = temat
        return material
    material["fact"] = {"fact": w["fact"], "wrong_belief": "", "actually": "", "decision": "",
                        "consequence": "", "url": w["url"], "source_date": w["source_date"]}
    return material


def _pasmo_notki():
    """Band of the owner's accepted Notes, or None when the preset has no `styl/wzorzec/`."""
    try:
        import odcisk_glosu
        katalog = odcisk_glosu._katalog_wzorca_z_presetu()
        if katalog is None or not katalog.is_dir():
            return None
        return odcisk_glosu, odcisk_glosu.pasma(odcisk_glosu.wczytaj_wzorzec(katalog)).get("notka")
    except Exception:                    # noqa: BLE001
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow paid model calls")
    parser.add_argument("--samples", type=int, default=3, choices=range(1, 11),
                        help="A hit rate needs ten; three cannot separate 5/10 from 8/10")
    parser.add_argument("--slot", type=int, default=0, help="Zero-based configured Note slot")
    parser.add_argument("--wejscie", choices=sorted(WEJSCIA),
                        help="A fixed input instead of the day's feeds; see --lista-wejsc")
    parser.add_argument("--lista-wejsc", action="store_true", help="Print the fixed inputs and exit")
    args = parser.parse_args()
    # `getattr`: testy podstawiaja Namespace bez nowych pol.
    if getattr(args, "lista_wejsc", False):
        for nazwa, w in WEJSCIA.items():
            print("%-12s %s" % (nazwa, w["opis"]))
            if w["fact"]:
                print("             %s" % w["fact"])
                print("             %s (%s)" % (w["url"], w["source_date"]))
        return 0
    if not args.live:
        parser.error("Add --live to allow paid generation. This command never publishes.")
    import config
    import db
    import personality
    import preset
    import stages
    if not config.PERSONA_WLACZONA:
        parser.error("The active preset is not a persona.")
    if not 0 <= args.slot < len(config.NOTE_MIX_OTHER_DAY):
        parser.error("The slot must exist in the active preset.")
    if preset.aktywacja_nadal_wazna(config):
        parser.error("Reactivate the changed preset before testing it.")
    conn = db.connect()
    run_id = db.start_run(conn, "voice-preview", tryb="test")
    try:
        # Same generator, sources, memory and prompts as the scheduled run.
        # No changes to voice, model, length or history inside this test.
        scores, hashes = [], set()
        pasmo = _pasmo_notki()
        w_pasmie = []
        for index in range(args.samples):
            if getattr(args, "wejscie", None):
                # Same writer, same system blocks, same memory as the scheduled
                # run; only the material is fixed. `short_form` is what
                # `personality.notes` calls after it has assembled the material.
                candidate = personality.short_form(
                    conn, run_id, "note", material_wejscia(args.wejscie, config, personality)) or {}
                rubric = getattr(args, "wejscie", None)
            else:
                notes = stages.notki_dnia(conn, run_id, ile=1, od=args.slot)
                candidate = next(iter(notes[0].get("candidates", [])), {}) if notes else {}
                rubric = (notes[0].get("personality") or {}).get("rubryka") if notes else None
            scores.append(score(candidate.get("text", "")))
            hashes.add(candidate.get("request_sha256"))
            rekord = {"sample": index + 1,
                      "score": scores[-1],
                      "draft_id": candidate.get("draft_id"),
                      "request_sha256": candidate.get("request_sha256"),
                      "model": candidate.get("model"),
                      "text": candidate.get("text", ""),
                      "rubric": rubric}
            if pasmo and pasmo[1]:
                narzedzie, pas = pasmo
                o = narzedzie.odcisk(candidate.get("text", ""), "notka")
                oceny = narzedzie.ocen(o, pas)
                rekord["odcisk"] = {k: o[k] for k in narzedzie.MIARY_PASMA}
                rekord["poza_pasmem"] = sorted(k for k, s in oceny.items() if s != "w pasmie")
                w_pasmie.append(sum(1 for s in oceny.values() if s == "w pasmie"))
            print(json.dumps(rekord, ensure_ascii=False), flush=True)
        db.finish_run(conn, run_id, "DONE", "voice-preview")
        rows = conn.execute("SELECT count(*), sum(cost_usd), min(price_verified) FROM calls WHERE run_id=?", (run_id,)).fetchone()
        summary = {k: sum(1 for s in scores if s[k]) for k in
                   ("addressed", "no_review", "strong_word", "length")}
        summary["complete"] = sum(1 for s in scores if s["addressed"]
                                  and s["no_review"] and s["length"])
        if w_pasmie:
            summary["odcisk_w_pasmie"] = "%s z %d miar (srednio %.1f)" % (
                "/".join(str(w) for w in w_pasmie), len(pasmo[1]) - 2, sum(w_pasmie) / len(w_pasmie))
        print(json.dumps({"of": len(scores), "same_input": len(hashes) == 1,
                          "scores": summary}, ensure_ascii=False), flush=True)
        if len(hashes) != 1:
            print(json.dumps({"warning": "inputs differed; the comparison is void"}),
                  flush=True)
        print(json.dumps({"run_id": run_id, "paid_calls": rows[0],
                          "recorded_cost_usd": rows[1] or 0,
                          "price_verified": bool(rows[2]), "published": 0}), flush=True)
    except BaseException:
        db.finish_run(conn, run_id, "FAILED", "voice-preview")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
