"""Kopia listy subskrybentow — jedyne aktywo, ktorego nie da sie odtworzyc.

Teksty, karty dowodowe, okladki i cala historia kosztow powstaja lokalnie
i leza w gicie. Lista subskrybentow nie: zyje wylacznie u Substacka. Przy
zmierzonym tempie okolo 2,2 nowego subskrybenta miesiecznie sto osob na liscie
to okolo czterdziestu pieciu miesiecy pracy systemu, a regulamin pozwala
zamknac konto natychmiast i w wylacznej ocenie Substacka.

`SUBSKRYPCJE_MIESIECZNIE` (12-20) NIE JEST TU MNOZNIKIEM i dwa razy juz nim
bylo przez pomylke: ta stala liczy subskrypcje, ktore MY klikamy CUDZYM
publikacjom, a ten plik wycenia liste osob, ktore subskrybuja NAS. Podzielenie
stu przez nasze wyjscia dawalo „6,25 miesiaca" — siedem razy za malo.

## Jak to sie pobiera

OD 23 SIERPNIA SAMO, i to jest sprostowanie do tego, co stalo tu wczesniej.
`browser.pobierz_subskrybentow` czyta liste z WLASNEGO panelu wlasna sesja —
ta sama przegladarka i ta sama droga, ktora agent wystawia notki. Zamysl calego
systemu to zero dotyku, a eksport raz na dwa tygodnie byl jedynym miejscem,
gdzie wlasciciel musial cos kliknac.

Reczny eksport ZOSTAJE jako droga zapasowa: gdy panel zmieni uklad albo lista
nie da sie odczytac w calosci, skrypt mowi o tym wprost i czeka na plik.

## Czego dalej NIE robimy

Nie zgadujemy adresow API. `/api/v1/subscriber/csv` i dwa podobne zwracaja
404, a `/api/v1/subscriptions/page_v2`, ktorego uzywa panel, oddaje NASZE
SUBSKRYPCJE — publikacje, ktore my obserwujemy — a nie naszych subskrybentow;
widac to po `publication_id: 1`, czyli publikacji samego Substacka.

Powtarzane sondowanie nieudokumentowanych adresow to jest to, co regulamin
nazywa scrapingiem. Czytanie WLASNEGO panelu wlasna sesja nie jest — to jest
wlasciciel patrzacy na wlasne konto, tak samo jak przy publikowaniu notki.
Roznica jest realna i przebiega dokladnie tedy: zadnego cudzego konta, zadnego
omijania limitow, zadnego adresu, ktorego panel sam by nie odpytal.

## Jak zrobic kopie

Automatycznie:  python agent-v2/kopia_subskrybentow.py
(agent robi to sam co `config.KOPIA_SUBSKRYBENTOW_CO_ILE_DNI` dni)

Recznie, gdy automat odmowi:
1. Dashboard -> Subscribers -> menu (trzy kropki) -> Export
2. Zapisz plik do `agent-v2/data/kopie/przychodzace/`
3. Uruchom:  python agent-v2/kopia_subskrybentow.py

Skrypt oznaczy plik data, sprawdzi, czy to naprawde CSV z adresami, policzy
wiersze i porowna z poprzednia kopia. Spadek liczby subskrybentow o wiecej
niz `ALARM_SPADEK` procent jest zglaszany — bo to albo utrata konta, albo
uszkodzony eksport, i obie rzeczy trzeba zobaczyc od razu.
"""
from __future__ import annotations

import csv
import io
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config    # noqa: E402

KATALOG = config.DATA_DIR / "kopie"
PRZYCHODZACE = KATALOG / "przychodzace"
ILE_KOPII = 30
ALARM_SPADEK = 20        # procent


def _wierszy(tekst: str) -> int:
    return sum(1 for w in csv.reader(io.StringIO(tekst)) if any(p.strip() for p in w)) - 1


def _to_lista_subskrybentow(tekst: str) -> tuple[bool, str]:
    """Czy to naprawde eksport listy, a nie przypadkowy plik albo strona HTML."""
    if "<html" in tekst[:400].lower():
        return False, "to jest strona HTML, nie CSV — pewnie eksport sie nie udal"
    pierwsza = (tekst.splitlines() or [""])[0].lower()
    if "," not in pierwsza:
        return False, "pierwszy wiersz nie wyglada na naglowek CSV"
    if "email" not in pierwsza:
        return False, ("naglowek nie zawiera kolumny 'email': %s" % pierwsza[:90])
    return True, ""


def pobierz_z_panelu() -> tuple[bool, str]:
    """Sciaga liste z wlasnego panelu i zapisuje ja jako CSV do `przychodzace/`.

    CELOWO oddaje plik do tego samego katalogu, ktory obsluguje reczny eksport.
    Dzieki temu automat i czlowiek ida DALEJ TA SAMA DROGA: ta sama walidacja
    naglowka, to samo porownanie z poprzednia kopia, ten sam alarm przy spadku
    i te same prawa 0600. Druga sciezka zapisu znaczylaby druga sciezke, na
    ktorej cos moze pojsc inaczej.

    NIEPELNA LISTA NIE JEST ZAPISYWANA. Kopia, ktora wyglada na komplet, a jest
    polowa, jest grozniejsza niz brak kopii — przy odtwarzaniu konta nikt nie
    sprawdza, czy plik byl pelny; sprawdza sie, czy w ogole jest.
    """
    try:
        import browser
    except Exception as exc:
        return False, "nie moge uzyc przegladarki: %s" % type(exc).__name__

    print("  pobieram z panelu wlasna sesja...")
    try:
        wynik = browser.pobierz_subskrybentow()
    except Exception as exc:
        return False, "%s: %s" % (type(exc).__name__, str(exc)[:120])

    wiersze = wynik.get("wiersze") or []
    if not wynik.get("kompletna"):
        return False, (wynik.get("powod")
                       or "panel nie potwierdzil, ze to cala lista")
    if not wiersze:
        return False, "panel nie oddal ani jednego adresu"

    PRZYCHODZACE.mkdir(parents=True, exist_ok=True)
    cel = PRZYCHODZACE / ("z-panelu-%s.csv"
                          % datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S"))
    with open(cel, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Email", "Type", "Start date"])
        for r in wiersze:
            w.writerow([r.get("email", ""), r.get("typ", ""), r.get("od", "")])
    return True, "%d adresow z panelu" % len(wiersze)


def main() -> int:
    PRZYCHODZACE.mkdir(parents=True, exist_ok=True)
    if not sorted(PRZYCHODZACE.glob("*.csv")):
        # Automat pierwszy. Gdy odmowi, mowi DLACZEGO i schodzimy na reczna
        # droge — cicha porazka automatu bylaby najgorszym wariantem, bo
        # wlasciciel przestalby robic eksport, wierzac, ze agent go robi.
        ok, powod = pobierz_z_panelu()
        print("  %s: %s" % ("pobrane" if ok else "NIE POBRALEM automatycznie", powod))
    nowe = sorted(PRZYCHODZACE.glob("*.csv"))
    if not nowe:
        print("== kopia listy subskrybentow ==")
        print()
        print("  Nie ma czego zarchiwizowac. Zrob eksport recznie:")
        print("    1. Dashboard -> Subscribers -> menu -> Export")
        print("    2. Zapisz plik do: %s" % PRZYCHODZACE)
        print("    3. Uruchom ten skrypt jeszcze raz")
        print()
        print("  Powod, dla ktorego to nie chodzi samo, stoi w naglowku pliku:")
        print("  nie ma udokumentowanego endpointu, a zgadywanie adresow to")
        print("  scraping — czyli dokladnie to, przed czym ta kopia ma chronic.")
        return 1

    KATALOG.mkdir(parents=True, exist_ok=True)
    poprzednie = sorted(KATALOG.glob("subskrybenci-*.csv"))
    ostatnia = _wierszy(poprzednie[-1].read_text(encoding="utf-8")) if poprzednie else None

    wynik = 0
    for plik in nowe:
        tekst = plik.read_text(encoding="utf-8", errors="replace")
        ok, powod = _to_lista_subskrybentow(tekst)
        if not ok:
            print("  ODRZUCONY %s — %s" % (plik.name, powod))
            wynik = 1
            continue
        ile = _wierszy(tekst)
        dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cel = KATALOG / ("subskrybenci-%s.csv" % dzis)
        cel.write_text(tekst, encoding="utf-8")
        # TYLKO WLASCICIEL. To sa cudze adresy e-mail, a domyslne prawa na
        # serwerze to 0664 — czytelne dla kazdego konta na maszynie. Ta sama
        # klasa niedopatrzenia co sesja przegladarki zapisana z 0644.
        # Ustawiamy przy KAZDYM zapisie, nie raz recznie, bo recznie znaczy
        # „przy pierwszej kopii", a kopii ma byc trzydziesci.
        try:
            cel.chmod(0o600)
        except OSError:
            # Windows nie ma tych praw i to nie jest powod, zeby stracic kopie.
            pass
        plik.unlink()
        print("  ZAPISANE: %s   %d subskrybentow" % (cel.name, ile))
        if ostatnia is not None:
            zmiana = ile - ostatnia
            print("  poprzednio: %d   zmiana: %+d" % (ostatnia, zmiana))
            if ostatnia > 0 and zmiana < 0 and abs(zmiana) * 100 / ostatnia > ALARM_SPADEK:
                print("  !! SPADEK O %.0f%% — albo utrata konta, albo uszkodzony"
                      " eksport. Sprawdz, zanim nadpiszesz stara kopie."
                      % (abs(zmiana) * 100 / ostatnia))
                wynik = 1
        ostatnia = ile

    kopie = sorted(KATALOG.glob("subskrybenci-*.csv"))
    for x in kopie[:-ILE_KOPII]:
        x.unlink()
        print("  usunieta stara kopia: %s" % x.name)
    print("  kopii w katalogu: %d" % len(sorted(KATALOG.glob("subskrybenci-*.csv"))))
    print()
    print("  UWAGA: te pliki zawieraja cudze adresy e-mail. Katalog `data/`")
    print("  jest poza gitem i ma tam zostac — kopie trzymaj u siebie, nie")
    print("  w publicznym repozytorium.")
    return wynik


if __name__ == "__main__":
    sys.exit(main())
