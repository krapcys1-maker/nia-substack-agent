"""Pelna sciezka: Federal Register -> kandydaci -> bramki -> indeks.

Pomiar, o ktory prosil wlasciciel: ilu kandydatow przechodzi bramke na sto
pobranych dokumentow. Darmowa czesc (ile preambul niesie spor) zmierzona
osobno w `tests/test_korpus_fedreg.py` — wyszlo 20 procent. Ten test mierzy
druga polowe: ile z tych gestych preambul daje kandydata, ktory przechodzi
cztery bramki.

PLATNY: jedno wywolanie flasha na preambule. Wejscie bywa duze, wiec to jest
najdrozsza czesc tego korpusu i wlasnie dlatego filtr sporu dziala PRZED nim.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
config.DB_PATH = pathlib.Path("/tmp/fedreg-test.db")
import db       # noqa: E402
import stages   # noqa: E402
stages.INDEKS_KANDYDATOW = pathlib.Path("/tmp/indeks-fedreg.json")

ILE_DOKUMENTOW = 40
ILE_GESTYCH = 4


def main() -> int:
    conn = db.connect()
    run_id = db.start_run(conn, stage="test-fedreg")
    przed = conn.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)
    ).fetchone()[0]

    print("== 1. KORPUS (darmowe) ==")
    dokumenty = stages.korpus_fedreg(ILE_DOKUMENTOW, ILE_GESTYCH)
    if not dokumenty:
        print("nic nie znaleziono")
        return 1

    print()
    print("== 2. WYCIAGANIE KANDYDATOW (platne) ==")
    wszyscy = []
    try:
        for d in dokumenty:
            print()
            print("--- %s" % d["tytul"][:66])
            try:
                k = stages.kandydaci_z_fedreg(conn, run_id, d)
            except Exception as exc:
                print("    BLAD: %s: %s" % (type(exc).__name__, str(exc)[:90]))
                continue
            print("    kandydatow: %d" % len(k))
            for x in k:
                ok, powod = stages.bramka_kandydata(x)
                print("    %s %s" % ("PRZECHODZI" if ok else "odpada    ",
                                     str(x.get("wrong_belief", ""))[:82]))
                if ok:
                    print("               -> %s" % str(x.get("actually", ""))[:78])
                    print("               dotyka: %s" % str(x.get("consequence", ""))[:64])
                else:
                    print("               %s" % powod[:78])
            wszyscy.extend(k)
    finally:
        db.finish_run(conn, run_id, "DONE", "test-fedreg", "")

    print()
    print("== 3. DO INDEKSU ==")
    licznik = stages.dopisz_kandydatow(wszyscy)
    koszt = conn.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)
    ).fetchone()[0] - przed

    print()
    print("=" * 74)
    print("POMIAR")
    print("  dokumentow przejrzanych:      %3d" % ILE_DOKUMENTOW)
    print("  gestych preambul:             %3d" % len(dokumenty))
    print("  kandydatow wyciagnietych:     %3d" % len(wszyscy))
    print("  przeszlo cztery bramki:       %3d" % licznik["przyjete"])
    print("  odrzuconych:                  %3d" % licznik["odrzucone"])
    if ILE_DOKUMENTOW:
        print()
        print("  NA STO DOKUMENTOW: %.0f kandydatow przechodzacych bramki"
              % (100 * licznik["przyjete"] / ILE_DOKUMENTOW))
    print()
    print("  KOSZT: $%.4f  (%.4f za uzytecznego kandydata)"
          % (koszt, koszt / max(1, licznik["przyjete"])))
    print()
    print("  dla porownania: curiosity kosztuje $0,0514 za wywolanie")
    return 0


if __name__ == "__main__":
    sys.exit(main())
