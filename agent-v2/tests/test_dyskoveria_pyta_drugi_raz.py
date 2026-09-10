# -*- coding: utf-8 -*-
"""Zero wyszukiwan w dyskoverii nie zabija artykulu przy pierwszej probie.

## Pomiar

Logi serwera, ten sam kod i ten sam model (`deepseek-v4-flash`):

    8 wrzesnia   szukania=18, 12      wejscie 325 414 / 91 128 tokenow
    9 wrzesnia   szukania=15, 6       wejscie 131 562 /  29 788
   10 wrzesnia   szukania=0,  0       wejscie   1 288 /   1 357

Liczba tokenow wejscia jest dowodem, nie poszlaka: przy prawdziwym szukaniu
wracaja wyniki i wejscie idzie w setki tysiecy. 10 wrzesnia model odpowiedzial
od reki z wlasnej pamieci, DWA RAZY POD RZAD, a straznik dwa razy slusznie
wywalil caly przebieg artykulu — po oplaceniu tematu, pytan i klasyfikacji.

## Czego NIE robimy

Nie wymuszamy narzedzia. `tool_choice` twarde na `{"type": "web_search"}` bylo
juz sprawdzone na zywo 26 sierpnia: model wolal je w kolko, pietnascie
wyszukiwan i ani jednego zdania odpowiedzi (patrz `llm._deepseek`).

Nie luzujemy tez straznika. Adresy z pamieci modelu nadal sa odrzucane —
pierwsza wersja tamtego filtru przepuscila dziesiec zmyslonych adresow.

Powtarzamy zapytanie RAZ. Kosztuje 0,003 USD i jest jedyna roznica miedzy
artykulem a brakiem artykulu.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_dyskoveria_pyta_drugi_raz.py
"""
import json
import sys
from unittest.mock import patch

sys.path.insert(0, "agent-v2")
import stages          # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


ZRODLA = {"sources": [
    {"url": "https://www.politico.com/news/2026/09/09/house-ai-committee",
     "why": "the reporting itself", "kind": "reporting"},
    {"url": "https://www.congress.gov/bill/2026/hr-9911",
     "why": "the record", "kind": "primary"},
]}


def _atrapa(ile_szukan_kolejno):
    """Oddaje te same zrodla; wpisuje adresy do `collect_urls` wedle planu."""
    stan = {"nr": 0}

    def call(purpose, system, user, **kw):
        i = stan["nr"]
        stan["nr"] += 1
        ile = ile_szukan_kolejno[min(i, len(ile_szukan_kolejno) - 1)]
        zebrane = kw.get("collect_urls")
        if zebrane is not None:
            for s in ZRODLA["sources"][:ile]:
                zebrane.append(s["url"])
        return json.dumps(ZRODLA)

    call.stan = stan
    return call


print("=== 1. PIERWSZA PROBA BEZ WYSZUKIWANIA — PYTAMY DRUGI RAZ ===")
atrapa = _atrapa([0, 2])          # najpierw zero, potem normalnie
with patch.object(stages.llm, "call", atrapa), \
     patch.object(stages, "hosty_ktore_nigdy_nie_dzialaly", lambda c: []):
    wynik = stages.discovery(None, None, "czy komisja powstanie?", [])
sprawdz("model zostal zapytany DWA razy", atrapa.stan["nr"] == 2,
        atrapa.stan["nr"])
sprawdz("i artykul dostal zrodla", bool(wynik), wynik)

print()
print("=== 2. GDY PIERWSZA PROBA SZUKALA — NIE PLACIMY DRUGI RAZ ===")
# Kontrdowod: powtorzenie ma byc ratunkiem, nie nawykiem. Bez tego kazdy
# artykul kosztowalby dwie dyskoverie zamiast jednej.
atrapa2 = _atrapa([2, 2])
with patch.object(stages.llm, "call", atrapa2), \
     patch.object(stages, "hosty_ktore_nigdy_nie_dzialaly", lambda c: []):
    wynik2 = stages.discovery(None, None, "czy komisja powstanie?", [])
sprawdz("model zapytany RAZ", atrapa2.stan["nr"] == 1, atrapa2.stan["nr"])
sprawdz("i tak samo oddal zrodla", bool(wynik2))

print()
print("=== 3. TRZY RAZY ZERO — STRAZNIK NADAL ZAMYKA ===")
# Straznik zostaje. Adresy z pamieci modelu przepuszczone raz kosztowaly
# dziesiec zmyslonych zrodel, z ktorych trzy sie pobraly.
atrapa3 = _atrapa([0, 0, 0])
with patch.object(stages.llm, "call", atrapa3), \
     patch.object(stages, "hosty_ktore_nigdy_nie_dzialaly", lambda c: []):
    try:
        stages.discovery(None, None, "czy komisja powstanie?", [])
        sprawdz("uporczywe zero konczy sie bledem", False, "przeszlo bez bledu")
    except ValueError as exc:
        sprawdz("uporczywe zero konczy sie bledem", True)
        sprawdz("i blad mowi, o co chodzi",
                "ani jednego wyszukiwania" in str(exc), str(exc)[:70])
sprawdz("byly dokladnie trzy podejscia: proba, powtorka, model zapasowy",
        atrapa3.stan["nr"] == 3, atrapa3.stan["nr"])

print()
print("=== 3b. POWTORKA, KTORA SAMA SIE WYWALA, NIE ZABIJA DIAGNOZY ===")
# WLASNY REGRES, ZLAPANY NA PRODUKCJI GODZINE PO NAPISANIU POPRAWKI.
# Druga proba rzucila `llm.Truncated: Search completed without usable text or
# URLs` i przebieg umarl na wyjatku, ktory nic nie mowi o przyczynie — gorzej
# niz straznik, ktory nazywa rzecz po imieniu. Ratunek ma prawo nie zadzialac;
# nie ma prawa zamienic czytelnej diagnozy w niezrozumialy blad.
stan = {"nr": 0}


def wybuchowa(purpose, system, user, **kw):
    stan["nr"] += 1
    if stan["nr"] == 1:
        return json.dumps(ZRODLA)          # zero adresow w collect_urls
    raise stages.llm.Truncated("Search completed without usable text or URLs")


with patch.object(stages.llm, "call", wybuchowa),      patch.object(stages, "hosty_ktore_nigdy_nie_dzialaly", lambda c: []):
    try:
        stages.discovery(None, None, "czy komisja powstanie?", [])
        sprawdz("konczy sie bledem straznika", False, "przeszlo bez bledu")
    except ValueError as exc:
        sprawdz("konczy sie bledem straznika", True)
        sprawdz("i to on mowi, o co chodzi",
                "ani jednego wyszukiwania" in str(exc), str(exc)[:70])
    except Exception as exc:               # noqa: BLE001
        sprawdz("konczy sie bledem straznika", False,
                "%s zamiast ValueError" % type(exc).__name__)
sprawdz("po niej weszlo jeszcze wyjscie awaryjne", stan["nr"] == 3,
        stan["nr"])

print()
print("=== 3c. AWARIA DOSTAWCY WLACZA MODEL ZAPASOWY, GLOSNO ===")
# ZMIERZONE 10 wrzesnia 2026 na serwerze, gole wywolanie z jednym zdaniem
# polecenia „You MUST use the web_search tool before answering":
#     deepseek-v4-flash   wej=103   wyj=91    zero adresow, Truncated
#     claude-opus-5       wej=38463 wyj=2230  szukania=2, 19 adresow
# Dwa dni wczesniej ten sam deepseek robil po 12-18 wyszukiwan. To awaria
# narzedzia u dostawcy, nie zly prompt.
uzyte_modele = []
stan2 = {"nr": 0}


def po_awarii(purpose, system, user, **kw):
    stan2["nr"] += 1
    uzyte_modele.append(stages.config.MODEL_FOR["discovery"])
    zebrane = kw.get("collect_urls")
    if stan2["nr"] >= 3 and zebrane is not None:      # zapasowy juz szuka
        for zrodlo in ZRODLA["sources"]:
            zebrane.append(zrodlo["url"])
    return json.dumps(ZRODLA)


przed = stages.config.MODEL_FOR.get("discovery")
with patch.object(stages.llm, "call", po_awarii),      patch.object(stages, "hosty_ktore_nigdy_nie_dzialaly", lambda c: []):
    wynik3 = stages.discovery(None, None, "czy komisja powstanie?", [])
sprawdz("artykul jednak powstal", bool(wynik3))
sprawdz("trzecie podejscie poszlo na INNYM modelu",
        len(uzyte_modele) == 3 and uzyte_modele[2] != uzyte_modele[0],
        uzyte_modele)
sprawdz("i byl to model zapasowy",
        uzyte_modele[-1] == getattr(stages.config, "MODEL_ZAPASOWY_WYSZUKIWANIA",
                                    stages.config.CLAUDE),
        uzyte_modele[-1] if uzyte_modele else "-")
# ROUTING WRACA NA MIEJSCE. Bez tego jedna awaria przestawialaby caly przebieg
# na najdrozszy model po cichu — i nikt by tego nie zauwazyl az do rachunku.
sprawdz("routing wrocil na swoje", stages.config.MODEL_FOR.get("discovery") == przed,
        "%s wobec %s" % (stages.config.MODEL_FOR.get("discovery"), przed))

print()
print("=== 4. POWTORKA IDZIE Z TYM SAMYM PYTANIEM ===")
zapytania = []
atrapa4 = _atrapa([0, 2])
prawdziwe = atrapa4


def zapamietaj(purpose, system, user, **kw):
    zapytania.append(user)
    return prawdziwe(purpose, system, user, **kw)


with patch.object(stages.llm, "call", zapamietaj), \
     patch.object(stages, "hosty_ktore_nigdy_nie_dzialaly", lambda c: []):
    stages.discovery(None, None, "czy komisja powstanie?", [])
sprawdz("wszystkie zapytania identyczne", len(zapytania) >= 2
        and len(set(zapytania)) == 1, len(set(zapytania)))
# Powtarzamy TO SAMO, bo problem lezy po stronie wyboru narzedzia, nie tresci.
# Przepisanie pytania przy powtorce zamienialoby ratunek w loterie.

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
