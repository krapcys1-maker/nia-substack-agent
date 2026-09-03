"""Pliki z cudzymi danymi maja byc czytelne TYLKO dla wlasciciela.

Dwie rzeczy na tej maszynie zawieraja dane, ktore nie sa nasze:

- `storage-state-serwer.json` — zalogowana sesja Substacka. Kto ja przeczyta,
  jest nami. Lezala z prawami 0644, czyli czytelna dla kazdego konta na
  serwerze.
- `data/kopie/subskrybenci-*.csv` — adresy e-mail czytelnikow. Pierwsza kopia
  wyladowala z 0664 z tego samego powodu: domyslna umaska, nikt nie ustawil
  inaczej.

Roznica miedzy jednorazowym `chmod` a poprawka w kodzie jest cala pointa:
recznie znaczy „przy pierwszej kopii", a kopii ma byc trzydziesci. Prawo ma
byc ustawiane przy KAZDYM zapisie.

Test jest dwuczesciowy, bo Windows nie ma praw POSIX: statyczna czesc chodzi
wszedzie, funkcjonalna tylko tam, gdzie te prawa cokolwiek znacza.
"""
import os
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


kopia_src = pathlib.Path("agent-v2/kopia_subskrybentow.py").read_text(encoding="utf-8")

print("=== 1. KOPIA LISTY ZAMYKA SIE SAMA ===")
sprawdz("skrypt ustawia prawa po zapisie", "chmod(0o600)" in kopia_src)
sprawdz("i robi to przy kazdym zapisie, nie raz",
        kopia_src.find("chmod(0o600)") > kopia_src.find("cel.write_text"),
        "chmod musi stac PO zapisie pliku")
# KONTRDOWOD: brak praw POSIX nie moze kosztowac nas kopii. Windows ma to
# przemilczec, a nie wywalic sie i zostawic liste bez archiwum.
sprawdz("brak praw POSIX nie przerywa archiwizacji", "except OSError" in kopia_src)
sprawdz("i katalog jest poza gitem",
        "agent-v2/data/" in pathlib.Path(".gitignore").read_text(encoding="utf-8"))
sprawdz("skrypt sam o tym przypomina",
        "cudze adresy e-mail" in kopia_src)

print()
print("=== 2. NA POSIX SPRAWDZAMY TO NAPRAWDE ===")
if os.name == "nt":
    print("  (pominiete: Windows nie ma praw POSIX — te same asercje chodza")
    print("   na serwerze, czyli tam, gdzie pliki naprawde leza)")
else:
    import config
    import kopia_subskrybentow as kop

    with tempfile.TemporaryDirectory() as tmp:
        _zdjecie = config.uzyj_katalogu_danych(pathlib.Path(tmp))
        kop.KATALOG = config.DATA_DIR / "kopie"
        kop.PRZYCHODZACE = kop.KATALOG / "przychodzace"
        kop.PRZYCHODZACE.mkdir(parents=True)
        (kop.PRZYCHODZACE / "eksport.csv").write_text(
            "Email,Name\nktos@example.com,Ktos\n", encoding="utf-8")
        kop.main()
        zapisane = sorted(kop.KATALOG.glob("subskrybenci-*.csv"))
        sprawdz("kopia powstala", len(zapisane) == 1, zapisane)
        if zapisane:
            prawa = zapisane[0].stat().st_mode & 0o777
            sprawdz("i ma prawa 0600", prawa == 0o600, oct(prawa))
            # Plik zrodlowy ma zniknac — inaczej cudze adresy leza w dwoch
            # miejscach, a to drugie nikogo nie pilnuje.
            sprawdz("plik przychodzacy zostal usuniety",
                    not list(kop.PRZYCHODZACE.glob("*.csv")))
        config.przywroc_katalog_danych(_zdjecie)

print()
print("=== 6. POBIERANIE LISTY Z WLASNEGO PANELU ===")
# Kopia byla jedynym miejscem, gdzie wlasciciel musial cos kliknac, a zamysl
# calego systemu to zero dotyku. Rozroznienie, ktore to umozliwia: ZGADYWANIE
# nieudokumentowanych adresow API jest scrapingiem, CZYTANIE WLASNEGO PANELU
# wlasna sesja nie jest — to wlasciciel patrzacy na wlasne konto, ta sama
# droga, ktora agent wystawia notki.
sys.path.insert(0, "agent-v2")
import browser   # noqa: E402

# Komorki DOKLADNIE takie, jakie oddal panel na zywo — z pusta pierwsza
# (checkbox) i z naglowkiem jako osobnym wierszem.
PANEL = [
    ["", "Subskrybent", "Typ", "Aktywnosc", "Data rozpoczecia", "Przychody"],
    ["", "ktos@example.com", "Darmowy", "*****", "Jul 12, 2026", "$0.00"],
    ["", "autor@example.com", "Autor", "*****", "Jul 11, 2026", "$0.00"],
]
w = browser.zloz_wiersze_subskrybentow(PANEL)
sprawdz("naglowek nie jest subskrybentem", len(w) == 2, w)
sprawdz("adresy odczytane", [x["email"] for x in w]
        == ["ktos@example.com", "autor@example.com"], w)
# TO BYL PRAWDZIWY BLAD: typ brany z `komorki[1]` na sztywno wstawial tam
# POWTORZONY ADRES. Wyszlo dopiero przy ogladaniu zapisanego pliku.
sprawdz("typ to typ, nie drugi adres", [x["typ"] for x in w] == ["Darmowy", "Autor"],
        [x["typ"] for x in w])
sprawdz("i zadne pole typu nie jest adresem",
        all("@" not in x["typ"] for x in w), [x["typ"] for x in w])
sprawdz("data rozpoczecia odczytana", all(x["od"] for x in w), w)
# Odpornosc na inna kolejnosc kolumn — panel moze ja zmienic bez uprzedzenia.
inne = [["Darmowy", "ktos@example.com", "Jan 3, 2027"]]
w2 = browser.zloz_wiersze_subskrybentow(inne)
sprawdz("adres znaleziony takze przy innej kolejnosci kolumn",
        w2 and w2[0]["email"] == "ktos@example.com", w2)
# KONTRDOWODY: smiec nie moze udawac subskrybenta.
sprawdz("wiersz bez adresu jest pomijany",
        browser.zloz_wiersze_subskrybentow([["", "Darmowy", "x"]]) == [])
sprawdz("pusta tabela to pusta lista", browser.zloz_wiersze_subskrybentow([]) == [])
sprawdz("None tez nie wywala", browser.zloz_wiersze_subskrybentow(None) == [])

print()
print("=== 7. NIEPELNA LISTA NIE MOZE ZOSTAC ZAPISANA ===")
# Kopia, ktora wyglada na komplet, a jest polowa, jest grozniejsza niz brak
# kopii: przy odtwarzaniu konta nikt nie sprawdza, czy plik byl pelny —
# sprawdza sie, czy w ogole jest.
br = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
sprawdz("pobieranie oddaje informacje o kompletnosci", '"kompletna"' in br)
sprawdz("warunkiem konca jest STABILNA liczba wierszy, nie liczba prob",
        "bez_zmian >= 2" in br)
sprawdz("i przy niepewnosci podaje powod", "nie moge zarczyc" in br
        or "nie moge zaręczyć" in br or "nadal rosla" in br)
kop = pathlib.Path("agent-v2/kopia_subskrybentow.py").read_text(encoding="utf-8")
sprawdz("kopia odmawia zapisu niepelnej listy",
        'if not wynik.get("kompletna"):' in kop)
sprawdz("i mowi, dlaczego nie pobrala", "NIE POBRALEM automatycznie" in kop)
# Automat i czlowiek MUSZA isc dalej ta sama droga — inaczej powstaje druga
# sciezka zapisu, na ktorej cos moze pojsc inaczej.
sprawdz("pobrany plik ladnie tam, gdzie reczny eksport",
        "PRZYCHODZACE /" in kop)
sprawdz("reczna droga zostaje jako zapasowa", "Recznie, gdy automat odmowi" in kop)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
