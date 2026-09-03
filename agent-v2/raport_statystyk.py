"""Co przyniosla kazda notka, restack i artykul — do czytania przez czlowieka.

Statystyki lezą w `data/statystyki.jsonl` jako historia pomiarow. Ten plik
zamienia je w tabele, ktora odpowiada na pytania wlasciciela:

    ile wejsc mial ten wpis
    ile polubien i komentarzy z tego wyszlo
    ilu ludzi z TEGO wpisu zaczelo subskrybowac albo obserwowac

DLACZEGO OSOBNY PLIK, A NIE WYDRUK W PRZEBIEGU: przebieg drukuje raz i ginie.
Licznik `zrobione` w run.py zyl dokladnie tak i przez dwa tygodnie nikt nie
wiedzial, ze polowa dzialan nie wychodzi. Raport ma dac sie odpalic kiedykolwiek,
bez przebiegu i bez przegladarki.

Uruchomienie:
    python agent-v2/raport_statystyk.py
    python agent-v2/raport_statystyk.py notka
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import statystyki  # noqa: E402


def _skrot(tekst: str, ile: int = 46) -> str:
    t = " ".join(str(tekst or "").split())
    return (t[: ile - 1] + "…") if len(t) > ile else t


# Dzien, w ktorym konto przestalo pisac o ukrytych systemach w zwyklych
# rzeczach, a zaczelo o AI. Wszystko starsze opisuje INNA publikacje i
# mieszanie tego z dzisiejszym stanem juz raz doprowadzilo do zlej decyzji.
PIVOT = "2026-08-25"

POLA = ("wyswietlenia", "polubienia", "odpowiedzi", "restacki",
        "subskrypcje", "obserwacje", "klikniecia_w_link")


def _mediana(liczby: list[int]) -> float:
    if not liczby:
        return 0.0
    s = sorted(liczby)
    n = len(s)
    return float(s[n // 2]) if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def dwie_epoki(najnowsze: dict) -> None:
    """Epoka AI osobno, epoka ukrytych systemow osobno.

    DZIELIMY PO DACIE WYSTAWIENIA, NIGDY PO DACIE POMIARU. Pole `zmierzone`
    mowi, kiedy PYTALISMY — a pytamy zawsze niedawno, takze o notki sprzed
    miesiaca. Podzial po nim daje dwie epoki, z ktorych jedna jest pusta; ta
    sama pomylka przepuscila juz raz filtr, ktory nie odfiltrowal niczego.

    `wystawione` dopisano do rekordu 31 sierpnia 2026. Pomiary starsze go nie
    maja i trafiaja do osobnej kolumny zamiast po cichu doliczyc sie do
    ktorejkolwiek epoki — bo doliczone po cichu skrzywilyby porownanie w
    strone, ktorej nie widac.
    """
    epoki: dict[str, list[dict]] = {"PRZED": [], "AI": [], "?": []}
    for r in najnowsze.values():
        data = str(r.get("wystawione") or "")[:10]
        if not data:
            epoki["?"].append(r)
        else:
            epoki["AI" if data >= PIVOT else "PRZED"].append(r)

    if not epoki["AI"] and not epoki["PRZED"]:
        print()
        print("PODZIAL NA EPOKI: zaden pomiar nie ma jeszcze daty wystawienia.")
        print("   Pole `wystawione` dopisano 31.08.2026 — pojawi sie przy")
        print("   nastepnym pomiarze kazdej pozycji.")
        return

    print()
    print("=" * 96)
    print("EPOKA AI (od %s) OSOBNO OD EPOKI UKRYTYCH SYSTEMOW" % PIVOT)
    print("=" * 96)
    if epoki["?"]:
        print("  bez daty wystawienia (pomiar sprzed 31.08): %d — NIE wliczone"
              " do zadnej epoki" % len(epoki["?"]))

    for rodzaj in sorted({str(r.get("rodzaj") or "?")
                          for r in najnowsze.values()}):
        wiersze = []
        for epoka in ("PRZED", "AI"):
            poz = [r for r in epoki[epoka]
                   if str(r.get("rodzaj") or "?") == rodzaj]
            if poz:
                wiersze.append((epoka, poz))
        if not wiersze:
            continue
        print()
        print("  %s" % rodzaj.upper())
        print("    %-8s %6s %10s %10s %10s %10s" % (
            "EPOKA", "ILE", "WEJSC", "MED.WEJSC", "POLUBIEN", "SUBSKR"))
        for epoka, poz in wiersze:
            wejscia = [int(r.get("wyswietlenia") or 0) for r in poz]
            print("    %-8s %6d %10d %10.1f %10d %10d" % (
                epoka, len(poz), sum(wejscia), _mediana(wejscia),
                sum(int(r.get("polubienia") or 0) for r in poz),
                sum(int(r.get("subskrypcje") or 0) for r in poz)))

    # POLA, KTORE NIGDY NIE DRGNELY. Pole zawsze zerowe wyglada w tabeli tak
    # samo jak pole, ktore po prostu dzis nic nie zebralo — a to zupelnie inna
    # informacja: pierwsze znaczy, ze mierzymy cos, czego nie dostajemy.
    martwe = [p for p in POLA
              if not any(int(r.get(p) or 0) for r in najnowsze.values())]
    if martwe:
        print()
        print("  MIERZONE, ALE ZAWSZE ZEROWE (we wszystkich epokach): %s"
              % ", ".join(martwe))

    print()
    print("  SKAD PRZYCHODZILY WEJSCIA, wg epoki:")
    for epoka in ("PRZED", "AI"):
        lic: dict[str, int] = {}
        for r in epoki[epoka]:
            for nazwa, ile in (r.get("powierzchnie") or {}).items():
                lic[str(nazwa)] = lic.get(str(nazwa), 0) + int(ile or 0)
        razem = sum(lic.values())
        if not razem:
            continue
        opis = ", ".join("%s %d (%d%%)" % (n, i, round(100 * i / razem))
                         for n, i in sorted(lic.items(), key=lambda x: -x[1])[:4])
        print("    %-6s %s" % (epoka, opis))


def wzrost_konta() -> None:
    """Ilu nas czyta i czy tego przybywa.

    To jedyna liczba, ktora mierzy CEL calego systemu wprost. Reszta raportu
    mowi, co przyniosl konkretny wpis; ta mowi, czy konto rosnie.

    Do 31 sierpnia 2026 nie byla nigdzie zapisywana — krzywa z panelu Substacka
    zyla wylacznie u Substacka.
    """
    import json as _json
    import browser as _browser

    if not _browser.WZROST.exists():
        return
    stany = []
    for linia in _browser.WZROST.read_text(encoding="utf-8").splitlines():
        linia = linia.strip()
        if not linia:
            continue
        try:
            w = _json.loads(linia)
        except ValueError:
            continue
        if isinstance(w, dict):
            stany.append(w)
    if not stany:
        return

    print()
    print("=" * 96)
    print("ILU NAS CZYTA")
    print("=" * 96)
    # Jeden wiersz na DZIEN, nie na pomiar: mierzymy kilka razy dziennie,
    # a krzywa dzienna jest tym, o co chodzi.
    po_dniach: dict[str, dict] = {}
    for w in stany:
        po_dniach[str(w.get("kiedy") or "")[:10]] = w
    dni = sorted(po_dniach)
    print("%-12s %13s %13s %13s" % (
        "DZIEN", "SUBSKRYBENCI", "OBSERWUJACY", "MY SUBSKR."))
    for d in dni[-14:]:
        w = po_dniach[d]
        print("%-12s %13d %13d %13d" % (
            d, int(w.get("subskrybenci") or 0),
            int(w.get("obserwujacy") or 0),
            int(w.get("nasze_subskrypcje") or 0)))
    if len(dni) >= 2:
        a, b = po_dniach[dni[0]], po_dniach[dni[-1]]
        print("-" * 96)
        print("OD %s DO %s: subskrybentow %+d, obserwujacych %+d"
              % (dni[0], dni[-1],
                 int(b.get("subskrybenci") or 0) - int(a.get("subskrybenci") or 0),
                 int(b.get("obserwujacy") or 0) - int(a.get("obserwujacy") or 0)))
    else:
        print()
        print("   To pierwszy zapis — przyrostu nie ma jeszcze z czego policzyc.")


def main() -> int:
    rodzaj = sys.argv[1] if len(sys.argv) > 1 else None

    najnowsze = statystyki.najnowsze_per_pozycja(rodzaj)
    if not najnowsze:
        print("Zadnych pomiarow jeszcze nie ma.")
        print()
        print("Statystyki zbieraja sie w cyklu dnia, razem z odpowiadaniem na")
        print("komentarze. Jesli plik jest pusty, a bot chodzi — sprawdz, czy")
        print("wystawione pozycje maja zapisane numery: bez numeru nie ma czego")
        print("pytac. Zmierzone 25 sierpnia: z 29 notek numer mialo szesc.")
        return 0

    # Sortujemy po tym, co wlasciciela interesuje najbardziej: ile osob z tego
    # zostalo. Przy remisie po zasiegu, bo to jedyna druga os, ktora mamy.
    pozycje = sorted(
        najnowsze.values(),
        key=lambda r: (r.get("subskrypcje", 0) + r.get("obserwacje", 0),
                       r.get("wyswietlenia", 0)),
        reverse=True,
    )

    print("=" * 96)
    print("CO PRZYNIOSLA KAZDA POZYCJA%s" % (
        "  (tylko: %s)" % rodzaj if rodzaj else ""))
    print("=" * 96)
    print("%-11s %-10s %6s %6s %5s %5s %5s  %s" % (
        "RODZAJ", "NUMER", "WEJSC", "POLUB", "KOM", "SUBS", "OBS", "TRESC"))
    print("-" * 96)
    for r in pozycje:
        print("%-11s %-10s %6s %6s %5s %5s %5s  %s" % (
            r.get("rodzaj", "?"),
            r.get("id", "?"),
            r.get("wyswietlenia", 0),
            r.get("polubienia", 0),
            r.get("odpowiedzi", 0),
            r.get("subskrypcje", 0),
            r.get("obserwacje", 0),
            _skrot(r.get("tekst", ""))))

    p = statystyki.podsumowanie(rodzaj)
    print("-" * 96)
    print("RAZEM  pozycji %s | wejsc %s | polubien %s | komentarzy %s | "
          "subskrypcji %s | obserwacji %s | klikniec w link %s" % (
              p.get("pozycje", 0), p.get("wyswietlenia", 0),
              p.get("polubienia", 0), p.get("odpowiedzi", 0),
              p.get("subskrypcje", 0), p.get("obserwacje", 0),
              p.get("klikniecia_w_link", 0)))
    print("SREDNIO wejsc na pozycje: %s   (pomiarow w pliku: %s)" % (
        p.get("srednia_wyswietlen", 0), p.get("pomiary", 0)))

    # OSTRZEZENIE O ROZJEZDZIE. Substack podaje wlasna sume interakcji; my
    # sumujemy pozycje z listy. Gdy te dwie liczby sie roznia, znaczy to, ze
    # pojawil sie rodzaj interakcji, ktorego nie rozpoznajemy — czyli ze konto
    # dostaje sygnal, ktorego nie widzimy. Bez tego wydruku liczba byla
    # wyliczana i wyrzucana.
    _od_substacka = p.get("interakcje_razem", 0)
    _z_pozycji = p.get("interakcje_z_pozycji", 0)
    if _od_substacka != _z_pozycji:
        print()
        print("UWAGA: Substack liczy %s interakcji, a z rozpoznanych pozycji "
              "wychodzi %s." % (_od_substacka, _z_pozycji))
        print("       Roznica %s znaczy nowy rodzaj interakcji, ktorego nie "
              "nazywamy po imieniu." % abs(_od_substacka - _z_pozycji))
    naj = p.get("najlepsza")
    if naj:
        print("NAJLEPSZA: %s %s — %s wejsc, %s subskrypcji" % (
            naj.get("rodzaj", "?"), naj.get("id", "?"),
            naj.get("wyswietlenia", 0), naj.get("subskrypcje", 0)))
        print("           %s" % _skrot(naj.get("tekst", ""), 80))

    # Skad ludzie w ogole trafiaja — to decyduje, czy warto pisac wiecej notek,
    # czy raczej komentowac u innych.
    powierzchnie: dict[str, int] = {}
    for r in najnowsze.values():
        for nazwa, ile in (r.get("powierzchnie") or {}).items():
            powierzchnie[nazwa] = powierzchnie.get(nazwa, 0) + int(ile or 0)
    if powierzchnie:
        print()
        print("SKAD PRZYCHODZA WEJSCIA:")
        for nazwa, ile in sorted(powierzchnie.items(), key=lambda x: -x[1]):
            print("   %-16s %s" % (nazwa, ile))

    dwie_epoki(najnowsze)
    wzrost_konta()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
