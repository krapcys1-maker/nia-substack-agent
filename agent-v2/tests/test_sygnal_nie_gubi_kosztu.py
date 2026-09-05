# -*- coding: utf-8 -*-
"""Wywolanie przerwane sygnalem ma trafic do ksiag, nie zniknac.

## Wada, ktora ten plik pilnuje

`run.py` CELOWO zamienia SIGTERM na wyjatek (`_na_sygnale`, ~2246), zeby
przebieg zdazyl sie zapisac, gdy systemd utnie go po `TimeoutStartSec`. Rzuca
`KeyboardInterrupt`.

A `llm.call` lapal `except Exception` — i `KeyboardInterrupt` NIE JEST podklasa
`Exception`. Przelatywal wiec tedy bez zatrzymania.

Skutek byl rozdzielony na dwa poziomy i to jest cala trudnosc: PRZEBIEG
zapisywal sie poprawnie (pilnuje tego `test_czas.py`), ale WYWOLANIE W LOCIE
nie trafialo do `calls` w ogole. `db.spent_usd` czyta wlasnie `calls`, wiec
sufit dzienny, miesieczny i przebiegu nie widzialy pieniedzy wydanych na
wywolanie, ktore akurat trwalo, gdy przyszedl sygnal.

Traci sie przy tym NAJDROZSZE. Sygnal przychodzi po `TimeoutStartSec`, czyli
trafia dokladnie w te wywolania, ktore trwaly najdluzej — a czas idzie
z tokenami wyjscia.

Zmierzone przed poprawka: ten sam kod z `RuntimeError` zapisywal wiersz,
z `KeyboardInterrupt` nie zapisywal nic.

## Dlaczego `except BaseException` jest tu poprawne

Zwykle jest bledem, bo polyka sygnaly. Tutaj nie polyka: zapisujemy wiersz
i PODAJEMY WYJATEK DALEJ. Sygnal ma nadal zatrzymac przebieg — chodzi wylacznie
o to, zeby po sobie posprzatal. Sekcja 3 pilnuje wlasnie tego i bez niej
poprawka mogla by po cichu zamienic sie w polykacz sygnalow.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_sygnal_nie_gubi_kosztu.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
# DWA PRZELACZNIKI, KAZDY Z INNEGO POWODU.
#
# `DRY_RUN = False` — bo inaczej `llm.call` konczy sie na nim ZANIM dojdzie do
# wywolania, i caly ten plik przechodzilby nie badajac niczego.
#
# `WOLNO_WOLAC_MODEL = True` — bo pod testem zapora platnych wywolan jest
# opuszczona i sama podnosi `PreflightFailed`. Pierwsza wersja tego pliku
# zdjela tylko `DRY_RUN` i oblala szesc razy na tej zaporze; zapora zadzialala
# dokladnie tak, jak ma.
#
# ZADEN PLATNY RUCH STAD NIE WYJDZIE: `_call_deepseek` jest podmieniony na
# funkcje, ktora tylko rzuca wyjatkiem, wiec siec nie jest dotykana ani razu.
config.DRY_RUN = False
config.WOLNO_WOLAC_MODEL = True

import db    # noqa: E402
import llm   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


CONN = db.connect()
RUN = db.start_run(CONN, "test-sygnalu")


def ile_w_ksiegach() -> int:
    return CONN.execute("SELECT COUNT(*) FROM calls WHERE run_id=?",
                        (RUN,)).fetchone()[0]


def wywolaj_z(wyjatek) -> tuple[str, int, int]:
    """Podstawia wybuch pod dostawce i oddaje (typ, przed, po)."""
    def wybuch(*a, **k):
        raise wyjatek
    llm._call_deepseek = wybuch
    llm._call_deepseek_responses = wybuch
    przed = ile_w_ksiegach()
    nazwa = type(wyjatek).__name__
    try:
        llm.call("cele", "system", "user", conn=CONN, run_id=RUN)
    except BaseException as exc:                                 # noqa: BLE001
        nazwa = type(exc).__name__
    return nazwa, przed, ile_w_ksiegach()


print("=== 1. ZWYKLA AWARIA DOSTAWCY TRAFIA DO KSIAG ===")
# Tak bylo zawsze i ma zostac — bez tego nie widac, ze sekcja 2 cokolwiek zmienia.
_, przed, po = wywolaj_z(RuntimeError("dostawca padl"))
sprawdz("awaria dostawcy zapisana", po == przed + 1, (przed, po))

print()
print("=== 2. SYGNAL TEZ — I TO JEST TA POPRAWKA ===")
# `KeyboardInterrupt` to dokladnie to, co `run.py` rzuca po SIGTERM.
for wyjatek in (KeyboardInterrupt("przerwany sygnalem SIGTERM"), SystemExit(1)):
    nazwa, przed, po = wywolaj_z(wyjatek)
    sprawdz("  %s zapisany" % nazwa, po == przed + 1, (przed, po))

sprawdz("KeyboardInterrupt naprawde NIE jest Exception",
        not issubclass(KeyboardInterrupt, Exception))

print()
print("=== 3. ALE WYJATEK LECI DALEJ — NIE POLYKAMY SYGNALU ===")
# Bez tego poprawka zamienilaby sie w cos gorszego od wady: przebieg, ktorego
# nie da sie zatrzymac SIGTERM-em, bo `llm.call` zjada sygnal i wraca po wiecej.
def _przepuszcza(wyjatek) -> bool:
    def wybuch(*a, **k):
        raise wyjatek
    llm._call_deepseek = wybuch
    llm._call_deepseek_responses = wybuch
    try:
        llm.call("cele", "system", "user", conn=CONN, run_id=RUN)
    except BaseException as exc:                                 # noqa: BLE001
        return type(exc) is type(wyjatek)
    return False


sprawdz("KeyboardInterrupt wychodzi na zewnatrz",
        _przepuszcza(KeyboardInterrupt("sygnal")))
sprawdz("SystemExit wychodzi na zewnatrz", _przepuszcza(SystemExit(1)))

print()
print("=== 4. ZAPIS MOWI, CO SIE STALO ===")
# Kwoty nie zgadujemy — nieudane wywolanie ma koszt „nie wiadomo". Ale POWOD
# ma byc w wierszu, inaczej za tydzien nikt nie odrozni sygnalu od awarii.
wiersze = CONN.execute("SELECT ok, note FROM calls WHERE run_id=?", (RUN,)).fetchall()
sprawdz("wszystkie zapisane jako nieudane", all(r[0] == 0 for r in wiersze),
        [r[0] for r in wiersze])
sprawdz("i kazdy niesie nazwe wyjatku",
        all(r[1] and ":" in str(r[1]) for r in wiersze),
        [str(r[1])[:34] for r in wiersze])
sprawdz("w tym wiersz o sygnale",
        any("KeyboardInterrupt" in str(r[1]) for r in wiersze))

print()
print("=== 5. KONTRDOWOD: `except Exception` BY TEGO NIE ZLAPAL ===")
# Bez tego caly plik przechodzilby takze wtedy, gdyby ktos cofnal poprawke,
# a testy dalej pokazywalyby zielono.
zlapane = False
try:
    try:
        raise KeyboardInterrupt("sygnal")
    except Exception:                                            # noqa: BLE001
        zlapane = True
except BaseException:
    pass
sprawdz("sam `except Exception` NIE lapie sygnalu", not zlapane)
zrodlo = pathlib.Path("agent-v2/llm.py").read_text(encoding="utf-8")
sprawdz("a `llm.call` lapie BaseException", "except BaseException as exc" in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
