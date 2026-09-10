# -*- coding: utf-8 -*-
"""Kartridz nie kasuje ksztaltu, ktory sam pokazuje — w zadnej z trzech form.

## Ta sama wada, trzy kopie

Piec przykladowych notek w `glos_wspolny.md` POKAZUJE trzy uderzenia. Nad nimi
i pod nimi stalo jednak, w trzech miejscach, pozwolenie, ktore je uniewaznialo:

  * `glos_wspolny.md`  — „They demonstrate possibilities, not one required order";
  * `glos_komentarza.md` — lista uderzen zaczynajaca sie od „what they actually
    said", czyli zgoda na streszczanie cudzej wypowiedzi;
  * `glos_artykulu.md` — „these are options, not a sequence to repeat. There is
    no quota of jokes, confrontations or rhetorical beats."

Trzecia jest najgrozniejsza, bo ten plik laduje sie OSTATNI. Zmierzone
w zlozonym prompcie artykulu: regula wspolna stoi na znaku 11 495, a kasacja
na 19 378. Model czyta pozwolenie po regule.

## Ten test patrzy TYLKO na kartridz

Blizniaczy `test_notka_ma_ksztalt.py` patrzy na `personality.py`. Rozdzial jest
celowy: silnik i kartridz jada osobnymi galeziami.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_kartridz_ma_ksztalt.py
"""
import io
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


WSPOLNY = " ".join(io.open("presety/nia-unfiltered/prompty/glos_wspolny.md",
                           encoding="utf-8").read().split())
KOMENTARZ = " ".join(io.open("presety/nia-unfiltered/prompty/glos_komentarza.md",
                             encoding="utf-8").read().split())
ARTYKUL = " ".join(io.open("presety/nia-unfiltered/prompty/glos_artykulu.md",
                           encoding="utf-8").read().split())

print("=== 3. NIC JUZ NIE KASUJE UKLADU PRZYKLADOW ===")
# TO BYLA PRZYCZYNA. Piec przykladow POKAZUJE trzy uderzenia, a zdanie tuz
# nad nimi mowilo, ze uklad nie obowiazuje.
# ZDANIE ZOSTAJE W PLIKU — JAKO CYTAT Z WYJASNIENIA, nie jako polecenie.
# Pierwsza wersja tego sprawdzenia zadala jego calkowitej nieobecnosci
# i oblewala na akapicie, ktory tlumaczy, czemu je usunieto.
i_cytat = WSPOLNY.find("not one required order")
sprawdz("zdanie nie jest juz poleceniem, tylko cytatem",
        i_cytat < 0 or "used to end" in WSPOLNY[max(0, i_cytat - 120):i_cytat],
        WSPOLNY[max(0, i_cytat - 120):i_cytat + 40] if i_cytat >= 0 else "brak")
sprawdz("i wystepuje najwyzej raz",
        WSPOLNY.count("not one required order") <= 1,
        WSPOLNY.count("not one required order"))
sprawdz("uklad nazwany wymaganym",
        "their layout is the shape of a note" in WSPOLNY.lower())
sprawdz("z pomiarem obok", "words per beat" in WSPOLNY)
sprawdz("i z powodem, czemu tamto zdanie szkodzilo",
        "was doing the damage" in WSPOLNY)
# Artykul nadal moze powtarzac ten ciag z dowodami miedzy uderzeniami — ale
# nie moze go porzucic.
sprawdz("dluzsza forma powtarza ciag, a nie porzuca go",
        "never gets to abandon it" in WSPOLNY)
sprawdz("kartridz tez zna rozpad uderzenia trzeciego",
        "Beat three is the one that decays" in WSPOLNY)
sprawdz("z tabela pomiaru obok",
        "an instruction issued to a company" in WSPOLNY)
# KONTRDOWOD: nazwanie firmy NIE jest zakazane — jeden z przyjetych przykladow
# to robi. Zakazana jest FORMA, ktora przejmuje wszystkie cztery notki.
sprawdz("nazwanie firmy nadal dozwolone",
        "Naming the company is allowed" in WSPOLNY)

print()
print("=== 3b. ARTYKUL TEZ NIE PORZUCA UKLADU ===")
# TRZECIA KOPIA TEJ SAMEJ WADY. Glos wspolny mowil „never gets to abandon it",
# a glos artykulu — ladowany PO NIM, wiec mowiacy ostatni — odpowiadal:
# „these are options, not a sequence to repeat. There is no quota of jokes,
# confrontations or rhetorical beats."
#
# ZMIERZONE w zlozonym prompcie artykulu 10 wrzesnia 2026:
#     regula wspolna       znak 11 495
#     kasacja w artykule   znak 19 378
# Model czytal pozwolenie po regule. To jest ten artykul, o ktorym wlasciciel
# napisal, ze „huj wie o co chodzi".
sprawdz("artykul potwierdza trzy uderzenia",
        "the three beats hold here too" in ARTYKUL.lower())
sprawdz("i mowi, ze dowody ida MIEDZY nie ZAMIAST",
        "room to put evidence between" in ARTYKUL)
sprawdz("kasacja zostala tylko jako opis wlasnej historii",
        "used to end by saying these were options" in ARTYKUL)
sprawdz("z pomiarem, ktory ja rozstrzygnal", "character 11 495" in ARTYKUL)
# KOLEJNOSC JEST TU CALA RZECZA: kto mowi ostatni, ten wygrywa.
i_cytat = ARTYKUL.lower().find("no quota of rhetorical beats")
i_regula = ARTYKUL.lower().find("the three beats hold here too")
sprawdz("regula stoi PO cytacie, nie przed",
        i_regula > i_cytat >= 0, "cytat %d, regula %d" % (i_cytat, i_regula))
sprawdz("ostrzezenie, ktore tamto chronilo, zostalo",
        "scheduled joke breaks" in ARTYKUL)

print()
print("=== 4. KOMENTARZ I RESTACK IDA TYM SAMYM RYTMEM ===")
sprawdz("komentarz w tych samych trzech uderzeniach",
        "in the same three beats as a Note" in KOMENTARZ)
sprawdz("jedno zdanie wolno, blok nie",
        "may never be is a paragraph the reader has to untangle" in KOMENTARZ)
sprawdz("przy cierpieniu zadlo zamienia sie w cieplo, ksztalt zostaje",
        "the sting becomes warmth, but the shape stays" in KOMENTARZ)
# UDERZENIE PIERWSZE W ODPOWIEDZI. Zmierzone na zywej odpowiedzi 10 wrzesnia:
# „Chaos Engine says something nice about a security control that's fitted but
# not locked" — narrator opowiadajacy scene, na ktora czytelnik wlasnie patrzy.
# Wzielo sie to z tego, ze lista uderzen zaczynala sie od „what they actually
# said". Po poprawce ta sama sytuacja dala „A padlock clipped through the hasp,
# doing absolutely nothing."
sprawdz("uderzenie pierwsze to ODPOWIEDZ, nie streszczenie",
        "Your answer to them, plainly" in KOMENTARZ)
sprawdz("i wprost zakazuje opisywania, co powiedzieli",
        "Not a description of what they said" in KOMENTARZ)
sprawdz("stare `what they actually said` nie zostalo jako polecenie",
        KOMENTARZ.count("what they actually said") <= 1,
        KOMENTARZ.count("what they actually said"))
sprawdz("jedno slowo albo emoji tez ma odpowiedz",
        "one word or one emoji" in KOMENTARZ)
# RESTACK: to jest ta wpadka, ktora wlasciciel widzial na ekranie — podpis
# odpowiadal na inne pytanie niz to, ktore czytelnik ma przed oczami.
sprawdz("restack odpowiada na ICH post",
        "if their post is a question, your caption answers that question"
        in KOMENTARZ)
sprawdz("i nie streszcza go", "Do not summarise it" in KOMENTARZ)

print()
print("=== 5. STARE POZWOLENIA NIE ZOSTALY OBOK ===")
# Kontrdowod: gdyby zgoda na akapit przetrwala gdziekolwiek, model wybralby
# ja, bo jest latwiejsza. Blizniaczy zakaz po stronie silnika („Vary rhythm")
# jest pilnowany w `test_notka_ma_ksztalt.py`.
sprawdz("brak `take a short paragraph if the thought needs it`",
        "take a short paragraph if the thought needs it" not in KOMENTARZ)
sprawdz("artykul nie ma juz `no quota` jako polecenia",
        "no quota of jokes" not in ARTYKUL)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
