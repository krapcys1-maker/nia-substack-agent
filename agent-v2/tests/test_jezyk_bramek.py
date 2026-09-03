# -*- coding: utf-8 -*-
"""Wybor jezyka nie moze po cichu WYLACZYC bramek.

## Po co

`config.ARTICLE_LANGUAGE` byl polem konfiguracji od poczatku, ale siedem
wzorcow w `gates.py` to angielskie wyrazenia regularne. Ustawienie innego
jezyka dawalo bota, ktory pisze po nowemu, a bramki **zwracaja pustke** —
nie dlatego, ze tekst jest czysty, tylko dlatego, ze nie ma czym szukac.

To najgrozniejsza awaria w calym systemie, bo NIE WYGLADA na awarie. Kazdy
inny blad tutaj krzyczy; ten milczy i wszystko swieci na zielono.

## Co ten test mierzy

1. Dla znanego jezyka bramki NAPRAWDE lapia — na tekstach, ktore lapaly
   przed rozbiciem wzorcow na jezyki.
2. Dla nieznanego jezyka bramka jest JAWNIE wylaczona: nie dopasowuje nic
   ORAZ mowi o tym na ekran.
3. KONTRDOWOD: wzorzec-zaslepka naprawde nie lapie NICZEGO, wiec punkt 2
   mierzy wylaczenie, a nie przypadkowy brak dopasowania.
4. Kazdy jezyk w `WZORCE` ma KOMPLET kluczy — jezyk z polowa bramek jest
   gorszy od jego braku, bo wyglada na obsluzony.
"""
from __future__ import annotations

import contextlib
import io
import pathlib
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

import config    # noqa: E402
import jezyki    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa: str, warunek: bool, szczegol: object = "") -> None:
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# Teksty, ktore MUSZA byc zlapane po angielsku. Kazdy pochodzi z wady,
# ktora naprawde wyszla na produkcji — dlatego jest tu doslownie.
LAPIE_SIE = [
    ("ZMYSLONE_PRZEZYCIE", "I stood in the queue and counted them."),
    ("ZMYSLONE_PRZEZYCIE", "my wife pointed out the label."),
    ("ZMYSLONE_PRZEZYCIE", "Last week, I drove past the depot."),
    ("NIEISTNIEJACE_BADANIE", "According to a recent study, most people agree."),
    ("NIEISTNIEJACE_BADANIE", "Studies have shown the opposite."),
    ("ZASTRZEZENIE", "I think this is the reason."),
    ("ZASTRZEZENIE", "In my view the rule is older."),
    ("POWSCIAGLIWOSC", "I will not invent it."),
    ("ZAKAZANE_OTWARCIA", "Turn over the container and look."),
    ("ZAKAZANE_OTWARCIA", "Next time you buy one, check the base."),
    ("NIBY_ZRODLO", "In one survey, 68% said otherwise."),
    ("NIBY_ZRODLO", "Some estimates put it higher."),
]

# Teksty, ktorych zlapac NIE WOLNO — bo niosa szczegol z karty dowodowej.
NIE_LAPIE_SIE = [
    ("NIEISTNIEJACE_BADANIE", "In a shelf-life study at 8 degrees, the figure held."),
    ("ZAKAZANE_OTWARCIA", "The container is turned over at the depot."),
]

print("=== 1. ZNANY JEZYK: BRAMKI NAPRAWDE LAPIA ===")
for nazwa, tekst in LAPIE_SIE:
    wz = jezyki.wzorzec(nazwa, "English")
    sprawdz("%-22s lapie %r" % (nazwa, tekst[:34]), bool(wz.search(tekst)))

print()
print("=== 2. I NIE LAPIA TEGO, CZEGO NIE WOLNO ===")
for nazwa, tekst in NIE_LAPIE_SIE:
    wz = jezyki.wzorzec(nazwa, "English")
    sprawdz("%-22s przepuszcza %r" % (nazwa, tekst[:30]), not wz.search(tekst))

print()
print("=== 3. LISTY FRAZ TEZ SA NIEPUSTE ===")
for nazwa in ("SYGNAL_NIEWIADOMEJ", "META_GRANIC"):
    f = jezyki.frazy(nazwa, "English")
    sprawdz("%s ma frazy" % nazwa, len(f) >= 10, len(f))

print()
print("=== 4. NIEZNANY JEZYK: JAWNIE WYLACZONE, NIE PO CICHU ===")
jezyki._ostrzezono.clear()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    wz = jezyki.wzorzec("ZAKAZANE_OTWARCIA", "Klingon")
    fr = jezyki.frazy("META_GRANIC", "Klingon")
komunikat = buf.getvalue()

sprawdz("wzorzec nie lapie NICZEGO", not wz.search("Turn over the container"))
sprawdz("lista fraz jest pusta", fr == ())
sprawdz("ale MOWI o tym na ekran", "NIE MA WZORCOW" in komunikat, komunikat[:80])
sprawdz("i nazywa jezyk", "Klingon" in komunikat)
sprawdz("i nazywa bramke", "ZAKAZANE_OTWARCIA" in komunikat)
sprawdz("i mowi WPROST, ze to nie znaczy czysty tekst",
        "nie znaczy, ze tekst jest czysty" in komunikat)
sprawdz("i podpowiada, gdzie to naprawic", "jezyki.py" in komunikat)

print()
print("=== 5. OSTRZEZENIE RAZ NA PROCES, NIE PRZY KAZDYM ZDANIU ===")
# Ostrzezenie w petli po zdaniach zalewa log i przestaje byc czytane.
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    for _ in range(5):
        jezyki.wzorzec("ZAKAZANE_OTWARCIA", "Klingon")
sprawdz("powtorzone wywolanie juz milczy", buf2.getvalue() == "",
        buf2.getvalue()[:60])

print()
print("=== 6. KONTRDOWOD: ZASLEPKA NIE LAPIE NICZEGO ===")
# Bez tego punkt 4 moglby przechodzic dlatego, ze akurat ten tekst nie pasuje.
import re as _re   # noqa: E402
zaslepka = _re.compile(jezyki.NIGDY)
probki = ["", "x", "Turn over", "cokolwiek", "I stood", "\n\n", "123",
          "According to a recent study"]
sprawdz("zaslepka nie lapie zadnej z %d probek" % len(probki),
        not any(zaslepka.search(p) for p in probki))

print()
print("=== 7. KAZDY JEZYK MA KOMPLET, ALBO GO NIE MA WCALE ===")
# Jezyk z polowa bramek jest GORSZY od jego braku: wyglada na obsluzony,
# a polowa kontroli milczy.
for jezyk in jezyki.znane_jezyki():
    brak = jezyki.brakujace(jezyk)
    sprawdz("%s ma komplet bramek" % jezyk, not brak, brak)

sprawdz("jezyk skonfigurowany (%s) jest znany" % config.ARTICLE_LANGUAGE,
        not jezyki.brakujace(config.ARTICLE_LANGUAGE),
        jezyki.brakujace(config.ARTICLE_LANGUAGE))

print()
print("=== 8. GATES NAPRAWDE UZYWA TYCH WZORCOW ===")
# Kontrola, ze `gates.py` siega po `jezyki`, a nie ma wlasnej kopii — bo
# dwie kopie wzorca to dwie rozne bramki, z ktorych jedna nie jest testowana.
zrodlo = (KORZEN / "gates.py").read_text(encoding="utf-8")
sprawdz("gates.py importuje jezyki", "import jezyki" in zrodlo)
for nazwa in ("ZASTRZEZENIE", "ZAKAZANE_OTWARCIA", "NIBY_ZRODLO",
              "POWSCIAGLIWOSC"):
    sprawdz("  %s idzie z jezyki" % nazwa,
            'jezyki.wzorzec("%s"' % nazwa in zrodlo)
sprawdz("i zaden wzorzec nie zostal na sztywno w gates.py",
        "re.compile(\n    r\"\\bI\\s+(stood" not in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
