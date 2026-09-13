# -*- coding: utf-8 -*-
"""Nazwa rubryki jest DLA NAS. Model jej nie dostaje i nie ma jej wypisac.

## Po co ten plik istnieje

Rubryki w `[osobowosc] tematy` zaczynaja sie od wersalikowej nazwy
(„PARAGONY: ...", „HOT TAKE: ..."), bo po niej mierzymy pozniej, ktory format
sie broni. Nazwa szla jednak do modelu RAZEM z poleceniem.

ZNALEZIONE 7 wrzesnia 2026 przy pierwszej probie `gpt-5.6-sol`. Notka zaczela
sie tak:

    „PARAGONY reads the articles, not the Notes."

Model wzial polska etykiete za NAZWE SYSTEMU i wpisal ja do tekstu, ktory szedl
na konto. Fable i Opus czytaly ja jako naglowek i nigdy nie powtarzaly, wiec
wada byla NIEWIDOCZNA — az do zmiany pisarza. To jest jej najgorsza cecha:
nie zglasza sie sama, tylko czeka na inny model.

## Dwie warstwy, bo jedna nie wystarcza

ROZDZIELENIE — do modelu idzie samo polecenie. Chroni przed przepisaniem
etykiety z instrukcji, czyli przed tym, co sie faktycznie stalo.

BRAMKA — tekst z etykieta nie wychodzi, nawet gdyby model wzial ja skadinad.
Jedna notka z „PARAGONY" juz opublikowana wraca przez pamiec (`recent_published`)
do nastepnych promptow, wiec samo rozdzielenie zamykaloby drzwi po wyjsciu
konia.

Etykieta zostaje w dzienniku jako `rubryka` — pomiar ma dzialac dalej.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_etykieta_rubryki_nie_wycieka.py
"""
import sys

sys.path.insert(0, "agent-v2")
import config       # noqa: E402
import personality  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


RUBRYKA = ("PARAGONY: your own failure, admitted first, before a stiffer "
           "colleague files it.")
POLECENIE = "your own failure, admitted first, before a stiffer colleague files it."

print("=== 1. ROZDZIELANIE ===")
sprawdz("etykieta odcieta od polecenia",
        personality._rozdziel_rubryke(RUBRYKA) == ("PARAGONY", POLECENIE),
        str(personality._rozdziel_rubryke(RUBRYKA)))
sprawdz("apostrof w nazwie nie psuje wzorca",
        personality._rozdziel_rubryke("EXPLAIN IT LIKE I'M TIRED: wez naglowek.")
        == ("EXPLAIN IT LIKE I'M TIRED", "wez naglowek."))
sprawdz("temat bez etykiety zostaje w calosci",
        personality._rozdziel_rubryke("a plain topic") == ("", "a plain topic"))
# KONTRDOWOD: zwykle zdanie z dwukropkiem NIE jest etykieta, bo inaczej
# rozdzielacz zjadalby poczatek prawdziwego polecenia.
sprawdz("zdanie z dwukropkiem to nie etykieta",
        personality._rozdziel_rubryke("Ask this: what changed?")
        == ("", "Ask this: what changed?"),
        str(personality._rozdziel_rubryke("Ask this: what changed?")))

print()
print("=== 2. MODEL DOSTAJE POLECENIE, DZIENNIK DOSTAJE NAZWE ===")
stare_tematy = config.PERSONA_TEMATY
stary_short_form = personality.short_form
stara_pamiec = personality.memory
stary_stan = personality.memory_state
stare_staty = personality.statistics
stary_swiat = personality._swiat
zebrane = []
try:
    config.PERSONA_TEMATY = (RUBRYKA,)
    personality.short_form = lambda conn, run_id, kind, material, **_kw: (
        zebrane.append(material) or {})
    personality.memory = lambda *a, **k: []
    personality.memory_state = lambda *a, **k: {"intro": True}
    personality.statistics = lambda *a, **k: {}
    personality._swiat = lambda *a, **k: ""
    wynik = personality.notes(None, None, ile=1)
finally:
    config.PERSONA_TEMATY = stare_tematy
    personality.short_form = stary_short_form
    personality.memory = stara_pamiec
    personality.memory_state = stary_stan
    personality.statistics = stare_staty
    personality._swiat = stary_swiat

material = zebrane[0] if zebrane else {}
sprawdz("model dostal samo polecenie", material.get("theme") == POLECENIE,
        repr(material.get("theme"))[:90])
sprawdz("i NIE dostal nazwy rubryki", "PARAGONY" not in str(material.get("theme")),
        repr(material.get("theme"))[:90])
wpis = (wynik[0].get("personality") if wynik else {}) or {}
sprawdz("dziennik zapamietal nazwe do pomiaru", wpis.get("rubryka") == "PARAGONY",
        repr(wpis.get("rubryka")))
sprawdz("i pelny temat, zeby odsiewanie piatki dzialalo",
        wpis.get("theme") == RUBRYKA, repr(wpis.get("theme"))[:90])

print()
print("=== 3. BRAMKA: TEKST Z NAZWA NIE WYCHODZI ===")
try:
    config.PERSONA_TEMATY = (RUBRYKA,)
    zly = "PARAGONY reads the articles, not the Notes. Admire the governance model."
    dobry = "The fact-check reads the articles, not the Notes. Admire it from afar."
    sprawdz("notka z nazwa rubryki odrzucona", personality._valid(zly, 600) is False)
    sprawdz("ta sama mysl bez nazwy przechodzi", personality._valid(dobry, 600) is True)
finally:
    config.PERSONA_TEMATY = stare_tematy

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
