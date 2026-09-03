"""Sufity tokenow musza pokrywac to, o co prompt NAPRAWDE prosi.

Powod: pelny przebieg padl na odsiewie z ucieta odpowiedzia, bo temat zaczal
niesc dwa nowe pola, a sufit byl policzony dla starego ksztaltu. Ta klasa
bledow wychodzi u nas WYLACZNIE na platnym przebiegu — a nie musi.
"""
import re
import sys
sys.path.insert(0, "agent-v2")
import config   # noqa: E402

zdane = oblane = 0
def sprawdz(n, w, s=""):
    global zdane, oblane
    if w: zdane += 1; print("  OK    %s" % n)
    else: oblane += 1; print("  BLAD  %s   %s" % (n, s))

print("=== 1. KAZDY ETAP Z PROMPTEM MA SUFIT ===")
for plik, etap in (("skaut.md", "scout"), ("wykonalnosc.md", "feasibility"),
                   ("dyskoveria.md", "discovery"), ("klasyfikacja.md", "classify"),
                   ("synteza.md", "synthesis"), ("pisarz.md", "write"),
                   ("recenzent.md", "review"), ("bibliotekarz.md", "bibliotekarz"),
                   ("warto_pisac.md", "warto_pisac"), ("notka.md", "note")):
    sprawdz("%-18s -> sufit %s" % (plik, etap),
            etap in config.MAX_TOKENS and config.MAX_TOKENS[etap] > 0)

print()
print("=== 2. SUFIT POKRYWA REALNE ZUZYCIE, NIE MOJA ARYTMETYKE ===")
# Pierwsza wersja tego testu liczyla miejsce na TRESC i przeszla, podczas gdy
# przebieg padal — bo problemem jest objetosc ROZUMOWANIA, ktora z objetoscia
# tresci nie ma zwiazku. Liczby ponizej to zmierzone maksima z prawdziwych
# przebiegow. Prog 1,5x, bo rozumowanie DeepSeeka waha sie miedzy wywolaniami.
ZMIERZONE_MAX = {
    "discovery": 27253, "curiosity": 26581, "review": 24645, "cele": 19161,
    "feasibility": 16206, "scout": 16187, "classify": 11104, "synthesis": 11059,
    "factcheck": 9771, "write": 9036, "note": 7574, "comment": 7097,
}
PROG = 1.5
for etap, zmierzone in sorted(ZMIERZONE_MAX.items()):
    suf = config.MAX_TOKENS.get(etap, 0)
    sprawdz("%-12s sufit %6d vs zmierzone %5d (%.2fx)" % (
        etap, suf, zmierzone, suf / zmierzone if zmierzone else 0),
        suf >= zmierzone * PROG,
        "margines ponizej %.1fx — utnie sie przy pierwszym dluzszym rozumowaniu" % PROG)

print()
print("=== 3. KONTRDOWOD: STARY ZAPAS BY NIE PRZESZEDL ===")
# Przy zapasie 16000 odsiew mial 19085 sufitu i ucielo go DWA RAZY pod rzad.
STARY_ZAPAS = 16000
stary_feas = config._tokens_for(config.TOPIC_COUNT * 1100) - config.THINKING_HEADROOM_TOKENS + STARY_ZAPAS
sprawdz("sufit odsiewu ze starym zapasem zostalby zlapany",
        stary_feas < ZMIERZONE_MAX["feasibility"] * PROG,
        "stary=%d, potrzeba >=%d" % (stary_feas, ZMIERZONE_MAX["feasibility"] * PROG))
sprawdz("zapas na rozumowanie pokrywa najobfitszy zmierzony etap",
        config.THINKING_HEADROOM_TOKENS >= max(ZMIERZONE_MAX.values()),
        config.THINKING_HEADROOM_TOKENS)

print()
print("=== 4. KAZDY SUFIT MIESCI SIE W TERMINIE ===")
for etap, sufit in config.MAX_TOKENS.items():
    if etap in config.BEZ_TOKENOW:
        continue
    t = config.timeout_for(sufit)
    sprawdz("%-14s sufit %6d -> termin %4.0f s" % (etap, sufit, t), t > 0)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
