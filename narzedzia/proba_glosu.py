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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow paid model calls")
    parser.add_argument("--samples", type=int, default=3, choices=range(1, 11),
                        help="A hit rate needs ten; three cannot separate 5/10 from 8/10")
    parser.add_argument("--slot", type=int, default=0, help="Zero-based configured Note slot")
    args = parser.parse_args()
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
        for index in range(args.samples):
            notes = stages.notki_dnia(conn, run_id, ile=1, od=args.slot)
            candidate = next(iter(notes[0].get("candidates", [])), {}) if notes else {}
            scores.append(score(candidate.get("text", "")))
            hashes.add(candidate.get("request_sha256"))
            print(json.dumps({"sample": index + 1,
                              "score": scores[-1],
                              "draft_id": candidate.get("draft_id"),
                              "request_sha256": candidate.get("request_sha256"),
                              "model": candidate.get("model"),
                              "text": candidate.get("text", ""),
                              "rubric": (notes[0].get("personality") or {}).get("rubryka") if notes else None},
                             ensure_ascii=False), flush=True)
        conn.execute("UPDATE runs SET finished_at=?, status='DONE' WHERE id=?", (db.now(), run_id))
        conn.commit()
        rows = conn.execute("SELECT count(*), sum(cost_usd), min(price_verified) FROM calls WHERE run_id=?", (run_id,)).fetchone()
        summary = {k: sum(1 for s in scores if s[k]) for k in
                   ("addressed", "no_review", "strong_word", "length")}
        summary["complete"] = sum(1 for s in scores if s["addressed"]
                                  and s["no_review"] and s["length"])
        print(json.dumps({"of": len(scores), "same_input": len(hashes) == 1,
                          "scores": summary}, ensure_ascii=False), flush=True)
        if len(hashes) != 1:
            print(json.dumps({"warning": "inputs differed; the comparison is void"}),
                  flush=True)
        print(json.dumps({"run_id": run_id, "paid_calls": rows[0],
                          "recorded_cost_usd": rows[1] or 0,
                          "price_verified": bool(rows[2]), "published": 0}), flush=True)
    except BaseException:
        conn.execute("UPDATE runs SET finished_at=?, status='FAILED' WHERE id=?", (db.now(), run_id))
        conn.commit()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
