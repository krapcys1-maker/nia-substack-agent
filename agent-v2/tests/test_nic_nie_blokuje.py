# -*- coding: utf-8 -*-
"""Zadna nowa bramka nie ma prawa wejsc niezauwazona.

ZASADA WLASCICIELA, powtarzana od tygodnia i dosadnie: NIC SIE NIE BLOKUJE.
Nic nie czeka na czlowieka, nic nie jest wycinane, zadna tresc nie przepada
dlatego, ze system nabral watpliwosci. Lepiej, zeby wyszlo cos niejasnego, niz
zeby nie wyszlo nic.

PO CO TEN PLIK. 2 wrzesnia 2026 wlasciciel zadal najprostsze mozliwe pytanie —
„czy cos sie blokuje?" — i odpowiedz zajela pol godziny oraz czterech
rownoleglych agentow czytajacych kod. Repozytorium ma mape na 12 774 wiersze,
doktryne i dwa audyty, a mimo to nikt nie umial odpowiedziec z pamieci.

Ten test zamienia tamto pytanie w BRAMKE, ktora sama sie pilnuje: czyta drzewo
skladni (`bramki.py`) i sprawdza, ze przy publikacji nie stoi zaden warunek
poza dwoma dozwolonymi. Kazdy nowy warunek — czyjkolwiek, w tym moj — oblewa
ten test i wymaga swiadomej decyzji zamiast cichego wejscia.

CO JEST DOZWOLONE I DLACZEGO:
  * `wyslij` / `args.wyslij` — to nie jest bramka jakosci, tylko przelacznik
    „tryb sprawdzenia kontra tryb publikacji". Bez niego nie dalo by sie
    uruchomic przebiegu bez wystawiania.
  * `c.get('gdzie') == 'artykul'` — rozgalezienie na RODZAJ celu (odpowiedz pod
    artykulem kontra pod notka), a nie ocena tresci.

CZEGO TEN TEST NIE PILNUJE: czy trzy zapory sprzed dzisiaj (dwie przeciw
wstrzyknieciu, jedna przeciw zmyslonemu przezyciu) sa sluszne. Sa i maja
zostac — bronia przed cudzym tekstem piszacym przez nasze konto, a to co
innego niz watpliwosc co do faktu. Ich LICZBA jest tu jednak przybita, wiec
czwarta taka zapora rowniez oblewa.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_nic_nie_blokuje.py
"""
import sys

sys.path.insert(0, "agent-v2")
import bramki      # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# Warunki, ktore WOLNO postawic przed publikacja. Wszystko poza ta lista jest
# nowa bramka i ma oblac ten test.
DOZWOLONE = {
    "wyslij",
    "args.wyslij",
    "c.get('gdzie') == 'artykul'",
}

print("=== 1. PRZY PUBLIKACJI NIE STOI ZADEN WARUNEK O TRESCI ===")
wystawienia = bramki.warunki_przed_wystawieniem()
sprawdz("znaleziono wystawienia w kodzie", len(wystawienia) >= 6,
        len(wystawienia))

obce = []
for w in wystawienia:
    for warunek in w["warunki"]:
        if warunek not in DOZWOLONE:
            obce.append("%s:%d  %s()  <- if %s"
                        % (w["plik"], w["linia"], w["co"], warunek))

sprawdz("zaden warunek spoza listy dozwolonych", not obce,
        " | ".join(obce[:3]))
if obce:
    print()
    print("  NOWA BRAMKA PRZED PUBLIKACJA:")
    for o in obce:
        print("     %s" % o)
    print("  Jesli to swiadoma decyzja, dopisz warunek do DOZWOLONE w tym")
    print("  pliku RAZEM Z UZASADNIENIEM. Jesli nie — to jest blokada.")

print()
print("=== 2. KAZDY RODZAJ TRESCI MA SWOJE WYSTAWIENIE ===")
# Gdyby ktos usunal cala sciezke, sekcja 1 przeszlaby pusto.
co_wystawiamy = {w["co"] for w in wystawienia}
for rodzaj in ("wystaw_notke", "wystaw_komentarz", "wystaw_odpowiedz",
               "wystaw_artykul"):
    sprawdz("%-26s jest wolane" % rodzaj, rodzaj in co_wystawiamy,
            sorted(co_wystawiamy))

print()
print("=== 3. ILE JEST ZAPOR ODBIERAJACYCH PRAWO DO PUBLIKACJI ===")
# Trzy zapory sprzed 2 wrzesnia 2026 plus werdykt samej bramki faktow.
# Werdykt jest NADPISYWANY przez wolajacych na `True` — patrz `note` i
# `comment_on` — wiec nie zatrzymuje niczego; liczy sie tu, bo jest
# przypisaniem do tego samego pola.
zapory = bramki.wstrzymania_publikacji()
opis = ["%s:%d %s" % (z["plik"], z["linia"], z["funkcja"]) for z in zapory]
sprawdz("dokladnie cztery przypisania `safe_to_post` inne niz True",
        len(zapory) == 4, opis)

funkcje = sorted(z["funkcja"] for z in zapory)
sprawdz("i stoja tam, gdzie stac maja",
        funkcje == ["comment_on", "comment_on", "note", "zweryfikuj"], funkcje)

print()
print("=== 4. KONTRDOWOD: WYKRYWACZ NAPRAWDE BY ZLAPAL NOWA BRAMKE ===")
# Gdyby `warunki_przed_wystawieniem` zwracalo puste warunki, sekcja 1
# przechodzilaby zawsze. Sprawdzamy na SZTUCZNYM kodzie, ze wykrywacz widzi
# warunek, ktorego tam nie wolno.
import ast          # noqa: E402
import tempfile     # noqa: E402
import pathlib      # noqa: E402

PROBKA = '''
def dzien(wyslij):
    for data in candidates:
        if data.get("safe_to_post"):
            browser.wystaw_notke(data["note"], wyslij=True)
'''
katalog = pathlib.Path(tempfile.mkdtemp(prefix="bramki-kontrdowod-"))
(katalog / "run.py").write_text(PROBKA, encoding="utf-8")
stary_korzen, stare_pliki = bramki.KORZEN, bramki.PLIKI
bramki.KORZEN, bramki.PLIKI = katalog, ("run.py",)
try:
    udawane = bramki.warunki_przed_wystawieniem()
finally:
    bramki.KORZEN, bramki.PLIKI = stary_korzen, stare_pliki

sprawdz("wykrywacz znalazl udawane wystawienie", len(udawane) == 1, udawane)
znalezione = [w for u in udawane for w in u["warunki"]]
sprawdz("i zobaczyl warunek o tresci",
        any("safe_to_post" in w for w in znalezione), znalezione)
sprawdz("a taki warunek NIE jest na liscie dozwolonych",
        all(w not in DOZWOLONE for w in znalezione), znalezione)

print()
print("=" * 62)
print("ZDANE: %d    OBLANE: %d" % (zdane, oblane))
sys.exit(1 if oblane else 0)
