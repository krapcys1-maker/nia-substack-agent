"""Notki z banku: DeepSeek-pro vs Fable 5, ten sam material, te same formy.

Poprzedni test czytal nieistniejacy klucz i drukowal "(brak)" niezaleznie od
wyniku. `note()` oddaje {"type", "candidates"} — wybrany jest ten kandydat,
ktory ma safe_to_post=True.
"""
import sys, random, json, pathlib
sys.path.insert(0, "agent-v2")
import config, db, stages   # noqa: E402

config.DB_PATH = pathlib.Path("/tmp/notki-ab.db")
random.seed(11)
conn = db.connect()
bank = stages.bank_fragmentow(conn)
wg = {}
for f in bank:
    wg.setdefault(f["z_artykulu"], []).append(f)
wybrane = [random.choice(v) for v in list(wg.values())[:3]]
FORMY = ["LICZBA", "KONTRAST", "SCENA"]

def wybrany(w):
    for c in w.get("candidates", []):
        if c.get("safe_to_post"):
            return c
    return None

wyniki = {}
for model_nazwa, model in (("deepseek-pro", config.DEEPSEEK_PRO), ("fable-5", config.FABLE)):
    config.MODEL_FOR["note"] = model
    run_id = db.start_run(conn, stage="notki-%s" % model_nazwa)
    przed = conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)).fetchone()[0]
    print()
    print("#" * 78)
    print("### %s" % model_nazwa.upper())
    print("#" * 78)
    try:
        for i, f in enumerate(wybrane):
            dowod = {"confirmed_claims": [{"text": f["text"], "url": f["url"],
                                           "publisher": f["publisher"]}],
                     "citable_numbers": []}
            print()
            print("--- forma %s | zrodlo %s ---" % (FORMY[i], f["publisher"][:34]))
            try:
                w = stages.note(conn, run_id, "CIEKAWOSTKA", dowod, note_form=FORMY[i])
                c = wybrany(w)
                if c:
                    print("WYBRANA (%d slow):" % c.get("words_actual", 0))
                    print(c["note"])
                else:
                    print("ZADEN KANDYDAT NIE PRZESZEDL. Kandydaci:")
                    for k in w.get("candidates", []):
                        print("  [%d slow, dlugosc_ok=%s] %s" % (
                            k.get("words_actual", 0), k.get("length_ok"),
                            (k.get("note") or "")[:100]))
            except Exception as e:
                print("BLAD: %s: %s" % (type(e).__name__, str(e)[:110]))
    finally:
        db.finish_run(conn, run_id, "DONE", "notki-%s" % model_nazwa, "")
    wyniki[model_nazwa] = conn.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)).fetchone()[0] - przed

print()
print("=" * 78)
for k, v in wyniki.items():
    print("KOSZT %-14s $%.4f  (3 notki x %d kandydatow + weryfikacja)" % (k, v, config.NOTE_CANDIDATES))
