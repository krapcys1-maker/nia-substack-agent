# -*- coding: utf-8 -*-
"""Slepa proba glosu: „ktory z trzech nie jest z wzorca?"

## Po co

Wlasciciel jest jedyna instancja, ktora wie, czy tekst brzmi jak NIA — jego
werdykty sa definicja tego glosu. Ale czytanie nowego tekstu z etykieta
„nowy" nie jest testem, tylko recenzja. Test jest wtedy, gdy nowy tekst lezy
obok dwoch przyjetych i nie wiadomo, ktory jest ktory. Jesli wlasciciel nie
umie wskazac nowego, glos sie utrzymal. Jesli wskazuje go za kazdym razem,
cos go zdradza — i wtedy warto policzyc `odcisk_glosu.py --zdania`.

Ta sama zasada, co w `tests/platne/test_slepa_ocena_notek.py`: mieszamy,
zdejmujemy etykiety, klucz lezy w osobnym pliku i czyta sie go PO ocenie.

## Uzycie (z korzenia repozytorium)

  python narzedzia/slepa_proba_glosu.py --kandydaci PLIK [PLIK ...] [--forma notka]
      wypisuje ponumerowane zestawy po trzy teksty (A/B/C) i zapisuje klucz
  python narzedzia/slepa_proba_glosu.py --z-instancji 5
      kandydaci = piec ostatnich szkicow notek aktywnej instancji
  python narzedzia/slepa_proba_glosu.py --odpowiedzi KLUCZ.json 1=B 2=A 3=C
      ocena odpowiedzi wlasciciela; werdykty dopisuja sie do `glos-werdykty.jsonl`
      w katalogu danych instancji (albo obok klucza, gdy presetu nie ma)

  --wzorzec KATALOG   inny wzorzec niz `styl/wzorzec` aktywnego presetu
  --ziarno N          powtarzalne losowanie (domyslnie z zegara)
  --wyjscie KATALOG   gdzie zapisac klucz (domyslnie `glos-slepa-proba/` w danych instancji)

Bez sieci i bez wywolan modelu. Nie publikuje niczego.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import odcisk_glosu  # noqa: E402

LITERY = ("A", "B", "C")


def zestawy(probki: list[dict], kandydaci: list[dict], forma: str, rng: random.Random) -> list[dict]:
    """Dla kazdego kandydata: dwie losowe probki wzorca tej formy plus kandydat, w losowej kolejnosci."""
    wzor = [p for p in probki if p["forma"] == forma]
    if len(wzor) < 2:
        raise ValueError("wzorzec ma mniej niz dwie probki formy %r" % forma)
    wynik = []
    for nr, k in enumerate(kandydaci, 1):
        para = rng.sample(wzor, 2)
        teksty = [{"tekst": para[0]["tekst"], "wzorzec": True, "nazwa": para[0]["tytul"]},
                  {"tekst": para[1]["tekst"], "wzorzec": True, "nazwa": para[1]["tytul"]},
                  {"tekst": k["tekst"], "wzorzec": False, "nazwa": k["nazwa"]}]
        rng.shuffle(teksty)
        litera = next(LITERY[i] for i, t in enumerate(teksty) if not t["wzorzec"])
        wynik.append({"zestaw": nr, "forma": forma, "teksty": teksty, "kandydat": litera,
                      "kandydat_nazwa": k["nazwa"]})
    return wynik


def arkusz(zest: list[dict]) -> str:
    """Tekst do czytania: bez nazw, bez etykiet, bez klucza."""
    linie = ["SLEPA PROBA GLOSU — w kazdym zestawie DWA teksty sa z wzorca, JEDEN nie.",
             "Wskaz ten, ktory nie jest z wzorca. Odpowiedz: numer=litera, np. 1=B.", ""]
    for z in zest:
        linie.append("=" * 72)
        linie.append("ZESTAW %d  (%s)" % (z["zestaw"], z["forma"]))
        for litera, t in zip(LITERY, z["teksty"]):
            linie.append("")
            linie.append("--- %s ---" % litera)
            linie.append(t["tekst"])
        linie.append("")
    return "\n".join(linie)


def ocen_odpowiedzi(klucz: dict, odpowiedzi: dict[int, str]) -> list[dict]:
    wynik = []
    for z in klucz["zestawy"]:
        wskazany = odpowiedzi.get(z["zestaw"])
        wynik.append({"zestaw": z["zestaw"], "wskazany": wskazany, "poprawny": z["kandydat"],
                      "rozpoznany": wskazany == z["kandydat"], "kandydat": z["kandydat_nazwa"],
                      "forma": z["forma"]})
    return wynik


def _parsuj_odpowiedzi(napisy: list[str]) -> dict[int, str]:
    wynik = {}
    for n in napisy:
        nr, _, litera = n.partition("=")
        litera = litera.strip().upper()
        if not nr.strip().isdigit() or litera not in LITERY:
            raise ValueError("odpowiedz w formie numer=litera, np. 2=B, a nie %r" % n)
        wynik[int(nr)] = litera
    return wynik


def _kandydaci_z_plikow(pliki: list[str], forma: str) -> list[dict]:
    wynik = []
    for nazwa in pliki:
        p = Path(nazwa)
        surowy = p.read_text(encoding="utf-8")
        tekst = odcisk_glosu.cialo_artykulu(surowy)[2] if forma == "artykul" else odcisk_glosu.tekst_probki(surowy)
        wynik.append({"nazwa": p.name, "tekst": tekst})
    return wynik


def _kandydaci_z_instancji(ile: int) -> list[dict]:
    rekordy = [r for r in odcisk_glosu.teksty_z_instancji(0) if r["forma"] == "notka"]
    return [{"nazwa": r["nazwa"], "tekst": r["tekst"]} for r in rekordy[-ile:]]


def _katalog_wyjscia(podany: str | None, klucz: Path | None = None) -> Path:
    if podany:
        return Path(podany)
    try:
        import config                                             # noqa: PLC0415
        return Path(config.DATA_DIR) / "glos-slepa-proba"
    except Exception:                                             # noqa: BLE001
        return klucz.parent if klucz else Path("glos-slepa-proba")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Slepa proba glosu: ktory z trzech nie jest z wzorca.")
    parser.add_argument("--kandydaci", nargs="*", default=[], help="pliki z tekstami do sprawdzenia")
    parser.add_argument("--z-instancji", type=int, default=0, help="ile ostatnich szkicow notek instancji wziac za kandydatow")
    parser.add_argument("--forma", choices=odcisk_glosu.FORMY, default="notka")
    parser.add_argument("--wzorzec", help="katalog wzorca")
    parser.add_argument("--ziarno", type=int, help="ziarno losowania")
    parser.add_argument("--wyjscie", help="katalog na klucz i arkusz")
    parser.add_argument("--odpowiedzi", nargs="+", metavar="ARG",
                        help="KLUCZ.json i odpowiedzi numer=litera")
    args = parser.parse_args(argv)

    if args.odpowiedzi:
        klucz_plik = Path(args.odpowiedzi[0])
        klucz = json.loads(klucz_plik.read_text(encoding="utf-8"))
        odpowiedzi = _parsuj_odpowiedzi(args.odpowiedzi[1:])
        wyniki = ocen_odpowiedzi(klucz, odpowiedzi)
        rozpoznane = sum(1 for w in wyniki if w["rozpoznany"])
        print("kandydat rozpoznany jako obcy w %d z %d zestawow" % (rozpoznane, len(wyniki)))
        print("(im mniej rozpoznan, tym lepiej glos sie trzyma; losowe zgadywanie daje okolo 1 na 3)")
        for w in wyniki:
            print("  zestaw %d: wskazano %s, kandydat byl %s -> %s  (%s)" % (
                w["zestaw"], w["wskazany"] or "-", w["poprawny"],
                "rozpoznany" if w["rozpoznany"] else "NIEROZPOZNANY", w["kandydat"]))
        katalog = _katalog_wyjscia(args.wyjscie, klucz_plik)
        katalog.mkdir(parents=True, exist_ok=True)
        dziennik = katalog / "glos-werdykty.jsonl"
        teraz = datetime.now(timezone.utc).isoformat()
        with dziennik.open("a", encoding="utf-8") as f:
            for w in wyniki:
                f.write(json.dumps({"at": teraz, "klucz": klucz_plik.name, **w}, ensure_ascii=False) + "\n")
        print("werdykty dopisane do %s" % dziennik)
        return 0

    katalog_wzorca = Path(args.wzorzec) if args.wzorzec else odcisk_glosu._katalog_wzorca_z_presetu()
    if katalog_wzorca is None or not katalog_wzorca.is_dir():
        parser.error("nie znajduje wzorca: podaj --wzorzec KATALOG albo podlacz preset ze `styl/wzorzec/`")
    probki = odcisk_glosu.wczytaj_wzorzec(katalog_wzorca)
    kandydaci = _kandydaci_z_plikow(args.kandydaci, args.forma)
    if args.z_instancji:
        kandydaci += _kandydaci_z_instancji(args.z_instancji)
    if not kandydaci:
        parser.error("podaj --kandydaci PLIK... albo --z-instancji N")
    rng = random.Random(args.ziarno)
    zest = zestawy(probki, kandydaci, args.forma, rng)

    katalog = _katalog_wyjscia(args.wyjscie)
    katalog.mkdir(parents=True, exist_ok=True)
    znacznik = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    klucz_plik = katalog / ("%s.klucz.json" % znacznik)
    arkusz_plik = katalog / ("%s.arkusz.txt" % znacznik)
    klucz_plik.write_text(json.dumps({"schema": 1, "utworzono": znacznik, "forma": args.forma,
                                      "zestawy": [{k: v for k, v in z.items() if k != "teksty"} for z in zest]},
                                     ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tekst = arkusz(zest)
    arkusz_plik.write_text(tekst + "\n", encoding="utf-8")
    print(tekst)
    print("arkusz: %s" % arkusz_plik)
    print("klucz (NIE czytac przed ocena): %s" % klucz_plik)
    print("ocena: python narzedzia/slepa_proba_glosu.py --odpowiedzi %s 1=A 2=B ..." % klucz_plik)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
