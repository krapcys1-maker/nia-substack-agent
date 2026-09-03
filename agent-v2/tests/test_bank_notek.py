"""Bank notek: piszemy, gdy mamy material, wystawiamy, gdy jest dobra pora."""
import sys, pathlib, tempfile, json
sys.path.insert(0, "agent-v2")
import config   # noqa: E402
# KATALOG DANYCH PRZESTAWIAMY GLOBALNIE — i dlatego oddajemy go w `finally`.
# Bez tego kazdy proces, ktory uruchomi ten plik razem z innymi (chocby
# `pytest agent-v2/tests`), zostaje z `config.DATA_DIR` wskazujacym na katalog
# tymczasowy tego testu, a nastepny test pisze albo czyta nie tam, gdzie mysli.
_ZDJECIE_SCIEZEK = config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
import stages   # noqa: E402
_ORYG_BANK = stages.BANK_NOTEK
stages.BANK_NOTEK = config.DATA_DIR / "bank_notek.json"

zdane = oblane = 0
def sprawdz(n, w, s=""):
    global zdane, oblane
    if w: zdane += 1; print("  OK    %s" % n)
    else: oblane += 1; print("  BLAD  %s   %s" % (n, s))

try:
    print("=== 1. PUSTY BANK NIE WYWALA ===")
    sprawdz("pusty bank to pusta lista", stages.wczytaj_bank_notek() == [])
    sprawdz("z pustego nic nie wyjmiemy", stages.wez_z_banku_notek(3) == [])
    sprawdz("stan pustego", stages.stan_banku_notek() == {"razem": 0, "wolne": 0, "wyjete": 0})

    print()
    print("=== 2. DOKLADANIE I ODPORNOSC NA DUPLIKATY ===")
    n1 = [{"tekst": "Pierwsza notka o czyms.", "forma": "LICZBA", "zrodlo": "a.gov"},
          {"tekst": "Druga notka o czyms innym.", "forma": "SCENA", "zrodlo": "b.org"}]
    sprawdz("dodano dwie", stages.dopisz_do_banku_notek(n1) == 2)
    sprawdz("te same dwie nie dodaja sie drugi raz",
            stages.dopisz_do_banku_notek(n1) == 0)
    sprawdz("bank ma dwie", stages.stan_banku_notek()["wolne"] == 2)
    sprawdz("notka bez tekstu odrzucona",
            stages.dopisz_do_banku_notek([{"forma": "X"}, {"tekst": "   "}]) == 0)

    print()
    print("=== 3. WYJMOWANIE ZNACZY OD RAZU (kontrdowod: podwojne wystawienie) ===")
    a = stages.wez_z_banku_notek(1)
    sprawdz("wyjeto jedna", len(a) == 1 and a[0]["tekst"].startswith("Pierwsza"))
    b = stages.wez_z_banku_notek(1)
    sprawdz("druga proba daje INNA notke, nie te sama",
            len(b) == 1 and b[0]["tekst"] != a[0]["tekst"], b)
    c = stages.wez_z_banku_notek(1)
    sprawdz("trzecia proba nie daje nic — zapas wyczerpany", c == [], c)
    sprawdz("stan: dwie wyjete, zero wolnych",
            stages.stan_banku_notek() == {"razem": 2, "wolne": 0, "wyjete": 2},
            stages.stan_banku_notek())

    print()
    print("=== 4. ZNACZNIK PRZEZYWA ZAPIS NA DYSK ===")
    surowe = json.loads(stages.BANK_NOTEK.read_text(encoding="utf-8"))
    sprawdz("obie maja znacznik wyjeta w pliku",
            all(n.get("wyjeta") for n in surowe), surowe)
    sprawdz("po ponownym wczytaniu nadal nic wolnego",
            stages.wez_z_banku_notek(5) == [])

    print()
    print("=== 5. USZKODZONY PLIK NIE ZATRZYMUJE AGENTA ===")
    stages.BANK_NOTEK.write_text("{to nie jest json", encoding="utf-8")
    sprawdz("smieci czytamy jako pusty bank", stages.wczytaj_bank_notek() == [])
    stages.BANK_NOTEK.write_text('{"nie": "lista"}', encoding="utf-8")
    sprawdz("slownik zamiast listy tez", stages.wczytaj_bank_notek() == [])
    sprawdz("po smieciach da sie dopisac", stages.dopisz_do_banku_notek(
        [{"tekst": "Nowa po awarii."}]) == 1)

    print()
finally:
    # Oddajemy swiat w stanie, w jakim go zastalismy — takze wtedy, gdy
    # ktoras asercja wywali sie wyjatkiem w polowie pliku.
    config.przywroc_katalog_danych(_ZDJECIE_SCIEZEK)
    stages.BANK_NOTEK = _ORYG_BANK

print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
