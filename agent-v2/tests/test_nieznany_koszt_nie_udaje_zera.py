# -*- coding: utf-8 -*-
"""Nieudane wywolanie ma koszt NIEZNANY, nie zerowy — i widac to w podsumowaniu.

## Wada, ktora ten plik pilnuje

`llm.call` po wyczerpaniu ponowien zapisuje wiersz z `cost_usd=0.0`,
`price_verified=0` i `ok=0`. Robi to SWIADOMIE i slusznie: jego komentarz
mowi, ze „zgadnieta kwota w zapisie finansowym jest gorsza niz jej brak".

Podsumowanie przebiegu tego nie odrozniało. `_summary` sumowalo `cost_usd`
i liczylo `COUNT(*)`, wiec nieudana proba wchodzila do LICZBY wywolan,
wnosila zero do KWOTY i nic tego nie sygnalizowalo. Dzien z trzema padnietymi
`curiosity` — kazde po dwoch ponowieniach, czyli dziewiec zadan wyslanych do
dostawcy — meldowal sie jak dzien bez strat.

ZMIERZONE NA ZYWO 5 wrzesnia 2026, na prawdziwej awarii DeepSeeka
(`RemoteProtocolError: peer closed connection`): wiersz w `calls` POWSTAJE,
`ok=0`, `price_verified=0`, `note` niesie typ bledu. Suma jest wiec DOLNA
granica rachunku, nie rachunkiem — i podsumowanie ma to mowic.

Uwaga metodyczna: pierwszy odczyt tej awarii pokazal ZERO wierszy w `calls`
i wygladal na powazniejsza wade. Byl bledny — to moj wlasny `timeout` zabijal
proces przed zapisem. Dopiero przebieg z wiekszym zapasem czasu pokazal
prawde. Stad ten test mierzy stan bazy, a nie to, co widac w konsoli.

## Czego ten plik pilnuje w DRUGA strone

Zeby przebieg BEZ awarii nie dostawal doklejki o niczym. Sekcja 1.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_nieznany_koszt_nie_udaje_zera.py
"""
import io
import contextlib
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
import db   # noqa: E402
import run as runmod  # noqa: E402

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


def udane(rid, usd=0.05, verified=1):
    db.record_call(conn=CONN, run_id=rid, provider="deepseek", model="m",
                   purpose="note", tokens_in=10, tokens_out=10, web_searches=0,
                   cost_usd=usd, price_verified=verified, ok=1, note=None)


def nieudane(rid):
    # KSZTALT ZMIERZONY NA ZYWO przy awarii dostawcy.
    db.record_call(conn=CONN, run_id=rid, provider="deepseek", model="m",
                   purpose="curiosity", tokens_in=0, tokens_out=0,
                   web_searches=0, cost_usd=0.0, price_verified=0, ok=0,
                   note="RemoteProtocolError: peer closed connection")


def podsumuj(rid):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        runmod._summary(CONN, rid)
    return buf.getvalue().strip()


print("=== 1. PRZEBIEG BEZ AWARII: BEZ DOKLEJKI ===")
udane(1); udane(1)
czysty = podsumuj(1)
print("    %s" % czysty)
sprawdz("nie ma slowa o nieudanych", "NIEZNANYM" not in czysty)
sprawdz("nie ma slowa o stawce", "niepotwierdzonej" not in czysty)
sprawdz("kwota i liczba sie zgadzaja",
        "$0.1000" in czysty and "2 wywołaniach" in czysty, czysty)

print()
print("=== 2. AWARIE SA WIDOCZNE ===")
udane(2); nieudane(2); nieudane(2); nieudane(2)
z_awaria = podsumuj(2)
print("    %s" % z_awaria)
sprawdz("podsumowanie mowi o NIEZNANYM koszcie", "NIEZNANYM koszcie: 3" in z_awaria,
        z_awaria)
# KONTRDOWOD: kwota nadal jest tylko z udanych, wiec bez tej doklejki
# przebieg wygladalby na tanszy, niz byl.
sprawdz("kwota liczy tylko udane", "$0.0500" in z_awaria, z_awaria)
sprawdz("a liczba wywolan liczy wszystkie", "4 wywołaniach" in z_awaria, z_awaria)

print()
print("=== 3. NIEPOTWIERDZONA STAWKA TO OSOBNY STAN ===")
# „nie wiadomo, ile kosztowalo" i „wiadomo ile, ale po niepewnej stawce"
# to dwie rozne rzeczy i maja sie nie zlewac w jedna.
udane(3); udane(3, usd=0.02, verified=0)
mieszany = podsumuj(3)
print("    %s" % mieszany)
sprawdz("widac niepotwierdzona stawke", "niepotwierdzonej: 1" in mieszany, mieszany)
sprawdz("i nie nazywa jej nieudanym wywolaniem", "NIEZNANYM" not in mieszany,
        mieszany)

print()
print("=== 4. KOD LICZY PO WLASCIWYCH KOLUMNACH ===")
ZR = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("nieudane po ok = 0", "AND ok = 0" in ZR)
sprawdz("niepewne po price_verified = 0 przy ok = 1",
        "ok = 1 " in ZR and "price_verified = 0" in ZR)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
