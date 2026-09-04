# -*- coding: utf-8 -*-
"""Audyt segmentu tematow — kazdy etap na ZYWYCH danych, jednym poleceniem.

    python agent-v2/audyt_tematow.py

PO CO TO ISTNIEJE. Segment znajdowania tematow ma jedenascie etapow i kazdy z
nich byl kiedys zepsuty w sposob, ktorego testy jednostkowe nie widzialy:
bramka odrzucajaca 62% oplaconego materialu, indeks zapisywany i nieczytany,
spizarnia z poprzedniego pisma, licznik notek liczacy cudze notki, korpus
pobierany dwa razy. Wspolna cecha: KAZDA z tych wad byla widoczna w danych i
niewidoczna w testach, bo test sprawdza atrape, a nie stan produkcji.

Wiec to nie zastepuje testow. Testy pilnuja, ze kod robi to, co obiecuje;
ten audyt pyta, czy PRODUKCJA wyglada tak, jak powinna wygladac.

NIE WOLA PLATNEGO MODELU. Wszystko liczy sie z tego, co juz jest na dysku, plus
darmowe pobranie kanalow. Ranking i szukanie ciekawostek sa platne i sprawdza
sie je osobno.

Kod wyjscia 1, gdy cokolwiek jest BLEDEM.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG))

import config          # noqa: E402
import korpus_kanalow  # noqa: E402
import stages          # noqa: E402

WERDYKTY: list[tuple[str, str]] = []


def etap(nr: int, nazwa: str) -> None:
    print()
    print("=" * 78)
    print("ETAP %d — %s" % (nr, nazwa))
    print("=" * 78)


def werdykt(nazwa: str, stan: str, szczegol: str = "") -> None:
    WERDYKTY.append((nazwa, stan))
    print("  >> %-5s %s%s" % (stan, nazwa, ("   " + szczegol) if szczegol else ""))


def bank() -> list[dict]:
    """Indeks kandydatow, albo pusto — narzedzie audytowe NIE MOZE sie wywalac.

    Do 2026-09-03 czytalo plik wprost i na swiezej instalacji konczylo sie
    `FileNotFoundError` w polowie ekranu. Audyt, ktory pada zamiast powiedziec
    „nie ma danych", jest bezuzyteczny dokladnie wtedy, gdy jest najbardziej
    potrzebny: przy pierwszym uruchomieniu, gdy czlowiek nie wie, czego szukac.

    Produkcyjne `stages.wczytaj_indeks` radzi sobie z brakiem pliku od dawna
    — to narzedzie po prostu nie korzystalo z tej samej drogi.
    """
    plik = config.DATA_DIR / "indeks_kandydatow.json"
    if not plik.exists():
        print("  (brak %s — bank jeszcze nie powstal)" % plik.name)
        return []
    try:
        p = json.loads(plik.read_text(encoding="utf-8"))
    except ValueError as exc:
        print("  (indeks kandydatow NIECZYTELNY: %s — traktuje jak pusty, "
              "ale to NIE znaczy, ze bank jest pusty)" % exc)
        return []
    return p if isinstance(p, list) else (p.get("kandydaci") or [])


def main() -> int:
    poz = bank()
    nowi = [k for k in poz if k.get("status") == "nowy"]
    po_pivocie = [k for k in nowi
                  if str(k.get("kiedy") or "")[:10] >= config.DATA_PRZESTAWIENIA]
    zywi = [k for k in po_pivocie if not stages._po_terminie(k)]

    # ---------------------------------------------------------------
    etap(1, "ZRODLA — korpus kanalow i jego zapas")
    korpus_kanalow._ZAPAS["wpisy"] = None
    korpus_kanalow._ZAPAS["kiedy"] = 0.0
    # BRAK KANALOW TO DECYZJA, NIE AWARIA — i to jest cala roznica miedzy
    # „nie ma czego pobrac" a „jest co pobrac i nie idzie".
    #
    # `zrodla.kanaly_youtube` jest domyslnie PUSTE, wiec swieza instalacja
    # dostawala tu DWA BLEDY i kod wyjscia 1 za stan calkowicie poprawny.
    # Pierwszy audyt, jaki widzi nowy operator, meldowal awarie swojej wlasnej
    # konfiguracji domyslnej — a ten plik ostrzega przed falszywym alarmem
    # w trzech miejscach („falszywy alarm uczy ignorowac alarmy").
    k1: list = []
    k2: list = []
    if not korpus_kanalow.KANALY:
        print("  (zadnego kanalu nie skonfigurowano —"
              " `zrodla.kanaly_youtube` w konfiguracji)")
        werdykt("korpus kanalow: skonfigurowany", "UWAGA",
                "brak kanalow. To DECYZJA, nie awaria: notki stana na siatce"
                " dziedzin, bez zaczynu z dnia")
    else:
        k1 = korpus_kanalow.korpus_kanalow(26)
        k2 = korpus_kanalow.korpus_kanalow(200)
        print("  pierwsze wywolanie oddalo %d, drugie %d" % (len(k1), len(k2)))
        werdykt("kanaly odpowiadaja", "OK" if k1 else "BLAD",
                "%d tematow z %d kanalow" % (len(k1), len(korpus_kanalow.KANALY)))
        werdykt("zapas oddaje PELNA liste drugiemu wolajacemu",
                "OK" if len(k2) > len(k1) else "BLAD",
                "%d > %d" % (len(k2), len(k1)))
    # `k2` istnieje tylko w galezi ze skonfigurowanymi kanalami — bez nich
    # pytanie „ile kanalow dalo material" nie ma podmiotu.
    # PROG Z LICZBY SKONFIGURTOWANYCH KANALOW, NIE WPISANY. Stalo tu
    # `zywe_kanaly >= 8` — liczba z konta, ktore mialo ich trzynascie. Konto
    # z czterema kanalami dostawaloby UWAGA kazdego dnia swojego zycia, nawet
    # gdy wszystkie cztery odpowiedzialy. Pytanie brzmi „czy KANALY, ktore
    # podales, w ogole zyja", a to jest udzial, nie liczba bezwzgledna.
    zywe_kanaly = len({w.get("kanal") for w in k2})
    if korpus_kanalow.KANALY:
        werdykt("ile kanalow dalo material",
                "OK" if zywe_kanaly * 2 >= len(korpus_kanalow.KANALY)
                else "UWAGA",
                "%d z %d" % (zywe_kanaly, len(korpus_kanalow.KANALY)))

    # ---------------------------------------------------------------
    etap(2, "PAS PIERWSZENSTWA — wielkie wydarzenia")
    wyd = korpus_kanalow.wielkie_wydarzenia(k2)
    print("  wydarzen w dzisiejszym korpusie: %d" % len(wyd))
    for w in wyd[:3]:
        print("    %s  (%d kanalow, %s)"
              % (" ".join(w["o_czym"][:4]), w["kanalow"], w["data"]))
    # PUSTO TO NIE JEST DOWOD. Wykrywacz, ktory nigdy nie strzela, wyglada
    # identycznie jak spokojny tydzien — wiec sprawdzamy go na atrapie.
    dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dawno = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    swieze = [{"temat": "titan seven release changes inference pricing",
               "kanal": c, "data": dzis} for c in "abcd"]
    stare = [{**w, "data": dawno} for w in swieze]
    jeden = [{**swieze[0], "kanal": "a"}]
    werdykt("na sztucznym swiezym wydarzeniu STRZELA",
            "OK" if korpus_kanalow.wielkie_wydarzenia(swieze) else "BLAD")
    werdykt("na tym samym, ale starym — nie",
            "OK" if not korpus_kanalow.wielkie_wydarzenia(stare) else "BLAD")
    werdykt("na jednym kanale — nie",
            "OK" if not korpus_kanalow.wielkie_wydarzenia(jeden) else "BLAD")

    # ---------------------------------------------------------------
    etap(3, "SIATKA TEMATOW")
    print("  dziedzin %d, generatorow %d, na przebieg %d"
          % (len(config.DZIEDZINY_CIEKAWOSTEK), len(config.GENERATORY),
             config.ILE_GENERATOROW_NA_PRZEBIEG))
    # TA SAMA LISTA, CO W `tests/test_prompty_o_niszy.py`. Stalo tu wlasne
    # osiem slow przy stu tamtych, wiec ta kontrola przepuszczala dziedzine,
    # ktora tamta by zatrzymala — i obie swiecily na zielono niezaleznie.
    sys.path.insert(0, str(KATALOG.parent / "narzedzia"))
    import dawne_slownictwo
    slownik = dawne_slownictwo.wszystkie()
    sprzed = [d for d in config.DZIEDZINY_CIEKAWOSTEK
              if any(s in d.lower() for s in slownik)]
    werdykt("zadna dziedzina nie jest z poprzedniej epoki",
            "OK" if not sprzed else "BLAD", str(sprzed[:3]))
    werdykt("i lista, ktora to sprawdza, nie jest pusta",
            "OK" if len(slownik) >= 20 else "BLAD",
            "%d hasel" % len(slownik))
    werdykt("dziedzin wystarczy na rotacje",
            "OK" if len(config.DZIEDZINY_CIEKAWOSTEK) >= 30 else "UWAGA",
            str(len(config.DZIEDZINY_CIEKAWOSTEK)))

    # ---------------------------------------------------------------
    etap(4, "BRAMKA SWIEZOSCI na materiale w banku")
    # UWAGA METODOLOGICZNA: to jest proba PO SELEKCJI. Kandydat, ktory odpadl
    # przy wkladaniu, nigdy tu nie trafil, wiec wysoki odsetek zdanych NIE
    # dowodzi, ze bramka jest luzna. Interesuje nas cos innego: czy material
    # LEZACY w banku nie zestarzal sie od czasu wlozenia.
    powody: Counter = Counter()
    przeszlo = 0
    for k in po_pivocie:
        ok, powod = stages.swiezosc_faktu(k)
        przeszlo += 1 if ok else 0
        if not ok:
            powody[powod.split("(")[0].strip()[:52]] += 1
    print("  z %d w banku nadal swiezych: %d" % (len(po_pivocie), przeszlo))
    for p, n in powody.most_common(5):
        print("    %2dx %s" % (n, p))
    # PUSTY BANK TO NIE JEST ZGNILY MATERIAL. `max(1, len(...))` chronilo przed
    # dzieleniem przez zero i przy okazji KLAMALO: 0/1 = „0% swiezych" i BLAD
    # przy banku, w ktorym nie ma ani jednej pozycji. Swieza instalacja
    # dostawala wiec BLAD i kod wyjscia 1 za stan poprawny.
    #
    # Ten projekt rozstrzygnal to poprawnie w czterech innych miejscach —
    # `wzajemnosc.odwzajemnienie` („mianownik zerowy nie daje zera procent,
    # tylko brak odpowiedzi"), `norma._srednia`, `statystyki.podsumowanie`,
    # `alarm.wolumeny`.
    if not po_pivocie:
        werdykt("material w banku nie zgnil", "UWAGA",
                "bank pusty — nie ma czego mierzyc, i to NIE jest 0% swiezych")
    else:
        werdykt("material w banku nie zgnil",
                "OK" if przeszlo / len(po_pivocie) > 0.5 else "BLAD",
                "%d%% swiezych" % round(100 * przeszlo / len(po_pivocie)))

    # ---------------------------------------------------------------
    etap(5, "BRAMKA KANDYDATA na materiale w banku")
    odrzuty: Counter = Counter()
    zdane = 0
    for k in po_pivocie:
        ok, powod = stages.bramka_kandydata(k)
        zdane += 1 if ok else 0
        if not ok:
            odrzuty[powod.split(":")[0][:52]] += 1
    print("  przechodzi %d z %d" % (zdane, len(po_pivocie)))
    for p, n in odrzuty.most_common(5):
        print("    %2dx %s" % (n, p))
    werdykt("bank nie trzyma materialu, ktorego bramka nie przepuszcza",
            "OK" if po_pivocie and zdane / len(po_pivocie) > 0.8 else "UWAGA",
            ("%d%%" % round(100 * zdane / len(po_pivocie))) if po_pivocie
            else "bank pusty — nie ma czego mierzyc")

    # ---------------------------------------------------------------
    etap(6, "TERMIN PRZYDATNOSCI I SUFIT")
    z_terminem = sum(1 for k in nowi if k.get("wazny_do"))
    po_terminie = [k for k in po_pivocie if stages._po_terminie(k)]
    print("  nowych %d, po przestawieniu konta %d, zywych %d"
          % (len(nowi), len(po_pivocie), len(zywi)))
    print("  z jawnym `wazny_do` %d, po terminie %d"
          % (z_terminem, len(po_terminie)))
    werdykt("bank_pelny zgadza sie z licznikiem",
            "OK" if stages.bank_pelny() == (len(zywi) >= config.BANK_MAKS_WOLNYCH)
            else "BLAD",
            "zywych %d, sufit %d, bank_pelny=%s"
            % (len(zywi), config.BANK_MAKS_WOLNYCH, stages.bank_pelny()))
    werdykt("bank jest buforem, nie magazynem",
            "OK" if len(zywi) <= config.BANK_MAKS_WOLNYCH * 2 else "UWAGA",
            "zywych %d przy sufcie %d" % (len(zywi), config.BANK_MAKS_WOLNYCH))

    # ---------------------------------------------------------------
    etap(7, "RANKING — slad po ostatnim przebiegu")
    ocenieni = [k for k in zywi if "ranga" in k]
    art = [k for k in ocenieni if k.get("na_artykul")]
    rangi = [k["ranga"] for k in ocenieni]
    print("  ocenionych %d z %d zywych, na artykul %d"
          % (len(ocenieni), len(zywi), len(art)))
    werdykt("rangi sa unikalne",
            "OK" if len(rangi) == len(set(rangi)) else "BLAD")
    if ocenieni:
        u = len(art) / len(ocenieni)
        werdykt("znacznik artykulowy pod sufitem",
                "OK" if u <= config.BANK_UDZIAL_ARTYKULOW + 0.02 else "BLAD",
                "%d%% przy sufcie %d%%"
                % (round(100 * u), round(100 * config.BANK_UDZIAL_ARTYKULOW)))
    odrzuceni = [k for k in poz if str(k.get("powod", "")).startswith("bank:")]
    bez_kodu = [k for k in odrzuceni
                if not any(kod in str(k.get("powod", "")).upper()
                           for kod in stages.POWODY_WYRZUCENIA)]
    print("  wyrzuconych przez ranking kiedykolwiek: %d" % len(odrzuceni))
    werdykt("kazde odrzucenie ma legalny kod",
            "OK" if not bez_kodu else "UWAGA",
            "%d bez kodu (sprzed bramki — przejrzyj recznie)" % len(bez_kodu))

    # ---------------------------------------------------------------
    etap(8, "WYJMOWANIE — kolejnosc, termin, blizniaki")
    wziete = stages.wez_kandydatow(6)
    for k in wziete:
        print("    #%-3s %s" % (k.get("ranga", "-"), str(k.get("fact"))[:72]))
    kolej = [k.get("ranga", 10 ** 6) for k in wziete]
    werdykt("wychodza w kolejnosci rangi",
            "OK" if kolej == sorted(kolej) else "BLAD", str(kolej))
    pary = [(a, b) for i, a in enumerate(wziete) for b in wziete[i + 1:]
            if stages._o_tym_samym(str(a.get("fact")), str(b.get("fact")),
                                   **stages.POROWNANIE_MIEDZY_DNIAMI)]
    werdykt("w partii nie ma blizniakow", "OK" if not pary else "BLAD",
            "%d par" % len(pary))
    werdykt("kazdy wziety przechodzi bramke swiezosci",
            "OK" if all(stages.swiezosc_faktu(k)[0] for k in wziete) else "BLAD")

    # ---------------------------------------------------------------
    etap(9, "ZWROT DO PULI")
    oddane = stages.zwroc_kandydatow(wziete)
    po = [k for k in bank() if k.get("status") == "nowy"]
    werdykt("wszystko wrocilo", "OK" if oddane == len(wziete) else "BLAD",
            "%d z %d" % (oddane, len(wziete)))
    werdykt("stan banku bez zmian po wzieciu i zwrocie",
            "OK" if len(po) == len(nowi) else "BLAD",
            "%d wobec %d" % (len(po), len(nowi)))

    # ---------------------------------------------------------------
    etap(10, "KOTWICA W KANALACH — prog wlasciciela")
    zakotw = [k for k in zywi if k.get("z_kanalu")]
    if zywi:
        udzial = 100.0 * len(zakotw) / len(zywi)
        print("  z kanalow %d z %d (%.0f%%), prog %.0f%%"
              % (len(zakotw), len(zywi), udzial,
                 100 * config.SKAUT_UDZIAL_Z_KANALOW))
        kanaly = Counter(k.get("kanal_zrodlowy") for k in zakotw)
        for nazwa, ile in kanaly.most_common(6):
            print("    %-22s %d" % (nazwa or "(bez nazwy)", ile))
        werdykt("bank trzyma prog kotwic",
                "OK" if udzial >= 100 * config.SKAUT_UDZIAL_Z_KANALOW
                else "UWAGA", "%.0f%%" % udzial)
        werdykt("kotwice pamietaja, z ktorego kanalu",
                "OK" if all(k.get("kanal_zrodlowy") for k in zakotw) else "BLAD",
                "%d bez nazwy" % sum(1 for k in zakotw
                                     if not k.get("kanal_zrodlowy")))
        werdykt("material nie jest z jednego kanalu",
                "OK" if len(kanaly) >= 3 else "UWAGA",
                "%d roznych kanalow" % len(kanaly))
    else:
        werdykt("bank ma cokolwiek do sprawdzenia", "UWAGA", "bank pusty")

    # ---------------------------------------------------------------
    etap(11, "ZIELONE SWIATLO I SEDZIA")
    zielone = [k for k in zywi if k.get("zielone_swiatlo")]
    werdykt("dokladnie jedno zielone swiatlo",
            "OK" if len(zielone) == 1 else ("UWAGA" if not ocenieni else "BLAD"),
            "%d" % len(zielone))
    if zielone:
        z = zielone[0]
        print("  >> %s" % str(z.get("fact"))[:96])
        print("     kanal: %s | ranga: %s" % (z.get("kanal_zrodlowy"),
                                              z.get("ranga")))
        werdykt("zielone swiatlo ma range 0",
                "OK" if z.get("ranga") == 0 else "BLAD", str(z.get("ranga")))
    z_uzasadnieniem = [k for k in ocenieni if str(k.get("podobne_do") or "").strip()]
    if ocenieni:
        werdykt("sedzia porownuje ze zmierzonym odbiorem",
                "OK" if len(z_uzasadnieniem) >= len(ocenieni) * 0.5 else "UWAGA",
                "%d z %d ma pole `podobne_do`" % (len(z_uzasadnieniem),
                                                  len(ocenieni)))
    dowody = stages.co_zadzialalo()
    werdykt("sedzia dostaje prawdziwe pomiary",
            "OK" if "likes" in dowody and "THESE DID NOT" in dowody else "UWAGA",
            dowody[:40])
    # DOWODY DLA SEDZIEGO BANKU TEZ MUSZA BYC Z OBECNEJ EPOKI. Stalo tu jedno
    # slowo wpisane na sztywno; teraz pyta ta sama liste, co dwie kontrole
    # wyzej — inaczej wystarczylo, ze stara notka mowila o czym innym niz
    # akurat to jedno slowo, i przechodzila jako dowod „co dziala na tym
    # koncie".
    stare_w_dowodach = [s for s in slownik if s in dowody.lower()]
    werdykt("i sa one z obecnej epoki konta",
            "OK" if not stare_w_dowodach else "BLAD",
            ", ".join(stare_w_dowodach[:3]))

    # ---------------------------------------------------------------
    etap(12, "PROMPTY")
    korzen = KATALOG.parent
    w = subprocess.run([sys.executable, "agent-v2/tests/test_prompty_o_niszy.py"],
                       capture_output=True, text=True, cwd=str(korzen))
    werdykt("zaden prompt nie zawiera slowa z listy epoki przedmiotow",
            "OK" if w.returncode == 0 else "BLAD",
            (w.stdout or w.stderr)[-200:] if w.returncode else "")

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
