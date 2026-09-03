# -*- coding: utf-8 -*-
"""Dwie podlogi bez karty dowodowej dzialaja na KOMENTARZU i na NOTCE.

`_podloga_z_pamieci` sama nazywa w docstringu trzy etapy pisane z pamieci
modelu: „komentarz, odpowiedz, restack". Odpowiedz te podlogi miala i
blokowala, restack mial i blokowal. KOMENTARZ, wymieniony pierwszy, nie mial
zadnej — pilnowalo go jedno zdanie w `prompts/komentarz.md` („Never claim
personal experience").

Notek na tamtej liscie nie bylo wcale, a typ MYSL jest w `config.NOTE_TYPES`
opisany wprost jako „JEDYNY TYP BEZ KARTY DOWODOWEJ": pisany z pamieci, w
pierwszej osobie, bez materialu do porownania. Uzasadnienie z `reply_to`
stosuje sie do niego co do slowa.

Czemu `zweryfikuj` tego nie zastepuje: ono sprawdza TWIERDZENIA wobec zrodel,
a „I asked three people about this" nie jest twierdzeniem sprawdzalnym — nie
ma czego wyszukac. Zmyslone przezycie przechodzilo wiec przez cala scianke
i szlo na cudzy post pod nazwa pisma.
"""
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402

# PROBKI W TYM TESCIE SA PO ANGIELSKU, wiec bramki musza byc angielskie.
#
# `gates.py` wiaze wzorce PRZY IMPORCIE, z `config.ARTICLE_LANGUAGE`. Gdy
# operator ustawi w `konfiguracja.toml` inny jezyk, ten test podaje angielskie
# zdania polskim wzorcom i oblewa — nie dlatego, ze kod jest zly, tylko
# dlatego, ze mierzy co innego, niz mysli. Zmierzone na koncie przestawionym
# na polski: trzy takie testy na czerwono, zero prawdziwych awarii.
#
# Ustawiamy jezyk PRZED importem `gates`. Wlasciwosc kodu, ktora ten plik
# sprawdza, jest niezalezna od jezyka konta.
config.ARTICLE_LANGUAGE = "English"
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


def odcisk(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "brak"


PILNOWANE = [config.DB_PATH, config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "promocja.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

# Teksty realne co do ksztaltu: pierwszy to zmyslone przezycie, drugi to
# powolanie na badanie, ktorego nikt nie nazwal, trzeci jest czysty.
PRZEZYCIE = ("I asked three people about this and none of them could name the "
             "company that runs the model they use every day. The label says "
             "the assistant, the invoice says somebody else entirely, and the "
             "gap between those two is where the interesting part sits today.")
BADANIE = ("Studies have shown that people trust a confident answer more than "
           "a correct one, which is the whole design brief for a chat box. "
           "The interface promises a colleague and delivers a search engine "
           "that never says it does not know the answer to your question.")
CZYSTY = ("The model does not keep the conversation. Every turn ships the "
          "whole history back through the wire and gets billed again, which "
          "is why a long chat costs more per word than a short one. Memory "
          "here is a receipt, and somebody is paying it twice over.")


class Licznik:
    """Podstawka pod `zweryfikuj` — liczy PLATNE sprawdzenia faktow."""

    def __init__(self):
        self.wywolan = 0
        self.teksty = []

    def __call__(self, conn, run_id, tekst, kontekst=""):
        self.wywolan += 1
        self.teksty.append(tekst)
        return {"claims": [], "safe_to_post": True, "verdict": "ok"}


def podstaw_llm(kandydaci):
    """Model oddaje po kolei podane slowniki, bez sieci i bez kosztu.

    PODMIENIAMY WYLACZNIE `call`. Do 2 wrzesnia ten plik podstawial takze
    `llm.parse_json` — czyli omijal jedyna funkcje, ktora tlumaczy odpowiedz
    modelu na ksztalt oczekiwany przez kod. Trzydziesci linii obslugi prozy
    wokol JSON-a, o ktorych wlasny docstring mowi, ile kosztowala ich awaria
    („dwadziescia wyszukiwan i 0,13 USD, po czym oddalo zero"), nie bylo w
    tescie dotkniete ani razu.

    Atrapa oddaje wiec SUROWY tekst — z proza dookola, bo tak wlasnie pisze
    model z wlaczonym wyszukiwaniem — i prawdziwy `parse_json` musi go
    rozebrac.
    """
    kolejka = list(kandydaci)

    def call(*a, **k):
        dane = kolejka.pop(0) if kolejka else {}
        return ("Working through the post — one object {like this}.\n\n"
                + json.dumps(dane, ensure_ascii=False)
                + "\n\nThat is the version I would stand behind.")

    stages.llm.call = call


ORYG_CALL, ORYG_PARSE = stages.llm.call, stages.llm.parse_json
ORYG_WERYFIKUJ = stages.zweryfikuj

print("=== 1. SAME PODLOGI WIDZA TE TEKSTY ===")
sprawdz("zmyslone przezycie rozpoznane",
        stages._podloga_z_pamieci(PRZEZYCIE) == "zmyslone przezycie",
        stages._podloga_z_pamieci(PRZEZYCIE))
sprawdz("nieistniejace badanie rozpoznane",
        stages._podloga_z_pamieci(BADANIE) == "nieistniejace badanie",
        stages._podloga_z_pamieci(BADANIE))
sprawdz("czysty tekst przechodzi",
        stages._podloga_z_pamieci(CZYSTY) == "",
        stages._podloga_z_pamieci(CZYSTY))

print()
print("=== 2. KOMENTARZ: ZMYSLONE PRZEZYCIE NIE WYCHODZI ===")
try:
    licznik = Licznik()
    stages.zweryfikuj = licznik
    podstaw_llm([{"comment": PRZEZYCIE, "what_it_adds": "x"},
                 {"comment": BADANIE, "what_it_adds": "y"},
                 {"comment": CZYSTY, "what_it_adds": "z"}])
    out = stages.comment_on(None, 0, {"url": "https://x/p/a", "title": "T",
                                      "text": "cudzy tekst", "author": "A"})
    po_tresci = {(k.get("comment") or "")[:20]: k for k in out["candidates"]}
    a = po_tresci[PRZEZYCIE[:20]]
    b = po_tresci[BADANIE[:20]]
    c = po_tresci[CZYSTY[:20]]
    sprawdz("kandydat z przezyciem NIE jest bezpieczny",
            a.get("safe_to_post") is False, a.get("safe_to_post"))
    sprawdz("i powod jest nazwany podloga",
            "zmyslone przezycie" in str(a.get("odrzucony")), a.get("odrzucony"))
    sprawdz("kandydat z badaniem NIE jest bezpieczny",
            b.get("safe_to_post") is False, b.get("safe_to_post"))
    sprawdz("i powod jest nazwany podloga",
            "nieistniejace badanie" in str(b.get("odrzucony")), b.get("odrzucony"))
    sprawdz("czysty kandydat przechodzi", c.get("safe_to_post") is True,
            c.get("safe_to_post"))
    # Blokada zapada bez wzgledu na wynik wyszukiwania, wiec placenie za nie
    # byloby wydatkiem na nic. Przy 17 komentarzach dziennie to nie drobiazg.
    sprawdz("platne sprawdzanie faktow NIE dotknelo odrzuconych",
            licznik.teksty == [CZYSTY], licznik.teksty)

    print()
    print("=== 3. KONTRDOWOD: STARA SCIEZKA BY JE PRZEPUSCILA ===")
    # Kod sprzed poprawki mial w tej petli dokladnie dwa sprawdzenia:
    # `bez_wstrzykniecia` i `zweryfikuj`. Odtwarzamy je wiernie.
    for nazwa, tekst in (("przezycie", PRZEZYCIE), ("badanie", BADANIE)):
        czysty, powod = stages.bez_wstrzykniecia(tekst)
        sprawdz("stara zapora wstrzykniec przepuszcza %s" % nazwa, czysty, powod)
    # Drugie stare sprawdzenie oddawalo `safe_to_post` na podstawie TWIERDZEN
    # znalezionych w tekscie. Zmyslone przezycie zadnego twierdzenia nie
    # zawiera, wiec lista `claims` jest pusta, a pusta lista to przepustka.
    puste = {"claims": [], "safe_to_post": True}
    sprawdz("a puste `claims` znaczylo PRZECHODZI",
            bool(puste["safe_to_post"]) and not puste["claims"])

    # SEKCJE 4 i 5 USUNIETE 1 wrzesnia 2026 RAZEM Z KODEM, KTORY BADALY.
    # Sprawdzaly, ze `note()` odrzuca zmyslone przezycie. Podloga w
    # `note()` zostala COFNIETA, bo byla nakladana na wszystkie piec typow
    # notek, a nie tylko na MYSL (jedyny typ bez karty dowodowej):
    #  - `gates.VAGUE_STUDY` blokuje „According to a paper published in
    #    Nature in December 2024" — zdanie, ktore nazywa zrodlo, pismo i
    #    date, czyli dokladnie to, co pisze zweryfikowana CIEKAWOSTKA;
    #  - `config.py` w ksztalcie OBSERWACJA WPROST zamawia pierwsza osobe
    #    o nawyku lub chwili, a `losowy_ksztalt_mysli` losuje go co czwarty
    #    raz — kod kazal wiec pisac to, co bramka odrzuca;
    #  - przy `config.NOTE_CANDIDATES = 1` odrzucenie jedynego kandydata
    #    znaczy, ze notka dnia przepada bez sladu, bo `note()` nie ponawia.
    # NOTKI NIE MAJA DZIS ZADNEJ PODLOGI NA ZMYSLONE PRZEZYCIE — pilnuje
    # ich tylko zdanie w `prompts/notka.md`. To jest dlug, nie stan
    # docelowy. Zamkniecie: nakladac podloge tam, gdzie naprawde nie ma
    # karty dowodowej, i zawezic `VAGUE_STUDY`, zeby nie lapal zdan
    # nazywajacych zrodlo.

finally:
    stages.llm.call, stages.llm.parse_json = ORYG_CALL, ORYG_PARSE
    stages.zweryfikuj = ORYG_WERYFIKUJ

# SEKCJA 6 USUNIETA. Byla asercja po TRESCI ZRODLA (`zrodlo.count(...)`,
# `zrodlo.index(...)`) — a taka asercja przechodzi takze wtedy, gdy kod
# jest martwy. Ten sam wzorzec przepuscil w tej sesji regresje w
# `artykul_z_puli.py`: test szukal napisu „stages.zwroc_kandydatow([fakt])"
# w zrodle i swiecil na zielono, podczas gdy petla brala CZTERY RAZY TEN
# SAM fakt. Etykieta „cztery etapy" byla przy tym nieprawdziwa: `reply_to`
# ma wlasna, recznie przepisana kopie tych regul i podlogi nie wola.
# To, co ta sekcja miala pokazac, pokazuja sekcje 1-3 zachowaniem.

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
