# -*- coding: utf-8 -*-
"""Nasz wlasny przyklad ma przejsc reguly, ktore stawiamy KAZDEMU operatorowi.

## Po co ten plik istnieje

`test_przyklad_konfiguracji.py` pilnuje, ze przyklad ma komplet pol i wczytuje
sie bez bledu, i mowi wprost, ze WARTOSCI nie sprawdza. To slusznie — wartosci
maja byc czytelne, nie poprawne dla czyjegos konta.

Ale jest osobne pytanie, ktorego nikt nie zadawal: CZY NASZ PRZYKLAD
PRZESZEDLBY NASZE WLASNE REGULY. Jesli nie przechodzi, to znaczy jedno z dwojga
i oba sa wada:

  * przyklad jest zly — czlowiek skopiuje go i dostanie oblany audyt
    przy pierwszym uruchomieniu, zanim cokolwiek zdazy zrobic; albo
  * REGULA JEST NASZA, a nie powszechna — czyli prog z naszej instalacji
    podany jako prawo natury.

Drugie zdarzylo sie 2026-09-04 i kosztowalo szesc oblanych asercji na
instalacji calkowicie poprawnej. Uruchomilismy kreator od zera dla wymyslonej
publikacji o pieczywie i dostalismy:

    BLAD  hasel szukania jest >= 19            3
    BLAD    rewir obejmuje: ludzie i prawo
    BLAD    rewir obejmuje: pieniadze i wladza

Dziewietnascie bylo NASZA liczba. `OBSZARY_REWIRU` bylo NASZA mapa rewiru,
z polskimi nazwami, i nie ma jej nawet w kreatorze — wiec zadanie od
anglojezycznej publikacji o pieczywie, zeby jej hasla pokrywaly „pieniadze
i wladza", bylo niewykonalne z definicji.

## Czym ten plik rozni sie od audytu

Audyt bada INSTALACJE, ktora stoi na maszynie. Ten plik bada PRZYKLAD, ktory
lezy w repozytorium — czyli to, co dostanie ktos, kto jeszcze niczego nie ma.
Te dwie rzeczy rozjezdzaja sie po cichu: przyklad nie jest uruchamiany przez
nikogo, dopoki ktos go nie skopiuje, a wtedy jest juz za pozno na uwagi.

Regula, ktora tu stoi, MUSI byc niezalezna od niszy — inaczej ten plik
powtorzy blad, ktory ma lapac. Kazda asercja ponizej wywodzi sie ze STRUKTURY
(ile losujemy na przebieg, ile notek na dobe), nigdy z liczby wpisanej recznie.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_przyklad_przechodzi_reguly.py
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config           # noqa: E402
import konfiguracja     # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


PRZYKLAD = pathlib.Path("konfiguracja.example.toml")
dane = konfiguracja.wczytaj(PRZYKLAD)

hasla = [str(h).lower() for h in dane.get("temat.hasla_szukania", ())]
znaki = [str(z).lower() for z in dane.get("temat.znaki_niszy", ())]
dziedziny = list(dane.get("temat.dziedziny", ()))

print("=== 1. PULA HASEL JEST SZERSZA NIZ JEDEN PRZEBIEG ===")
# STRUKTURA, NIE LICZBA. Kazdy przebieg losuje `ILE_HASEL_NA_PRZEBIEG` hasel
# (`kanal.szukaj_celow`). Pula rowna temu albo mniejsza idzie za kazdym razem
# CALA — i przyprowadza te sama garstke kont, niezaleznie od tego, jak dobrze
# jest napisana. Trzykrotnosc daje losowaniu z czego wybierac.
minimum = 3 * config.ILE_HASEL_NA_PRZEBIEG
sprawdz("przyklad ma co najmniej %d hasel" % minimum,
        len(hasla) >= minimum,
        "%d hasel przy %d losowanych na przebieg"
        % (len(hasla), config.ILE_HASEL_NA_PRZEBIEG))
sprawdz("i nie idzie cala pula naraz",
        config.ILE_HASEL_NA_PRZEBIEG < len(hasla),
        (config.ILE_HASEL_NA_PRZEBIEG, len(hasla)))

print()
print("=== 2. HASLA TRZYMAJA SIE ZNAKOW NISZY Z TEGO SAMEGO PLIKU ===")
# To sa DWA POLA TEGO SAMEGO OPERATORA i maja sie zgadzac ze soba. Zlamanie
# ma zmierzony skutek: agent szuka po haslach, dostaje posty, a `cele.md`
# odrzuca je co do jednego jako spoza rewiru. W logu wyglada to na wybrednosc
# modelu („warte komentarza: 0/15"), a jest szukaniem nie tego, czego trzeba.
#
# ZNAKI BIERZEMY Z PRZYKLADU, nie z `config.py` — inaczej sprawdzalibysmy
# przyklad nasza nisza, czyli dokladnie ten blad, ktory ten plik ma lapac.
poza = [h for h in hasla if not any(z in h for z in znaki)]
sprawdz("kazde haslo z przykladu niesie znak z przykladu", not poza, poza[:5])

print()
print("=== 3. SIATKA MA Z CZEGO LOSOWAC PRZEZ WIECEJ NIZ JEDEN DZIEN ===")
# Wzorce x dziedziny daja komorki. Notek na dobe jest `len(NOTE_MIX_OTHER_DAY)`.
# Prog dziesieciu komorek na notke znaczy: ten sam wzorzec w tej samej
# dziedzinie nie wraca w tym samym tygodniu.
komorki = len(config.GENERATORY) * max(1, len(dziedziny))
na_dobe = max(1, len(config.NOTE_MIX_OTHER_DAY))
sprawdz("co najmniej 10 komorek na notke",
        komorki >= 10 * na_dobe,
        "%d komorek (%d wzorcow x %d dziedzin) przy %d notkach na dobe"
        % (komorki, len(config.GENERATORY), len(dziedziny), na_dobe))

print()
print("=== 4. LICZBY W PRZYKLADZIE SA W ZAKRESACH, KTORE LOADER PRZYJMUJE ===")
# Przyklad, ktorego loader nie przyjmuje, jest gorszy niz brak przykladu —
# ale `test_przyklad_konfiguracji.py` sprawdza juz walidacje pole po polu.
# Tu pytamy o rzecz, ktorej walidator nie zlapie, bo jest MIEDZY polami:
# komentarzy dziennie nie moze byc wiecej, niz przebiegow razy cokolwiek.
widelki = dane.get("wolumeny.komentarze_dziennie")
if widelki:
    sprawdz("dolna granica komentarzy nie jest wieksza od gornej",
            widelki[0] <= widelki[1], widelki)

print()
print("=== 5. KONTRDOWOD: ZATRUTY PRZYKLAD MUSI TU POLEC ===")
# Bez tego nie wiadomo, czy powyzsze cokolwiek mierzy.
_ciasna_pula = ["bread regulation", "flour standards", "bakery inspection"]
sprawdz("trzy hasla przy pieciu losowanych NIE przechodza",
        not (len(_ciasna_pula) >= minimum))
_znaki_obok = ["flour", "yeast", "bakery"]
sprawdz("haslo bez zadnego znaku NIE przechodzi",
        [h for h in _ciasna_pula if not any(z in h for z in _znaki_obok)]
        == ["bread regulation"])
# LICZBE BIERZEMY Z PROGU, NIE Z GLOWY. Pierwsza wersja mowila „cztery
# dziedziny nie daja siatki" i OBLALA, bo 14 wzorcow x 4 = 56 przy progu 50
# przechodzi — czyli kontrdowod twierdzil cos, co nie jest prawda, i tylko
# dlatego bylo to widac, ze go uruchomilismy. Najwieksza liczba dziedzin,
# ktora MUSI polec, wynika z progu.
_za_malo = (10 * na_dobe - 1) // len(config.GENERATORY)
sprawdz("%d dziedzin przy %d notkach NIE daje siatki" % (_za_malo, na_dobe),
        not (len(config.GENERATORY) * _za_malo >= 10 * na_dobe),
        "%d komorek wobec progu %d"
        % (len(config.GENERATORY) * _za_malo, 10 * na_dobe))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
