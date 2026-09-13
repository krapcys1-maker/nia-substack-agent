# -*- coding: utf-8 -*-
"""Notka persony dostaje TLO ZE SWIATA — i ma go NIE referowac.

## Po co ten plik istnieje

Notka persony nie widziala swiata w ogole. `personality.notes` brala temat
z listy `[osobowosc] tematy` i podawala go pisarzowi bez niczego wiecej: bez
researchu, bez faktu, bez jednego zdania o tym, co sie w tej branzy stalo.
Przy dwoch notkach dziennie lista dwudziestu tematow zamyka petle co dziesiec
dni, a kazda notka mogla powstac rownie dobrze pol roku wczesniej.

PIERWSZA PROBA BYLA BLEDNA i to jest tu zapisane, zeby nikt jej nie powtorzyl:
podpiete zostalo `aktualne_modele`, ktore oddaje SPIS NAZW I WERSJI („GPT-6
Astra (2026-09), Claude Opus 5 (2026-07)..."). Modul sam opisuje swoj wynik
jako „a list to check a name against, not material" — powstal po to, zeby
pisarz nie napisal o modelu wycofanym z API, a nie po to, zeby bylo o czym
pisac. Spis nazw nie jest wydarzeniem i nie ma sie do czego odniesc.

Zrodlem jest wiec `stages.zaczyn_z_kanalow`: tytul, kanal i data z kanalow
RSS presetu. To sa WYDARZENIA, i nie kosztuja ani grosza, bo to samo
pobieranie, bez wywolania modelu.

## Czego pilnuje ten plik

Ramki. Sam wykaz naglowkow podany pisarzowi konczy sie tym, ze pisarz je
REFERUJE — a `glos_notki` zabrania tego wprost („not a news report"). Konto
zamienia sie wtedy w serwis informacyjny z zarcikami, czyli w to, czym jest
juz pol Substacka. Dlatego test zada, zeby zakaz referowania jechal razem
z naglowkami, w tym samym slowniku, zawsze.

Do tego trzy sytuacje, w ktorych notka MA POWSTAC MIMO WSZYSTKO: kanaly
milcza, kanaly nie odpowiadaja, pobieranie rzuca wyjatkiem. Notka bez tla
jest mniej aktualna; brak notki jest gorszy.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_notka_widzi_swiat.py
"""
import sys
import types

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


def podstaw_kanaly(wynik=None, wyjatek=None):
    """Fałszywy `stages` w `sys.modules` — `_swiat` importuje go leniwie."""
    modul = types.ModuleType("stages")

    wywolania = []

    def zaczyn_z_kanalow(*a, **k):
        wywolania.append(k)
        if wyjatek is not None:
            raise wyjatek
        return wynik

    modul.zaczyn_z_kanalow = zaczyn_z_kanalow
    # ODCISKI WYSTAWIONYCH NOTEK — od 9 wrzesnia 2026 `_swiat` je przekazuje,
    # zeby pozycja, o ktorej juz pisalismy, nie wracala do dwunastki. Atrapa bez
    # tej funkcji dawala `AttributeError`, a `_swiat` — oslonieta szerokim
    # `except` — oddawala pusty napis. Cztery sprawdzenia nizej oblewaly wtedy
    # z powodu, ktory nie mial nic wspolnego z ich trescia.
    modul.pamiec_wystawionych = lambda: [frozenset({"grzyby", "mushro"})]
    modul.wywolania = wywolania
    sys.modules["stages"] = modul


NAGLOWKI = ("- [2026-09-04] Ars Technica AI — OpenAI agents discussed ways to "
            "escape their sandbox\n"
            "- [2026-09-03] Latent Space — GPT-6 Astra: an AI Engineer for <$6 an hour")

stary_stages = sys.modules.get("stages")
try:
    print("=== 1. SA NAGLOWKI: WCHODZA RAZEM Z ZAKAZEM REFEROWANIA ===")
    podstaw_kanaly(NAGLOWKI)
    tlo = personality._swiat()
    sprawdz("tlo jest slownikiem, nie golym napisem", isinstance(tlo, dict), repr(tlo)[:80])
    sprawdz("naglowki doszly w calosci",
            isinstance(tlo, dict) and NAGLOWKI in tlo.get("headlines", ""),
            repr(tlo)[:120] if isinstance(tlo, dict) else repr(tlo))
    # TO JEST CALY SENS TEGO PLIKU: swiat ma byc TEMATEM, ale jedna rzecza.
    # Pierwsza wersja ramki mowila „w wiekszosc dni nie pojawi sie w ogole"
    # i byla odwrotnoscia tego, co zamawiaja rubryki kartridza („wez jeden
    # naglowek z tla"). Preset prosil o swiat, silnik odradzal.
    instrukcja = (tlo.get("how_to_use_it", "") if isinstance(tlo, dict) else "").lower()
    sprawdz("swiat jest tematem, nie dodatkiem",
            "your subject on most days" in instrukcja, instrukcja[:150])
    sprawdz("ma wziac JEDNA rzecz", "pick one thing" in instrukcja, instrukcja[:150])
    sprawdz("nie wolno robic przegladu prasy",
            "never a news feed" in instrukcja and "do not list" in instrukcja
            and "never mention a second item" in instrukcja, instrukcja[:200])
    sprawdz("naglowka nadal sie nie cytuje",
            "quote a headline" in instrukcja, instrukcja[:200])
    sprawdz("wolno pominac news i wybrac opinie, fikcje albo historie projektu",
            "ignore all of it" in instrukcja and "an opinion" in instrukcja
            and "fictional office bit" in instrukcja and "supplied project history" in instrukcja,
            instrukcja)
    sprawdz("brak newsow nie uprawnia do zmyslania wlasnych zdarzen",
            "do not invent an event in your life" in instrukcja, instrukcja)
    # KONTRDOWOD DLA STAREJ RAMKI: gdyby wrocila, ten test ma oblac.
    sprawdz("stara ramka 'not come up at all' NIE wrocila",
            "not come up at all" not in instrukcja, instrukcja[:200])

    print()
    print("=== 2. TRZY SPOSOBY, ZEBY SWIAT ZAMILKL — NOTKA MA POWSTAC ===")
    # `zaczyn_z_kanalow` ma wlasna oslone i oddaje NAPIS zastepczy, a nie
    # wyjatek. Napis podany pisarzowi jako „swiat" bylby material do zartu
    # o tym, ze nic sie nie stalo — a nie stalo sie nic tylko u nas.
    for zastepczy in personality.ZASTEPCZE_ZACZYNY:
        podstaw_kanaly(zastepczy)
        sprawdz("napis zastepczy %r to brak tla" % zastepczy,
                personality._swiat() == "", repr(personality._swiat()))
    podstaw_kanaly("   \n  ")
    sprawdz("same biale znaki to brak tla", personality._swiat() == "")
    podstaw_kanaly(wyjatek=RuntimeError("kanal padl"))
    sprawdz("wyjatek przy pobieraniu NIE przerywa notki",
            personality._swiat() == "")

    print()
    print("=== 3. NOTKA NAPRAWDE DOSTAJE TO TLO ===")
    # Kontrdowod dla sekcji 1: `_swiat` moglby oddawac idealne tlo i nikt by go
    # nie podawal dalej. Podgladamy material, ktory `notes` wklada pisarzowi.
    podstaw_kanaly(NAGLOWKI)
    zebrane = []
    stary_short_form = personality.short_form
    stara_pamiec = personality.memory
    stary_stan = personality.memory_state
    stare_staty = personality.statistics
    # TEMAT PODSTAWIAMY SAMI, i to nie jest ozdoba testu. `PERSONA_TEMATY`
    # przychodzi z PODLACZONEGO KARTRIDZA — na maszynie z presetem lista jest
    # pelna, a na czystym drzewie (CI, swiezy klon) pusta, wiec `notes` spada na
    # `config.NISZA`, ktora tam tez jest pusta. Test opierajacy sie na tym, co
    # akurat podlaczone, przechodzi u autora i oblewa u wszystkich innych.
    stare_tematy = config.PERSONA_TEMATY
    config.PERSONA_TEMATY = ("a deadline nobody set, enforced by a timer",)
    try:
        personality.short_form = lambda conn, run_id, kind, material, **_kw: (
            zebrane.append(material) or {})
        personality.memory = lambda *a, **k: []
        personality.memory_state = lambda *a, **k: {"intro": True}
        personality.statistics = lambda *a, **k: {}
        personality.notes(None, None, ile=1)
    finally:
        personality.short_form = stary_short_form
        personality.memory = stara_pamiec
        personality.memory_state = stary_stan
        personality.statistics = stare_staty
        config.PERSONA_TEMATY = stare_tematy
    sprawdz("pisarz dostal jakis material", bool(zebrane), repr(zebrane)[:80])
    material = zebrane[0] if zebrane else {}
    sprawdz("material niesie klucz `world`", "world" in material,
            ", ".join(sorted(material)))
    sprawdz("i sa w nim te same naglowki",
            NAGLOWKI in (material.get("world") or {}).get("headlines", ""),
            repr(material.get("world"))[:120])
    # OKNO SWIEZOSCI. Bez niego do promptu wchodzil wpis sprzed trzech tygodni
    # podany jako „o czym sie mowi w tym tygodniu" — zmierzone 7 wrzesnia 2026
    # na zywych kanalach: dwie z dwunastu pozycji byly starsze niz tydzien.
    k = sys.modules["stages"].wywolania[-1] if sys.modules["stages"].wywolania else {}
    sprawdz("notka prosi o okno swiezosci", k.get("max_dni") == 14, str(k))
    sprawdz("i o skroty, bo z naglowka nie da sie nic wytlumaczyc",
            k.get("ze_skrotem") is True, str(k))
    sprawdz("temat z listy persony nadal jest",
            material.get("theme") == "a deadline nobody set, enforced by a timer",
            repr(material.get("theme"))[:80])

finally:
    if stary_stages is not None:
        sys.modules["stages"] = stary_stages
    else:
        sys.modules.pop("stages", None)

print()
print()
print("=== ODCISKI WYSTAWIONYCH NOTEK IDA DO SELEKTORA ===")
# CALA POPRAWKA Z 9 WRZESNIA 2026. 8 wrzesnia o 01:43 poszla notka o tym, ze
# najlepszy model rozpoznaje grzyby w 65% przypadkow; 9 wrzesnia o 01:15 poszla
# druga, o tym samym, innymi slowami. Audyt zglosil to sam:
# „POWTORKA 2026-09-08 / 2026-09-09, 1 par w 5 notkach".
#
# Wykluczenie po ADRESIE nie mialo szans — starsza notka ma `source_urls=None`.
# A straznicy rdzeni, ktorzy zlapaliby to bez trudu (zmierzone na obu tekstach:
# dwanascie wspolnych rdzeni, udzial 0,353 przy progu 0,30), siedza na sciezce
# banku ciekawostek i TEN plik nie wolal ich ani razu.
podstaw_kanaly(NAGLOWKI)
personality._swiat()
k = sys.modules["stages"].wywolania[-1]
sprawdz("selektor dostaje odciski wystawionych notek",
        k.get("opisane_rdzenie") is not None, str(sorted(k))[:90])
sprawdz("i nie sa puste", bool(k.get("opisane_rdzenie")), str(k.get("opisane_rdzenie")))
sprawdz("adresy nadal wykluczane obok", "exclude_urls" in k, str(sorted(k))[:90])

print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
