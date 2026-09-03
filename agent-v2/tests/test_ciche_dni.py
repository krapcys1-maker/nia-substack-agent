"""Ciche dni: ostatni wyrazny podpis automatu.

Siedem dni z rzedu, ten sam rytm, zadnej przerwy — to bylo widac na profilu
bez analizowania stylu. Ale cichy dzien musi wyciszac NADAWANIE, nigdy
ODPOWIADANIE: nieodpisanie komus, kto sie odezwal, to nie cisza, tylko
lekcewazenie.
"""
import re
import sys
from datetime import datetime, timedelta, timezone

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


print("=== 1. TA SAMA ODPOWIEDZ PRZEZ CALY DZIEN (kontrdowod na losowanie) ===")
d = datetime(2026, 8, 24, tzinfo=timezone.utc)
odpowiedzi = {config.cichy_dzien(d.replace(hour=h)) for h in (0, 6, 11, 19, 23)}
sprawdz("piec przebiegow tego samego dnia zgadza sie", len(odpowiedzi) == 1,
        odpowiedzi)
sprawdz("i to samo po ponownym wywolaniu",
        config.cichy_dzien(d) == config.cichy_dzien(d))

print()
print("=== 2. CZESTOTLIWOSC JEST TAKA, JAK ZAMOWIONA ===")
start = datetime(2026, 1, 1, tzinfo=timezone.utc)
ile_dni = 730
ciche = sum(1 for i in range(ile_dni)
            if config.cichy_dzien(start + timedelta(days=i)))
udzial = ciche / ile_dni
oczekiwany = 1 / config.CICHY_DZIEN_NA_ILE
print("    ciche: %d z %d dni (%.1f%%), zamawiane %.1f%%"
      % (ciche, ile_dni, 100 * udzial, 100 * oczekiwany))
sprawdz("udzial w granicach polowy-dwoch oczekiwanego",
        oczekiwany * 0.5 <= udzial <= oczekiwany * 1.6, udzial)
sprawdz("ciche dni w ogole wystepuja", ciche > 0)
sprawdz("ale nie jest ich wiekszosc", udzial < 0.3)

print()
print("=== 3. NIE MA DWOCH CISZ POD RZAD PRZEZ CALY ROK ===")
pod_rzad = maks = 0
for i in range(ile_dni):
    if config.cichy_dzien(start + timedelta(days=i)):
        pod_rzad += 1
        maks = max(maks, pod_rzad)
    else:
        pod_rzad = 0
print("    najdluzsza cisza z rzedu: %d dni" % maks)
sprawdz("cisza NIGDY nie ciagnie sie dwa dni z rzedu", maks <= 1, maks)

print()
print("=== 4. DA SIE WYLACZYC ===")
pierwotne = config.CICHE_DNI_WLACZONE
config.CICHE_DNI_WLACZONE = False
sprawdz("wylacznik dziala",
        not any(config.cichy_dzien(start + timedelta(days=i)) for i in range(40)))
config.CICHE_DNI_WLACZONE = pierwotne

print()
print("=== 5. CISZA WYCISZA NADAWANIE, NIE ROZMOWE ===")
zrodlo = open("agent-v2/run.py", encoding="utf-8").read()
blok = re.search(r"if config\.cichy_dzien\(\):(.{0,700})", zrodlo, re.S)
sprawdz("cichy dzien jest wpiety w przebieg", blok is not None)
if blok:
    t = blok.group(1)
    # ZASADA, NIE BRZMIENIE. Ten warunek byl przypiety do dokladnej linii
    # `zostalo["notki"] = 0` i pekl 30 sierpnia, gdy dwie zahardkodowane
    # pozycje zastapiono petla po `config.CICHY_DZIEN_WYCISZA` — regula stala
    # nietknieta, test nie. Lista jest teraz w jednym miejscu, bo `norma.py`
    # tez musi ja znac: inaczej licznik krzyczy „0/5, ponizej progu" w dniu
    # zaprojektowanej ciszy i uczy ignorowania siebie.
    sprawdz("wycisza to, co wymienia config",
            "CICHY_DZIEN_WYCISZA" in t
            or all('zostalo[%r] = 0' % p in t for p in config.CICHY_DZIEN_WYCISZA),
            t[:200])
    sprawdz("a config wymienia notki i restacki",
            set(config.CICHY_DZIEN_WYCISZA) == {"notki", "restacki"},
            config.CICHY_DZIEN_WYCISZA)
    for rozmowa in ("komentarze", "lajki"):
        sprawdz("NIE wycisza pozycji %r" % rozmowa,
                rozmowa not in config.CICHY_DZIEN_WYCISZA
                and 'zostalo["%s"] = 0' % rozmowa not in t, t[:200])
sprawdz("odpowiedzi nie sa objete limitem dnia",
        config.ODPOWIEDZI_POZA_LIMITEM is True)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
