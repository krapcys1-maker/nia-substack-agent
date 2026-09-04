"""Jednorazowe uzupelnienie pola `dodane` w kolejce promocji.

DLACZEGO. `artykul_do_promocji` dostalo okno waznosci (config.OKNO_PROMOCJI_DNI):
artykul przestaje byc promowany po tygodniu, nawet jesli nie wybral swoich
trzech notek. Okno mierzy sie od pola `dodane`, ktorego wpisy sprzed tej zmiany
nie maja — a wpis bez `dodane` jest z definicji traktowany jak przeterminowany.

Bez tej migracji ucierpialby WLASNIE swiezy artykul: „Example Article One
Verdict" trafil do kolejki 25 sierpnia, jeszcze starym zapisem, wiec nazajutrz
przestalby byc promowany po pierwszej z trzech notek.

SKAD BIERZEMY DATE. Z dziennika, nie z sufitu. Kazda udana publikacja artykulu
zostawia tam wpis z tytulem i znacznikiem czasu, wiec date publikacji mamy
zapisana faktem. Dopasowujemy po tytule, bo dziennik nie notuje adresu.

Wpis, dla ktorego dziennik nic nie wie, zostaje BEZ `dodane` — czyli
przeterminowany. To wybor swiadomy: brak dowodu na swiezosc nie jest dowodem
swiezosci, a jedyny koszt bledu to niewystawiona notka promujaca stary tekst.

Uruchamiac raz. Powtorne uruchomienie niczego nie psuje — wpisy, ktore juz maja
`dodane`, sa pomijane.

NA SWIEZEJ INSTALACJI TEN PLIK NIE MA CO ROBIC i mowi to wprost: kolejka
promocji jest wtedy pusta, a kazdy nowy wpis dostaje `dodane` od razu. Zostaje
w repozytorium jako zapis TEGO, CO SIE STALO — schemat zmienil sie w locie
i istniejace wpisy trzeba bylo uzupelnic z dziennika, a nie z sufitu. Nastepna
zmiana schematu w tym miejscu ma wygladac tak samo: date bierze sie z faktu,
brak dowodu na swiezosc nie jest dowodem swiezosci.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import stages  # noqa: E402

# SCIEZKA Z `config.DATA_DIR`, NIE SKLEJANA Z `__file__`. Stalo tu
# `Path(__file__).parent / "data" / "dziennik.jsonl"` — czwarty sposob na
# policzenie tej samej sciezki i JEDYNY, ktory nie idzie za `DATA_DIR`.
# Skutek jest dokladnie ten, ktory opisuje `db._odmow_produkcji`: test albo
# narzedzie podstawiajace katalog danych przez `config.uzyj_katalogu_danych`
# przestawia `browser.DZIENNIK` i `norma.DZIENNIK`, a ten plik dalej czyta
# PRODUKCJE. Wartosc jest dzis ta sama, wiec nic nie pekalo — i wlasnie
# dlatego nikt tego nie widzial.
DZIENNIK = config.DATA_DIR / "dziennik.jsonl"


def daty_publikacji() -> dict[str, str]:
    """Tytul artykulu -> data pierwszej udanej publikacji (YYYY-MM-DD)."""
    daty: dict[str, str] = {}
    if not DZIENNIK.exists():
        return daty
    with DZIENNIK.open(encoding="utf-8") as plik:
        for linia in plik:
            linia = linia.strip()
            if not linia:
                continue
            try:
                wpis = json.loads(linia)
            except ValueError:
                continue
            if not isinstance(wpis, dict):
                continue
            if wpis.get("rodzaj") != "artykul" or not wpis.get("udane"):
                continue
            tytul = str(wpis.get("tytul") or "").strip()
            kiedy = str(wpis.get("kiedy") or "")[:10]
            if not tytul or not kiedy:
                continue
            # Pierwsza publikacja, nie ostatnia — artykul moze wrocic w
            # dzienniku przy ponowieniu, a okno liczy sie od premiery.
            daty.setdefault(tytul, kiedy)
    return daty


def main() -> int:
    kolejka = stages.wczytaj_promocje()
    if not kolejka:
        print("kolejka promocji pusta — nic do zrobienia")
        return 0

    daty = daty_publikacji()
    zmienione = 0
    for wpis in kolejka:
        if wpis.get("dodane"):
            continue
        tytul = str(wpis.get("tytul") or "").strip()
        data = daty.get(tytul)
        if data:
            wpis["dodane"] = data
            zmienione += 1
            print("  + %-58s dodane=%s" % (tytul[:58], data))
        else:
            print("  - %-58s BRAK w dzienniku -> zostaje przeterminowany"
                  % tytul[:58])

    if zmienione:
        stages.PROMOCJA.write_text(
            json.dumps(kolejka, ensure_ascii=False, indent=1),
            encoding="utf-8")
    print("uzupelnione: %d z %d wpisow" % (zmienione, len(kolejka)))

    print()
    print("kto bylby dzis promowany:")
    wybrany = stages.artykul_do_promocji()
    print("  %s" % (wybrany["tytul"] if wybrany else "(nikt)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
