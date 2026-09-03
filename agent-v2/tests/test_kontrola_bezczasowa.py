# -*- coding: utf-8 -*-
"""Prog wieku dokumentu kontrolnego dotyczy tylko twierdzen o STANIE DZIS.

DLACZEGO TO POWSTALO. Przebieg produkcyjny 30 sierpnia oplacil osiem faktow i
wyrzucil piec z nich na jednym progu: „dokument kontrolny ma N dni (prog 90)".
Cztery z tych pieciu byly bezczasowe — liczba genow kodujacych bialko, prefill
czytajacy caly prompt naraz, kuracja danych treningowych, badanie podluzne.
Dla takiego faktu nie istnieje swiezszy dokument rzadzacy, bo nic sie nie
zmienilo, wiec prog nie chronil przed niczym i kosztowal 62% partii.

Gorsza polowa tej samej wady: model, ktory daty NIE PODAWAL, przechodzil. Kara
spadala na precyzje — model z prawdziwym dokumentem w reku byl odrzucany, model
bez dokumentu nie. Ten plik pilnuje obu polowek naraz.

KAZDY TEST MA KONTRDOWOD. Cztery ponizsze oblewaja na kodzie sprzed poprawki —
dwa dlatego, ze bezczasowy fakt byl odrzucany, i dwa dlatego, ze pominiecie
daty przy twierdzeniu o dzis bylo latwiejsza droga niz jej podanie.

BEZ PYTESTA. Serwer go nie ma i nie bedzie mial — testy w tym repozytorium sa
skryptami. Plik uruchamia sie z korzenia repozytorium.
"""
import datetime
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import stages   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def _dni_temu(ile):
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=ile)).strftime("%Y-%m-%d")


STARY = _dni_temu(config.MAKS_WIEK_ZRODLA_DNI + 80)
SWIEZY = _dni_temu(10)

# Fakt bezczasowy: nie nazywa wersji i nie mowi o stanie dzis. Zdanie o badaniu
# podluznym — dokladnie ta klasa, ktora produkcja wyrzucila po zaplaceniu.
BEZCZASOWY = ("In a 12-month longitudinal study, participants who used a "
              "conversational assistant every day described their own "
              "reasoning differently afterwards.")

# Twierdzenie o stanie dzis: slowa ze slownika `TWIERDZI_O_TERAZ`.
O_DZIS = ("The newest model from that lab supports a context window an order "
          "of magnitude larger than the one before it.")


def fakt(tresc, **pola):
    d = {"fact": tresc, "actually": "", "wrong_belief": "", "consequence": "",
         "decision": "", "source_date": SWIEZY, "control_verdict": "CONFIRMS"}
    d.update(pola)
    return d


print("=== 0. ATRAPY SA TYM, ZA CO JE BIORE ===")
# Test na atrapie, ktora nie ma zakladanej wlasciwosci, dowodzi tylko tego, ze
# kod cos zwraca. Ta sesja spalila na tym dosc czasu, wiec najpierw dowod.
sprawdz("bezczasowy nie nazywa wersji", not stages.nazywa_wersje(BEZCZASOWY))
_o = [s for s in config.TWIERDZI_O_TERAZ if s in BEZCZASOWY.lower()]
sprawdz("bezczasowy nie mowi o stanie dzis", not _o, _o)
_o2 = [s for s in config.TWIERDZI_O_TERAZ if s in O_DZIS.lower()]
sprawdz("a atrapa 'o dzis' trafia w slownik", bool(_o2), _o2)

print()
print("=== 1. FAKT BEZCZASOWY ZE STARYM DOKUMENTEM PRZECHODZI ===")
# KONTRDOWOD: przed poprawka to bylo odrzucane, i to kosztowalo pieniadze.
ok, powod = stages.swiezosc_faktu(fakt(
    BEZCZASOWY, control_date=STARY, control_url="https://example.org/study",
    control_fact="searched, nothing newer than the source changes the finding"))
sprawdz("bezczasowy z prawdziwym starym dokumentem przechodzi", ok, powod)

ok, powod = stages.swiezosc_faktu(fakt(
    BEZCZASOWY, control_date=STARY, control_url="https://example.org/study",
    control_fact=""))
sprawdz("ale bez sladu szukania odpada", not ok, powod)
sprawdz("i powod mowi o braku sladu", "sladu szukania" in powod, powod)

print()
print("=== 2. PRZY TWIERDZENIU O DZIS PROG ZOSTAJE ===")
# Uklad z Kenii wygladal dobrze pod stara kontrola. Tam prog ma sens.
ok, powod = stages.swiezosc_faktu(fakt(
    O_DZIS, control_date=STARY, control_url="https://example.org/launch",
    control_fact="checked, unchanged"))
sprawdz("stary dokument przy twierdzeniu o dzis odpada", not ok, powod)
sprawdz("i powod nazywa dokument kontrolny", "kontroln" in powod, powod)

print()
print("=== 3. POMINIECIE DATY NIE JEST LATWIEJSZA DROGA ===")
# KONTRDOWOD: przed poprawka to PRZECHODZILO. Nagradzalismy mniej informacji.
ok, powod = stages.swiezosc_faktu(fakt(
    O_DZIS, control_date="", control_fact="searched, nothing newer"))
sprawdz("brak daty przy twierdzeniu o dzis odpada", not ok, powod)
sprawdz("i powod mowi o braku daty", "bez daty kontrolnej" in powod, powod)

ok, powod = stages.swiezosc_faktu(fakt(
    BEZCZASOWY, control_date="", control_fact="searched, nothing newer"))
sprawdz("ale przy bezczasowym slad wystarcza", ok, powod)

print()
print("=== 4. BEZ DATY I BEZ SLADU ODPADA ZAWSZE ===")
for nazwa, tresc in (("bezczasowy", BEZCZASOWY), ("o dzis", O_DZIS)):
    ok, powod = stages.swiezosc_faktu(fakt(tresc, control_date="",
                                           control_fact=""))
    sprawdz("%s bez niczego odpada" % nazwa, not ok, powod)
    sprawdz("  i powod nazywa brak sladu", "bez sladu szukania" in powod, powod)

print()
print("=== 5. SWIEZY DOKUMENT PRZECHODZI W OBU RODZAJACH ===")
# Poprawka nie moze zepsuc sciezki, ktora dzialala.
for nazwa, tresc in (("bezczasowy", BEZCZASOWY), ("o dzis", O_DZIS)):
    ok, powod = stages.swiezosc_faktu(fakt(
        tresc, control_date=SWIEZY, control_url="https://example.org/doc",
        control_fact="checked today, unchanged"))
    sprawdz("%s ze swiezym dokumentem przechodzi" % nazwa, ok, powod)

print()
print("=== 6. ENDS I MODIFIES NIETKNIETE ===")
# Wlasciciel zatrzymal mnie raz na tej regule: „odnoszenie sie do historii jest
# ok, jesli pozniej piszemy o terazniejszosci". Ma zostac, jak jest.
for werdykt in ("ENDS", "MODIFIES"):
    ok, powod = stages.swiezosc_faktu(fakt(
        BEZCZASOWY, control_verdict=werdykt, control_date=STARY,
        control_fact="the arrangement was cancelled in the meantime"))
    sprawdz("%s z trescia przechodzi" % werdykt, ok, powod)
    ok, powod = stages.swiezosc_faktu(fakt(
        BEZCZASOWY, control_verdict=werdykt, control_date=STARY,
        control_fact=""))
    sprawdz("%s bez tresci odpada" % werdykt, not ok and "bez tresci" in powod,
            powod)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
