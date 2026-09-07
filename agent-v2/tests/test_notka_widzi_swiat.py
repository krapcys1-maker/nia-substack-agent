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

    def zaczyn_z_kanalow(*a, **k):
        if wyjatek is not None:
            raise wyjatek
        return wynik

    modul.zaczyn_z_kanalow = zaczyn_z_kanalow
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
    # TO JEST CALY SENS TEGO PLIKU. Bez tego zdania pisarz streszcza naglowki.
    instrukcja = (tlo.get("how_to_use_it", "") if isinstance(tlo, dict) else "").lower()
    sprawdz("zakaz referowania jedzie razem z naglowkami",
            "do not report it" in instrukcja, instrukcja[:120])
    sprawdz("zakaz obejmuje takze streszczanie i cytowanie",
            "summarise" in instrukcja and "quote a headline" in instrukcja,
            instrukcja[:160])
    sprawdz("wolno pominac tlo — wiekszosc dni bez niego",
            "not come up at all" in instrukcja, instrukcja[:160])

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
        personality.short_form = lambda conn, run_id, kind, material: (
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
    sprawdz("temat z listy persony nadal jest",
            material.get("theme") == "a deadline nobody set, enforced by a timer",
            repr(material.get("theme"))[:80])

finally:
    if stary_stages is not None:
        sys.modules["stages"] = stary_stages
    else:
        sys.modules.pop("stages", None)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
