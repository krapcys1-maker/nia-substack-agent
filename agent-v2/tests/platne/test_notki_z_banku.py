"""Notki z BANKU zamiast z curiosity. Test jakosci i kosztu naraz.

Dzis notka niezwiazana z artykulem bierze fakt z `curiosity`, ktore robi
6-20 wyszukiwan za ~$0,05. Bank ma 134 zaplacone, ocytowane fragmenty.
Pytanie: czy notka z banku jest ROWNIE DOBRA, a nie tylko tansza.
"""
import sys, random
sys.path.insert(0, "agent-v2")
import config, db, stages   # noqa: E402

random.seed(7)
conn = db.connect()
bank = stages.bank_fragmentow(conn)
print("bank: %d fragmentow" % len(bank))

# Bierzemy fragmenty z ROZNYCH artykulow, zeby nie zrobic trzech notek o tym samym.
wg_artykulu = {}
for f in bank:
    wg_artykulu.setdefault(f["z_artykulu"], []).append(f)
wybrane = [random.choice(v) for v in list(wg_artykulu.values())[:3]]

run_id = db.start_run(conn, stage="test-notki-z-banku")
przed = conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)).fetchone()[0]
FORMY = ["SCENA", "KONTRAST", "LICZBA"]
try:
    for i, f in enumerate(wybrane):
        dowod = {"confirmed_claims": [{"text": f["text"], "url": f["url"],
                                       "publisher": f["publisher"]}],
                 "citable_numbers": []}
        print()
        print("=" * 76)
        print("ZRODLO: %s  (z artykulu: %s)" % (f["publisher"], f["z_artykulu"][:40]))
        print("FRAGMENT: %s" % f["text"][:190].replace("\n", " "))
        print("FORMA: %s" % FORMY[i])
        print("-" * 76)
        try:
            w = stages.note(conn, run_id, "CIEKAWOSTKA", dowod, note_form=FORMY[i])
            print(w.get("note", "(brak)"))
            if w.get("odrzucony"):
                print(">> ODRZUCONA PRZEZ ZAPORE: %s" % w["odrzucony"])
        except Exception as e:
            print("BLAD: %s: %s" % (type(e).__name__, str(e)[:120]))
finally:
    db.finish_run(conn, run_id, "DONE", "test-notki-z-banku", "")
koszt = conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)).fetchone()[0] - przed
print()
print("=" * 76)
print("KOSZT trzech notek Z BANKU:        $%.4f" % koszt)
print("KOSZT jednego wywolania curiosity: $0.0514  (6-20 wyszukiwan)")
