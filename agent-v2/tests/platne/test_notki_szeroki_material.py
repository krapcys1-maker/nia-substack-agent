"""Czy agent pisze na poziomie notek, ktore wlasciciel uznal za wzorcowe.

Hipoteza do sprawdzenia: roznica nie lezy w PISARZU, tylko w MATERIALE.
Notki wzorcowe powstaly z calej wiedzy o swiecie — sieć energetyczna jako
zegar, numery kierunkowe jako czas wykrecania tarczy, awaria BGP Pakistanu.
Nasze powstaja ze 134 resztek po pieciu artykulach, czyli z zalacznikow
o kosmetykach i sekcji CFR.

Ten test daje pisarzowi TEN SAM material, co mial Claude — fakt z szerokiej
wiedzy zamiast okrawka z naszego korpusu — i patrzy, co wyjdzie. Jesli wyjdzie
rownie dobrze, wina lezy po stronie doboru materialu i to jest do naprawy.
Jesli nie, problem jest w prompcie notki.

NIE jest to test automatyczny: ocena nalezy do czlowieka. Wypisuje material,
notke i miary, ktore da sie policzyc.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
config.DB_PATH = pathlib.Path("/tmp/notki-szeroki.db")
import db       # noqa: E402
import stages   # noqa: E402

# Fakty z szerokiej wiedzy, kazdy z prawdziwym zrodlem. Zadnego z nich NIE MA
# w naszym banku — o to wlasnie chodzi.
MATERIAL = [
    {"forma": "LICZBA",
     "fakt": "Mains-powered clocks keep time by counting cycles of the electricity "
             "grid rather than by measuring seconds. In early 2018 a shortfall in "
             "the Continental European synchronous area caused the grid frequency "
             "to run below 50 Hz for weeks, and clocks across the continent fell "
             "about six minutes behind.",
     "url": "https://www.entsoe.eu/news/2018/03/06/press-release-continuing-frequency-deviation-in-the-continental-european-power-system/",
     "zrodlo": "ENTSO-E"},
    {"forma": "KONTRAST",
     "fakt": "United States packers wash eggs before sale, which removes the "
             "cuticle sealing the shell, so refrigeration becomes necessary. "
             "European Union marketing standards forbid washing Class A eggs and "
             "advise against refrigeration before sale.",
     "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32008R0589",
     "zrodlo": "EUR-Lex, Regulation 589/2008"},
    {"forma": "ZACZEP_I_KONKRET",
     "fakt": "The North American Numbering Plan of 1947 assigned area codes whose "
             "digits were quicker to dial on a rotary telephone to the areas with "
             "the most telephones: New York received 212, Los Angeles 213 and "
             "Chicago 312, while less populous areas received codes with higher "
             "digits that took longer for the dial to return.",
     "url": "https://nationalnanpa.com/about_us/abt_nanp.html",
     "zrodlo": "North American Numbering Plan Administrator"},
]


def main() -> int:
    conn = db.connect()
    run_id = db.start_run(conn, stage="test-szeroki-material")
    przed = conn.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)
    ).fetchone()[0]
    wyniki = []
    try:
        for m in MATERIAL:
            dowod = {"confirmed_claims": [{"text": m["fakt"], "url": m["url"],
                                           "publisher": m["zrodlo"]}],
                     "citable_numbers": []}
            print()
            print("=" * 76)
            print("forma %s   zrodlo %s" % (m["forma"], m["zrodlo"]))
            print("-" * 76)
            try:
                w = stages.note(conn, run_id, "CIEKAWOSTKA", dowod,
                                note_form=m["forma"])
                wybrana = next((c for c in w.get("candidates", [])
                                if c.get("safe_to_post")), None)
                if not wybrana:
                    print("(zaden kandydat nie przeszedl)")
                    continue
                tekst = wybrana["note"]
                print(tekst)
                pierwsze = tekst.split("\n")[0]
                wyniki.append({
                    "forma": m["forma"], "slow": wybrana.get("words_actual"),
                    "pierwsza_linia_slow": len(pierwsze.split()),
                    "ma_liczbe": any(z.isdigit() for z in pierwsze),
                    "ostatnie": tekst.strip().split("\n")[-1].strip(),
                })
            except Exception as exc:
                print("BLAD: %s: %s" % (type(exc).__name__, str(exc)[:120]))
    finally:
        db.finish_run(conn, run_id, "DONE", "test-szeroki-material", "")

    koszt = conn.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)
    ).fetchone()[0] - przed
    print()
    print("=" * 76)
    print("%-18s %5s %14s %9s" % ("forma", "slow", "1. linia slow", "liczba w 1."))
    for w in wyniki:
        print("%-18s %5s %14s %9s" % (w["forma"], w["slow"],
                                      w["pierwsza_linia_slow"],
                                      "tak" if w["ma_liczbe"] else "nie"))
    print()
    print("zamkniecia (to one decyduja, czy notka zostaje w glowie):")
    for w in wyniki:
        print("  %s" % w["ostatnie"][:100])
    print()
    print("KOSZT: $%.4f za %d notek" % (koszt, len(wyniki)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
