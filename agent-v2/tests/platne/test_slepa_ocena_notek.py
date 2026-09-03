"""Slepa ocena: Fable czy DeepSeek do finalnego pisania notek.

Poprzedni test porownywal MATERIAL, trzymajac pisarza stalego — i rozstrzygnal,
ze waskim gardlem nie jest pisarz. Ale pisarzy nie porownal wcale: dobre notki,
ktore wlasciciel widzial, napisal Fable, a DeepSeeka na tym samym materiale
nikt nie ogladal.

Ten skrypt pisze te same fakty oboma modelami, MIESZA wyniki i zdejmuje
etykiety. Ocena nalezy do czlowieka — automat nie ma czym zmierzyc tego, co tu
decyduje: czy pierwsze zdanie zatrzymuje obcego i czy ostatnie kompresuje
zamiast streszczac.

Klucz zapisuje sie do osobnego pliku, zeby dalo sie sprawdzic PO ocenie.
"""
import json
import pathlib
import random
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
config.DB_PATH = pathlib.Path("/tmp/slepa-ocena.db")
import db       # noqa: E402
import stages   # noqa: E402

# Pare modeli podaje sie w wywolaniu, zeby ten sam skrypt sluzyl kazdemu
# porownaniu i zeby wynik jednego nie zaciemnial drugiego:
#   python <plik> claude-fable-5 deepseek-v4-pro
#   python <plik> claude-fable-5 claude-opus-5
MODELE = (sys.argv[1] if len(sys.argv) > 1 else "claude-fable-5",
          sys.argv[2] if len(sys.argv) > 2 else "deepseek-v4-pro")
ETYKIETA = "-".join(m.replace("claude-", "").replace("deepseek-", "")
                    for m in MODELE)
KLUCZ = pathlib.Path("/tmp/slepa-klucz-%s.json" % ETYKIETA)

# Ten sam material dla obu modeli. Fakty z szerokiej wiedzy, kazdy z decydentem
# i skutkiem, ktory czytelnik trzyma — czyli takie, jakie przechodza bramki.
MATERIAL = [
    {"forma": "LICZBA",
     "fakt": "Mains-powered clocks keep time by counting cycles of the electricity "
             "grid rather than by measuring seconds. In early 2018 a shortfall in "
             "the Continental European synchronous area held the frequency below "
             "50 Hz for weeks and clocks across the continent fell about six "
             "minutes behind.",
     "zrodlo": "ENTSO-E", "url": "https://www.entsoe.eu/news/2018/03/06/"},
    {"forma": "KONTRAST",
     "fakt": "United States packers wash eggs before sale, which removes the "
             "cuticle sealing the shell, so refrigeration becomes necessary. "
             "European Union marketing standards forbid washing Class A eggs and "
             "advise against refrigeration before sale.",
     "zrodlo": "EUR-Lex 589/2008", "url": "https://eur-lex.europa.eu/eli/reg/2008/589"},
    {"forma": "ODWROCENIE",
     "fakt": "Aircraft emergency oxygen generators supply roughly twelve minutes "
             "of oxygen, which is not a compromise but the time an airliner needs "
             "to descend from cruising altitude to an altitude where cabin air is "
             "breathable.",
     "zrodlo": "FAA", "url": "https://www.faa.gov/"},
    {"forma": "ZACZEP_I_KONKRET",
     "fakt": "The 1947 North American Numbering Plan gave area codes that were "
             "quicker to dial on a rotary telephone to the places with the most "
             "telephones: New York received 212, Los Angeles 213, Chicago 312.",
     "zrodlo": "NANPA", "url": "https://nationalnanpa.com/about_us/abt_nanp.html"},
    {"forma": "SCENA",
     "fakt": "A shopping trolley wheel locks when it crosses a wire buried at the "
             "edge of the car park, not by radio signal, and the wire has to be "
             "physically installed in the ground by the retailer.",
     "zrodlo": "Gatekeeper Systems", "url": "https://www.gatekeepersystems.com/"},
]


def main() -> int:
    random.seed()
    conn = db.connect()
    run_id = db.start_run(conn, stage="slepa-%s" % ETYKIETA)
    przed = conn.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)
    ).fetchone()[0]

    pary = []
    koszty = {m: 0.0 for m in MODELE}
    try:
        for m in MATERIAL:
            dowod = {"confirmed_claims": [{"text": m["fakt"], "url": m["url"],
                                           "publisher": m["zrodlo"]}],
                     "citable_numbers": []}
            warianty = {}
            for model in MODELE:
                config.MODEL_FOR["note"] = model
                p = conn.execute(
                    "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?",
                    (run_id,)).fetchone()[0]
                try:
                    w = stages.note(conn, run_id, "CIEKAWOSTKA", dowod,
                                    note_form=m["forma"])
                    wyb = next((c for c in w.get("candidates", [])
                                if c.get("safe_to_post")), None)
                    warianty[model] = wyb["note"] if wyb else None
                except Exception as exc:
                    print("  BLAD %s: %s" % (model, str(exc)[:80]), flush=True)
                    warianty[model] = None
                koszty[model] += conn.execute(
                    "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?",
                    (run_id,)).fetchone()[0] - p
            if all(warianty.values()):
                pary.append({"forma": m["forma"], "warianty": warianty})
    finally:
        db.finish_run(conn, run_id, "DONE", "slepa-%s" % ETYKIETA, "")
        config.MODEL_FOR["note"] = config.FABLE

    # MIESZAMY. Etykieta A/B jest losowana per para, wiec ocena nie moze
    # dryfowac w strone jednego modelu przez kolejnosc.
    klucz = []
    print()
    print("=" * 78)
    print("SLEPA OCENA — etykiety zdjete. Oceniaj trzy rzeczy:")
    print("  1. czy PIERWSZE zdanie zatrzymuje obcego w przewijanym kanale")
    print("  2. czy OSTATNIE kompresuje, zamiast streszczac")
    print("  3. czy cokolwiek brzmi nie po angielsku albo jak kalka")
    print("=" * 78)
    for i, para in enumerate(pary, 1):
        modele = list(para["warianty"])
        random.shuffle(modele)
        klucz.append({"para": i, "forma": para["forma"],
                      "A": modele[0], "B": modele[1]})
        print()
        print("--- PARA %d  (forma %s) ---" % (i, para["forma"]))
        for etykieta, model in zip("AB", modele):
            print()
            print("  [%s]" % etykieta)
            for linia in para["warianty"][model].split("\n"):
                print("      %s" % linia)
    KLUCZ.write_text(json.dumps(klucz, ensure_ascii=False, indent=2),
                     encoding="utf-8")

    koszt = conn.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?", (run_id,)
    ).fetchone()[0] - przed
    print()
    print("=" * 78)
    print("par do oceny: %d" % len(pary))
    print("klucz zapisany w %s — NIE zagladaj przed ocena" % KLUCZ)
    print()
    for model, k in koszty.items():
        print("  %-18s $%.4f  (%.4f za notke)"
              % (model, k, k / max(1, len(pary))))
    print("  RAZEM              $%.4f" % koszt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
