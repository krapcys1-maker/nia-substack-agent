# -*- coding: utf-8 -*-
"""Kandydat blisko starego tematu idzie na koniec kolejki, a nie do kosza.

## Skad to sie wzielo

9 wrzesnia 2026, tuz przed puszczeniem artykulu, zmierzono szesc kandydatur
z zywego banku wobec dwoch juz opublikowanych tekstow. Udzial wspolnych
rdzeni, prog powtorki 0,20:

    ranga 0   0,161   agenty ogrywajace swoja ocene w piaskownicy
    ranga 1   0,036
    ranga 2   0,067
    ranga 3   0,042
    ranga 4   0,077
    ranga 5   0,069

Straznik powtorek przepuscil pierwszego — 0,161 to mniej niz 0,20 — i to on
mial isc do pisania, bo sedzia banku dal mu range 0. Byl to jednak temat
CZTEROKROTNIE blizszy staremu niz kazdy inny w banku, a oba opublikowane
teksty mowily o agentach ogrywajacych zasady. Formalnie bez powtorki; dla
czytelnika ten sam artykul trzeci raz z rzedu.

Przyczyna jest ukladowa, nie przypadkowa. Sedzia banku ocenia jakosc i NIE WIE
nic o tym, co juz wyszlo. Straznik wie, ale jest bramka zero-jedynkowa: nie
odroznia „ledwo przeszedl" od „zupelnie inna dziedzina". Miedzy nimi nie ma
nikogo, kto by powiedzial: skoro obok leza tematy z medycyny, genomiki
i Kongresu, to niech pojda pierwsze.

## Regula

Kandydat powyzej POLOWY progu jest DEGRADOWANY, nie odrzucany. Idzie za tymi,
ktore sa wyraznie swieze, i wraca do gry, gdy innych nie ma — bo artykul ma
powstac takze wtedy, gdy caly bank jest bliski. Twarda granica zostaje tam,
gdzie byla.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_temat_dalej_od_napisanych.py
"""
import io
import sys
from unittest.mock import patch

sys.path.insert(0, "agent-v2")
import config           # noqa: E402
import stages           # noqa: E402
import artykul_z_puli as art   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# TEKSTY PRZEPISANE Z PRODUKCJI, nie wymyslone.
NAPISANE = [
    "The Double-Edged Knowledge Commons Your agent's constitution can't enforce "
    "itself Giving AI agents a constitution sounds grand collusion governance "
    "agents coordinating rules enforcement sanctions",
]

BLISKI = {"fact": "OpenAI's own post-breach report describes the incident as reward "
                  "hacking: agents working inside a sandbox on evaluation tasks "
                  "coordinating around the rules they were given",
          "domain": "AI agent safety and evals", "url": "https://example.org/blisko",
          "ranga": 0, "na_artykul": True}
DALEKI = {"fact": "The FDA cleared Vitestro's Aletta, the first autonomous "
                  "blood-draw device authorized for clinical use in hospitals",
          "domain": "medical robotics", "url": "https://example.org/daleki",
          "ranga": 3, "na_artykul": False}
DALEKI2 = {"fact": "A petabyte genomics atlas was released free of charge for "
                   "non-commercial laboratory research",
           "domain": "life sciences", "url": "https://example.org/daleki2",
           "ranga": 4, "na_artykul": False}


def wybierz(kandydaci, napisane=NAPISANE):
    """Uruchamia `wybierz_fakt` na podstawionej pamieci i banku."""
    with patch.object(stages, "wez_kandydatow", return_value=list(kandydaci)), \
         patch.object(stages, "tematy_do_porownania", return_value=list(napisane)), \
         patch.object(stages, "ostatnie_notki", return_value=[]), \
         patch.object(stages, "zwroc_kandydatow", return_value=0), \
         patch.object(stages, "znajdz_ciekawostki", return_value=[]):
        import research_tasks
        with patch.object(research_tasks, "decision", return_value=None):
            return art.wybierz_fakt(None, 1)


print("=== 1. BLISKI USTEPUJE DALEKIEMU, MIMO LEPSZEJ RANGI ===")
# Dokladnie uklad z produkcji: najlepiej oceniony jest zarazem najblizszy.
f = wybierz([BLISKI, DALEKI, DALEKI2])
sprawdz("wybrany NIE jest ten bliski staremu tematowi",
        f and f["url"] != BLISKI["url"], str((f or {}).get("url")))
sprawdz("wybrany jest ktorys z odleglych",
        f and f["url"] in (DALEKI["url"], DALEKI2["url"]),
        str((f or {}).get("url")))

print()
print("=== 2. WSROD ODLEGLYCH NADAL DECYDUJE RANGA ===")
# Degradacja dotyczy bliskich. Miedzy swiezymi kolejnosc sedziego zostaje.
f = wybierz([DALEKI2, DALEKI])
sprawdz("kolejnosc wejsciowa zachowana", f and f["url"] == DALEKI2["url"],
        str((f or {}).get("url")))

print()
print("=== 3. GDY WSZYSCY SA BLISCY, ARTYKUL I TAK POWSTAJE ===")
# Degradacja nie moze zamienic sie w odrzucenie. Doktryna tego repo: po
# oplaconym researchu tekst MUSI powstac.
f = wybierz([BLISKI])
sprawdz("jedyny bliski kandydat zostaje wybrany",
        f and f["url"] == BLISKI["url"], str((f or {}).get("url")))

print()
print("=== 4. TWARDA GRANICA SIE NIE ZMIENILA ===")
# KONTRDOWOD. Gdyby ktos pomylil degradacje z zaostrzeniem progu, temat
# naprawde powtorzony przestalby byc odrzucany albo przeciwnie — odrzucanoby
# wszystko powyzej polowy. Powtorzenie wprost ma nadal odpadac.
POWTORKA = {"fact": NAPISANE[0], "domain": "collusion governance",
            "url": "https://example.org/powtorka", "ranga": 0}
f = wybierz([POWTORKA, DALEKI])
sprawdz("jawna powtorka odpada", f and f["url"] == DALEKI["url"],
        str((f or {}).get("url")))
sprawdz("prog w kodzie to nadal polowa, nie nowa bramka",
        'stages.POWTORKA_TEMATU["prog"] / 2' in
        io.open("agent-v2/artykul_z_puli.py", encoding="utf-8").read())

print()
print("=== 5. BEZ HISTORII NIC SIE NIE DEGRADUJE ===")
# Swieze konto: `tematy_do_porownania` oddaje pustke i kazdy udzial to zero.
f = wybierz([BLISKI, DALEKI], napisane=[])
sprawdz("pierwszy z rankingu wygrywa", f and f["url"] == BLISKI["url"],
        str((f or {}).get("url")))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
