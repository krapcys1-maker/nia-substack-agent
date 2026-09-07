"""Generate repeated Notes through the installed persona; never publish them."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent-v2"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow paid model calls")
    parser.add_argument("--samples", type=int, default=3, choices=range(1, 7))
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
        for index in range(args.samples):
            notes = stages.notki_dnia(conn, run_id, ile=1, od=args.slot)
            candidate = next(iter(notes[0].get("candidates", [])), {}) if notes else {}
            print(json.dumps({"sample": index + 1,
                              "draft_id": candidate.get("draft_id"),
                              "request_sha256": candidate.get("request_sha256"),
                              "model": candidate.get("model"),
                              "text": candidate.get("text", ""),
                              "rubric": (notes[0].get("personality") or {}).get("rubryka") if notes else None},
                             ensure_ascii=False), flush=True)
        conn.execute("UPDATE runs SET finished_at=?, status='DONE' WHERE id=?", (db.now(), run_id))
        conn.commit()
        rows = conn.execute("SELECT count(*), sum(cost_usd), min(price_verified) FROM calls WHERE run_id=?", (run_id,)).fetchone()
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
