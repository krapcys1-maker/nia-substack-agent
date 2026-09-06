# -*- coding: utf-8 -*-
"""Konto jest instalacji, preset moze byc wspolny: uchwyt i marka z .env, placeholder blokuje podlacz.

## Po co ten plik istnieje

Cel repozytorium (6 wrzesnia 2026): ktos pobiera bota z GitHuba, podoba mu sie
preset `ai`, wpisuje klucze do `.env` i bot dziala — a w repozytorium zostaje
czysta wersja. Do tej pory uchwyt konta i nazwa marki siedzialy TYLKO w polu
`[konto]` presetu, wiec kazdy musialby edytowac wspolny plik `presety/ai/`,
a `podlacz ai` z placeholderem `your-handle` przechodzil bez slowa — bot
sprawdzalby potem konto o nazwie „your-handle" i pisal pod marka „Your AI
Publication".

Teraz: `SUBSTACK_HANDLE` i `NAZWA_MARKI` z `.env` nadpisuja `[konto]`
(w `config` przy starcie i w kazdym `rozwiaz`), `sprawdz` ostrzega przed
placeholderem, a `podlacz` odmawia. Wlasciciel instancji zapisuje uchwyt
faktycznie uzyty.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_konto_z_env.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2/tests")
import wlasna_konfiguracja  # noqa: E402

wlasna_konfiguracja.pomin_gdy_bez_tomllib("konto z .env, nie z presetu")

sys.path.insert(0, "agent-v2")
import config          # noqa: E402
import konfiguracja    # noqa: E402
import preset          # noqa: E402

BAZA = config.DOMYSLNE_SILNIKA
AI = pathlib.Path("presety/ai")
KONTO = {"SUBSTACK_HANDLE": "ktos-z-zewnatrz", "NAZWA_MARKI": "Ktos Pisze o AI"}
zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def oblewa(fabryka):
    try:
        fabryka()
        return None
    except preset.BladPresetu as exc:
        return str(exc)


def o_koncie(lista):
    return [x for x in lista if x.startswith("konto:")]


print("=== 1. WSPOLNY PRESET `ai` MA PLACEHOLDER; KONTO PRZYCHODZI Z .env ===")
ai = preset.wczytaj(AI)
sprawdz("presety/ai zostaje z placeholderem uchwytu (do dzielenia sie)",
        ai.pola.get("konto.uchwyt") == konfiguracja.PLACEHOLDER_UCHWYTU, ai.pola.get("konto.uchwyt"))
bledy, uwagi = preset.sprawdz(ai, config, BAZA, srodowisko={})
sprawdz("bez konta w srodowisku `sprawdz` NIE ma bledu (preset da sie ocenic bez konta)", not o_koncie(bledy), bledy)
sprawdz("  ale ostrzega i mowi, co wpisac do .env",
        any("SUBSTACK_HANDLE" in u and "NAZWA_MARKI" in u for u in o_koncie(uwagi)), uwagi)
bledy_a, _ = preset.sprawdz(ai, config, BAZA, srodowisko={}, do_aktywacji=True)
sprawdz("do aktywacji placeholder jest BLEDEM",
        any("placeholder" in b and "SUBSTACK_HANDLE" in b for b in o_koncie(bledy_a)), bledy_a)
bledy_b, uwagi_b = preset.sprawdz(ai, config, BAZA, srodowisko=dict(KONTO), do_aktywacji=True)
sprawdz("z uchwytem i marka w srodowisku aktywacja przechodzi kontrole konta",
        not o_koncie(bledy_b) and not o_koncie(uwagi_b), (bledy_b, uwagi_b))
proba, meldunki = preset.rozwiaz(ai, config, BAZA, srodowisko=dict(KONTO))
sprawdz("rozwiazane stale maja konto z .env, nie z presetu",
        proba.SUBSTACK_HANDLE == KONTO["SUBSTACK_HANDLE"] and proba.NAZWA_MARKI == KONTO["NAZWA_MARKI"],
        (proba.SUBSTACK_HANDLE, proba.NAZWA_MARKI))
sprawdz("  i meldunek to mowi", any("srodowisko ->" in m for m in meldunki), meldunki[-3:])
tylko_uchwyt = preset.sprawdz(ai, config, BAZA, srodowisko={"SUBSTACK_HANDLE": "ktos"}, do_aktywacji=True)[0]
sprawdz("sam uchwyt nie wystarczy: marka Your AI Publication tez jest placeholderem",
        any("marki" in b for b in o_koncie(tylko_uchwyt)), tylko_uchwyt)

print()
print("=== 2. KONTRDOWODY: PRESET Z PRAWDZIWYM KONTEM DZIALA BEZ .env, A .env I TAK WYGRYWA ===")
tekst_ai = (AI / "preset.toml").read_text(encoding="utf-8")
wlasny = preset.wczytaj_tekst(
    tekst_ai.replace('uchwyt = "your-handle"', 'uchwyt = "moj-uchwyt"')
            .replace('nazwa_marki = "Your AI Publication"', 'nazwa_marki = "Moja Gazeta"'),
    "wlasny.toml", plik=AI / "preset.toml", katalog=AI)
sprawdz("kontrdowod: podmiana w tekscie zadzialala",
        wlasny.pola["konto.uchwyt"] == "moj-uchwyt" and wlasny.pola["konto.nazwa_marki"] == "Moja Gazeta")
bledy_w, uwagi_w = preset.sprawdz(wlasny, config, BAZA, srodowisko={}, do_aktywacji=True)
sprawdz("preset z prawdziwym kontem przechodzi bez zadnej zmiennej w srodowisku",
        not o_koncie(bledy_w) and not o_koncie(uwagi_w), (bledy_w, uwagi_w))
proba_w, _ = preset.rozwiaz(wlasny, config, BAZA, srodowisko={})
sprawdz("  i uchwyt jest z presetu", proba_w.SUBSTACK_HANDLE == "moj-uchwyt")
proba_w2, _ = preset.rozwiaz(wlasny, config, BAZA, srodowisko=dict(KONTO))
sprawdz("instalacja (.env) wygrywa z presetem, gdy oba maja konto",
        proba_w2.SUBSTACK_HANDLE == KONTO["SUBSTACK_HANDLE"])
sprawdz("konfiguracja.placeholder_konta rozroznia: prawdziwe konto = pusta lista",
        konfiguracja.placeholder_konta("ktos", "Gazeta") == []
        and len(konfiguracja.placeholder_konta("", "Your Publication")) == 2)

print()
print("=== 3. PODLACZ: ODMOWA Z PLACEHOLDEREM, WLASCICIEL Z UCHWYTEM FAKTYCZNIE UZYTYM ===")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    agent = pathlib.Path(tmp) / "agent-v2"
    agent.mkdir()
    odm = oblewa(lambda: preset.podlacz(AI, agent, config, BAZA, srodowisko={}))
    sprawdz("podlacz ai bez konta w .env: odmowa", odm is not None and "SUBSTACK_HANDLE" in odm, odm)
    sprawdz("  i wskaznik nie powstal", not preset.wskaznik(agent).exists())
    akt, uwagi_p = preset.podlacz(AI, agent, config, BAZA, srodowisko=dict(KONTO))
    sprawdz("podlacz ai z kontem w .env: przechodzi", akt.preset.nazwa == "ai" and preset.wskaznik(agent).exists())
    wl = json.loads((akt.katalog_danych / preset.NAZWA_WLASCICIELA).read_text(encoding="utf-8"))
    sprawdz("wlasciciel instancji ma uchwyt z .env, nie placeholder",
            wl.get("uchwyt") == KONTO["SUBSTACK_HANDLE"], wl)
    inne = dict(KONTO, SUBSTACK_HANDLE="ktos-inny")
    odm2 = oblewa(lambda: preset.podlacz(AI, agent, config, BAZA, srodowisko=inne))
    sprawdz("ten sam preset, inne konto z .env, ta sama instancja: odmowa (inny wlasciciel)",
            odm2 is not None and "konto" in odm2, odm2)

print()
print("=== 4. START BOTA I SZABLON .env MOWIA TO SAMO ===")
zr = pathlib.Path("agent-v2/config.py").read_text(encoding="utf-8")
i_k = zr.index("KONTO_ZE_SRODOWISKA = _konf.konto_ze_srodowiska(")
sprawdz("config naklada konto ze srodowiska PO presecie i po starym TOML-u",
        i_k > zr.index("_aktywacja = _aktywacja_przy_starcie()")
        and i_k > zr.index("KONFIGURACJA_ZMIENILA = _konf.zastosuj(_dane_konfiguracji"))
env = pathlib.Path(".env.example").read_text(encoding="utf-8")
sprawdz(".env.example ma SUBSTACK_HANDLE= i NAZWA_MARKI=", "\nSUBSTACK_HANDLE=\n" in env and "\nNAZWA_MARKI=\n" in env)
sprawdz("README prowadzi od klonu przez .env do podlacz",
        "cp .env.example agent-v2/.env" in pathlib.Path("README.md").read_text(encoding="utf-8"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
