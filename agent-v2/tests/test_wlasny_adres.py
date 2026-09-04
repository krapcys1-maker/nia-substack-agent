# -*- coding: utf-8 -*-
"""„Czy to nasz wlasny tekst" nie moze zalezec od DLUGOSCI uchwytu.

## Po co ten plik istnieje

`kanal.py` odsiewa nasze wlasne teksty z kanalu czytelnika — filtr powstal, bo
agent uznal wlasny artykul za wart skomentowania i komentowalby sam siebie.
Stalo tam:

    if config.SUBSTACK_HANDLE in adres:
        continue

Podnapis w adresie. Dziala dla uchwytu dlugiego i nietypowego; dla krotkiego
albo bedacego zwyklym slowem wycina CUDZE publikacje BEZ SLADU:

    uchwyt „art"  -> odpada `smartinvestor.substack.com`, `chartbook.substack.com`
    uchwyt „news" -> odpada `thenewsletter.substack.com`

Cena jest niesymetryczna i cicha. Odrzucony cel nie zostawia zadnego wpisu
w dzienniku, a licznik pokazuje po prostu mniejsza liczbe postow — wiec konto
z krotkim uchwytem komentuje mniej i nikt nie wie dlaczego.

UCHWYT JEST POLEM KONFIGURACJI (`konto.uchwyt`). To nie jest hipoteza o dziwnym
przypadku, tylko zwykla instalacja: „art", „news", „data", „bio" to uchwyty,
ktore ktos moze miec.

## Czego pilnuje

1. NASZ adres jest rozpoznany — na `uchwyt.substack.com` i na wlasnej domenie.
2. CUDZY adres zawierajacy uchwyt jako fragment NIE jest naszy. To jest cala
   poprawka i cala roznica wobec starej wersji.
3. Krotki uchwyt zachowuje sie tak samo jak dlugi — czyli wynik NIE ZALEZY od
   dlugosci uchwytu.
4. Pusty uchwyt nie odsiewa niczego (swieza instalacja bez konfiguracji nie ma
   milczec).
5. KONTRDOWOD: stara regula (podnapis) na tych samych adresach daje INNY wynik.
   Bez tego caly plik moglby przechodzic na obu wersjach.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wlasny_adres.py
"""
import sys

sys.path.insert(0, "agent-v2")
import config  # noqa: E402
import kanal   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


_stary = config.SUBSTACK_HANDLE

# (uchwyt, adres, czy nasz)
PRZYPADKI = (
    ("art", "https://art.substack.com/p/tekst", True),
    ("art", "https://www.art.substack.com/p/tekst", True),
    ("art", "https://smartinvestor.substack.com/p/tekst", False),
    ("art", "https://chartbook.substack.com/p/x", False),
    ("art", "https://example.com/artykul-o-czyms", False),
    ("news", "https://news.substack.com/p/x", True),
    ("news", "https://thenewsletter.substack.com/p/x", False),
    ("mojapublikacja", "https://mojapublikacja.substack.com/p/x", True),
    ("mojapublikacja", "https://innapublikacja.substack.com/p/x", False),
)

try:
    print("=== 1. NASZ ADRES ROZPOZNANY, CUDZY NIE ===")
    for uchwyt, adres, ma_byc in PRZYPADKI:
        config.SUBSTACK_HANDLE = uchwyt
        wynik = kanal.nasz_adres(adres)
        sprawdz("%-16s %-46s -> %s" % (uchwyt, adres[:46], ma_byc),
                wynik is ma_byc, wynik)

    print()
    print("=== 2. WYNIK NIE ZALEZY OD DLUGOSCI UCHWYTU ===")
    # Ten sam ksztalt pytania dla uchwytu trzyliterowego i czternastoliterowego.
    for uchwyt in ("art", "mojapublikacja"):
        config.SUBSTACK_HANDLE = uchwyt
        swoj = "https://%s.substack.com/p/x" % uchwyt
        cudzy = "https://ktostam%sowo.substack.com/p/x" % uchwyt
        sprawdz("%-16s swoj adres  -> True" % uchwyt, kanal.nasz_adres(swoj))
        sprawdz("%-16s cudzy z uchwytem w srodku -> False" % uchwyt,
                not kanal.nasz_adres(cudzy), cudzy)

    print()
    print("=== 3. PUSTY UCHWYT NIE ODSIEWA NICZEGO ===")
    # Swieza instalacja bez konfiguracji ma dzialac, a nie milczec.
    config.SUBSTACK_HANDLE = ""
    sprawdz("pusty uchwyt: nic nie jest nasze",
            not kanal.nasz_adres("https://cokolwiek.substack.com/p/x"))
    sprawdz("i pusty adres tez nie",
            not kanal.nasz_adres(""))

    print()
    print("=== 4. KONTRDOWOD: STARA REGULA DAWALA INNY WYNIK ===")
    # Bez tego caly plik przechodzilby takze na wersji sprzed poprawki —
    # a wtedy nie mierzylby zmiany, tylko zgodnosc z samym soba.
    def _po_staremu(uchwyt: str, adres: str) -> bool:
        return uchwyt in adres

    rozjazdy = []
    for uchwyt, adres, _ in PRZYPADKI:
        config.SUBSTACK_HANDLE = uchwyt
        if _po_staremu(uchwyt, adres) != kanal.nasz_adres(adres):
            rozjazdy.append((uchwyt, adres))
    sprawdz("stara i nowa regula RÓŻNIĄ SIĘ na tych adresach",
            len(rozjazdy) >= 3, rozjazdy)
    for uchwyt, adres in rozjazdy:
        print("        %-16s %s" % (uchwyt, adres))
finally:
    config.SUBSTACK_HANDLE = _stary

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
