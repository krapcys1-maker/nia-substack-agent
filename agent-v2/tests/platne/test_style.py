"""Trzy style okladki na TYM SAMYM przedmiocie. Rozni sie wylacznie traktowanie.

Przedmiot: tylna sciana szkolnego autobusu w zoltym lakierze — z 0020
„The Fossil of a Vote", najlepszego tekstu serii, ktory grafiki jeszcze nie ma.
"""
import sys, pathlib
sys.path.insert(0, "agent-v2")
import config, db, llm   # noqa: E402

PRZEDMIOT = ("A single flat rectangular steel panel painted in the standardised "
             "school-bus yellow, photographed as a specimen.")

STYLE = {
"A-obecny": """Photographed as a single isolated specimen on a plain warm off-white paper
background. Flat, even, diffuse studio light with one soft shadow falling short
and to the right. Slightly elevated three-quarter angle. Muted restrained
palette — paper, graphite, faded ochre — with at most one quiet accent colour
drawn from the object itself. Sharp focus edge to edge, fine surface texture
visible, no gloss, no dramatic highlights. Generous empty space around the
object. Calm, forensic, editorial. Absolutely no text, no lettering, no
numbers, no logos, no watermarks, no people, no hands.""",

"B-glebsze-tlo": """Photographed as a single isolated specimen resting on a deep putty-grey paper
background, clearly darker than the object so the silhouette separates cleanly
even at thumbnail size. The object fills roughly two thirds of the frame. Flat,
even, diffuse studio light with one soft shadow falling short and to the right.
Slightly elevated three-quarter angle. Restrained palette — grey ground,
graphite, and the object's own colour allowed to stay saturated. Sharp focus
edge to edge, fine surface texture visible, no gloss, no dramatic highlights.
Calm, forensic, editorial. Absolutely no text, no lettering, no numbers, no
logos, no watermarks, no people, no hands.""",

"C-ciemne-tlo": """Photographed as a single isolated specimen on a deep desaturated ink-blue
background, almost black at the corners. One low raking light from the left
rakes across the surface so texture and edge-wear read clearly; a long soft
shadow falls to the right. The object fills roughly two thirds of the frame and
is the only bright thing in it. Palette: near-black ground, cool shadow, and the
object's own colour kept fully saturated. Sharp focus edge to edge, no gloss,
no lens flare. Calm, forensic, editorial — a specimen in an evidence room.
Absolutely no text, no lettering, no numbers, no logos, no watermarks, no
people, no hands.""",
}

conn = db.connect()
run_id = db.start_run(conn, stage="test-styl-grafik")
katalog = pathlib.Path("/tmp/style"); katalog.mkdir(exist_ok=True)
przed = conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)).fetchone()[0]
try:
    for nazwa, styl in STYLE.items():
        print("\n>> %s" % nazwa, flush=True)
        try:
            dane = llm.obraz(PRZEDMIOT + " " + " ".join(styl.split()),
                             conn=conn, run_id=run_id)
            p = katalog / ("%s.png" % nazwa)
            p.write_bytes(dane)
            print("   zapisano %s (%.1f KB)" % (p, len(dane)/1024), flush=True)
        except Exception as e:
            print("   BLAD: %s" % e, flush=True)
finally:
    db.finish_run(conn, run_id, "DONE", "test-styl-grafik", "")
koszt = conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)).fetchone()[0] - przed
print("\nKOSZT: $%.4f" % koszt)
