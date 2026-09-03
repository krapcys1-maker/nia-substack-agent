"""Bramka ciekawosci na pieciu PRAWDZIWYCH kartach.

Kontrdowod jest tu ostry i sprawdzalny wobec rzeczywistosci:
- 0016 (symbol na kosmetykach) — wlasciciel nazwal go nudnym i rozwleczonym.
  Bramka MUSI go odrzucic albo odloz.
- 0020 (kolor autobusu) — najlepszy tekst serii, zero uwag z bramek.
  Bramka MUSI go przepuscic.
Jesli bramka tego nie odwzorowuje, jest bezwartosciowa.
"""
import sys, json, pathlib
sys.path.insert(0, "agent-v2")
import config   # noqa: E402
config.DB_PATH = pathlib.Path("/tmp/warto.db")
import db, stages   # noqa: E402

conn = db.connect()
karty = conn.execute(
    "SELECT run_id, title, evidence FROM articles WHERE evidence IS NOT NULL ORDER BY run_id"
).fetchall()
print("kart do oceny: %d" % len(karty))
run_id = db.start_run(conn, stage="test-warto-pisac")
przed = conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)).fetchone()[0]
wyniki = []
try:
    for rid, tytul, ev in karty:
        karta = json.loads(ev)
        karta.pop("unused_evidence", None)     # bramka ocenia to, co dostal pisarz
        print()
        print("=" * 78)
        print("%04d  %s" % (rid, (tytul or "")[:64]))
        print("=" * 78)
        try:
            o = stages.warto_pisac(conn, run_id, karta)
        except Exception as e:
            print("  BLAD: %s: %s" % (type(e).__name__, str(e)[:130]))
            continue
        b = o.get("contradicted_belief") or {}
        print("  ZLAMANE PRZEKONANIE: %s" % ("TAK" if o["przekonanie"] else "NIE"))
        if b.get("the_belief"):
            print('     czytelnik wierzy: "%s"' % str(b["the_belief"])[:120])
        print("     dowod: %s" % str(b.get("evidence", ""))[:130])
        for k, etykieta in (("named_decider", "decydent"), ("felt_number", "liczba"),
                            ("second_domain", "druga dziedzina")):
            blok = o.get(k) or {}
            print("  %-16s %s   %s" % (etykieta, "TAK" if o["filary"][k] else "NIE ",
                                       str(blok.get("evidence", ""))[:96]))
        print("  --> WERDYKT: %s   (%s)" % (o["werdykt"], o["powod"]))
        print("      czego brakuje: %s" % str(o.get("what_would_rescue_it", ""))[:150])
        for u in o.get("uwagi_kodu", []):
            print("      [kod] %s" % u)
        wyniki.append((rid, tytul, o["werdykt"]))
finally:
    db.finish_run(conn, run_id, "DONE", "test-warto-pisac", "")

print()
print("=" * 78)
print("PODSUMOWANIE")
for rid, tytul, w in wyniki:
    print("  %04d  %-8s %s" % (rid, w, (tytul or "")[:56]))
print()
d = dict((rid, w) for rid, _, w in wyniki)
print("KONTRDOWOD:")
print("  0016 szampon (nudny wg wlasciciela) -> %s   %s" % (
    d.get(16), "OK — odrzucony" if d.get(16) in ("ODLOZ", "DOLOZ") else "PORAZKA: przepuszczony"))
print("  0020 autobus (najlepszy w serii)    -> %s   %s" % (
    d.get(20), "OK — przepuszczony" if d.get(20) == "PISZ" else "PORAZKA: odrzucony"))
koszt = conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)).fetchone()[0] - przed
print()
print("KOSZT oceny pieciu kart: $%.4f  (czyli $%.4f za karte)" % (koszt, koszt/max(1,len(wyniki))))
