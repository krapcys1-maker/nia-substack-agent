"""Pliki uslug systemd: jedno wejscie, jeden zegar, jedna liczba.

Trzy rzeczy, ktore kosztowaly albo omal nie kosztowaly:

1. `nia-agent.service` mial sekcje [Install] z WantedBy=multi-user.target.
   Usluga typu oneshot uruchamiana z zegara nie ma czego instalowac — ale
   `systemctl enable nia-agent`, polecenie ktore kazdy odruchowo wpisuje,
   dopisaloby ja do startu systemu. Przebieg z `--wyslij` ruszalby wtedy przy
   kazdym bootcie, poza harmonogramem. Na serwerze usluga byla `disabled`,
   wiec do niczego nie doszlo — ale to nie jest zabezpieczenie, tylko szczescie.
   Pozostale dwie uslugi byly `static` od poczatku i to jest wzorzec.

2. TimeoutStartSec w usludze i LIMIT_CZASU_PRZEBIEGU_S w configu to TA SAMA
   liczba zapisana w dwoch miejscach. Rozjazd nie daje bledu — daje agenta,
   ktory liczy sobie inny koniec przebiegu niz ten, po ktorym systemd go ubija.
   Dokladnie taki rozjazd zabil dwa przebiegi.

3. Kazda usluga oneshot musi miec swoj timer. Usluga bez zegara i bez
   [Install] nie uruchomi sie nigdy, a wyglada na wdrozona.
"""
import pathlib
import re
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


KAT = pathlib.Path("agent-v2/systemd")
uslugi = sorted(KAT.glob("*.service"))
zegary = {p.stem for p in KAT.glob("*.timer")}

print("=== 1. ZADNA USLUGA Z ZEGARA NIE MA [Install] ===")
sprawdz("uslugi w ogole istnieja", len(uslugi) >= 3, len(uslugi))
for u in uslugi:
    tresc = u.read_text(encoding="utf-8")
    oneshot = re.search(r"^Type=oneshot", tresc, re.M) is not None
    ma_install = re.search(r"^\[Install\]", tresc, re.M) is not None
    if oneshot:
        sprawdz("%s (oneshot) nie ma sekcji [Install]" % u.name, not ma_install)
        sprawdz("%s ma swoj zegar" % u.name, u.stem in zegary,
                sorted(zegary))
    else:
        # Uslugi dlugodzialajace (VNC, Chrome) [Install] MAJA MIEC — maja
        # wstawac razem z systemem. Rozroznienie idzie po Type=, nie po nazwie.
        #
        # TU STALO `sprawdz(..., True)` — asercja, ktora nie mogla oblac nigdy,
        # a zajmowala miejsce w liczniku zdanych. Zdanie powyzej jest twarde
        # („MAJA MIEC") i wlasnie ono jest tu sprawdzane: usluga dlugodzialajaca
        # BEZ `[Install]` nie wstanie po restarcie maszyny i nikt tego nie
        # zauwazy, dopoki agent nie zamilknie na dobre.
        sprawdz("%s nie jest oneshot — MA mieć [Install] (wstaje z systemem)"
                % u.name, ma_install,
                "brak sekcji [Install] w usludze dlugodzialajacej")

print()
print("=== 2. LIMIT CZASU: JEDNA LICZBA W JEDNYM MIEJSCU ===")
agent = (KAT / "nia-agent.service").read_text(encoding="utf-8")
m = re.search(r"^TimeoutStartSec=(\d+)", agent, re.M)
sprawdz("usluga agenta ma limit czasu", m is not None)
if m:
    sprawdz("i jest rowny LIMIT_CZASU_PRZEBIEGU_S z configu",
            int(m.group(1)) == config.LIMIT_CZASU_PRZEBIEGU_S,
            "usluga=%s config=%s" % (m.group(1), config.LIMIT_CZASU_PRZEBIEGU_S))
    # Zapas musi byc mniejszy od limitu, inaczej koniec przebiegu wypada
    # PRZED jego poczatkiem i agent nie zrobi nic.
    sprawdz("zapas czasu jest mniejszy od limitu",
            0 < config.ZAPAS_CZASU_S < config.LIMIT_CZASU_PRZEBIEGU_S,
            (config.ZAPAS_CZASU_S, config.LIMIT_CZASU_PRZEBIEGU_S))
    # KONTRDOWOD dla samego limitu: musi starczyc na wiecej niz jedno
    # dzialanie z najdluzszym odstepem, inaczej agent nigdy nie wystawi dwoch.
    najdluzszy = max(g for _, g in config.ODSTEPY.values())
    sprawdz("i starczy na co najmniej dwa dzialania z najdluzsza przerwa",
            config.LIMIT_CZASU_PRZEBIEGU_S - config.ZAPAS_CZASU_S > najdluzszy,
            "najdluzsza przerwa %d s" % najdluzszy)

print()
print("=== 3. BEZ AUTOMATYCZNEGO PONAWIANIA PLATNYCH PRZEBIEGOW ===")
# Restart= po bledzie oznacza ponawianie oplaconych wywolan bez nadzoru.
for u in uslugi:
    tresc = u.read_text(encoding="utf-8")
    if re.search(r"^Type=oneshot", tresc, re.M):
        sprawdz("%s nie restartuje sie sama" % u.name,
                re.search(r"^Restart=", tresc, re.M) is None)

print()
print("=== 4. ZEGAR WSKAZUJE NA SCIEZKE, KTORA NAPRAWDE UZYWAMY ===")
# `artykul_z_puli.py` powstal 25 sierpnia 2026, zeby ZASTAPIC sciezke skauta:
# skaut wymaga dwoch udokumentowanych precedensow, a pod AI takie tematy sa
# tylko trzy — zasilki, auta autonomiczne, gielda — wiec trzy artykuly z rzedu
# wyszly o zautomatyzowanej biurokracji zamiast o AI.
#
# Zastepnik napisano, uzywano RECZNIE i przez piec dni NIE WPIETO W ZEGAR.
# `nia-artykul.service` wskazywal caly czas na sciezke zastapiona, wiec gdyby
# timer wystartowal, produkowalby te sama monokulture i pomijal bramke
# „uniesie artykul", podpytania do researchu, glebokosc z pieciu filarow oraz
# spizarnie kandydatow. Ta sama klasa zaniedbania, co szampon w kolejce
# promocyjnej: zmiana zrobiona, resztka po niej nie sprzatnieta.
_artykul = [u for u in uslugi if "artykul" in u.name]
sprawdz("jednostka artykulu istnieje", bool(_artykul), [u.name for u in uslugi])
for u in _artykul:
    tresc = u.read_text(encoding="utf-8")
    exec_line = next((l for l in tresc.splitlines()
                      if l.startswith("ExecStart=")), "")
    sprawdz("%s uruchamia sciezke z puli, nie skauta" % u.name,
            "artykul_z_puli.py" in exec_line, exec_line[:90])
    sprawdz("%s nie wola run.py na artykul" % u.name,
            "run.py" not in exec_line, exec_line[:90])
    # Bez --wyslij timer napisalby artykul i zostawil go na dysku, czyli
    # tygodniowa publikacja przestalaby wychodzic bez jednego komunikatu.
    sprawdz("%s ma --wyslij, inaczej nic nie wychodzi" % u.name,
            "--wyslij" in exec_line, exec_line[:90])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
