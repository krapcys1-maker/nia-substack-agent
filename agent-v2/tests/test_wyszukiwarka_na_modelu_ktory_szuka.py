# -*- coding: utf-8 -*-
"""Role, ktore musza szukac w sieci, chodza na modelu, ktory NAPRAWDE szuka — a brak wyszukiwan jest glosny.

## Pomiar, ktory to wywolal

14 wrzesnia 2026, cztery minimalne wywolania DeepSeek `/responses` z narzedziem
`web_search`, na serwerze:

    deepseek-flash, tool_choice auto          0 wyszukiwan, odpowiedz zmyslona
    deepseek-v4-flash (API oddaje flash)      0 wyszukiwan, model mysli, ze jest maj
    deepseek-flash, narzedzie wymuszone       wywolanie wypisane tekstem, niewykonane
    deepseek-v4-pro, tool_choice auto         7 wyszukiwan, poprawny adres

W tabeli `calls` od 10 wrzesnia kazde wywolanie tematow (`curiosity`), researchu
artykulu (`discovery`), sprawdzania faktow i stanu modeli mialo ZERO wyszukiwan
— przez cztery dni, bez slowa w logu. Kartridz serwera mial te role na
`deepseek-v4-flash`, a dostawca skierowal te nazwe na nowy model.

## Co ten test sprawdza

1. `napraw_role_wyszukiwania` przestawia role z wyszukiwarka z modelu bez niej
   i nie rusza pozostalych;
2. po zaladowaniu konfiguracji zadna rola z wyszukiwarka nie stoi na takim
   modelu, a naprawa idzie PO presecie i PO zamianach wersji;
3. `llm.call` z wyszukiwarka, ktore nie wykonalo wyszukiwania, mowi o tym
   glosno — i tylko w rolach, dla ktorych wyszukiwanie jest caloscia.

BEZ PYTESTA, bez sieci, bez platnych wywolan (transport podmieniony).
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wyszukiwarka_na_modelu_ktory_szuka.py
"""
import contextlib
import io
import pathlib
import sys
import tempfile
import types

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. NAPRAWA ROL ===")
cfg = types.SimpleNamespace(
    ROLE_Z_WYSZUKIWARKA=config.ROLE_Z_WYSZUKIWARKA,
    MODELE_BEZ_WYSZUKIWARKI=config.MODELE_BEZ_WYSZUKIWARKI,
    MODEL_WYSZUKIWARKI=config.MODEL_WYSZUKIWARKI,
    MODEL_FOR={"curiosity": "deepseek-flash", "discovery": "deepseek-v4-flash",
               "factcheck": "deepseek-v4-pro", "comment": "deepseek-flash"})
zmiany = config.napraw_role_wyszukiwania(cfg)
sprawdz("tematy z flasha na model z wyszukiwarka", cfg.MODEL_FOR["curiosity"] == config.MODEL_WYSZUKIWARKI, cfg.MODEL_FOR)
sprawdz("research ze starej nazwy flasha tez", cfg.MODEL_FOR["discovery"] == config.MODEL_WYSZUKIWARKI, cfg.MODEL_FOR)
sprawdz("rola juz na pro nietknieta", cfg.MODEL_FOR["factcheck"] == "deepseek-v4-pro")
sprawdz("komentarz (bez wyszukiwarki) zostaje na flashu — wybor wlasciciela",
        cfg.MODEL_FOR["comment"] == "deepseek-flash")
sprawdz("zmiany oddane do wypisania", sorted(z[0] for z in zmiany) == ["curiosity", "discovery"], zmiany)
sprawdz("model wyszukiwarki sam nie jest na liscie bez wyszukiwarki",
        config.MODEL_WYSZUKIWARKI not in config.MODELE_BEZ_WYSZUKIWARKI)

print()
print("=== 2. KONFIGURACJA PO ZALADOWANIU ===")
zle = {r: config.MODEL_FOR.get(r) for r in config.ROLE_Z_WYSZUKIWARKA
       if config.MODEL_FOR.get(r) in config.MODELE_BEZ_WYSZUKIWARKI}
sprawdz("zadna rola z wyszukiwarka na modelu, ktory nie szuka", not zle, zle)
ZR = io.open("agent-v2/config.py", encoding="utf-8").read()
i_preset = ZR.find("_preset.zastosuj(")
i_zamiany = ZR.find("_wersje_modeli.zastosuj(")
i_naprawa = ZR.find("in napraw_role_wyszukiwania():")
sprawdz("naprawa po presecie i po zamianach wersji", 0 < i_preset < i_zamiany < i_naprawa,
        (i_preset, i_zamiany, i_naprawa))

print()
print("=== 3. BRAK WYSZUKIWAN JEST GLOSNY ===")
config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
config.DRY_RUN = False
config.WOLNO_WOLAC_MODEL = True
config.DEEPSEEK_API_KEY = "test-key"
import db   # noqa: E402
import llm  # noqa: E402

CONN = db.connect()
RUN = db.start_run(CONN, "test-wyszukiwarki")


def wywolaj(rola, wyszukan, web_search=True):
    llm._call_deepseek_responses = lambda *a, **k: ('{"facts": []}', 100, 50, wyszukan, [])
    llm._call_deepseek = lambda *a, **k: ('{"facts": []}', 100, 50, 0, 0)
    bufor = io.StringIO()
    stary = config.MODEL_FOR.get(rola)
    config.MODEL_FOR[rola] = config.MODEL_WYSZUKIWARKI
    try:
        with contextlib.redirect_stdout(bufor):
            llm.call(rola, "system", "user", conn=CONN, run_id=RUN, web_search=web_search)
    finally:
        if stary is None:
            config.MODEL_FOR.pop(rola, None)
        else:
            config.MODEL_FOR[rola] = stary
    return bufor.getvalue()


wyjscie = wywolaj("curiosity", 0)
sprawdz("tematy bez ani jednego wyszukiwania: ostrzezenie w logu",
        "[wyszukiwarka] UWAGA: curiosity" in wyjscie, wyjscie[-300:])
wyjscie = wywolaj("curiosity", 5)
sprawdz("tematy z wyszukiwaniami: cisza", "[wyszukiwarka]" not in wyjscie, wyjscie[-300:])
wyjscie = wywolaj("reply", 0)
sprawdz("odpowiedz (wyszukiwanie opcjonalne) bez wyszukiwan: cisza",
        "[wyszukiwarka]" not in wyjscie, wyjscie[-300:])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
