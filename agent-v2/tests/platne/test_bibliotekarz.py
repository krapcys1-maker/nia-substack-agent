"""Bibliotekarz na prawdziwym banku 134 fragmentow z piecu artykulow."""
import sys, json, sqlite3, shutil, pathlib
sys.path.insert(0, "agent-v2")
import config, db, stages   # noqa: E402

ZASIEW = config.DATA_DIR / "zasiew-produkcji.db"
if not config.DB_PATH.exists() or config.DB_PATH.stat().st_size < 50000:
    shutil.copy2(ZASIEW, config.DB_PATH)
    print("baze testowa zasiano kopia produkcji (tylko material, zero publikacji)")

conn = db.connect()
bank = stages.bank_fragmentow(conn)
print("bank: %d fragmentow, %d znakow, ~%.1f tys. tokenow" % (
    len(bank), sum(len(f["text"]) for f in bank),
    sum(len(f["text"]) for f in bank)/3500))
print("zrodla w banku: %s" % ", ".join(sorted({f["publisher"] for f in bank})[:8]))
print()

run_id = db.start_run(conn, stage="test-bibliotekarz")
przed = conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM calls").fetchone()[0]
try:
    w = stages.bibliotekarz(conn, run_id, bank)
finally:
    db.finish_run(conn, run_id, "DONE", "test-bibliotekarz", "")
koszt = conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM calls").fetchone()[0] - przed

print("=" * 78)
print("PRZYJETE GRUPY (>=2 fragmenty z >=2 ROZNYCH dziedzin): %d" % len(w["groups"]))
print("=" * 78)
po_id = {f["id"]: f for f in bank}
for i, g in enumerate(w["groups"], 1):
    print()
    print("%d. MECHANIZM: %s" % (i, g.get("mechanism", "")))
    print("   dlaczego podrozuje: %s" % g.get("why_it_travels", ""))
    print("   dziedziny: %s" % ", ".join(g.get("dziedziny", [])))
    for m in g["members"]:
        f = po_id[m["id"]]
        print("     - [%s] %s" % (m.get("domain", ""), f["publisher"]))
        print("       rola: %s" % m.get("role", ""))
        print("       \"%s...\"" % f["text"][:110].replace("\n", " "))
    if g.get("missing"):
        print("   czego brakuje: %s" % g["missing"])

print()
print("ODRZUCONE PRZEZ KOD: %d" % len(w.get("odrzucone_grupy", [])))
for g in w.get("odrzucone_grupy", []):
    print("   - %s  [%s]" % (g.get("mechanism", "")[:70], g.get("powod_odrzucenia", "")))
print()
print("samotnych fragmentow: %d z %d" % (len(w.get("loners", [])), len(bank)))
print("uwaga o banku: %s" % w.get("note", ""))
print()
print("KOSZT: $%.4f" % koszt)
