# -*- coding: utf-8 -*-
"""Audyt segmentu researchu na ZYWYCH danych, jednym poleceniem.

    python agent-v2/audyt_researchu.py

PO CO. Segment ma cztery etapy — dyskoveria, pobieranie, klasyfikacja, synteza —
i kazdy z nich mial wade widoczna w DANYCH, a niewidoczna w testach:

  - dyskoveria dopychala liste do dziesieciu pozycji omowieniami, wiec dluzsze
    szukanie dawalo MNIEJ dokumentow pierwotnych (5,1 -> 3,0),
  - ponowienie w przegladarce omijalo blokady, wiec przebieg z samymi zrodlami
    pierwotnymi zginal na trzech 403,
  - pusty korpus rzucal wyjatek WEWNATRZ `fetch`, przez co druga runda w
    `run.py` byla nieosiagalna,
  - `feasible` w odsiewie bylo True u wszystkich szesciu, czyli filtr nie
    filtrowal.

Testy pilnuja, ze kod robi to, co obiecuje. Ten audyt pyta, czy PRODUKCJA
wyglada tak, jak powinna. NIE WOLA PLATNEGO MODELU.

Kod wyjscia 1, gdy cokolwiek jest BLEDEM.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG))

import config   # noqa: E402
import stages   # noqa: E402

WERDYKTY: list[tuple[str, str]] = []


def etap(nr: int, nazwa: str) -> None:
    print()
    print("=" * 78)
    print("ETAP %d — %s" % (nr, nazwa))
    print("=" * 78)


def werdykt(nazwa: str, stan: str, szczegol: str = "") -> None:
    WERDYKTY.append((nazwa, stan))
    print("  >> %-5s %s%s" % (stan, nazwa, ("   " + szczegol) if szczegol else ""))


def main() -> int:
    c = sqlite3.connect(str(config.DB_PATH))
    c.row_factory = sqlite3.Row
    zrodla = list(c.execute("SELECT * FROM sources"))

    # ---------------------------------------------------------------
    etap(1, "DYSKOVERIA — rekordy, nie pozycje")
    # Tylko przebiegi z JEDNYM wywolaniem: przy kilku nie da sie przypisac
    # zrodel do wywolania i pomiar sie znieksztalca.
    jedno = [r[0] for r in c.execute(
        "SELECT run_id FROM calls WHERE purpose='discovery' AND web_searches>0"
        " GROUP BY run_id HAVING COUNT(*)=1")]
    pary = []
    for rid in jedno:
        k = c.execute("SELECT web_searches, cost_usd FROM calls"
                      " WHERE run_id=? AND purpose='discovery'", (rid,)).fetchone()
        s = c.execute(
            "SELECT COUNT(*) a, COALESCE(SUM(fetched_ok),0) b,"
            " SUM(CASE WHEN source_class='PRIMARY' THEN 1 ELSE 0 END) p"
            " FROM sources WHERE run_id=?", (rid,)).fetchone()
        if s["a"]:
            pary.append((rid, k["web_searches"], s["a"], s["p"]))
    print("  przebiegow z jednym wywolaniem: %d" % len(pary))
    if pary:
        ost = sorted(pary)[-4:]
        for rid, sz, ile, pierw in ost:
            print("    przebieg %-4s %2d wyszukiwan -> %2d zrodel, %2d pierwotnych"
                  % (rid, sz, ile, pierw))
        udzialy = [p / max(1, i) for _, _, i, p in pary]
        sredni = sum(udzialy) / len(udzialy)
        werdykt("dyskoveria oddaje glownie rekordy",
                "OK" if sredni >= 0.5 else "UWAGA",
                "srednio %d%% pozycji to zrodla pierwotne" % round(100 * sredni))
        # Najnowszy przebieg mowi wiecej niz srednia calej historii.
        rid, sz, ile, pierw = sorted(pary)[-1]
        werdykt("ostatni przebieg: wiekszosc pierwotnych",
                "OK" if pierw * 2 >= ile else "UWAGA",
                "%d z %d w przebiegu %s" % (pierw, ile, rid))
    brief = " ".join(
        (KATALOG / "prompts" / "dyskoveria.md").read_text(encoding="utf-8").split())
    werdykt("brief zabrania dopychania do liczby",
            "OK" if "Never add a source to reach a number" in brief else "BLAD")
    werdykt("i nazywa dziesiatke sufitem, nie celem",
            "OK" if "ceiling, not a target" in brief else "BLAD")

    # ---------------------------------------------------------------
    etap(2, "POBIERANIE — skutecznosc i blokady")
    ok = sum(1 for r in zrodla if r["fetched_ok"])
    print("  zrodel w bazie: %d, pobranych: %d" % (len(zrodla), ok))
    for powod, ile in Counter(str(r["fail_reason"] or "?")[:44]
                              for r in zrodla if not r["fetched_ok"]).most_common(6):
        print("    %3dx %s" % (ile, powod))
    udzial = ok / max(1, len(zrodla))
    werdykt("skutecznosc pobierania", "OK" if udzial >= 0.7 else "UWAGA",
            "%d%%" % round(100 * udzial))
    odzyskane = sum(1 for r in zrodla
                    if r["fetched_ok"] and "przegląd" in str(r["fail_reason"] or ""))
    werdykt("ponowienie w przegladarce cos odzyskuje",
            "OK" if odzyskane else "UWAGA",
            "%d stron odzyskanych" % odzyskane)
    werdykt("blokady trafiaja do ponowienia",
            "OK" if "HTTP 403" in stages._DO_PONOWIENIA else "BLAD")
    werdykt("a odmowa wprost NIE trafia",
            "OK" if "host odmówił automatowi" not in stages._DO_PONOWIENIA
            else "BLAD")

    # ---------------------------------------------------------------
    etap(3, "MARTWE HOSTY — czy pamiec dziala")
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    martwe = stages.hosty_ktore_nigdy_nie_dzialaly(conn)
    print("  na liscie: %s" % (", ".join(martwe) or "(pusto)"))
    werdykt("lista martwych hostow jest liczona",
            "OK" if isinstance(martwe, list) else "BLAD")
    # PDF-owe porazki NIE moga trafiac na te liste — easa.europa.eu wypadl tak
    # 2 na 2, a po dodaniu obslugi PDF-ow oddal 94 tys. znakow.
    pdfowe = {r["domain"] for r in zrodla
              if not r["fetched_ok"] and "PDF" in str(r["fail_reason"] or "")}
    zle = [h for h in martwe if h in pdfowe]
    werdykt("porazki PDF-owe nie skreslaja hosta",
            "OK" if not zle else "BLAD", str(zle))

    # ---------------------------------------------------------------
    etap(4, "KARTA DOWODOWA — czy cytaty stoja w zrodlach")
    karty = []
    for a in c.execute("SELECT id, evidence FROM articles"):
        try:
            k = json.loads(a["evidence"] or "{}")
        except Exception:
            continue
        if k.get("confirmed_claims"):
            karty.append((a["id"], k))
    tw = sum(len(k.get("confirmed_claims") or []) for _, k in karty)
    bez_cytatu = sum(1 for _, k in karty
                     for t in k.get("confirmed_claims") or []
                     if not str(t.get("evidence") or "").strip())
    bez_url = sum(1 for _, k in karty
                  for t in k.get("confirmed_claims") or []
                  if not urlparse(str(t.get("url") or "")).netloc)
    print("  kart: %d, twierdzen: %d" % (len(karty), tw))
    werdykt("kazde twierdzenie ma cytat", "OK" if not bez_cytatu else "BLAD",
            "%d bez" % bez_cytatu)
    werdykt("kazde twierdzenie ma adres", "OK" if not bez_url else "BLAD",
            "%d bez" % bez_url)
    sr = tw / max(1, len(karty))
    werdykt("karta nie jest pusta ani rozdeta",
            "OK" if 4 <= sr <= config.CARD_MAX_CONFIRMED else "UWAGA",
            "srednio %.1f twierdzen przy sufcie %d"
            % (sr, config.CARD_MAX_CONFIRMED))
    synt = " ".join(
        (KATALOG / "prompts" / "synteza.md").read_text(encoding="utf-8").split())
    werdykt("prompt zada, by cytat niosl CALE twierdzenie",
            "OK" if "MUST CARRY THE WHOLE CLAIM" in synt else "BLAD")

    # ---------------------------------------------------------------
    etap(5, "ZABEZPIECZENIA, KTORE MUSZA BYC OSIAGALNE")
    rp = (KATALOG / "run.py").read_text(encoding="utf-8")
    st = (KATALOG / "stages.py").read_text(encoding="utf-8")
    werdykt("pusty korpus nie rzuca wyjatku w fetch",
            "OK" if 'raise ValueError("nie pobrano ani jednej strony'
            not in st else "BLAD")
    werdykt("druga runda odpala sie takze przy braku rekordow",
            "OK" if "if za_chudo or bez_rekordow:" in rp else "BLAD")
    werdykt("i wyprzedza koniec przebiegu",
            "OK" if rp.index("if za_chudo or bez_rekordow:")
            < rp.index("if not corpus:") else "BLAD")
    werdykt("odsiew melduje martwe pola",
            "OK" if "[odsiew] MARTWE W TYM PRZEBIEGU" in st else "BLAD")

    # ---------------------------------------------------------------
    print()
    print("=" * 78)
    licz = Counter(s for _, s in WERDYKTY)
    print("PODSUMOWANIE: OK %d, UWAGA %d, BLAD %d"
          % (licz.get("OK", 0), licz.get("UWAGA", 0), licz.get("BLAD", 0)))
    for nazwa, stan in WERDYKTY:
        if stan != "OK":
            print("  %-6s %s" % (stan, nazwa))
    print("=" * 78)
    return 1 if licz.get("BLAD") else 0


if __name__ == "__main__":
    raise SystemExit(main())
