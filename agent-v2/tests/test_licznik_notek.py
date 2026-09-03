"""Licznik notek liczy WLASNE notki, nie cudze.

CO SIE STALO. Przez pietnascie dni bot wystawial 2,9 notki dziennie przy
normie piec — 57 procent. Wlasciciel opisal to jako dwa fakty: „dopisywalem
tam notki" oraz „widze, ze on prawie nic notek nie dal". To byl jeden fakt.

`ile_dzis_wystawione` liczylo notki z KANALU PROFILU, na zasadzie
„rzeczywistosc jest lepszym zrodlem niz wlasna ksiegowosc". Zalozenie pod tym
brzmialo: na tym profilu publikuje wylacznie bot. Nieprawda — wlasciciel pisze
recznie, a kanal nie odroznia jego notek od naszych.

ZMIERZONE NA ZYWO 30 sierpnia 2026:
  29 sierpnia: kanal pokazywal 5 notek, z czego 2 byly bota,
  28 sierpnia: kanal pokazywal 6 notek, z czego 1 byla bota.
Licznik meldowal „dzienny przydzial juz wyczerpany" i przebieg konczyl sie
zerem notek. Kazda notka wlasciciela po cichu kasowala jedna notke bota.

CZEGO PILNUJE TEN TEST. Ze zrodlem decyzji jest DZIENNIK — jedyny zapis, w
ktorym atrybucja jest z definicji poprawna, bo dziennik notuje wylacznie
wlasne dzialania. Odczyt z Substacka ma zostac, ale wylacznie jako kontrola,
ktora GLOSNO melduje roznice zamiast po cichu zabierac przydzial.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


import browser   # noqa: E402
from datetime import datetime, timezone   # noqa: E402

DZIS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
KAT = pathlib.Path(tempfile.mkdtemp())
ORYG = browser.DZIENNIK


def zapisz(*wpisy):
    plik = KAT / "dziennik.jsonl"
    plik.write_text(
        "\n".join(json.dumps(w, ensure_ascii=False) for w in wpisy),
        encoding="utf-8")
    browser.DZIENNIK = plik


def wpis(rodzaj, udane=True, tekst="x"):
    return {"kiedy": DZIS, "rodzaj": rodzaj, "udane": udane, "tekst": tekst}


try:
    print("=== 1. DZIENNIK LICZY TERAZ TAKZE NOTKI ===")
    zapisz(wpis("notka"), wpis("notka"), wpis("komentarz"),
           wpis("polubienie"), wpis("restack"))
    ile = browser.z_dziennika_dzis()
    sprawdz("notki sa w wyniku", "notki" in ile, sorted(ile))
    sprawdz("policzone poprawnie", ile.get("notki") == 2, ile)
    sprawdz("pozostale kategorie nietkniete",
            (ile.get("komentarze"), ile.get("lajki"), ile.get("restacki"))
            == (1, 1, 1), ile)

    print()
    print("=== 2. NIEUDANE PROBY SIE NIE LICZA ===")
    # Notka, ktora nie wyszla, nie zajmuje miejsca w normie — inaczej awaria
    # przegladarki kasowalaby przydzial tak samo jak publikacja.
    zapisz(wpis("notka"), wpis("notka", udane=False))
    sprawdz("liczymy tylko udane",
            browser.z_dziennika_dzis().get("notki") == 1,
            browser.z_dziennika_dzis())

    print()
    print("=== 3. WCZORAJSZE NOTKI NIE ZAJMUJA DZISIEJSZEJ NORMY ===")
    zapisz(wpis("notka"),
           {"kiedy": "2026-01-01T10:00:00+00:00", "rodzaj": "notka",
            "udane": True, "tekst": "stara"})
    sprawdz("liczymy tylko dzisiejsze",
            browser.z_dziennika_dzis().get("notki") == 1,
            browser.z_dziennika_dzis())

    print()
    print("=== 4. ZRODLEM DECYZJI JEST DZIENNIK, NIE KANAL PROFILU ===")
    src = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
    poczatek = src.find("def ile_dzis_wystawione")
    ciało = src[poczatek:poczatek + 3000]

    sprawdz("wynik startuje z dziennika",
            "wynik = z_dziennika_dzis()" in ciało, ciało[:200])
    # KONTRDOWOD: przed poprawka bylo `wynik = {"notki": 0, **z_dziennika_dzis()}`
    # i petla dopisywala do `wynik["notki"]`. Gdyby to zostalo, ponizsze przejdzie.
    sprawdz("kanal NIE dopisuje juz do wyniku",
            'wynik["notki"] += 1' not in ciało,
            "stara linia nadal obecna")
    sprawdz("kanal liczy do osobnej zmiennej kontrolnej",
            "na_profilu += 1" in ciało, ciało[-400:])
    sprawdz("roznica jest MELDOWANA, nie zjadana",
            "praca reczna" in ciało, ciało[-500:])

    print()
    print("=== 5. FILTR TYPU JAK W POZOSTALYCH TRZECH MIEJSCACH ===")
    # Trzy inne miejsca pytaja ten sam endpoint z filtrem. To jedno go nie mialo
    # — nie to bylo przyczyna 57 procent, ale rozjazd nie ma po co zostawac.
    sprawdz("zapytanie ma types[]=note", "types%5B%5D=note" in ciało)
    # Sprawdzamy REGULE, nie sume wystapien: filtr pojawia sie tez w komentarzu
    # objasniajacym, wiec liczenie wystapien dawalo 4 zapytania i 5 filtrow.
    # Kazde ZAPYTANIE ma miec filtr w tej samej albo nastepnej linii.
    linie = src.splitlines()
    bez_filtra = []
    for i, l in enumerate(linie):
        if "reader/feed/profile" not in l:
            continue
        okno = " ".join(linie[i:i + 2])
        if "types%5B%5D=note" not in okno:
            bez_filtra.append(i + 1)
    sprawdz("kazde zapytanie o kanal profilu ma filtr typu",
            not bez_filtra, "linie bez filtra: %s" % bez_filtra)
finally:
    browser.DZIENNIK = ORYG

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
