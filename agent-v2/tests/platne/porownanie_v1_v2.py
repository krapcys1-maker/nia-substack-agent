"""Porownanie starego i nowego bota na TYM SAMYM temacie.

Uruchamiany DWA RAZY, raz w kazdej kopii:
  cd ~/nia-substack-bot && python <ten plik> v1
  cd ~/nia-test              && python <ten plik> v2

Temat jest narzucony, zeby porownac potok, a nie los skauta. Kazde ramie
zapisuje wynik do /tmp/porownanie-<wersja>/ — artykul, notke, grafike
i liczby. Zestawienie robi czlowiek, patrzac na oba obok siebie.

Czym v2 rozni sie w tym miejscu potoku:
  - bramka ciekawosci przed pisarzem (v1 jej nie ma)
  - druga runda dyskoverii przy chudym korpusie
  - PDF-y w pobieraniu
  - pomijanie hostow, ktore nas nigdy nie wpuscily
  - losowany ruch koncowy i szerokosc drugiego aktu
  - inny styl okladki
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import db       # noqa: E402
import llm      # noqa: E402
import stages   # noqa: E402

WERSJA = (sys.argv[1] if len(sys.argv) > 1 else "x").lower()
WYNIKI = pathlib.Path("/tmp/porownanie-%s" % WERSJA)

# Temat wybrany tak, zeby oba boty mialy rowne szanse: zwykly przedmiot,
# udokumentowana decyzja, zlamane przekonanie. NIE byl uzywany w zadnym
# z dotychczasowych artykulow.
TEMAT = {
    "title": "The Handle on a Fire Hydrant",
    "question": "Who decides the colour of a fire hydrant, and what does the "
                "colour tell a firefighter that it does not tell anyone else?",
    "broken_belief": "Everyone assumes fire hydrants are red, and that the "
                     "colour is just paint.",
    "why_they_believe_it": "Red hydrants are the ones that appear in "
                           "illustrations and on street signage.",
    "ma_przekonanie": True,
}


def main() -> int:
    WYNIKI.mkdir(parents=True, exist_ok=True)
    conn = db.connect()
    run_id = db.start_run(conn, stage="porownanie-%s" % WERSJA)
    t0 = time.time()
    raport = {"wersja": WERSJA, "temat": TEMAT["title"]}

    def koszt() -> float:
        return conn.execute(
            "SELECT COALESCE(SUM(cost_usd),0) FROM calls WHERE run_id=?",
            (run_id,)).fetchone()[0]

    try:
        print("== %s | temat: %s ==" % (WERSJA.upper(), TEMAT["title"]), flush=True)

        print("\n-- dyskoveria --", flush=True)
        zrodla = stages.discovery(conn, run_id, TEMAT["question"], [])
        raport["zrodel_zaproponowanych"] = len(zrodla)

        print("\n-- pobieranie --", flush=True)
        korpus = stages.fetch(conn, run_id, zrodla)
        raport["pobranych"] = len(korpus)
        raport["znakow"] = sum(len(s.get("text", "")) for s in korpus)
        raport["pdf"] = sum(1 for s in korpus
                            if ".pdf" in (s.get("url") or "").lower())

        # DRUGA RUNDA — tylko v2 ja ma. W v1 tej galezi nie bedzie.
        prog = getattr(config, "MIN_ZRODEL_DO_PISANIA", 0)
        if prog and len(korpus) < prog:
            print("\n-- za chudo, druga runda (tylko v2) --", flush=True)
            juz = {s.get("host") or s.get("url", "") for s in korpus}
            dodatkowe = [s for s in stages.discovery(conn, run_id,
                                                     TEMAT["question"], [])
                         if (s.get("host") or s.get("url", "")) not in juz]
            if dodatkowe:
                korpus += stages.fetch(conn, run_id, dodatkowe)
                raport["po_drugiej_rundzie"] = len(korpus)

        print("\n-- klasyfikacja --", flush=True)
        material = stages.classify(conn, run_id, TEMAT["question"], korpus)
        raport["uzytecznych"] = len(material)
        raport["fragmentow"] = sum(len(s["excerpts"]) for s in material)
        raport["liczb"] = sum(len(s["numbers"]) for s in material)

        print("\n-- synteza --", flush=True)
        karta = stages.synthesis(conn, run_id, TEMAT["question"], material)

        # BRAMKA CIEKAWOSCI — tylko v2.
        if hasattr(stages, "warto_pisac"):
            print("\n-- bramka ciekawosci (tylko v2) --", flush=True)
            ocena = stages.warto_pisac(conn, run_id, karta)
            raport["werdykt_bramki"] = ocena["werdykt"]
            raport["przekonanie"] = (ocena.get("contradicted_belief") or {}).get(
                "the_belief", "")
            raport["filarow"] = ocena["ile_filarow"]

        print("\n-- pisanie --", flush=True)
        draft = stages.write(conn, run_id, karta, "RICH")
        raport["tytul"] = draft.get("title", "")
        raport["podtytul"] = draft.get("subtitle", "")
        raport["slow"] = len(draft["body"].split())
        (WYNIKI / "artykul.md").write_text(
            "# %s\n\n*%s*\n\n%s\n" % (draft.get("title", ""),
                                      draft.get("subtitle", ""), draft["body"]),
            encoding="utf-8")

        print("\n-- bramki --", flush=True)
        import gates
        uwagi = gates.deterministic_floors(draft["body"], karta)
        raport["uwagi"] = [u["gate"] for u in uwagi]

        print("\n-- notka z tego samego materialu --", flush=True)
        try:
            w = stages.note(conn, run_id, "ARTYKUL", karta, note_form="LICZBA")
            wyb = next((c for c in w.get("candidates", [])
                        if c.get("safe_to_post")), None)
            raport["notka"] = wyb["note"] if wyb else "(zadna nie przeszla)"
        except Exception as exc:
            raport["notka"] = "BLAD: %s" % str(exc)[:80]
        (WYNIKI / "notka.txt").write_text(raport["notka"], encoding="utf-8")

        print("\n-- grafika --", flush=True)
        try:
            opis = stages.image_brief(conn, run_id, draft) \
                if hasattr(stages, "image_brief") else None
            if opis is None:
                from stages import _prompt
                surowy = llm.call("grafika", "You write image briefs. Return JSON.",
                                  _prompt("grafika.md", title=draft.get("title", ""),
                                          body=draft["body"][:6000]),
                                  conn=conn, run_id=run_id)
                opis = llm.parse_json(surowy)
            raport["grafika_przedmiot"] = opis.get("subject", "")
            dane = llm.obraz(opis["prompt"], conn=conn, run_id=run_id)
            (WYNIKI / "grafika.png").write_bytes(dane)
            raport["grafika_kb"] = round(len(dane) / 1024)
        except Exception as exc:
            raport["grafika_blad"] = "%s: %s" % (type(exc).__name__, str(exc)[:80])
    finally:
        db.finish_run(conn, run_id, "DONE", "porownanie-%s" % WERSJA, "")

    raport["koszt"] = round(koszt(), 4)
    raport["sekund"] = round(time.time() - t0)
    (WYNIKI / "raport.json").write_text(
        json.dumps(raport, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=" * 74)
    for k, v in raport.items():
        if k != "notka":
            print("  %-22s %s" % (k, str(v)[:80]))
    print()
    print("  zapisane w %s" % WYNIKI)
    return 0


if __name__ == "__main__":
    sys.exit(main())
