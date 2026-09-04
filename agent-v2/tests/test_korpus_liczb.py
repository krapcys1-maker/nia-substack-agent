# -*- coding: utf-8 -*-
"""„Korpus" dla kontroli liczb ma byc MATERIALEM, a nie wypowiedzia modelu.

## Po co ten plik istnieje

`gates.numbers_outside_corpus` pyta, czy liczba z tekstu wystepuje w materiale
dowodowym. Korpusem byl caly `json.dumps(card)` — a karta w chwili sprawdzania
niesie takze:

  * `ocena_ciekawosci` — werdykt `warto_pisac` O TEJ KARCIE, z cytatami;
  * `parallel_mechanisms` z banku (`z_banku`) — mechanizmy z INNEJ dziedziny,
    dolozone przez bibliotekarza;
  * twierdzenie `not_fetched` — fakt z puli, ktorego strony nikt nie pobral.

Kazda liczba, ktora model przepisal sobie do uzasadnienia, stawala sie przez to
„obecna w materiale dowodowym". Bramka przestawala pytac o material i zaczynala
pytac SAMA SIEBIE.

TO BYLO ZNANE I SPISANE trzy tygodnie wczesniej:
`dokumentacja-zrodla/rozdzial_artykul.md` nosi naglowek „WADA — «korpus» dla
kontroli liczb jest szerszy, niz nazwa sugeruje" i wymienia oba pola po nazwie.
Docstring samej funkcji mowil „ZOSTAJE ZNANA WADA". Opisana i niezalatana —
ten sam wzorzec, co komunikaty systemowe z wpisana nisza.

## Czego pilnuje

1. Liczba z POBRANEGO materialu przechodzi.
2. Liczba, ktora jest TYLKO w wypowiedzi modelu, NIE przechodzi — osobno dla
   `ocena_ciekawosci`, `parallel_mechanisms[z_banku]` i `not_fetched`.
3. `parallel_mechanisms` BEZ znacznika `z_banku` zostaja: pochodza z syntezy
   pobranego korpusu i sa materialem.
4. KONTRDOWOD: bez tego rozroznienia wszystkie cztery liczby przechodzily.
   Pokazujemy to wprost, licząc korpus po staremu.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_korpus_liczb.py
"""
import json
import sys

sys.path.insert(0, "agent-v2")
import gates  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# Liczby dobrane tak, zeby zadna nie pojawila sie przypadkiem w innym polu.
KARTA = {
    "working_thesis": "teza",
    "confirmed_claims": [
        {"claim": "pobrane twierdzenie", "evidence": "wzrost o 12 procent",
         "url": "https://a.example/1"},
        {"claim": "fakt z puli", "evidence": "objelo 83 gminy",
         "url": "https://b.example/2", "not_fetched": True},
    ],
    "ocena_ciekawosci": {"werdykt": "PISZ", "powod": "widzialem 77 przypadkow"},
    "parallel_mechanisms": [
        {"domain": "z syntezy", "how_it_matches": "ten sam uklad, 41 razy"},
        {"domain": "z banku", "mechanism": "zapas mowi o 99 sztukach",
         "z_banku": True},
    ],
}

print("=== 1. LICZBA Z POBRANEGO MATERIALU PRZECHODZI ===")
sprawdz("12 (z `evidence` pobranego twierdzenia)",
        gates.numbers_outside_corpus("Wzroslo o 12 procent.", KARTA) == [])
sprawdz("41 (z `parallel_mechanisms` bez znacznika)",
        gates.numbers_outside_corpus("Powtorzylo sie 41 razy.", KARTA) == [])

print()
print("=== 2. LICZBA TYLKO Z WYPOWIEDZI MODELU NIE PRZECHODZI ===")
for liczba, skad in (("77", "ocena_ciekawosci"),
                     ("99", "parallel_mechanisms[z_banku]"),
                     ("83", "twierdzenie not_fetched")):
    wynik = gates.numbers_outside_corpus("W tekscie stoi %s." % liczba, KARTA)
    sprawdz("%s z %-28s -> zgloszone" % (liczba, skad), wynik == [liczba], wynik)

print()
print("=== 3. LICZBA ZNIKAD TEZ NIE PRZECHODZI ===")
sprawdz("liczba, ktorej nie ma nigdzie",
        gates.numbers_outside_corpus("Padlo 5555 razy.", KARTA) == ["5555"],
        gates.numbers_outside_corpus("Padlo 5555 razy.", KARTA))

print()
print("=== 4. KONTRDOWOD: PO STAREMU WSZYSTKIE TRZY PRZECHODZILY ===")
# Bez tego caly plik przechodzilby takze wtedy, gdyby te liczby nie
# wystepowaly w karcie w ogole — a wtedy nie mierzylby roznicy, tylko literowke.
_stary_korpus = gates._digit_tokens(json.dumps(KARTA, ensure_ascii=False))
for liczba, skad in (("77", "ocena_ciekawosci"),
                     ("99", "parallel_mechanisms[z_banku]"),
                     ("83", "twierdzenie not_fetched")):
    sprawdz("%s JEST w karcie (stary korpus by ja przepuscil)" % liczba,
            liczba in _stary_korpus, sorted(_stary_korpus))
sprawdz("a 5555 nie ma w karcie ani po staremu", "5555" not in _stary_korpus)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
