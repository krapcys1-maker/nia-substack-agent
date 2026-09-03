"""Swiezosc mierzona DOKUMENTEM KONTROLNYM, nie wiekiem kotwicy.

CO BYLO ZLE. `swiezosc_faktu` konczylo sie na warunku „jesli tekst nie nazywa
wersji produktu i nie trafil w liste trzydziestu slow typu now/costs — przepusc",
i wracalo ZANIM ktokolwiek spojrzal na date. Swiezosc byla sprawdzana
slownikiem, nie data. Zmierzone 26 sierpnia 2026 na setce tematow: 43 z 54
tematow po progu przechodzilo nieprzeczytanych.

TRZY NOTKI, KTORE TO WYPUSCILO, i wszystkie trzy mialy dobra kotwice:
  - Kenia: liczby zgodne ze sledztwem TIME ze stycznia 2023, ale Sama zerwala
    kontrakt z OpenAI w lutym 2022 i wyszla z moderacji tresci w 2023. Uklad
    opisany w czasie przeszlym, wiec bez bledu czasu — ale nie istnieje.
  - Japonia: art. 30-4 nadal obowiazuje (sprawdzone: nowela z czerwca 2026 go
    nie tyka), ale „zero pozwolen" zaciera szesc warunkow, a porownanie „ani
    USA, ani UE" jest po prostu falszywe — art. 4 dyrektywy DSM to rowniez
    wyjatek bez pozwolenia, roznica jest w opt-oucie.
  - Microsoft: liczba z 10-K prawdziwa, ale uklad zmienila umowa
    restrukturyzacyjna STARSZA od raportu.

TRZY RZECZY, KTORE Z TEGO WYNIKAJA:
  1. Dokument kontrolny nie musi byc NOWSZY od zrodla. Ma RZADZIC.
  2. Wiek kotwicy przestaje byc powodem odrzucenia. Badanie z 2023 i ustawa z
     2018 maja przechodzic czysto — wlasciciel powiedzial to wprost.
  3. WIEK NIE ODRZUCA NICZEGO, TAKZE ZERWANEGO UKLADU. Pierwsza wersja tej
     bramki odrzucala ENDS i wlasciciel zatrzymal to tego samego dnia:
     „odnoszenie sie do historii jest ok, jesli pozniej piszemy o
     terazniejszosci, tego nie mozemy zakazywac". Notka o kontraktach z 2021,
     w czasie przeszlym i z data, nie ma zadnego bledu — ma miec ciag dalszy.
     Jedyny wymog: notka musi powiedziec, czym rzecz jest DZISIAJ.

     Sam czas przeszly nie wystarcza. „Pracownikom placono ponizej dwoch
     dolarow za godzine" jest prawda i zostawia czytelnika w sierpniu 2026 z
     przekonaniem, ze opisuje cos dzialajacego. Zakonczenie ma byc widoczne.
"""
import datetime
import sys

sys.path.insert(0, "agent-v2")
import stages   # noqa: E402

zdane = oblane = 0
TERAZ = datetime.datetime(2026, 8, 26, tzinfo=datetime.timezone.utc)


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def fakt(**kw):
    d = {"fact": "x", "actually": "", "wrong_belief": "", "consequence": "",
         "decision": "", "source_date": "2023-01-18"}
    d.update(kw)
    return d


def wolno(**kw):
    return stages.swiezosc_faktu(fakt(**kw), teraz=TERAZ)


print("=== 1. WIEK NICZEGO NIE ODRZUCA — ANI NAWET ZERWANY UKLAD ===")
# Pierwsza wersja tej bramki odrzucala ENDS wprost. Wlasciciel zatrzymal to tego
# samego dnia: „odnoszenie sie do historii jest ok, jesli pozniej piszemy o
# terazniejszosci, tego nie mozemy zakazywac". Notka o kenijskich kontraktach z
# 2021 — w czasie przeszlym, z data — nie ma zadnego bledu. Ma miec ciag dalszy.
ok, powod = wolno(control_verdict="ENDS",
                  control_fact="Sama zerwala kontrakt w lutym 2022")
sprawdz("fakt o zerwanym ukladzie PRZECHODZI", ok, powod)
ok, powod = wolno(control_verdict="ENDS", control_fact="")
sprawdz("ale bez opisania, co sie stalo — nie", not ok, powod)
sprawdz("powod nazywa puste pole", "control_fact" in powod, powod)

print()
print("=== 2. MODIFIES: PRZECHODZI TYLKO Z ZASTRZEZENIEM ===")
ok, _ = wolno(control_verdict="MODIFIES",
              control_fact="art. 30-4 ma szesc warunkow, wykladnia niewiazaca")
sprawdz("z trescia zastrzezenia przechodzi", ok)
ok, powod = wolno(control_verdict="MODIFIES", control_fact="")
sprawdz("bez tresci odpada", not ok, powod)
# Zastrzezenie bez tresci jest GORSZE niz brak zastrzezenia: wyglada na
# sprawdzone, a nie niesie niczego, co pisarz moglby powiedziec.
sprawdz("powod mowi o pustym control_fact", "control_fact" in powod, powod)

print()
print("=== 3. CONFIRMS: WIEK KOTWICY PRZESTAJE MIEC ZNACZENIE ===")
# To jest cel calej zmiany. Obie kotwice sa grubo po progu 90 dni i obie MAJA
# przechodzic, bo ktos sprawdzil, ze rzecz nadal obowiazuje.
ok, powod = wolno(source_date="2023-07-06", control_verdict="CONFIRMS",
                  control_date="2026-06-26", control_fact="replikowane w 2026")
sprawdz("badanie z 2023 przechodzi (kotwica 1148 dni)", ok, powod)
ok, powod = wolno(source_date="2018-05-25", control_verdict="CONFIRMS",
                  control_date="2026-08-03", control_fact="nowela nie tyka art. 30-4")
sprawdz("ustawa z 2018 przechodzi (kotwica 3015 dni)", ok, powod)

print()
print("=== 4. CONFIRMS MUSI BYC SPRAWDZENIEM NA DZIS — ALE TYLKO TAM, ===")
print("===    GDZIE 'DZIS' W OGOLE COS ZNACZY                        ===")
# ZMIERZONE 30 sierpnia na produkcji. Prog stal na KAZDYM CONFIRMS i wyrzucal
# piec z osmiu OPLACONYCH faktow. Cztery z tych pieciu byly bezczasowe: liczba
# genow kodujacych bialko, prefill czytajacy caly prompt naraz, kuracja danych
# treningowych, badanie podluzne. Dla nich nie istnieje swiezszy dokument
# rzadzacy, bo nic sie nie zmienilo — prog nie chronil przed niczym i kosztowal
# 62% partii.
#
# Ta sekcja sprawdzala prog na atrapie `fact="x"`, czyli na zdaniu, ktore
# niczego nie twierdzi o terazniejszosci. Dlatego przechodzila, choc opisywala
# regule szersza, niz nam potrzebna.
TERAZ_TEKST = ("The newest model from that lab supports a far larger context "
               "window than the one before it.")
BEZCZASOWY = ("In a 12-month longitudinal study, participants described their "
              "own reasoning differently afterwards.")

ok, powod = wolno(fact=TERAZ_TEKST, control_verdict="CONFIRMS",
                  control_date="2024-01-01", control_fact="x")
sprawdz("stary dokument nie jest sprawdzeniem, gdy fakt mowi o dzis",
        not ok, powod)
sprawdz("prog liczony na DACIE KONTROLNEJ", "kontroln" in powod, powod)

ok, powod = wolno(fact=BEZCZASOWY, control_verdict="CONFIRMS",
                  control_date="2024-01-01",
                  control_fact="szukalem, nic nowszego nie zmienia wyniku")
sprawdz("ale fakt bezczasowy ze starym dokumentem PRZECHODZI", ok, powod)
ok, powod = wolno(fact=BEZCZASOWY, control_verdict="CONFIRMS",
                  control_date="2024-01-01", control_fact="")
sprawdz("bezczasowy bez sladu szukania nadal odpada", not ok, powod)

ok, _ = wolno(fact=BEZCZASOWY, control_verdict="CONFIRMS", control_date="",
              control_fact="szukalem, nic nowszego nie ma")
sprawdz("brak daty uchodzi ze sladem szukania", ok)
# Druga polowa tej samej wady: przed poprawka POMINIECIE daty bylo latwiejsza
# droga niz jej podanie. Model z prawdziwym dokumentem w reku byl odrzucany,
# model bez dokumentu — nie. Nagradzalismy mniej informacji.
ok, powod = wolno(fact=TERAZ_TEKST, control_verdict="CONFIRMS",
                  control_date="", control_fact="szukalem, nic nowszego nie ma")
sprawdz("przy twierdzeniu o dzis brak daty NIE jest latwiejsza droga",
        not ok, powod)
ok, powod = wolno(control_verdict="CONFIRMS", control_date="", control_fact="")
sprawdz("ale puste pole juz nie", not ok, powod)

print()
print("=== 5. KONTRDOWOD: STARA BRAMKA PRZEPUSZCZALA WSZYSTKO TO SAMO ===")
# Bez pol kontrolnych kod wraca na stara sciezke. Fakt bez nazwanej wersji i bez
# slowa z listy przechodzi mimo zrodla sprzed lat — dokladnie tak dzialalo
# WSZYSTKO przed ta zmiana. Gdyby ten przypadek odpadal, test nie dowodzilby,
# ze to dokument kontrolny robi robote.
ok, _ = wolno(fact="Sama paid workers under two dollars an hour",
              source_date="2023-01-18")
sprawdz("bez pol kontrolnych stara sciezka nadal przepuszcza", ok)

# Z polami kontrolnymi ten sam fakt nadal przechodzi — ale juz NIE MOZE wyjsc
# bez zdania o tym, ze uklad sie skonczyl. Roznica nie jest w tym, czy notka
# powstanie, tylko w tym, czy powie czytelnikowi prawde o dzisiaj.
ok, _ = wolno(fact="Sama paid workers under two dollars an hour",
              source_date="2023-01-18", control_verdict="ENDS",
              control_fact="kontrakt zerwany w lutym 2022, dostawca wyszedl z moderacji w 2023")
sprawdz("z opisanym zakonczeniem przechodzi", ok)
ok, _ = wolno(fact="Sama paid workers under two dollars an hour",
              source_date="2023-01-18", control_verdict="ENDS", control_fact="")
sprawdz("bez opisanego zakonczenia odpada", not ok)

print()
print("=== 6. STARE ODMOWY NIE ZNIKLY ===")
ok, powod = wolno(fact="o1 is being deprecated", control_verdict="CONFIRMS",
                  control_date="2026-08-20", control_fact="x")
sprawdz("rzecz z ogloszonym koncem zycia nadal odpada", not ok, powod)
sprawdz("i to PRZED sprawdzeniem kontrolnym", "koncem zycia" in powod, powod)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
