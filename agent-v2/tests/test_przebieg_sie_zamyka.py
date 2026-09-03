# -*- coding: utf-8 -*-
"""Sciezka artykulu musi ZAMKNAC przebieg, ktory otworzyla.

CO PRZYSZLO MAILEM 31 sierpnia 2026, 07:08 UTC:

    [agent NIA] Przebiegi wisialy w RUNNING
    4 przebiegow wisialo w stanie RUNNING ponad trzy godziny —
    zamkniete jako STALE (id: 85, 94, 95, 96).

Sprawdzone w bazie: 94, 95 i 96 to trzy podejscia do artykulu
z poprzedniego wieczora — W TYM TO, KTORE SIE UDALO I OPUBLIKOWALO.
Zaden z nich nie wisial. Wszystkie skonczyly sie normalnie.

PRZYCZYNA: `artykul_z_puli.py` wolal `db.start_run` i NIE WOLAL `finish_run`
ANI RAZU — dla porownania `run.py` wola je piec razy. Szesc wyjsc z funkcji,
zadne nie zamykalo przebiegu.

DLACZEGO TO GORSZE NIZ SMIEC W TABELI. Alarm o zawieszeniu odzywal sie po
KAZDEJ publikacji artykulu. Alarm, ktory klamie regularnie, uczy ignorowac
alarmy — a wtedy prawdziwe zawieszenie utonie w szumie razem z falszywymi.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


import artykul_z_puli  # noqa: E402

zamkniete: list[tuple] = []


class AtrapaDb:
    """Udaje `db` na tyle, na ile `main()` go uzywa."""

    @staticmethod
    def connect():
        return "polaczenie"

    @staticmethod
    def start_run(conn, stage, **kw):
        return 4242

    @staticmethod
    def finish_run(conn, run_id, status, stage, note=""):
        zamkniete.append((run_id, status, stage, note))


stary_db = artykul_z_puli.db
stary_przebieg = artykul_z_puli._przebieg
artykul_z_puli.db = AtrapaDb

try:
    print("=== 1. UDANY PRZEBIEG ZAMYKA SIE JAKO DONE ===")
    zamkniete.clear()
    artykul_z_puli._przebieg = lambda conn, run_id: 0
    kod = artykul_z_puli.main()
    sprawdz("kod wyjscia przechodzi na zewnatrz", kod == 0, kod)
    sprawdz("przebieg zamkniety dokladnie raz", len(zamkniete) == 1, zamkniete)
    sprawdz("ze statusem DONE", zamkniete and zamkniete[0][1] == "DONE",
            zamkniete)
    sprawdz("i z numerem tego przebiegu", zamkniete and zamkniete[0][0] == 4242)

    print()
    print("=== 2. ODPUSZCZONY TEZ SIE ZAMYKA, ALE INACZEJ ===")
    # „Zaden fakt nie uniesie artykulu" to nie awaria — ale przebieg ma byc
    # zamkniety tak samo, inaczej wisi.
    zamkniete.clear()
    artykul_z_puli._przebieg = lambda conn, run_id: 1
    kod = artykul_z_puli.main()
    sprawdz("kod 1 przechodzi", kod == 1, kod)
    sprawdz("status SKIPPED, nie DONE",
            zamkniete and zamkniete[0][1] == "SKIPPED", zamkniete)

    print()
    print("=== 3. WYJATEK NIE ZOSTAWIA WISZACEGO PRZEBIEGU ===")
    # To jest ta sytuacja, ktora alarm ma lapac naprawde. Jesli wyjatek
    # zostawi RUNNING, prawdziwa awaria bedzie nieodrozzialna od publikacji.
    zamkniete.clear()

    def wybucha(conn, run_id):
        raise ValueError("cos poszlo nie tak")

    artykul_z_puli._przebieg = wybucha
    try:
        artykul_z_puli.main()
        podniesione = False
    except ValueError:
        podniesione = True
    sprawdz("wyjatek leci dalej, nie jest polykany", podniesione)
    sprawdz("ale przebieg zostal zamkniety", len(zamkniete) == 1, zamkniete)
    sprawdz("ze statusem ERROR", zamkniete and zamkniete[0][1] == "ERROR")
    sprawdz("i z powodem w notatce",
            zamkniete and "ValueError" in str(zamkniete[0][3]), zamkniete)

    print()
    print("=== 4. PRZERWANIE Z ZEWNATRZ TAKZE ===")
    # SIGTERM i Ctrl-C to `BaseException`, nie `Exception`. Zlapanie tylko
    # `Exception` zostawiloby wiszacy przebieg dokladnie przy zabiciu procesu,
    # czyli w najczestszym prawdziwym przypadku.
    zamkniete.clear()

    def przerwane(conn, run_id):
        raise KeyboardInterrupt()

    artykul_z_puli._przebieg = przerwane
    try:
        artykul_z_puli.main()
    except KeyboardInterrupt:
        pass
    sprawdz("przebieg zamkniety takze przy KeyboardInterrupt",
            len(zamkniete) == 1, zamkniete)
finally:
    artykul_z_puli.db = stary_db
    artykul_z_puli._przebieg = stary_przebieg

print()
print("=== 5. KONTRDOWOD: TO NAPRAWDE BYLO NIEOBECNE ===")
# Gdyby `finish_run` bylo tam od zawsze, ten test nie mierzylby niczego.
zrodlo = pathlib.Path("agent-v2/artykul_z_puli.py").read_text(encoding="utf-8")
sprawdz("plik wola teraz finish_run", "finish_run" in zrodlo)
sprawdz("i robota siedzi w osobnej funkcji, nie w main",
        "def _przebieg(conn, run_id: int) -> int:" in zrodlo)
sprawdz("main lapie BaseException, nie sam Exception",
        "except BaseException" in zrodlo)
sprawdz("powod maila jest opisany w kodzie",
        "id: 85, 94, 95, 96" in zrodlo or "85, 94, 95, 96" in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
