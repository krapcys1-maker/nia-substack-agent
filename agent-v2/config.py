"""Jedyne miejsce ze stałymi.

Zasada nadrzędna tego pliku: **jeden limit, jedno miejsce**. Jeśli jakaś liczba
ma trafić także do promptu, prompt składa się z tej stałej (f-string), a nie
powtarza jej słownie. Poprzedni agent miał 22 pary liczb "stała w kodzie kontra
zdanie w prompcie" i nikt ich nigdy nie porównał — patrz
`archiwum/app/research/output_contract.py`.

Sufity tokenów są WYLICZANE z kontraktów, a nie wpisywane obok nich. Sufit
wpisany ręcznie obok promptu proszącego o więcej, niż się w nim mieści, uciął
odpowiedź DeepSeeka w połowie JSON-a przy pierwszym teście seryjnym.

Sekrety wyłącznie ze zmiennych środowiskowych. Wszystko inne tutaj, bo ten plik
jest w gicie, czyli jest identyczny na tym komputerze i na serwerze.
"""

from __future__ import annotations

import os
import os as _os
import sys
from pathlib import Path

from dotenv import load_dotenv

# --- ścieżki -----------------------------------------------------------------
# Wszystko względem tego pliku. Żadnych ścieżek absolutnych, żadnych backslashy.

AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AGENT_DIR.parent

ENV_PATH = AGENT_DIR / ".env"
DATA_DIR = AGENT_DIR / "data"
DB_PATH = DATA_DIR / "agent-v2.db"
PROMPTS_DIR = AGENT_DIR / "prompts"
ARTICLES_DIR = DATA_DIR / "articles"

# Korpus stylu. Przypięty hashem, bo to jedyna rzecz odróżniająca to konto od
# tysiąca innych — loader ma odmówić, jeśli ktoś po cichu podmieni głos, na
# który właściciel się zgodził.
#
# KORPUS DOSTARCZA OPERATOR I NIE MA GO W REPOZYTORIUM. Do 2026-09-03 leżało
# tu 9383 słowa cudzej, opublikowanej publicystyki — felietony konkretnego
# autora, przepisane co do znaku — a repozytorium jest publiczne. To nie jest
# kwestia higieny nazw, tylko rozpowszechniania cudzego utworu.
#
# Razem z korpusem wyszedł stąd jego SHA-256: opisywał JEDEN plik, którego
# nikt poza właścicielem tamtej instalacji nie ma. Przypięcia stoją teraz
# w `przypiecia.json` obok korpusu, generowane przez
# `narzedzia/przypnij_styl.py`. Zabezpieczenie działa tak samo — patrz
# `style.load_examples`.
#
# NAZWA PLIKU JEST WZORCEM, NIE STAŁĄ: bierzemy pierwszy `.txt` w katalogu,
# żeby operator nie musiał nazywać swojego korpusu po naszemu.
STYLE_CORPUS_DIR = PROMPTS_DIR / "styl"


def _korpus_stylu() -> Path:
    pliki = sorted(p for p in STYLE_CORPUS_DIR.glob("*.txt") if p.is_file())
    # Brak korpusu NIE jest tu błędem: sam import `config` musi się udać na
    # świeżym klonie. Odmawia dopiero `style.load_examples`, i to komunikatem,
    # który mówi, co zrobić.
    return pliki[0] if pliki else STYLE_CORPUS_DIR / "korpus.txt"


STYLE_CORPUS = _korpus_stylu()
STYLE_PROFILES_DIR = REPO_ROOT / "style-profiles"

# PROFILE STYLU SA POLEM PRESETU (`styl.profil_pozytywny`, `styl.profil_negatywny`).
# Do 2026-09-05 `style.load_profiles` mialo obie nazwy plikow wpisane w kod,
# wiec dwa presety o roznych glosach czytaly ten sam profil (C4 audytu).
STYLE_PROFILE_POSITIVE = STYLE_PROFILES_DIR / "ARTICLE_STYLE_PROFILE_V1.md"
STYLE_PROFILE_NEGATIVE = STYLE_PROFILES_DIR / "ARTICLE_NEGATIVE_STYLE_PROFILE_V1.md"

# Czy pisarz artykulu ODMAWIA bez przypietego korpusu. Tak bylo zawsze i tak
# zostaje domyslnie; preset moze to wylaczyc (`styl.wymagaj_korpusu = false`)
# i pisac z samych profili plus opisu glosu — patrz `style.przyklady_albo_pusto`.
STYL_WYMAGAJ_KORPUSU = True

# GLOS OPISANY SLOWAMI (`styl.opis`). Idzie do briefow pisarza, notki,
# komentarza i odpowiedzi jako `{styl_opis}` — patrz `stages._pola_wspolne`.
# Pusty znaczy „bez uwag dodatkowych": profile i korpus dzialaja jak dotad.
STYL_OPIS = ""

# GDZIE NAPRAWDE LEZY PRODUKCJA. Zapamietane TERAZ, przed jakimkolwiek
# przekierowaniem, bo po przestawieniu `DATA_DIR` nie da sie juz odtworzyc,
# gdzie bylo naprawde. Wszystkie zapory nizej pytaja o TE sciezke, nie o
# biezaca wartosc `DATA_DIR`.
PRODUKCYJNY_KATALOG_DANYCH = DATA_DIR

load_dotenv(ENV_PATH)
# Zapasowo .env z katalogu głównego repozytorium: właściciel dopisał klucz
# OpenAI tam, a agent szukał go tylko u siebie i widział "BRAK". Sekret ma leżeć
# w jednym miejscu, więc zamiast kopiować go w dwa pliki, czytamy oba. Bez
# `override` — plik agenta zawsze wygrywa.
load_dotenv(REPO_ROOT / ".env", override=False)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# --- sekrety -----------------------------------------------------------------

ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY")
OPENAI_API_KEY = _env("OPENAI_API_KEY")   # wylacznie do grafik

# Grafika do artykulu. Wybor NIE jest podyktowany cena: przy jednym obrazie na
# artykul nawet najdrozsza opcja to grosze miesiecznie, a taniej znaczy tu
# gorzej i mniej powtarzalnie. Rozmiar 1536x1024 mniej-wiecej odpowiada
# proporcjom naglowka na Substacku.
IMAGE_MODEL = "gpt-image-1.5"
IMAGE_SIZE = "1536x1024"
IMAGE_QUALITY = "high"
IMAGE_PRICE_USD = 0.04   # cennik sierpien 2026, NIEPOTWIERDZONY na fakturze
IMAGE_TIMEOUT_S = 300

# Konto na Substacku.
# Nazwa publikacji, tak jak ma ja widziec model i czytelnik.
#
# DO 2026-09-03 NIE ISTNIALA JAKO STALA. Nazwa stala wpisana w dziewieciu
# promptach, w dwoch komunikatach systemowych i w obu profilach stylu — i to
# wystarczylo, zeby przezyla caly przebieg czyszczenia tozsamosci:
# w `SCOUT_SYSTEM` byla ROZBITA MIEDZY DWA SASIADUJACE LITERALY, ktore
# Python sklei dopiero przy wykonaniu. Zaden skan po pelnej nazwie nie
# mial szansy jej zobaczyc, bo w zrodle pelnej nazwy nie bylo — byly
# dwa kawalki i cudzyslow miedzy nimi. Dlatego audyt sklada literaly
# przez `ast.literal_eval` i dopiero WYNIK porownuje ze wzorcami.
#
# ZDANIE, KTORE TU STALO, PRZESTALO BYC PRAWDA I TO TEZ JEST WADA. Brzmialo:
# „Prompty w `prompts/*.md` nadal maja ja wpisana w tresci — ich przepiecie na
# pole to osobna robota". Przepiecie zostalo zrobione tego samego dnia:
# dziewiec promptow sklada nazwe z `{marka}` (patrz `stages._pola_wspolne`),
# a `tests/test_prompty_o_niszy.py` oblewa, gdy ktorys wroci do wpisywania jej
# w tresci. Notatka „do zrobienia", ktora przezyla swoja robote, kaze szukac
# problemu, ktorego nie ma — i to jest ten sam koszt, co notatka, ktora
# obiecuje kontrole, ktorej nie ma.
NAZWA_MARKI = "Your Publication"

SUBSTACK_HANDLE = "your-handle"

# Czy agent ma klikac "Wylacz wykrywanie AI" przy kazdej publikacji.
# WLACZONE decyzja wlasciciela z 2026-08-15. To wybor publiczny, nie ustawienie
# techniczne, wiec nalezal do niego, a nie do kodu.
# Co to ZMIENIA: skan zwraca "nie kwalifikuje sie do wykrywania" zamiast oceny.
# Czego NIE zmienia: oswiadczenie "Jak to robie" (prompts/OSWIADCZENIE_AUTORSTWA.md)
# pokazuje sie tak samo, wiec pytajacy dalej dostaje nasza odpowiedz — a ta
# odpowiedz nadal nie twierdzi, ze pisal to czlowiek. Granica z ADR-018 stoi.
WYLACZ_WYKRYWANIE_AI = True

# --- tryby -------------------------------------------------------------------

DRY_RUN = _env("DRY_RUN", "false").lower() in {"1", "true", "yes"}
KILL_SWITCH = _env("KILL_SWITCH", "false").lower() in {"1", "true", "yes"}
NO_LIMIT = _env("AGENT_V2_NO_LIMIT", "0").lower() in {"1", "true", "yes"}

# Serwer bez ekranu: zamiast podlaczac sie do Chrome'a uruchomionego przez
# czlowieka, agent otwiera wlasna przegladarke bez ekranu i wklada jej zapisana
# sesje. Wlaczane zmienna, zeby ten sam kod chodzil tu i tam bez rozgalezien.
TRYB_SERWERA = _env("AGENT_V2_SERVER", "0").lower() in {"1", "true", "yes"}

# --- modele ------------------------------------------------------------------
# Podział z briefu: DeepSeek tam, gdzie błąd kosztuje jedno tanie wywołanie;
# Claude tam, gdzie błąd kosztuje cały łańcuch albo jakość tekstu.

CLAUDE = "claude-opus-5"
SONNET = "claude-sonnet-5"
# PISARZ ARTYKULOW. Fable 5.1 wyszedl 1 wrzesnia 2026 i od 3 wrzesnia pisze
# artykuly; poprzednik zostaje pod wlasna nazwa, bo pod nia stoi cala historia
# kosztow i porownan A/B z sierpnia.
#
# Sprawdzone NA ZYWO przed przestawieniem, nie po: `claude-fable-5-1` odpowiada
# (18 tokenow wejscia, 4 wyjscia). Przestawienie pisarza artykulow na
# identyfikator, ktorego nie ma, zabiloby wtorkowy artykul — a najblizszy jest
# 8 wrzesnia, wiec wyszloby to dopiero za piec dni.
FABLE_5 = "claude-fable-5"          # poprzednik, zostaje dla historii i porownan
FABLE = "claude-fable-5-1"  # najmocniejszy, dwa razy droższy od Opusa
DEEPSEEK = "deepseek-v4-flash"
DEEPSEEK_PRO = "deepseek-v4-pro"  # ma server-side web_search przez /responses

# Decyzja wlasciciela 2026-08-15 zaczela od DeepSeeka poza pisaniem. Po
# pozniejszych testach artykuly trafily do Fable 5, notki do Opusa 5, a etapy
# DeepSeeka zostaly rozdzielone miedzy wariant Pro i Flash ponizej.
MODEL_FOR = {
    "scout": DEEPSEEK_PRO,
    "feasibility": DEEPSEEK,  # tani odsiew przed drogim krokiem
    # Dyskoveria dziala na DeepSeek V4 Pro przez `/responses` z server-side
    # `web_search`: wybor adresow to praca mechaniczna, nie ocena. Kazda runda
    # przesyla cala rozmowe od nowa, wiec wejscie rosnie — zmierzone na
    # trzynastu wywolaniach `discovery` na DeepSeeku: od 72 do ponad 196 tys.
    # tokenow. (Liczba „~146 tys." opisywala epoke Opusa i domykal ja rachunek
    # $0,73 po stawce Anthropic; po przejsciu na DeepSeeka nie znaczy juz nic.)
    # Opus byl wczesniejsza droga, zanim skrocenie promptu domknelo DeepSeeka.
    #
    # Sprawdzone na żywo, żeby nie powtarzać:
    #  - Haiku 4.5, Sonnet 5: NIE wywołują wyszukiwania w ogóle, wypisują adresy
    #    z pamięci (977 i 1073 tokeny wejścia, zero wyników). Także po jawnym
    #    nakazie szukania w prompcie.
    #  - DeepSeek v4-pro przez /responses: szuka NAPRAWDĘ i tanio ($0,05 wobec
    #    $0,46 u Opusa, dziewięć razy taniej), zwraca prawdziwe adresy (OSHA,
    #    Cornell Law, NFPA). ALE przy tym prompcie nie kończy: robi 11-22
    #    wyszukiwań, zużywa cały budżet wyjścia na rozumowanie i nigdy nie tworzy
    #    bloku `message`. Przy krótkim prompcie kończy poprawnie, więc droga
    #    prowadzi przez uproszczenie promptu dyskoverii, nie przez model.
    #    Po skróceniu promptu do ~250 słów kończy poprawnie — i tak zostaje.
    #  - Opus jest NIEPRZEWIDYWALNY kosztowo: te same 8 wyszukiwań dały raz
    #    52 767 tokenów wejścia ($0,46), a raz 285 759 ($1,65), bo wielkość
    #    wyników zależy od tematu. To dyskwalifikuje go z etapu, który biegnie
    #    codziennie bez nadzoru.
    "discovery": DEEPSEEK_PRO,
    "classify": DEEPSEEK,  # mechaniczne, wysokowolumenowe
    "synthesis": DEEPSEEK_PRO,
    # TO JEST PRODUKT. Fable 5 po porównaniu A/B na identycznej karcie: krótszy
    # i bliższy celu długości (1127 wobec 1204 słów), ale przede wszystkim
    # dokładniejszy — wyłapał, że cytowany przepis jest WĘŻSZY niż jego
    # popularne streszczenie, i poprawił po tym omówienie w tekście. Opus tego
    # nie zauważył. Kosztuje 3,5x więcej, co przy 4 artykułach miesięcznie
    # znaczy $2,12 zamiast $0,61.
    "write": FABLE,
    "review": DEEPSEEK_PRO,
    # Obserwacja formy: beaty, eskalacja, moment przylapania, znajomosc
    # otwarcia. Osobne wywolanie od recenzji CELOWO — recenzent ma wprost
    # chronic wnioskowanie przed zgloszeniem, a ta bramka liczy m.in.
    # zastrzezenia. Zlaczone w jedno pytanie tepilyby sie nawzajem.
    "forma": DEEPSEEK_PRO,
    # Komentarze ida na DeepSeek V4 Pro, notki na Claude Opus 5. Notka ma jeden
    # wariant (`NOTE_CANDIDATES = 1`), wiec nie powstaje pula kilkunastu
    # kandydatow do wyboru.
    # PODZIAL PO TESCIE A/B NA TYM SAMYM POSCIE. Pro przynioslo KONKRETNY
    # precedens — nazwana sprawe z data — i nazwalo asymetrie kosztu bledu;
    # flash dal uwage trafna, ale ogolnikowa. Roznica
    # kosztu to ~12 USD miesiecznie i placimy ja TAM, GDZIE TEKST JEST PUBLICZNY
    # I TRWALY — a nie tam, gdzie model tylko wybiera z listy albo opisuje obrazek.
    # NOTKA IDZIE DO FABLE — zmiana na galezi v2-test, po A/B na tym samym
    # materiale z banku. Trzy powody, w tej kolejnosci:
    #
    # 1. Fable pisze wyraznie lepiej i to widac golym okiem. Na tym samym
    #    materiale DeepSeek dal opis nieprzezroczysty dla kogos spoza
    #    branzy, a Fable te sama rzecz nazwal tak, ze widac ja bez
    #    slownika — i zamknal jednym zdaniem, ktore niosło cala mysl.
    #    Fable sformatowal tez numer identyfikacyjny z przecinkami
    #    zamiast ciagiem, wiec czyta sie jak wielkosc, a nie jak kod.
    # 2. Badania nad Substackiem mowia zgodnie, ze NOTKI daja ponad 60%
    #    przyrostu subskrybentow i sa jedynym narzedziem pokazujacym nas
    #    ludziom, ktorzy nas nie obserwuja. Artykul czyta ten, kto juz
    #    przyszedl.
    # 3. Do tej pory bylo odwrotnie niz powinno: najdrozszy model pisal to,
    #    co NIE napedza wzrostu (piec artykulow = $2,13), a najtanszy to,
    #    co napedza.
    #
    # 2026-08-19, PO DWOCH SLEPYCH TESTACH: notka idzie do OPUSA, nie Fable.
    #
    # Powyzsze uzasadnienie bylo oparte na porownaniu, w ktorym znalismy
    # etykiety. Dwie proby na slepo daly co innego:
    #   Fable kontra DeepSeek-pro   3 : 2
    #   Fable kontra Opus 5         2 : 2
    # Na dziewiec par Fable wygral piec. To jest rzut moneta, a nie przewaga.
    # Wlasciciel wybieral w ciemno i w zadnej probie nie rozpoznal drozszego
    # modelu.
    #
    # Opus jest dokladnie dwa razy tanszy od Fable ($5/$25 wobec $10/$50)
    # i nadal jest modelem najwyzszej polki, wiec ryzyko, ze czterdziesci piec
    # slow zabrzmi „przetlumaczone", zostaje znikome. Tego akurat zaden slepy
    # test nie zlapie pewnie i dlatego nie schodzimy nizej dla ostatnich
    # $4,59 miesiecznie.
    #
    # Razem z zejsciem na jeden wariant: $42,05 -> $6,07 miesiecznie za notki.
    # ARTYKUL zostaje na Fable — tam A/B z Opusem dotyczyl calego tekstu,
    # a nie czterdziestu pieciu slow, i przy czterech artykulach miesiecznie
    # roznica ceny to $1,85.
    "note": CLAUDE,
    # DRUGI PISARZ NOTEK — TEN SAM ETAP, INNY MODEL, OSOBNA POZYCJA W KSIEDZE.
    #
    # Notki ida na zmiane: parzysta Opusem, nieparzysta DeepSeekiem. Osobna
    # nazwa etapu zamiast parametru `model=` przy wywolaniu jest tu celowa —
    # tabela `calls` rozlicza po etapie, wiec koszt obu pisarzy rozdziela sie
    # SAM, bez dokladania kolumny i bez liczenia czegokolwiek recznie.
    #
    # Po co w ogole: notka na Opusie kosztuje 0,084 USD, na DeepSeeku pro
    # 0,010 — osiem razy taniej. Slepa proba z 19 sierpnia pokazala, ze przy
    # notkach wlasciciel NIE ROZPOZNAL drozszego modelu (Fable kontra Opus
    # 2:2 na dziewieciu parach). Podzial pol na pol jest wiec jednoczesnie
    # oszczednoscia i testem: po dwoch tygodniach zobaczymy z dziennika, czy
    # notki jednego pisarza zbieraja wiecej odpowiedzi niz drugiego.
    "note_tani": DEEPSEEK_PRO,
    "comment": DEEPSEEK_PRO,
    "reply": DEEPSEEK_PRO,
    # RANKING BANKU POMYSLOW. Flash, bo to porzadkowanie kilkudziesieciu
    # jednozdaniowych opisow, a nie rozumowanie o tresci — i ma byc tanie,
    # zeby oplacalo sie wolac je czesto.
    "bank": DEEPSEEK,
    "factcheck": DEEPSEEK,
    # NAPRAWA OBALONEGO ZDANIA. Kazdy tekst wraca do TEGO SAMEGO modelu,
    # ktory go napisal — notka do Opusa, komentarz do DeepSeeka-pro. Nie z
    # oszczednosci, tylko dlatego, ze naprawa ma zachowac glos: model, ktory
    # nie pisal tego zdania, przepisuje przy okazji rytm calego tekstu, a
    # wtedy „popraw jedna liczbe" cichcem staje sie „napisz to jeszcze raz".
    "naprawa": CLAUDE,
    "naprawa_komentarza": DEEPSEEK_PRO,
    # Pytanie „jakie modele sa dzisiaj" MUSI isc na model z wyszukiwaniem —
    # to jest cala jego wartosc. Ten sam, co sprawdzanie faktow, bo robi
    # dokladnie to samo: konfrontuje pamiec ze swiatem.
    "aktualne_modele": DEEPSEEK,
    "curiosity": DEEPSEEK,
    "grafika": DEEPSEEK,
    "cele": DEEPSEEK,
    "wybor": DEEPSEEK_PRO,
    # Bibliotekarz czyta caly bank naraz i szuka MECHANIZMU wspolnego
    # dla roznych dziedzin. Pro, bo to jedyne zadanie w systemie, gdzie
    # trzeba trzymac w glowie sto kilkadziesiat fragmentow jednoczesnie
    # i widziec miedzy nimi zwiazek — a przy 10 tys. tokenow wejscia
    # roznica ceny to ulamek centa.
    "bibliotekarz": DEEPSEEK_PRO,
    # Bramka ciekawosci przed pisarzem. Pro, bo musi rozpoznac, jakie
    # przekonanie czytelnik przynosi ze soba — to sad o ludziach,
    # nie odczyt z tekstu.
    "warto_pisac": DEEPSEEK_PRO,
    # Restack: jedno zdanie, ktore ma stanac obok cudzego tekstu pod naszym
    # nazwiskiem. Pro z tego samego powodu co komentarze — najczesciej trzeba
    # przypomniec sobie, GDZIE INDZIEJ ten sam mechanizm dziala, a to pamiec
    # faktow, jedyna trwala przewaga pro nad flashem.
    "restack": DEEPSEEK_PRO,
    # Wyciaganie kandydatow z preambuly przepisu. Flash, bo to praca
    # WYDOBYWCZA na podanym tekscie, a nie siegniecie do pamieci o swiecie —
    # czyli dokladnie ta kategoria, w ktorej flash dorownuje pro i jest
    # trzykrotnie tanszy. Preambuly bywaja polmilionowe, wiec objetosc
    # wejscia decyduje o rachunku.
    "fedreg": DEEPSEEK,
}

DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Głębokość rozumowania DeepSeeka na /responses. Tokeny rozumowania liczą się
# do sufitu wyjścia, więc przy `high` model kończy budżet na szukaniu i nie
# zdąża napisać odpowiedzi.
DEEPSEEK_EFFORT = "low"

# Tryb tani: wszystko na DeepSeeku poza dyskoveria, ktora ten jawny override
# zostawia u Claude'a. Sluzy do testowania HYDRAULIKI — czy lancuch przechodzi,
# JSON sie parsuje i zapis dziala — nie do oceny produkcyjnego tekstu Fable 5.
# Produkcyjna dyskoveria korzysta z web_search DeepSeek V4 Pro; wyjatek dotyczy
# tylko tego trybu.
CHEAP_MODE = _env("AGENT_V2_CHEAP", "0").lower() in {"1", "true", "yes"}

if CHEAP_MODE:
    MODEL_FOR = {k: (CLAUDE if k == "discovery" else DEEPSEEK) for k in MODEL_FOR}

# Podmiana samego pisarza, do porównań A/B na tej samej karcie dowodowej:
#   AGENT_V2_WRITER=claude-fable-5 python agent-v2/run.py --use-cache
_writer = _env("AGENT_V2_WRITER")
if _writer:
    MODEL_FOR["write"] = _writer

# Rysowanie nie ma nic wspolnego z trybem taniego tekstu, wiec dopisujemy je PO
# podmianach powyzej — inaczej CHEAP_MODE przestawilby generator obrazow na
# model jezykowy. Etapy bez tokenow nie maja sufitu tokenow: wpisanie tam liczby
# byloby zmyslona wartoscia w pliku, ktory ma byc jedynym zrodlem prawdy.
MODEL_FOR["obraz"] = IMAGE_MODEL
BEZ_TOKENOW = {"obraz"}

# CZY OKLADKA W OGOLE POWSTAJE. Preset wylacza ja pustym `modele.obraz`;
# `stages.grafika` wtedy nie wola ani briefu, ani OpenAI. Do 2026-09-05
# jedynym sposobem na brak okladki byl brak klucza — czyli awaria udajaca
# decyzje.
OBRAZ_WLACZONY = True

# NA JAKI MODEL WRACA PISARZ PO AWARII SKONFIGUROWANEGO. `run.py`
# i `artykul_z_puli.py` mialy tu wpisane `config.CLAUDE` na sztywno, wiec
# zmiana pisarza w konfiguracji nie mowila nic o tym, co stanie sie po jego
# awarii (M3 audytu). Pusty napis znaczy: nie wracaj, zatrzymaj sie.
ZAPASOWY_PISARZ = CLAUDE

# --- cennik ------------------------------------------------------------------
# USD za milion tokenów. `verified` mówi, czy stawka została potwierdzona realnym
# rozliczeniem. Niepotwierdzonej ceny nie wolno podawać jako faktu — koszt liczony
# taką stawką jest oznaczany w bazie (`calls.price_verified = 0`).

PRICING = {
    CLAUDE: {"in": 5.00, "out": 25.00, "verified": True},
    SONNET: {"in": 3.00, "out": 15.00, "verified": True},
    # STAWKA FABLE 5.1 NIEPOTWIERDZONA. Wpisana z ceny poprzednika, bo model
    # wyszedl 1 wrzesnia i nie ma go jeszcze na zadnej naszej fakturze.
    # `verified: False` sprawia, ze kazde takie wywolanie zapisuje sie
    # z `price_verified = 0` — czyli koszt artykulu bedzie widoczny jako
    # SZACUNEK, dopoki nie sprawdzimy go na rozliczeniu.
    FABLE: {"in": 10.00, "out": 50.00, "verified": False},
    FABLE_5: {"in": 10.00, "out": 50.00, "verified": True},
    # STAWKI POTWIERDZONE FAKTURA (15-19 sierpnia 2026). Dziesiec wierszy
    # rozliczenia odtworzonych co do centa, wiec `verified` znaczy tu wreszcie
    # to, co powinno: rozliczone z rachunkiem, nie przepisane z cennika.
    #
    # Co bylo zle wczesniej i czemu trudno bylo to zobaczyc: mnozniki taryfy
    # wykalibrowano na WYJSCIU (0,87 x 2,28 = 1,98 — trafione co do grosza)
    # i ten sam mnoznik zastosowano do wejscia i cache. A rodzaje tokenow
    # podrozaly ROZNIE: wejscie 1,52x, wyjscie 2,28x, cache 6,07x. Skutek:
    # wejscie zawyzone o polowe, cache zanizone prawie trzykrotnie.
    #
    # "in" to stawka cache MISS; trafienia w cache licza sie osobno po "cache"
    # — dostawca podaje ich liczbe w kazdej odpowiedzi, wiec nie zgadujemy.
    DEEPSEEK: {"in": 0.22, "out": 0.66, "cache": 0.007, "verified": True},
    DEEPSEEK_PRO: {"in": 0.66, "out": 1.98, "cache": 0.022, "verified": True},
}

# --- taryfa szczytowa DeepSeeka -----------------------------------------------
# Od 2026-08-16 16:00 UTC DeepSeek wprowadza ceny szczytowe i pozaszczytowe:
# poza szczytem polowa ceny szczytowej. Rozniica jest ogromna — pro w szczycie
# to $3,96 za milion tokenow wyjscia wobec $1,98 poza nim.
#
# WNIOSEK DLA HARMONOGRAMU: agent ma pracowac POZA SZCZYTEM. To nie jest
# oszczedzanie na sile, tylko darmowa polowa rachunku za przesuniecie godziny.
# Stawki sprzed podwyzki z 16 sierpnia — trzymane, zeby dalo sie przeliczyc
# historie i zeby bylo widac, o ile podrozalo.
STAWKI_PRZED_PODWYZKA = {
    DEEPSEEK: {"in": 0.14, "out": 0.28, "cache": 0.0028},
    DEEPSEEK_PRO: {"in": 0.435, "out": 0.87, "cache": 0.003625},
}

TARYFA_SZCZYTOWA_OD = "2026-08-16T16:00:00+00:00"
GODZINY_SZCZYTU_UTC = frozenset(range(1, 4)) | frozenset(range(6, 10))

# Mnozniki wzgledem stawek wyzej, po wejsciu nowej taryfy.
# Szczyt to DOKLADNIE dwukrotnosc bazy, jednakowo dla wejscia, wyjscia
# i cache. Sprawdzone na fakturze: 1,32/0,66, 3,96/1,98, 0,044/0,022.
MNOZNIK_SZCZYT = 2.0
MNOZNIK_POZA_SZCZYTEM = 1.0   # baza to juz stawka po podwyzce


def stawka_deepseek(model: str, kiedy=None) -> dict[str, float]:
    """Stawka DeepSeeka z uwzglednieniem pory doby po wejsciu nowej taryfy."""
    from datetime import datetime, timezone

    baza = PRICING[model]
    kiedy = kiedy or datetime.now(timezone.utc)
    if kiedy < datetime.fromisoformat(TARYFA_SZCZYTOWA_OD):
        # Przed podwyzka. Zostawiamy do liczenia historii, nie do biezacych
        # wywolan — te i tak dzieja sie po tej dacie.
        stare = STAWKI_PRZED_PODWYZKA[model]
        return {"in": stare["in"], "out": stare["out"], "cache": stare["cache"],
                "szczyt": None}
    # PYTAMY `w_szczycie`, NIE POWTARZAMY WARUNKU. Ta sama regula stala tu
    # wpisana drugi raz (`kiedy.hour in GODZINY_SZCZYTU_UTC`, dwa razy
    # w tej funkcji), a `w_szczycie` — wersja wyciagnieta — nie miala ANI
    # JEDNEGO wolajacego. Dwie kopie jednej reguly, z ktorych ta uzywana
    # nie byla tą testowaną.
    szczyt = w_szczycie(kiedy)
    m = MNOZNIK_SZCZYT if szczyt else MNOZNIK_POZA_SZCZYTEM
    # CACHE TEZ. Brak tego klucza sprawial, ze `_cost` siegalo po stawke
    # wejsciowa i liczylo trafienia w cache 45 razy drozej, niz sa — a to
    # najliczniejszy rodzaj tokenow, jaki mamy.
    return {"in": round(baza["in"] * m, 6), "out": round(baza["out"] * m, 6),
            "cache": round(baza["cache"] * m, 6),
            "szczyt": szczyt}


def pora_na_publikacje(kiedy=None) -> tuple[bool, str]:
    """Czy teraz wolno wystawiac NOTKI — wg zegara CZYTELNIKOW, nie serwera.

    DOTYCZY WYLACZNIE NOTEK. Komentarze i odpowiedzi stoja pod CUDZYMI
    tekstami: ich widocznosc zalezy od ruchu na tamtym poscie, a nie od tego,
    czy nasza publicznosc akurat spi. Blokowanie ich oknem bylo rozszerzeniem
    reguly poza jej wlasne uzasadnienie („nowe tresci konkuruja o miejsce
    w kanale") — patrz `run.py`.

    „NAJGORSZE OKNO" PRZESTALO BYC BRAMKA 31 sierpnia 2026, decyzja
    wlasciciela („nawet za cene wypuszczania poza oknami, bo tak to do konca
    swiata bedziemy sie bawic z czekaniem na agenta i jego okno").

    ZMIERZONE TEGO DNIA, i to jest cala argumentacja: przebieg o 17:00 UTC
    wypada 13:00 ET, czyli DOKLADNIE w `WORST_NOTE_HOURS`. Blokowal sie wiec
    CODZIENNIE — jeden z pieciu przebiegow, 20% dziennej zdolnosci. Tego dnia
    znalazl DZIEWIEC celow wartych komentarza (`warte komentarza: 9/23`,
    najlepszy wynik od przestawienia konta) i nie wystawil ANI JEDNEGO.

    A sama regula stala na wlasnym zaprzeczeniu: komentarz dwa akapity nizej
    w tym pliku mowi wprost, ze NASZE WLASNE ZRODLA SIE NIE ZGADZAJA — jedno
    wskazuje 6-8 ET, drugie 15-18 ET. Egzekwowanie godzin, o ktorych sami
    piszemy, ze nie wiemy, kosztowalo nas piata czesc dnia.

    Prog snu ZOSTAJE. To jest inne twierdzenie i lepiej uzasadnione: tekst
    wrzucony, gdy publicznosc spi, traci pierwsze godziny widocznosci.
    """
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    kiedy = kiedy or datetime.now(timezone.utc)
    lokalnie = kiedy.astimezone(ZoneInfo(PUBLISH_TIMEZONE))
    g = lokalnie.hour
    dol, gora = OKNO_PUBLIKACJI_ET
    if not dol <= g < gora:
        return False, (f"{g:02d}:{lokalnie.minute:02d} u czytelnikow — poza oknem "
                       f"{dol}:00-{gora}:00, publicznosc spi")
    if g in WORST_NOTE_HOURS:
        # NIE BLOKUJEMY, MELDUJEMY. Zapis zostaje, zeby dalo sie pozniej
        # sprawdzic, czy notki z tych godzin faktycznie wypadaja gorzej —
        # a `wystawione` w statystykach daje juz do tego godzine.
        return True, (f"{g:02d}:{lokalnie.minute:02d} u czytelnikow"
                      f" (godzina oznaczona jako slabsza — nie blokuje)")
    return True, f"{g:02d}:{lokalnie.minute:02d} u czytelnikow"


def w_szczycie(kiedy=None) -> bool:
    """Czy teraz obowiazuje droga taryfa."""
    from datetime import datetime, timezone

    kiedy = kiedy or datetime.now(timezone.utc)
    if kiedy < datetime.fromisoformat(TARYFA_SZCZYTOWA_OD):
        return False
    return kiedy.hour in GODZINY_SZCZYTU_UTC


# Filtrowanie dynamiczne (`_20260209`) jest na Opusie i Sonnecie 5.
WEB_SEARCH_TOOL = {
    CLAUDE: "web_search_20260209",
    SONNET: "web_search_20260209",
    # FABLE brakowalo, a to na nim chodzi pisarz. Dzis nie wybucha, bo
    # `write` nie szuka w sieci — ale jedna zmiana MODEL_FOR wystarczyla,
    # zeby dostac KeyError w SRODKU platnej sciezki, po oplaceniu
    # wczesniejszych etapow.
    FABLE: "web_search_20260209",
    FABLE_5: "web_search_20260209",
}

# Wersja narzedzia wyszukiwania dla modelu Anthropic, z galezia awaryjna.
NAJNOWSZE_WYSZUKIWANIE = "web_search_20260209"


def narzedzie_wyszukiwania(model: str) -> tuple[str, str]:
    """Nazwa narzedzia wyszukiwania i ewentualne ostrzezenie.

    Bylo `WEB_SEARCH_TOOL[model]` — czyli KeyError dla kazdego modelu
    Anthropic spoza slownika, rzucany w srodku platnego wywolania, po
    oplaceniu wszystkich wczesniejszych etapow. Wpisu dla Fable po prostu
    nie bylo, choc to na nim chodzi pisarz.

    Nieznany model dostaje najnowsza znana wersje narzedzia i GLOSNE
    ostrzezenie. Zle zgadnieta wersja narzedzia konczy sie bledem od API,
    ktory widac; KeyError w polowie platnej sciezki widac duzo gorzej.
    """
    if model in WEB_SEARCH_TOOL:
        return WEB_SEARCH_TOOL[model], ""
    return NAJNOWSZE_WYSZUKIWANIE, (
        "model %s nie ma wpisu w WEB_SEARCH_TOOL — biore %s. "
        "Dopisz go, zanim ktos zmieni MODEL_FOR."
        % (model, NAJNOWSZE_WYSZUKIWANIE))

# Wyszukiwanie po stronie Anthropic: USD za 1000 zapytań.
WEB_SEARCH_USD_PER_1K = 10.00

# --- limity pieniężne --------------------------------------------------------

# SUFIT DZIENNY PODNIESIONY NA CZAS DOMYKANIA PRZEROBKI KONTA.
#
# 5,00 USD to wartosc dla NORMALNEJ pracy agenta i do niej wracamy. Zmierzone
# na czterech spokojnych dniach: 0,55 / 0,69 / 0,87 / 0,69 USD na dobe, czyli
# okolo jednej siodmej sufitu — zapas byl duzy.
#
# przerobka konta na nowa nisze wymagala wielokrotnych przebiegow
# testowych i sufit zostal dotkniety: 5,39 USD, z czego 3,04 na samo pisanie
# (cztery artykuly, bo trzy razy znajdowalem wade i puszczalem od nowa).
# Wlasciciel autoryzowal na te prace 10 USD wprost, wiec sufit rowna sie tej
# kwocie — nie wiecej.
#
# PO ZAKONCZENIU PRZEROBKI WRACA 5,00. To nie jest nowa norma, tylko okno.
#
# OKNO ZAMKNIETE 25 sierpnia o 21:40 UTC. Dzien testowy zamknal sie na 7,40 USD
# przy autoryzowanych 10 — artykul, dwie notki, cztery komentarze, dziesiec
# polubien, restack i subskrypcja zmiescily sie w tej kwocie. O 00:04 UTC timer
# odpala przebieg BEZ NADZORU, a sufit 10 USD byl zgoda na jeden dzien pracy
# przy wlascicielu, nie stala swoboda dla nocnych przebiegow. Normalna doba
# kosztuje 0,69–0,87 USD, wiec 5,00 zostawia ponad pieciokrotny zapas.
# OKNO OTWARTE PONOWNIE 30 sierpnia — I SAMO SIE ZAMYKA.
#
# Dzien audytu segmentu tematow zjadl 3,87 USD do poludnia, z czego wiekszosc na
# MOJE przebiegi sprawdzajace: trzy przejscia sciezki artykulu, dwa pelne
# przebiegi szukania ciekawostek, cztery rankingi banku, skaut. To nie jest
# produkcja konta — to jest praca nad kodem, ktora akurat kosztuje przez API.
#
# Wlasciciel: „zwieksz budzet na dzis do 10 albo nie licz budzetu do testow, to
# cos osobnego". Ma racje co do zasady i wlasciwa odpowiedzia jest OSOBNY TOR
# TESTOWY, a nie wieksza liczba — bo wieksza liczba wroci jutro jako ten sam
# problem. Tor powstaje osobno; to tutaj ratuje dzisiejszy przebieg.
#
# DATA, NIE PRZELACZNIK. Poprzednim razem sufit 10 USD zostal wlaczony na dzien
# pracy przy wlascicielu i trzeba go bylo pamietac wylaczyc — a o 00:04 timer
# odpala przebieg BEZ NADZORU. Tym razem podniesienie WYGASA SAMO: jutro plik
# jest ten sam, a sufit z powrotem 5,00, bez niczyjej pamieci.
#
# DZIEN JEST POLEM KONFIGURACJI I DOMYSLNIE PUSTY. Stala trzymala tu date
# jednego dnia pracy przy jednym koncie („2026-08-30"), wiec u kazdej innej
# instalacji ten mechanizm byl martwy: podniesienie sufitu wymagaloby edycji
# kodu. Pusta wartosc znaczy „dzis nie ma podniesienia" — i to jest stan,
# w ktorym ma stac przez wiekszosc dni.
import datetime as _dt_sufit  # noqa: E402


def _dzis_utc() -> str:
    """Dzisiejszy dzien UTC. Funkcja, nie stala — proces moze przejsc polnoc."""
    return _dt_sufit.datetime.now(_dt_sufit.timezone.utc).strftime("%Y-%m-%d")


SUFIT_PODNIESIONY_NA = ""

# O ILE PODNOSI SIE SUFIT W DNIU PRACY PRZY WLASCICIELU. Mnoznik, nie druga
# liczba: sufit dzienny jest polem konfiguracji, a wpisana tu kwota
# rozjechalaby sie z nim przy pierwszej zmianie.
SUFIT_PODNIESIONY_RAZY = 2.0

# SUFIT BAZOWY JEST POLEM KONFIGURACJI (`pieniadze.sufit_dzienny_usd`),
# a `DAILY_LIMIT_USD` — jego POCHODNA na dzis. Odwrotnie bylo zle i kosztowalo
# to podwojne naliczenie podwyzki: konfiguracja ustawiala `DAILY_LIMIT_USD`,
# ktory JUZ byl pomnozony przy imporcie, a `sufit_dnia()` mnozyl go DRUGI RAZ.
# W dniu podniesienia sufit wychodzil CZTERY razy wiekszy od bazowego — i to
# akurat tego dnia, w ktorym pieniedzy pilnuje sie najuwazniej. Branch nie
# wykonal sie nigdy, bo data podniesienia byla przeszla.
SUFIT_DZIENNY_BAZOWY = 5.00


def sufit_dnia(dzien: str) -> float:
    """Sufit obowiazujacy W TYM DNIU, nie dzisiaj.

    `DAILY_LIMIT_USD` mowi o DZISIAJ i to jest poprawne dla egzekwowania.
    Ale alarm kosztu patrzy takze na WCZORAJ — a wczoraj sufit mogl byc inny.

    Zmierzone 31 sierpnia: alarm doniosl „Wczoraj wydane $7.22 przy dziennym
    suficie $5.0". Wczorajszy sufit wynosil DWA RAZY WIECEJ (podniesiony na
    jeden dzien pracy przy wlascicielu), wiec zaden sufit nie zostal
    przekroczony — alarm porownal wczorajszy wydatek z dzisiejsza wartoscia.

    Falszywy alarm uczy ignorowac alarmy, a ten akurat ma pilnowac pieniedzy.

    LICZY SIE OD `SUFIT_DZIENNY_BAZOWY`, NIE OD LICZB WPISANYCH TUTAJ. Stalo
    tu `return 10.00 if ... else 5.00` — dwie kwoty wpisane drugi raz, obok
    pola konfiguracji, ktore mowi to samo. Konto z sufitem 3 USD dostawaloby
    alarm dopiero po piatym, a konto z sufitem 20 — codziennie o niczym.

    I NIE OD `DAILY_LIMIT_USD`, bo ten jest JUZ PO podniesieniu. Poprawka
    zdejmujaca dwie wpisane kwoty siegnela po niego i podwyzka naliczala sie
    dwa razy: w dniu podniesienia wychodzilo czterokrotnosc bazy. Pierwsza
    poprawka usunela duplikat i wprowadzila podwojne mnozenie; obie wady maja
    to samo zrodlo — dwie stale mowiace o tej samej kwocie w dwoch stanach.
    """
    return (SUFIT_DZIENNY_BAZOWY * SUFIT_PODNIESIONY_RAZY
            if SUFIT_PODNIESIONY_NA
            and str(dzien)[:10] == SUFIT_PODNIESIONY_NA
            else SUFIT_DZIENNY_BAZOWY)


# Podniesienie WYGASA SAMO: jutro plik jest ten sam, a sufit z powrotem bazowy.
# Przeliczany po wczytaniu konfiguracji — patrz koniec pliku.
DAILY_LIMIT_USD = sufit_dnia(_dzis_utc())

# SUFIT TORU TESTOWEGO — osobny od produkcyjnego i CELOWO NIE NIESKONCZONY.
#
# Wlasciciel: „nie licz budzetu do testow, to cos osobnego". Zgoda co do
# rozdzialu, ale „nie licz" i „bez granic" to dwie rozne rzeczy. Przebieg
# sprawdzajacy w petli potrafi wydac wiecej niz caly dzien pracy konta — a
# pomylka w skrypcie doraznym jest ZNACZNIE bardziej prawdopodobna niz w
# kodzie, ktory przeszedl testy.
#
# Trzy dolary to okolo dwudziestu pelnych przebiegow szukania ciekawostek albo
# ponad stu rankingow banku. Na dzien pracy nad kodem starczy z zapasem, a
# przy petli bez wyjscia strata konczy sie na kwocie, ktora nie boli.
# Ale gorna granica to nie caly warunek. Trzy dolary bylo kalibrowane do
# NASZEGO sufitu dziennego; operator, ktory ustawi `sufit_dzienny_usd = 1.0`,
# dostawal tor testowy zdolny wydac trzykrotnosc calej swojej produkcji — i
# dowiadywal sie o tym wylacznie z oblanego `test_tor_testowy`, bez slowa
# wyjasnienia. Kwota nizsza z dwoch wygrywa; przeliczenie jest na koncu pliku,
# bo tutaj `konfiguracja.toml` nie jest jeszcze wczytany.
TEST_LIMIT_USD_BAZA = 3.00
TEST_LIMIT_USD = TEST_LIMIT_USD_BAZA
MONTHLY_LIMIT_USD = 40.00

# Sufit na JEDEN przebieg. Działa ZAWSZE, także przy AGENT_V2_NO_LIMIT=1.
# „Bez limitu na budowę" miało znaczyć „nie blokuj eksperymentów", a nie
# „pozwól jednemu przebiegowi kosztować 2 USD". Przebieg 16 kosztował $1,92,
# z czego $1,33 poszło na 31 niepotrzebnych rund wyszukiwania.
# Ponowienia TYLKO bledow przejsciowych (zerwana siec, przekroczony czas, 429,
# 5xx). Bledy trwale — odmowa, zly klucz, przekroczony budzet, uciecie na suficie
# — nie sa ponawiane, bo powtorza sie identycznie i tylko koszruja.
PONOWIENIA = 4
PONOWIENIE_ODSTEP_S = 15

RUN_LIMIT_USD = 1.60

# =============================================================================
# KONTRAKTY — ile czego prosimy. Sufity tokenów liczą się z tych liczb niżej.
# =============================================================================

# --- skaut i różnorodność ----------------------------------------------------
TOPIC_COUNT = 6
DIVERSITY_LOOKBACK = 5

# --- dyskoveria --------------------------------------------------------------
# 10, nie 6. Odsiew przy pobieraniu jest brutalny: martwe adresy (404), blokady
# botów i strony bez treści potrafią zjeść pięć z sześciu źródeł. Przy sześciu
# znalezionych został raz jeden użyteczny dokument i artykuł stanął na nim
# samym. DeepSeek jest tani, więc szukamy szerzej.
DISCOVERY_MAX_RESULTS = 10
# Zmierzone na jednym trudnym temacie:
#   31 rund -> 7 organizacji, 6 pierwotnych, $1,33  (bez limitu, przeciek)
#    6 rund -> 1 organizacja,  0 pierwotnych, $0,53  (za mało, temat nie wyszedł)
# Koszt krańcowy ~$0,09 za rundę, bo każda przesyła całą rozmowę od nowa.
# Przy suficie $1,60 na przebieg dyskoveria może wziąć ~$0,8.
DISCOVERY_MAX_SEARCHES = 8
# Ponizej tylu POBRANYCH zrodel uruchamiamy druga runde dyskoverii, zanim tekst
# pojdzie do pisarza. Prog z danych, nie z przeczucia: artykuly, ktore wyszly
# dobrze, mialy 6-7 pobranych zrodel; ten, ktory wyszedl najcienszy i z jedynym
# faktem bez pokrycia, mial trzy. Czworka lapie tamten przypadek, a nie rusza
# tekstu, ktory wyszedl czysto na czterech zrodlach i zero uwag z bramek.
# Ile znakow preambuly czytamy. Najgestszy dokument z pomiaru mial 519 tys.
# znakow, a uzasadnienie siedzi na poczatku — dalej ida zalaczniki i tabele.
FEDREG_MAX_ZNAKOW = 60_000

MIN_ZRODEL_DO_PISANIA = 4

MIN_PRIMARY_SOURCES = 2  # wymóg właściciela: w korpusie ≥2 dokumenty pierwotne
MIN_WHY_SOURCES = 2  # ≥2 źródła mówiące DLACZEGO, nie tylko treść reguły

# Hosty, które serwują automatom CAPTCHA albo są płatne. Nie omijamy blokad —
# wykrywamy je i nie marnujemy na nie zapytań.
BLOCKED_HOSTS = (
    "federalregister.gov", "regulations.gov", "congress.gov", "ecfr.gov",
    "sciencedirect.com", "tandfonline.com", "academia.edu", "researchgate.net",
)

# --- klasyfikacja ------------------------------------------------------------
CLASSIFY_MAX_INPUT_CHARS = 90_000
CLASSIFY_MAX_EXCERPTS = 12
CLASSIFY_MAX_EXCERPT_CHARS = 700

# --- karta dowodowa ----------------------------------------------------------
CARD_MIN_CONFIRMED = 5
CARD_MAX_CONFIRMED = 8
CARD_MAX_UNCERTAIN = 3
CARD_MAX_CONTRADICTIONS = 3
CARD_MIN_NUMBERS = 3
CARD_MAX_NUMBERS = 8
CARD_MAX_CLAIM_CHARS = 240

# --- długość artykułu --------------------------------------------------------
# Wyprowadzone z dwóch tekstów, które właściciel uznał za dobre:
# ARTYKUL_DRAFT.md = 1048 słów / 62 zdania, ARTYKUL_DRAFT_2.md = 1101 słów / 58 zdań.
# Cel idzie do promptu pisarza. Długość NIE blokuje artykułu — jest notatką,
# bo na starym agencie nie złapała nic, a blokowała.

# Zmierzone na dziewięciu artykułach: przy „cel 1075, zakres 950-1250" model
# kotwiczył się przy górnej granicy (średnia 1212). Sufit obniżony, a prompt
# mówi teraz wprost, że 1075 to cel, nie podłoga.
# DLUGOSC SKALOWANA DO MATERIALU, nie stala.
#
# Bylo `TARGET_WORDS = 1075` przy `MIN_WORDS = 950`, wiec pisarz MUSIAL napisac
# tysiac slow z czegokolwiek dostal. Jeden artykul dostal material na TRZYSTA
# i wypelnil reszte: ten sam mechanizm trzy razy, trzy akapity o tym, czego
# dowody nie mowia, i opowiesc o wlasnym researchu.
#
# Teraz odsiew ocenia, czy temat ma DRUGI AKT, a dlugosc idzie za ta ocena.
# Waski temat nie jest odrzucany — dostaje krotsza forme, i to jest w porzadku.
DLUGOSC_WG_GLEBOKOSCI = {
    # drugi mechanizm albo ta sama rzecz w kilku dziedzinach
    "RICH":   {"cel": 1075, "min": 900, "max": 1250},
    # jeden mechanizm, dobrze udokumentowany
    "SINGLE": {"cel": 650,  "min": 480, "max": 820},
    # USTALENIE NA JEDNO ZDANIE. Prompt odsiewu mowi o THIN wprost: „no article
    # at any length, it belongs in a note". Mimo to wpis tu jest, bo potok nie
    # ma prawa odmowic — artykul powstaje ZAWSZE (decyzja wlasciciela). Gdy
    # THIN jest jedynym, co przeszlo, ma dostac forme najkrotsza z mozliwych.
    #
    # Bez tego wpisu THIN wpadal w galaz domyslna, czyli RICH, i temat
    # o najmniejszej ilosci materialu dostawal 1075 slow do wypelnienia.
    # To jest DOKLADNIE ta usterka, przed ktora cala ta tabela powstala:
    # tekst z materialem na trzysta slow wypelnil tysiac tym samym
    # mechanizmem opisanym trzy razy.
    "THIN":   {"cel": 420,  "min": 300, "max": 560},
}


KOTWICE_DLUGOSCI = {
    # ZDANIE, KTORE PISARZ DOSTAJE TUZ PO CELU DLUGOSCI. Bylo jedno, wspolne
    # dla wszystkich poziomow: „the two articles this publication has approved
    # run past a thousand words". Przy celu 420 slow
    # mowilo wiec pisarzowi, ze teksty przyjete przez to konto sa dwuipolkrotnie
    # dluzsze od tego, co ma napisac — czyli pracowalo PRZECIW jedynemu
    # mechanizmowi skalowania dlugosci, jaki tu zbudowano.
    #
    # BEZ HISTORII PUBLIKACJI, KTOREJ MOZE NIE BYC. Kotwica RICH mowila
    # o „dwoch najdluzszych tekstach, ktore ta publikacja zaakceptowala" —
    # to byl fakt o JEDNYM koncie, podawany kazdemu presetowi jako jego
    # wlasna historia (C3 audytu). Uzasadnienie dlugosci idzie teraz
    # z rodzaju materialu, nie z wymyslonych zatwierdzen.
    "RICH": ("this subject carries a second mechanism, or the same one in more "
             "than one field, and that is what earns the length — a thousand "
             "words spent on two things does not feel long"),
    "SINGLE": ("this subject carries one mechanism, well documented. A piece "
               "runs past a thousand words only when it carries two. Shorter "
               "here is the right size, not a shortfall"),
    "THIN": ("this is the shortest form we publish, and it is the honest one for "
             "a finding this size. A longer text would be the same finding said "
             "again"),
}


def kotwica_dlugosci(glebokosc: str) -> str:
    """Zdanie kalibrujace dlugosc, dobrane do ilosci materialu."""
    return KOTWICE_DLUGOSCI.get((glebokosc or "").upper(), KOTWICE_DLUGOSCI["SINGLE"])


def dlugosc_dla(glebokosc: str) -> dict[str, int]:
    """Ile slow ma miec artykul o tej glebokosci.

    Galaz domyslna to SINGLE, nie RICH. Nieznana glebokosc znaczy „nie wiem,
    ile tu jest materialu" — a na to uczciwa odpowiedzia jest forma srednia,
    nie najdluzsza. Domyslny RICH kazal pisarzowi zapelnic tysiac slow zawsze,
    gdy model oddal cokolwiek spoza slownika.
    """
    return DLUGOSC_WG_GLEBOKOSCI.get(
        (glebokosc or "").upper(), DLUGOSC_WG_GLEBOKOSCI["SINGLE"])


# TU STALY `TARGET_WORDS = 1075`, `MIN_WORDS = 950`, `MAX_WORDS = 1200`.
# Nie czytal ich zaden modul agenta — dlugosc ustala
# `DLUGOSC_WG_GLEBOKOSCI` (wyzej), osobno dla RICH / SINGLE / THIN.
# Byly przy tym ROZBIEZNE z tym, co obowiazuje: 950-1200 wobec
# faktycznych 900-1250 dla RICH.
#
# Usuniete, bo galka niepodlaczona jest gorsza od jej braku: nazywa sie
# dokladnie tak, jak trzeba, wiec operator szukajacy dlugosci artykulu
# znajdzie wlasnie ja. Ten sam blad juz raz kosztowal: log pisal
# „cel 1075, zakres 950-1200" o tekscie, ktory mial dostac 650 slow
# (opisane w JAK_ZBUDOWANY_JEST_BOT.md), wiec poprawny artykul
# wygladal w logu na o polowe za krotki.

# Ile razy w jednym tekscie wolno powiedziec „moim zdaniem" i pochodne.
# Znakowanie wnioskowania jest DOBRE — recenzent wprost go chce, bo dzieki
# niemu smiala interpretacja nie liczy sie jako fakt bez pokrycia. Ale szesc
# takich zwrotow w jednym tekscie to juz tik, nie uczciwosc.
#
# UWAGA NA PULAPKE: sciecie tego licznika NIE MOZE oznaczac, ze pisarz zacznie
# podawac wnioski jako fakty, bo wtedy zamiast tiku dostaniemy zdania bez
# pokrycia — czyli wade powazniejsza. `pisarz.md` mowi wprost, ze wnioskowanie
# znaczy sie STRUKTURA zdania („zapis mowi X; czym to jest, to juz inna
# sprawa"), a nie doklejona formulka.
BUDZET_ZASTRZEZEN = 1

# Od ilu ZNANYCH ISTNIEJACYCH TEKSTOW temat uznajemy za nasycony.
#
# Skaut wymienia, co jego zdaniem juz o danym temacie napisano — i uzywamy jego
# pamieci PRZECIW niemu. „Wszyscy wierza X, a X jest nieprawda" to nie jest
# rzadki wglad, tylko GATUNEK, i kazda dziedzina ma w nim swoj KANON: te
# kilkanascie rzeczy, o ktorych napisano juz tysiac tekstow. Model podaje je
# pierwsze, bo sa najczesciej opisane, czyli najlatwiej dostepne — a DOSTEPNOSC
# JEST ODWROTNOSCIA sygnalu, ktorego szukamy.
#
# Kanon wlasnej dziedziny wpisuje sie w `PRZYKLADY_NISZY["kanon"]`; ten prog
# dziala takze bez niego, bo liczy TEKSTY, a nie tematy z listy.
#
# Prog dwa, nie jeden: jeden przypomniany tekst zdarza sie przy kazdym temacie,
# ktory w ogole istnieje. Dwa znaczy, ze czytelnik juz to czytal.
NASYCENIE_OD_ILU = 2

# ILE UDOKUMENTOWANYCH AWARII ROBI Z TEMATU ARTYKUL.
#
# To jest kryterium, ktorego nie mielismy w ogole, i to przez jego brak
# wychodzily tematy wielkosci notki. Sama procedura to notka: „gdy maszyna do
# glosowania padnie, komisja wydaje karty tymczasowe" jest kompletna odpowiedzia
# w jednym zdaniu, a rozbicie jej na podpunkty daje rozdmuchana notke.
#
# Artykul niesie procedura, ktora POWSTALA, BO COS POSZLO NIE TAK — i to
# wielokrotnie. Regula zamykania konklawe wziela sie z trzyletniego wakatu
# zakonczonego dopiero wtedy, gdy mieszkancy zdjeli dach i obcieli kardynalom
# jedzenie. Bezpieczniki wstrzymujace notowania istnieja z powodu jednego dnia
# 1987 roku. Lancuch sukcesji glowy panstwa ma za soba zamach z 1963 i poprawke
# z 1967. Taki regulamin czyta sie jak blizny, a kazda blizna to scena z ludzmi.
#
# Dwa, nie jeden: jedna awaria to anegdota, dwie to juz wzorzec, ktory da sie
# pokazac.
PRECEDENSOW_NA_ARTYKUL = 2

# Co ile dni ma powstawac kopia listy subskrybentow, zanim alarm zacznie o niej
# przypominac. Eksportu NIE DA SIE zautomatyzowac — endpoint nie istnieje,
# a sondowanie nieudokumentowanych adresow to scraping wedlug regulaminu
# Substacka. Skoro krok jest reczny, ktos musi o nim przypominac, inaczej nie
# zdarzy sie nigdy. I nie zdarzyl sie: katalog `kopie/` nie istnial na produkcji
# ani jednego dnia, mimo ze skrypt do tego byl napisany.
KOPIA_SUBSKRYBENTOW_CO_ILE_DNI = 14

# KOGO WIAZE WYNIK. Drugie brakujace kryterium i drugi powod, dla ktorego
# tematy wychodzily mialkie. Zepsuta maszyna do glosowania to piecset glosow
# w jednym lokalu; zastrzelony prezydent zatrzymuje caly kraj w tej samej
# sekundzie. Oba maja spisana procedure, oba da sie sobie wyobrazic — rozni je
# wylacznie zasieg skutku.
#
# Na artykul potrzeba OBU rzeczy naraz: historii awarii i zasiegu. Sama
# historia bez stawki to ciekawostka, sama stawka bez historii to procedura.
ZASIEGI_ARTYKULOWE = ("AN_INDUSTRY", "A_COUNTRY")

# Ile ostatnich artykulow porownuje bramka ODCISK_FORMY.
ILE_TEKSTOW_DO_POROWNANIA_FORMY = 4

# Ile slow moze przypadac na jedno NOWE twierdzenie. Beat to zdanie, po ktorym
# czytelnik wierzy w cos innego niz zdanie wczesniej; powtorzenie tej samej
# tezy z nowym dowodem beatem NIE JEST.
#
# Tamten artykul mial szesc beatow na 1097 slow, czyli jeden co 183 — i cztery
# pierwsze akapity byly jednym beatem rozpisanym na cztery. To jest wlasciwa
# miara rozdmuchania, znacznie lepsza niz sama liczba slow: mierzy wade
# bezposrednio, zamiast zgadywac ja z dlugosci.
SLOW_NA_BEAT = 150

# Artykuł powstaje po angielsku — konto jest anglojęzyczne.
ARTICLE_LANGUAGE = "English"

# =============================================================================
# SUFITY TOKENÓW — wyliczane z kontraktów powyżej
# =============================================================================

# Zachowawczo, żeby sufit był raczej za duży niż za mały. Zmierzone na starym
# agencie: CJK 2,19x, cyrylica 1,41x; dla angielskiego 3,5 znaku na token
# z zapasem.
CHARS_PER_TOKEN = 3.5

# Ile tokenów zajmuje rusztowanie JSON-a, klucze i pola opisowe poza samą treścią.
JSON_OVERHEAD_TOKENS = 1200


# Myślenie na Opusie 5 jest domyślnie włączone, liczy się jak tokeny wyjściowe
# i NIE jest częścią kontraktu — więc sufit wyliczony z samego kontraktu potrafi
# uciąć odpowiedź w połowie mimo poprawnej arytmetyki.
# 16 tys., bo modele DeepSeek v4 rozumują znacznie obficiej niż Claude i przy
# 6 tys. ucinało syntezę. Sufit nic nie kosztuje, dopóki nie zostanie zużyty —
# płacimy za tokeny, nie za limit.
# 28 tys., nie 16. Zmierzone na realnych przebiegach: DeepSeek-pro rozumuje
# 16-19 tys. tokenow przy zadaniach WIELOELEMENTOWYCH (szesc tematow, szesc
# ocen, szesc celow) niezaleznie od objetosci samej tresci. Przy zapasie
# rownym 16 tys. margines wynosil 1,15-1,21x, czyli zaden — i trzy etapy
# stalyby sie bomba z opoznionym zaplonem. Odsiew ucialo dwa razy pod rzad.
# Sufit nic nie kosztuje, dopoki nie zostanie zuzyty: placimy za tokeny,
# nie za limit.
THINKING_HEADROOM_TOKENS = 28000

# Głębokość myślenia. Jawnie, bo domyślne `high` na Opusie 5 potrafi podwoić
# rachunek za wyjście bez pytania.
#
# TO JEST POKRETLO WYLACZNIE DLA MODELI CLAUDE i tak ma zostac. Sprawdzone na
# trzydziestu dniach produkcji: z szesciu wpisow ponizej dociera do API DOKLADNIE
# JEDEN — `write`, bo tylko on chodzi na Claude. `scout`, `discovery`,
# `synthesis` i `review` chodza na DeepSeeku, a `forma` nie wywolala sie ani
# razu (dodana po ostatnim artykule).
#
# DeepSeek ma wlasne pokretlo, DEEPSEEK_EFFORT="low", i jest ono JEDNO dla
# wszystkich etapow z twardego powodu: tokeny rozumowania licza sie do
# max_output_tokens, wiec "high" potrafi zjesc caly budzet i nie zostawic
# miejsca na odpowiedz (bylo: 11 wyszukiwan, status completed, zero tekstu).
# Przepiecie tych wpisow na DeepSeeka odtworzyloby dokladnie te awarie.
#
# Wpisy dla etapow deepseekowych ZOSTAJA, bo wyrazaja intencje na wypadek
# przepiecia etapu na Claude. Zeby jednak nie byly cicha ozdoba, `llm.call`
# mowi RAZ NA PROCES, ktory wpis nie zadzialal i dlaczego.
EFFORT = {
    "scout": "medium",
    "discovery": "medium",
    "synthesis": "high",
    "write": "high",
    "review": "high",
    "forma": "high",
}


def _tokens_for(chars: int) -> int:
    return int(chars / CHARS_PER_TOKEN) + JSON_OVERHEAD_TOKENS


MAX_TOKENS = {
    # 6 tematow: tytul, pytanie, ZLAMANE PRZEKONANIE, skad sie bierze, oceny
    "scout": _tokens_for(TOPIC_COUNT * 1400),
    # Jedna ocena na temat, kazda z uzasadnieniem. PODNIESIONE z 500 na 1100
    # znakow po realnym przebiegu: odkad temat niesie `broken_belief`
    # i `why_they_believe_it`, odsiew ma wiecej do przeczytania i wiecej do
    # powiedzenia, i ucielo mu odpowiedz w polowie JSON-a. Sufit nic nie
    # kosztuje, dopoki nie zostanie zuzyty — placimy za tokeny, nie za limit.
    "feasibility": _tokens_for(TOPIC_COUNT * 1100),
    # Dyskoveria dostaje budżet z zapasem, bo DeepSeek liczy do niego tokeny
    # rozumowania KAŻDEJ rundy wyszukiwania. Przy ciasnym budżecie kończył
    # szukanie i nigdy nie tworzył bloku `message`: 26 wyszukiwań, status
    # "completed", zero tekstu.
    "discovery": 32000,
    # Bibliotekarz oddaje grupy, nie eseje: mechanizm, czlonkowie,
    # czego brakuje. Sufit z zapasem, bo DeepSeek rozumuje obficie.
    "bibliotekarz": 12000,
    # Cztery obserwacje z cytatami plus dwa zdania. Nie esej.
    "warto_pisac": 6000,
    # Jedno zdanie do 40 slow plus uzasadnienie decyzji. Malo tekstu,
    # ale DeepSeek i tak rozumuje obficie — zapas zalatwia THINKING_HEADROOM.
    "restack": 3000,
    # Kilku kandydatow po cztery krotkie pola. Nie esej.
    "fedreg": 8000,
    # DOKŁADNIE tyle, ile prosi prompt: 12 fragmentów po 700 znaków plus liczby
    "classify": _tokens_for(
        CLASSIFY_MAX_EXCERPTS * CLASSIFY_MAX_EXCERPT_CHARS + 2000
    ),
    # karta: twierdzenia z cytatami, liczby, sprzeczności, granice
    "synthesis": _tokens_for(
        CARD_MAX_CONFIRMED * (CARD_MAX_CLAIM_CHARS + CLASSIFY_MAX_EXCERPT_CHARS)
        + CARD_MAX_NUMBERS * 200
        + 4000
    ),
    # ARTYKUL PLUS ZAPAS NA MYSLENIE — z NAJDLUZSZEJ formy, jaka potok
    # potrafi zamowic. Stalo tu `MAX_WORDS * 7`, czyli druga kopia dlugosci
    # artykulu, i ta kopia zdazyla sie rozjechac: 1200 wobec 1250 dla RICH.
    # Sufit byl liczony na tekst o 50 slow krotszy niz najdluzszy mozliwy.
    # Dwie kopie jednej liczby zawsze sie rozjezdzaja — liczymy ze zrodla.
    "write": _tokens_for(
        max(d["max"] for d in DLUGOSC_WG_GLEBOKOSCI.values()) * 7) + 6000,
    # Recenzja rozlicza KAŻDE zdanie i jest najdroższa w tokenach wyjścia:
    # DeepSeek dawał tu 19-22 tys. tokenów, a przy 28 764 ucięło go na żywo
    # i straciliśmy główny sygnał jakości. Sufit nic nie kosztuje, dopóki nie
    # zostanie zużyty.
    "review": 48000,
    "forma": 24000,
    "note": _tokens_for(400) + 8000,
    "note_tani": _tokens_for(400) + 8000,   # ten sam kontrakt, inny pisarz
    "comment": _tokens_for(600) + 8000,
    "reply": _tokens_for(600) + 8000,
    "bank": 24000,
    "factcheck": 24000,
    # Naprawa oddaje caly tekst od nowa plus jedna linie uzasadnienia — czyli
    # tyle samo co oryginal. Sufit jak przy `note`/`comment`, bo to jest to
    # samo zadanie pisarskie, tylko z narzuconym materialem.
    "naprawa": _tokens_for(400) + 8000,
    "naprawa_komentarza": _tokens_for(600) + 8000,
    # Pytanie o stan modeli wraca lista kilkunastu pozycji z datami —
    # krotka odpowiedz, ale wyszukiwanie dokłada do wyjscia swoje rundy.
    "aktualne_modele": 16000,
    "curiosity": 24000,
    "grafika": 4000,
    "cele": 6000,
    "wybor": 6000,
}

# --- notki i komentarze ------------------------------------------------------
# Zmierzone na publicznych analizach Substacka: 33-64 słowa dają najwyższe
# zaangażowanie (449 średnich reakcji), 65-256 słów wyraźnie spada. Środek jest
# najgorszy, a to właśnie tam ląduje instynkt "napiszę akapit".
NOTE_MIN_WORDS = 33
NOTE_MAX_WORDS = 64

# DLUGOSC WG TYPU NOTKI — zeby piec notek na dobe nie bylo piecioma notkami
# tej samej dlugosci.
#
# Reguła „nie pisz wszystkiego tej samej długości, jednakowość sama w sobie
# jest sygnałem" stała w `komentarz.md` i `odpowiedz.md`, a NOTEK NIE
# OBEJMOWAŁA. Skutek: pięć notek dziennie lądowało w paśmie 31 słów, co jest
# wzorem widocznym gołym okiem u kogoś, kto czyta konto codziennie.
#
# NIE PODNOSIMY SUFITU. Te 64 słowa są zmierzone: 65-256 słów wyraźnie spada.
# Zmienia się to, że pasmo jest teraz UŻYWANE NA CAŁEJ SZEROKOŚCI, a nie
# w okolicach środka.
#
# Podział idzie za tym, czym typ notki jest, a nie za losowaniem:
# sprostowanie jest z natury krótkie i ostre, myśl może oddychać.
# Każdy przedział MUSI mieścić się w [NOTE_MIN_WORDS, NOTE_MAX_WORDS] —
# pilnuje tego `test_dlugosc_notek.py`, bo bramka sprawdza pasmo globalne.
DLUGOSC_NOTKI_WG_TYPU = {
    "SPROSTOWANIE": (33, 42),   # najkrótsza: jedna rzecz do poprawienia
    "CIEKAWOSTKA":  (36, 50),   # koń roboczy, środek pasma
    "DYSKUSJA":     (44, 58),   # ma otworzyć rozmowę, potrzebuje zaczepienia
    "MYSL":         (50, 64),   # ta, której wolno się rozwinąć
}


def dlugosc_notki(typ: str) -> tuple[int, int]:
    """Przedział słów dla tego typu notki. Nieznany typ dostaje całe pasmo."""
    od, do = DLUGOSC_NOTKI_WG_TYPU.get(
        str(typ).upper(), (NOTE_MIN_WORDS, NOTE_MAX_WORDS))
    # Przyciecie do pasma globalnego, zeby przestawienie sufitu w konfiguracji
    # nie wypuscilo notki poza to, czego pilnuje bramka.
    return (max(NOTE_MIN_WORDS, od), min(NOTE_MAX_WORDS, do))

# Ilu kandydatow generujemy. Dawniej bylo pieciu, potem trzech; dodatkowe
# warianty tego samego zdania niczego nie dokladaly, a placilismy za nie i ich
# weryfikacje. Dzis notke pisze Opus, a kandydat jest jeden.
# JEDEN WARIANT, NIE TRZY. Trzy istnialy tylko po to, zeby po napisaniu wybrac
# ten, ktory nie powtarza pierwszego slowa poprzednich notek — czyli placilismy
# za dwa wyrzucone teksty, zeby zalatwic cos, o czym wystarczylo modelowi
# POWIEDZIEC. Od kiedy dostaje liste ostatnich otwarc w prompcie, konkurencja
# jest zbedna.
#
# To jest najwieksza pojedyncza oszczednosc w calym systemie: przy pieciu
# notkach dziennie roznica wynosi 28 dolarow miesiecznie — wiecej niz kosztuje
# cala reszta agenta razem wzieta.
#
# Zostawiamy pokretlo: gdyby jakosc spadla, wystarczy wrocic do 2 albo 3.
NOTE_CANDIDATES = 1
# Ile ciekawostek szukamy naraz. Cztery z pięciu notek dziennie stoją na nich,
# a jedno szukanie kosztuje tyle co jedno — więc bierzemy zapas na kilka dni.
# DZIEDZINY, Z KTORYCH BIORA SIE TEMATY NOTEK.
#
# Historia tej listy w dwoch krokach.
#
# KROK PIERWSZY: prompt mial na sztywno piec obszarow, wpisanych w jego tresc.
# Lista zuzytych faktow blokowala powtorzenie konkretu, ale nie blokowala
# krazenia po tym samym terytorium — i widac to w dwunastu pierwszych notkach,
# ktore trzymaly sie jednego rodzaju przedmiotow i jednego kraju. Komentarze
# rotowaly osiemnascie hasel od poczatku; notki nie rotowaly nic. Stad rotacja
# i druga os (GENERATORY).
#
# KROK DRUGI: cala lista zostala wymieniona przy zmianie tematu konta. Rotacja
# i generatory przetrwaly bez jednej poprawki, bo problem, ktory rozwiazywaly,
# jest ten sam w kazdej dziedzinie: bez drugiej osi model wraca tam, gdzie mu
# najlatwiej.
#
# TO, ZE GENERATORY PRZEZYLY ZMIANE NISZY, JEST ICH TESTEM. Sa neutralne wobec
# tematu z konstrukcji: MEASUREMENT pyta o liczbe, MIRROR o dwie jurysdykcje
# z przeciwnymi zasadami, DECIDER o czlowieka, ktory cos wybral i ma date.
# Kazde z tych pytan ma odpowiedz w dowolnej dziedzinie.
#
# DWA OSTATNIE — SEEMING i UNBIDDEN — dopisano pozniej i przez chwile NIE BYLY
# neutralne: mowily o „zachowaniu, ktore wyglada na myslenie" i o „systemie,
# ktory robi cos niezaprojektowanego", czyli o jednej konkretnej dziedzinie.
# Ksztalt pytania byl dobry, przyklady nie — dzis pytaja o to samo bez nazywania
# dziedziny. Powod ich istnienia zostaje: dwanascie starych pyta o liczbe,
# jurysdykcje, decydenta i awarie, a zadne o to, jak rzecz sie ZACHOWUJE.
# SIATKA DZIEDZIN NALEZY DO PRESETU (`temat.dziedziny`). Razem z `GENERATORY`
# wyznacza przestrzen, w ktorej szuka sie ciekawostek: kazda pozycja to nie
# slowo-klucz, a OPIS MIEJSCA, w ktorym cos ciekawego siedzi. Wymog
# strukturalny — co najmniej 10 komorek siatki na notke na dobe — sprawdza
# `preset.sprawdz`. Silnik nie ma dziedzin, bo nie ma tematu.
DZIEDZINY_CIEKAWOSTEK: tuple[str, ...] = ()
ILE_DZIEDZIN_NA_PRZEBIEG = 5

CURIOSITY_BATCH = 8
# Ile ostatnio zuzytych faktow pokazujemy szukajacemu jako zakaz powtorki.
# Bez tego to samo szukanie codziennie oddaje te same slynne osiem.
CURIOSITY_MEMORY = 60

# Ile OSTATNICH WYSTAWIONYCH NOTEK bot pamieta, wybierajac material na dzis.
# `None` = WSZYSTKIE, jakie kiedykolwiek wyszly. To jest stan obowiazujacy.
#
# Rozne od `CURIOSITY_MEMORY`, ktore pamieta zuzyte FAKTY po dokladnym odcisku.
# Ten sam fakt powiedziany innymi slowami daje inny odcisk i przechodzil — tak
# poszly dwie notki o TYM SAMYM, 23 i 24 sierpnia.
#
# BYLO 12, czyli okolo czterech dni. Wlasciciel chce zera powtorzen NIGDY, wiec
# okno znika. Bez tego powtorka sprzed pieciu dni przechodzila z automatu:
# ochrona konczyla sie nie o polnocy, tylko o dwunastej notce.
#
# Czy to kosztuje falszywe alarmy — ZMIERZONE 2026-08-25 na 29 wystawionych
# notkach (`stages.pamiec_wystawionych` niesie caly rachunek):
#     okno 8, 12, 20, 40 oraz PAMIEC PELNA  ->  5 blokad, te same piec.
# Zero roznicy. Wszystkie 5 to PRAWDZIWE powtorki — trzy pary o jednym temacie,
# trzy o drugim i dwie o trzecim — zero falszywych. Z 399 par o ROZNYCH tematach
# prog miedzy dniami nie przepuscil ani jednej.
#
# Ta stala zostaje jako JEDYNA dzwignia odwrotu: wpisanie tu liczby wraca do
# okna, bez ruszania kodu. Tak samo jak `FOLLOW_MIESIECZNIE` przy obserwacjach
# — wylaczenie ma byc jedna stala, a nie wypruciem bloku.
#
# TA DZWIGNIA ZDALA EGZAMIN W OBIE STRONY. Obserwacje byly wylaczone od
# 23 sierpnia do 1 wrzesnia 2026 i wlaczenie ich z powrotem kosztowalo jedna
# liczbe — blok czekal nietkniety. Ale dzwignia ma tez druga strone, ktora
# wtedy zawiodla: dopoki zero stalo w konfiguracji Z WYJASNIENIEM, nie bylo
# jak zauwazyc, ze wyjasnienie jest falszywe. Wylaczenie na jedna stala jest
# tanie w odwrocie i drogie w rewizji.
PAMIEC_NOTEK = None

# ILE DNI MOZE MIEC ZRODLO FAKTU, KTORY TWIERDZI COS O STANIE TERAZ.
#
# Wlasciciel ustawil to sam, dwa razy. Najpierw ogolnie: „cos, co mialo sens w
# styczniu 2026, w maju juz moze byc nieaktualne" — cztery miesiace. Potem, po
# zlapaniu tamtej notki, konkretnie: dane maja byc „max 2-3 miesiace do tylu".
#
# Stad 90 dni, a nie 180, ktore wpisalem najpierw. To jest decyzja wlasciciela
# o tym, jak swieze ma byc konto, nie wynik pomiaru — i tak jest zapisana.
#
# Zlapane na zywym tekscie: notka o szczegole technicznym produktu, ktory
# w miedzyczasie wycofano, napisana 25 sierpnia 2026 na podstawie artykulu
# o jego premierze sprzed dwoch lat. Okolo 700 dni. Sprawdzanie faktow ja
# przepuscilo, bo fakt byl PRAWDZIWY — tylko juz nieaktualny.
MAKS_WIEK_ZRODLA_DNI = 90

# Slowa, po ktorych poznajemy, ze zdanie twierdzi cos o STANIE SWIATA TERAZ,
# a nie opowiada o zdarzeniu z wlasna data. Tylko takie zdania podlegaja
# progowi wieku — wyrok sadu z 2023 roku jest dobry i bedzie dobry dalej.
TWIERDZI_O_TERAZ = (
    "now", "currently", "today", "these days", "at present",
    "newest", "latest", "the first", "the only", "the fastest", "the best",
    "state of the art", "state-of-the-art", "cutting edge", "leading",
    "costs", "cost is", "is priced", "price is", "charges", "sells for",
    "is available", "you can now", "offers", "supports", "recommends",
    "no longer", "has become", "is the standard", "generate", "generates",
)

# Slowa, ktore mowia, ze rzecz jest W TRAKCIE ZNIKANIA. Publikacja o szybko
# zmieniajacej sie dziedzinie nie ma
# po co opisywac czegos, co za osiem tygodni przestanie istniec — a dokladnie
# to sie stalo z tamta rodzina modeli.
ZNIKA = (
    "deprecat", "retired", "retirement", "sunset", "end of life",
    "end-of-life", "will be removed", "shutting down", "discontinued",
    "no longer available", "legacy model", "being phased out",
)

# NAZWA PRODUKTU Z NUMEREM WERSJI. Wlasciciel: „nie ma mi pisac o GPT 5.0, jak
# jest juz 5.5". Zdanie, ktore nazywa konkretna wersje, starzeje sie razem z
# nia — nawet gdy sam fakt pozostaje prawdziwy. Dlatego nazwanie wersji samo w
# sobie wlacza prog wieku.
#
# Wzorzec celuje w rodziny, ktore realnie numeruja wydania. Nie probuje byc
# pelna lista modeli swiata — taka lista przeterminowala by sie szybciej niz
# material, ktory ma pilnowac.
WZORZEC_WERSJI = (
    # LITERA PO CYFRZE. Wzorzec konczyl sie na `[0-9]+(\.[0-9]+)?\b`, wiec
    # "GPT-5" lapal, a "GPT-4o" NIE — po czworce idzie "o", czyli znak slowa,
    # i granica `\b` nie pasowala. Zmierzone przez audyt: dziura obejmowala
    # cala rodzine 4o, w tym "GPT-4o mini". Dodane `[a-z]?` zamyka ja, nie
    # psujac dopasowania do "5" ani do "4.5".
    # DWIE DZIURY DOMKNIETE PO POMIARZE na 19 realnych nazwach:
    #   `v` przed cyfra — "DeepSeek-V4" nie pasowal,
    #   slowo poziomu miedzy marka a numerem — "Mistral Medium 3.5" nie pasowal.
    # Lista poziomow jest ZAMKNIETA celowo: dowolne slowo daloby falszywki
    # w rodzaju "gemini is a constellation 3 stars away".
    r"\b(gpt|claude|gemini|llama|mistral|qwen|grok|deepseek|phi|command|"
    r"mythos|fable)"
    r"(\s+(medium|large|small|mini|pro|max|ultra|flash|lite|turbo|instant|"
    r"thinking|sonnet|opus|haiku))?"
    r"[\s\-]?v?[0-9]+(\.[0-9]+)?[a-z]?\b"
    r"|\bo[0-9]+(\s*-?\s*(mini|pro|preview))?\b"
    r"|\b(sonnet|opus|haiku|turbo|flash|lite)[\s\-]?v?[0-9]+(\.[0-9]+)?[a-z]?\b"
)
# SUFIT PROB, NIE LICZBA WYWOLAN. Do 5 wrzesnia 2026 ta stala znaczyla "napisz
# tylu kandydatow", i tyle wywolan szlo za kazdym razem — takze wtedy, gdy
# pierwszy przechodzil. Zmierzone na przebiegu z 3 wrzesnia 2026: szesc wywolan
# `comment` na dwa wystawione komentarze, 14 448 zetonow wyjscia wyrzuconych.
#
# Teraz oba miejsca (`comment_on`, `reply_to`) siegaja po kolejnego dopiero
# wtedy, gdy poprzedni odpadl: na bramce, na powtorzonym otwarciu albo na
# milczeniu. Polisa zostaje w calosci, placi sie za nia tylko wtedy, gdy byla
# potrzebna. Podniesienie tej liczby nie podnosi wiec kosztu dnia — podnosi
# tylko wytrwalosc w zlych dniach.
COMMENT_CANDIDATES = 3

# DLUGOSC KOMENTARZA I ODPOWIEDZI losowana osobno za kazdym razem.
# Sam prompt tego nie zalatwi: proszony o roznorodnosc model i tak osiada
# w waskim pasie (zmierzone: 40-65 slow przy prosbie o zmiennosc). Rozklad
# przechyla sie w strone KROTKICH, bo research o rozpoznawaniu botow wskazal
# jednolita dlugosc jako jeden z najmocniejszych tropow, a ludzie czesto
# odpowiadaja jednym zdaniem.
#
# (docelowa liczba slow, waga)
DLUGOSCI_WYPOWIEDZI = (
    (12, 3),    # jedno zdanie, najczestsze u ludzi
    (25, 3),
    (45, 2),
    (70, 1),    # dluzsze tylko wtedy, gdy mysl tego wymaga
)


# SPOSOB OTWARCIA, losowany tak samo jak dlugosc i z tego samego powodu.
# Zmierzone na naszych wlasnych komentarzach: SIEDEM Z DZIEWIECIU zaczynalo sie
# od "The". Model proszony o roznorodnosc i tak wpada w jeden szkielet, wiec
# wybor musi zapasc poza nim.
# PROFIL OSOBOWOSCI KOMENTUJACEGO — z wagami, bo czlowiek ma ROZKLAD reakcji,
# nie jedna.
#
# Zmierzone na dwudziestu siedmiu komentarzach: prompt oferowal cztery rozne
# ruchy i mowil „wybierz jeden", a model niemal zawsze wybieral ten sam
# i wyrazal go ta sama formula — „przyznaje ci racje, ale pominales X". Trzy
# komentarze slowo w slowo tym schematem. Pojedynczo trafne, w serii brzmi jak
# jedna osoba z jednym odruchem: wieczny korygujacy.
#
# Wlasciciel ustawil to celnie: WIECZNY KORYGUJACY i POTAKIWACZ to ta sama wada
# z dwoch stron. Obaj maja gotowa reakcje, zanim przeczytali tekst. Oba maja byc
# RZADKIE.
#
# Wagi, nie rownomierna rotacja — inaczej „rzadkie" nie byloby rzadkie.
#
# Jedyny komentarz, ktory dostal odpowiedz (1 z 27), zaczynal sie od „What
# surprised me is" — ciekawosc, nie korekta. Stad ona jest najciezsza.
POSTAWY_KOMENTARZA = {
    "CIEKAWOSC": (7, (
        "Say what genuinely caught you in the piece and what it opens up. You "
        "are not correcting anything and not claiming to know better — you "
        "noticed a thread the author left loose and you are pulling it. This is "
        "the house register: interested, specific, no verdict."
    )),
    "MECHANIZM": (6, (
        "Name the incentive, constraint or decision the post describes but does "
        "not state. The post says what happens; you say what makes it happen. "
        "This is the publication's speciality and it stands on its own — it is "
        "not a correction and must not be phrased as one."
    )),
    "KONKRET": (5, (
        "Bring one specific the author would actually want: a figure, a date, a "
        "document, a case, a precedent. Give it and stop. No framing, no lesson "
        "drawn, no telling them what it means for their argument."
    )),
    "ROZSZERZENIE": (4, (
        "Take the same mechanism somewhere the author did not go — another "
        "industry, another country, another era. The pleasure here is the "
        "unexpected match, so make the connection precise or do not make it."
    )),
    # WAGA PODNIESIONA Z 3 NA 6, 30 sierpnia 2026. Wlasciciel zapytal, czy
    # komentarze zachecaja do dyskusji. Zmierzone na 81 wystawionych: pytanie
    # zawiera 10 procent — i to nie byl dryf, tylko dokladnie ta waga (3/29).
    # System robil to, co mu kazano; kazano mu za malo.
    #
    # Szesc, nie dziesiec: komentarz konczacy sie pytaniem ZA KAZDYM RAZEM to
    # osobny podpis bota, a postawy CIEKAWOSC i ROZSZERZENIE i tak otwieraja
    # watek bez znaku zapytania. Przy szostce pyta wprost mniej wiecej co piaty.
    "PYTANIE": (6, (
        "Ask one question you actually want answered, about something the piece "
        "genuinely leaves open. Not rhetorical, not a test, not a question whose "
        "answer you are about to supply. If you would not read the reply with "
        "interest, this is not your move."
    )),
    "SPRZECIW": (2, (
        "Disagree with ONE named claim and say exactly why, carrying something "
        "concrete: a figure, a case, a counterexample. Aim at the claim, never "
        "at the author, and state it once without hedging it into mush. Rare on "
        "purpose: an account that objects to everything is as tiresome as one "
        "that agrees with everything."
    )),
    "KOREKTA": (1, (
        "The 'you got X right, but you skipped Y' move. Used by default it "
        "becomes a tic, the same shape under every post. It is allowed here, "
        "once in a while, when the omission genuinely changes the conclusion. "
        "Not when it merely lets you look thorough."
    )),
    "ZGODA_Z_DOPOWIEDZENIEM": (1, (
        "Agree — and earn it by adding exactly one thing the author did not "
        "say. Bare agreement is banned: 'good point', 'exactly this', 'I "
        "completely agree' add nothing to a conversation and mark an account as "
        "empty. If you have nothing to add, the correct move is silence, not "
        "applause."
    )),
}


def losowa_postawa() -> tuple[str, str]:
    """Ktora postawa dla TEGO komentarza. Wagi, nie rownomiernie."""
    import random

    nazwy = list(POSTAWY_KOMENTARZA)
    wagi = [POSTAWY_KOMENTARZA[n][0] for n in nazwy]
    wybrana = random.choices(nazwy, weights=wagi, k=1)[0]
    return wybrana, POSTAWY_KOMENTARZA[wybrana][1]


OTWARCIA = (
    "Start with the mechanism itself, no preamble.",
    "Start with a question you actually want answered.",
    "Start by naming what the piece got right, then the part it skipped.",
    "Start with a concrete example or case, and let it carry the point.",
    "Start with the objection: say plainly where you part company.",
    "Start with a number or a date that changes how the thing reads.",
    "Start mid-sentence, as if continuing a thought already in progress.",
    "Start with what surprised you, in the plainest words available.",
)


# OTWARCIA, KTORYCH DANA POSTAWA NIE MOZE WYKONAC.
#
# Postawa i otwarcie byly losowane NIEZALEZNIE, wiec komentarz potrafil dostac
# w jednym prompcie polecenie „nie korygujesz" i „zacznij od sprzeciwu".
# Zmierzone na wagach z tego pliku: cztery takie pary to 8,2% komentarzy.
#
# Gorsza jest jednak druga rzecz, ktora to samo losowanie robilo po cichu.
# Otwarcie „Start by naming what the piece got right, then the part it
# skipped" JEST ruchem KOREKTA — a KOREKTA ma wage 1, najnizsza w calej
# tabeli, i jej wlasny opis mowi dlaczego: „Used by default it becomes a tic".
# Waga dawala temu ruchowi 3,1% komentarzy, a otwarcie zamawialo go w 12,5%.
# Cztery razy czesciej, tylnymi drzwiami, omijajac wage, ktora istnieje
# wylacznie po to, zeby ten ruch byl rzadki.
#
# Nie zabieramy otwarcia nikomu, kto moze je wykonac: sprzeciw zostaje dla
# postaw, ktore sie nie zgadzaja, a ruch korekty dla tej, ktora go nazywa.
OTWARCIE_SPRZECIWU = "Start with the objection: say plainly where you part company."
OTWARCIE_KOREKTY = "Start by naming what the piece got right, then the part it skipped."

# Kto MOZE dostac dane otwarcie. Postawy spoza listy go nie dostaja.
OTWARCIA_TYLKO_DLA = {
    OTWARCIE_SPRZECIWU: frozenset({"SPRZECIW", "KOREKTA"}),
    OTWARCIE_KOREKTY: frozenset({"KOREKTA", "SPRZECIW"}),
}


def otwarcia_dla_postawy(postawa: str) -> tuple[str, ...]:
    """Otwarcia, ktore ta postawa ma jak wykonac."""
    p = (postawa or "").upper()
    wolno = tuple(o for o in OTWARCIA
                  if p in OTWARCIA_TYLKO_DLA.get(o, frozenset({p})))
    # Pusta lista znaczylaby, ze postawa nie ma ZADNEGO otwarcia — to bylby
    # blad w tablicy powyzej, a nie stan, w ktorym wolno milczkiem isc dalej.
    return wolno or OTWARCIA


def losowe_otwarcie(postawa: str = "") -> str:
    import random

    return random.choice(otwarcia_dla_postawy(postawa))


def losowa_dlugosc() -> int:
    """Ile slow ma miec ta konkretna wypowiedz."""
    import random

    dlugosci, wagi = zip(*DLUGOSCI_WYPOWIEDZI)
    return random.choices(dlugosci, weights=wagi, k=1)[0]

# Sufit dzienny. Research mówi, że trzy przemyślane komentarze tygodniowo biją
# piętnaście uprzejmych; pierwotne 15-20 dziennie było z planu sprzed danych.
# USUNIETE 2026-08-20: NOTES_PER_DAY = 5 bylo martwym duplikatem. Liczbe notek
# na dzien wyznacza dlugosc NOTE_MIX_OTHER_DAY i tylko ona. Stala kusila do
# zmiany, ktora nie zrobilaby nic.
COMMENTS_PER_DAY = 4

# Typy notek. W dniu publikacji artykułu lecą notki typu ARTYKUL z linkiem;
# w pozostałe dni — pozostałe typy, oparte na fragmentach, których artykuły
# nie zużyły. Zmierzone: konwertują notki konkretne i taktyczne, a nie
# motywacyjne; komentarze i restacki niosą dalej niż polubienia, więc notka
# dająca się z czymś nie zgodzić bije notkę, pod którą wszyscy kiwają głową.
# FORMA NOTKI — osobny wymiar od TYPU. Typ mowi, CO powiedziec; forma mowi, JAK
# to ma wygladac na ekranie.
#
# Zmierzone na wlasnych dwunastu notkach: dlugosc mamy idealna (12/12 w oknie
# 31-60 slow, zero pytajnikow), ale DZIESIEC z dwunastu to jeden zbity akapit,
# a cztery zaczynaja sie od slowa „The". Kazda notka ma ten sam ksztalt:
# rzecz, potem zaskakujacy fakt, potem przepis. Rozne tematy, jedna sylwetka —
# i wlasnie to widac w kanale jako monotonie.
#
# Zewnetrzne analizy (2,7 mln i 9,6 tys. notek) zgadzaja sie co do dwoch rzeczy:
# tekst ma byc SKANOWALNY, z lamaniem linii i zmienna dlugoscia zdan, a trzy
# kolejne linie zaczynajace sie tak samo (anafora) daja ponad trzykrotnie lepsza
# konwersje. Zadnej z tych rzeczy nie robilismy.
NOTE_FORMS = {
    "PROSTA": (
        "One tight paragraph. No line breaks. This is the default shape and it "
        "works — but it cannot be every note, so use it plainly and well."
    ),
    "KONTRAST": (
        "Two facts set against each other, on separate lines, with a blank line "
        "between them. Same object, opposite rules. Then one short line that "
        "names what the difference actually is. Three blocks, no more."
    ),
    "LISTA": (
        "Three consecutive short lines that begin with the same word, then one "
        "closing line that lands the point. The repetition builds a visual "
        "pattern that stops a thumb. Keep each line under ten words. "
        "EVERY line must carry a fact the previous line did not. Three lines "
        "that restate one idea to satisfy the pattern are worse than no pattern "
        "at all: the reader gets the shape of an argument with nothing inside "
        "it. If you only have one fact, this is not the form for it."
    ),
    "LICZBA": (
        "Open with the number itself, alone on the first line — a quantity, a "
        "duration, a price, a count. Blank line. Then what it is and who "
        "decided it. "
        "The number does the stopping; the rest does the explaining. "
        "It has to be a number a STRANGER CAN FEEL: a quantity, a duration, a "
        "price, a count of things. A version string, a catalogue or patent "
        "number, a document identifier, a section number or a case reference "
        "is not a number in this sense — "
        "it is a label that happens to be made of digits, and it stops nobody. "
        "A BARE YEAR is not a magnitude either — it is a label for a point in "
        "time. '2009.' alone on a line stops nobody; 'eleven seconds' or "
        "'three dollars a month' or 'two cents a copy' does. "
        "A year may appear later in the note, never as the hook. "
        "If the only figures in the material are identifiers or dates, this is "
        "the wrong form for that material."
    ),
    "SCENA": (
        "Start with what is in front of the reader, in the second person: what "
        "is in front of them right now, what they are waiting on, what decided "
        "something about them without telling them. One line. "
        "Blank line. Then the rule hiding inside it. It does not have to be a "
        "thing they can pick up — but it does have to be ONE thing and theirs, "
        "not a scene from somebody else's life. Never a question, and no "
        "invented experience of your own."
    ),
    "PYTANIE": (
        "Deliver the whole fact first, in two or three lines. Then, on its own "
        "line, one short question the reader can answer from their own life "
        "without looking anything up. "
        "This form is an experiment and it has a cost. Notes containing a "
        "question mark convert 35 percent fewer subscribers — but direct, "
        "easy questions are what actually pulls comments, and a young account "
        "needs conversation more than it needs a clean conversion rate. So: "
        "never a question INSTEAD of the fact, only after it. Never a question "
        "whose answer is in the note. Never a request for engagement."
    ),
    "ODWROCENIE": (
        "First line: the thing everyone believes, stated fairly and without "
        "mockery. Blank line. Then the record that contradicts it, and why the "
        "belief was reasonable in the first place. Break that second half too — "
        "four sentences crammed into one block undoes the whole point of the "
        "shape."
    ),
    # Struktura wskazywana zgodnie przez dwie niezalezne analizy duzych prob
    # notek (setki tysiecy sztuk): zaczep w pierwszej linii, dwie-cztery linie
    # tresci, konkret na koncu. Wersja dla NAS: zamiast osobistego wyniku,
    # ktorego anonimowa marka nie ma, konczymy rzecza do sprawdzenia u siebie.
    "ZACZEP_I_KONKRET": (
        "Three moves, in order. One: a hook line that works on somebody who "
        "has never heard of us and is scrolling — specific and surprising, "
        "never a category label. Two: two to four lines saying what the "
        "arrangement actually is and who decided it. Three: one closing line "
        "handing the reader something they can look at, count or compare "
        "themselves, today, without our help. Do not promise what they will "
        "find. No personal anecdote — we do not have one and must not invent it. "
        "THE THING MUST ALREADY BE IN THEIR LIFE: something they used this "
        "week, something they see every day, a choice they were never shown. "
        "Sending them to read a policy, a technical document or a regulator's "
        "guidance is homework, and nobody does homework from a feed; 'open "
        "the documentation and see for yourself' is the same homework with a "
        "newer document."
    ),
}

NOTE_FORM_MIX = ("SCENA", "KONTRAST", "ZACZEP_I_KONKRET", "PROSTA", "LISTA",
                 "PYTANIE", "ODWROCENIE", "LICZBA")

# FORMY, KTORYCH DANY TYP NIE MA JAK WYPELNIC.
#
# Forma byla dotad losowana z CALEJ osemki, niezaleznie od typu i od materialu:
# `(dzien_roku + wystawione_dzis + i) % 8`. Komentarz przy tym wyliczeniu mowi
# wprost, ze celem jest, by "po osmiu dniach kazda para typ-forma zdazyla
# wystapic" — i tak sie dzialo, takze dla par NIEWYKONALNYCH.
#
# MYSL to jedyny typ ZWOLNIONY z karty dowodowej; jego brief mowi "NO FACTS:
# no number, no date, no named company (...) nothing a reader could look up".
# LICZBA kaze "Open with the number itself, alone on the first line".
# LISTA kaze "EVERY line must carry a fact the previous line did not".
#
# To nie jest napiecie stylistyczne, tylko zlecenie bez rozwiazania: model
# dostaje zakaz faktow i nakaz faktu w jednym prompcie. Zmierzone symulacja
# roku kalendarzowego: 273 z 3597 par (7,6%) to MYSL z forma wymagajaca
# faktow — mniej wiecej co trzynasta notka.
#
# Nie zabieramy tu formy nikomu, kto moze ja wypelnic: dryf zostaje, a kazda
# ZGODNA para nadal wystapi.
FORMY_ZAKAZANE_DLA_TYPU = {
    "MYSL": frozenset({"LICZBA", "LISTA"}),
}


def formy_dla_typu(typ: str) -> tuple[str, ...]:
    """Formy, ktore ten typ notki ma czym wypelnic."""
    zakazane = FORMY_ZAKAZANE_DLA_TYPU.get((typ or "").upper(), frozenset())
    dozwolone = tuple(f for f in NOTE_FORM_MIX if f not in zakazane)
    # Pusta lista znaczylaby, ze typ nie ma ZADNEJ formy — to bylby blad
    # w tablicy powyzej, a nie stan, w ktorym wolno milczkiem isc dalej.
    return dozwolone or NOTE_FORM_MIX


NOTE_TYPES = {
    # MYSL — jedyny typ ZWOLNIONY z karty dowodowej, i jedyny, ktoremu nie
    # wolno niesc faktu.
    #
    # Wlasciciel pokazal cztery notki z kont, ktore chce nasladowac. Zadna nie
    # miala ani jednego udokumentowanego faktu — zero zrodel, zero liczb, zero
    # nazwisk — a ta zlozona z samych pytan zebrala pietnascie komentarzy. Wiecej niz cokolwiek, co dotad
    # wystawilismy przy naszych 26 polubieniach na dwanascie notek.
    #
    # Nasze pozostale cztery typy wymagaja dowodu, wiec takiej notki nie da sie
    # u nas napisac. Ten typ to naprawia, placac twarda cena: bez faktu znaczy
    # BEZ FAKTU. Dzieki temu sprawdzanie faktow jest tu EGZEKUTOREM, a nie
    # przeszkoda — notka bez sprawdzalnego twierdzenia nie ma czego oblac,
    # a notka, ktora fakt przemyci, oblewa sie sama.
    "MYSL": (
        "A thought, a question, or an observation about what it is like to "
        "live with the subject of this publication. NO EVIDENCE CARD, and therefore NO "
        "FACTS: no number, no date, no named company doing a named thing, no "
        "study, no percentage, nothing a reader could look up and find false. "
        "If your idea needs a fact to stand up, it is a different note type "
        "and you should say so instead of inventing one.\n\n"
        "What is left is the part people actually answer: a question nobody "
        "can settle, an observation about the shared experience of dealing "
        "with it, a position you would defend out loud. It may be openly "
        "uncertain. It may be funny. It may admit that you are behind, "
        "confused, or annoyed — those read as human because they are the "
        "things a person says and an account never does.\n\n"
        "Two shapes work. FIRST: the open question, asked in earnest, with "
        "the two or three ways it could go named underneath — not a rhetorical "
        "question whose answer you are holding. SECOND: the observation that "
        "names something everyone has felt and nobody has said, followed by "
        "what you think it means.\n\n"
        "Speak in the first person and mean it. 'I think', 'I just realised', "
        "'maybe' are allowed here and nowhere else in this publication. The "
        "reader is being invited to disagree, so give them a specific thing "
        "to disagree with, not a mood."
    ),
    "ARTYKUL": (
        "A fact from an article published today. State the fact so it stands on "
        "its own, then let the link do the rest. Do not summarise the article "
        "and do not tease it — the note has to be worth reading by someone who "
        "never clicks."
    ),
    "CIEKAWOSTKA": (
        "A single documented fact, surprising on its own, with no link and "
        "nothing to sell. The test: a reader who knows nothing about this "
        "publication stops scrolling and wants to know who found that out."
    ),
    "DYSKUSJA": (
        "A statement someone could reasonably disagree with, backed by a "
        "specific from the evidence. Not a question, and never a request for "
        "opinions — take a position and leave the obvious objection visible so "
        "a reader can pick it up. Comments carry more reach than likes."
    ),
    "SPROSTOWANIE": (
        "Name a thing widely believed, then the record that contradicts it. "
        "This is the house speciality: the gap between what people assume and "
        "what the document says. Do not mock the belief — explain why it is "
        "reasonable and where it goes wrong."
    ),
}

# Strefa czasowa publikacji. Liczy sie strefa CZYTELNIKOW, nie wlasciciela
# — i to jest cala rzecz. Godziny w tym pliku pochodza z pomiarow na
# publicznosci, a nie z tego, kiedy operatorowi wygodnie patrzec.
#
# Stalo tu wczesniej, w ktorej strefie mieszka wlasciciel. Nie bylo to
# potrzebne do niczego — agent chodzi z harmonogramu — a w publicznym
# repozytorium jest to po prostu jego dana osobowa.
PUBLISH_TIMEZONE = "America/New_York"

# NAJGORSZE OKNO — I TO JEST STALA EGZEKWOWANA, nie zapis ustalen.
# `pora_na_publikacje` odmawia publikacji w tych godzinach, wiec miedzy 12:00
# a 13:59 u czytelnikow agent nie wystawia ANI notek, ANI komentarzy. To dwie
# z szesnastu godzin okna, codziennie.
#
# Stala stala wczesniej w bloku opisanym jako „NIE SA UZYWANE PRZEZ ZADNA LINIE
# KODU" i to bylo grozne w konkretny sposob: kto uwierzylby temu komentarzowi
# i skasowal ja jako martwa, dostalby NameError w `pora_na_publikacje`, czyli
# w funkcji wolanej na poczatku KAZDEGO przebiegu dnia. Komentarz mowil tez
# „agent wystawia notki rownomiernie w calym oknie 6-22 ET" — nieprawda
# wlasnie z powodu tej stalej.
# OD 31 SIERPNIA 2026 NIE JEST BRAMKA, tylko adnotacja w logu — patrz
# `pora_na_publikacje`. Blokowala codziennie przebieg o 17:00 UTC (13:00 ET),
# czyli jeden z pieciu, a stala na badaniu, ktoremu przeczy inne badanie w tym
# samym pliku.
WORST_NOTE_HOURS = (12, 13)  # ET — TYLKO ADNOTACJA, nie blokada

# UWAGA: DWIE PONIZSZE STALE NIE SA UZYWANE PRZEZ ZADNA LINIE KODU.
# Agent nie wazy notek wedlug tych godzin ani dni — rozklada je losowo
# w oknie OKNO_PUBLIKACJI_ET z pominieciem WORST_NOTE_HOURS wyzej.
#
# To nie jest usterka do cichego naprawienia, bo NASZE WLASNE ZRODLA SIE NIE
# ZGADZAJA: ponizsze dane mowia, ze najlepsze jest 6-8 rano czasu nowojorskiego,
# a research z 18 sierpnia wskazywal 19:00-22:00 UTC, czyli 15:00-18:00 ET.
# Zanim cokolwiek zacznie wazyc godziny, trzeba rozstrzygnac ktore z tych
# dwoch. Do tego czasu stale zostaja jako ZAPIS USTALEN, wyraznie oznaczony
# jako nieuzywany — patrz `test_martwe_sygnaly.py`.
BEST_NOTE_HOURS = (6, 7, 8)  # ET — NIEUZYWANE
BEST_NOTE_DAYS = ("sunday", "saturday")  # NIEUZYWANE

# TWARDE OKNO PUBLIKACJI, w czasie CZYTELNIKOW. Agent wystawil notki o 03:57
# i 04:00 UTC — czyli 23:57 i polnoc w Nowym Jorku. Tekst wrzucony, gdy
# publicznosc spi, nie znika, ale traci pierwsze godziny widocznosci, a wlasnie
# one decyduja o zasiegu w kanale.
#
# Zegar mozna przestawic i reczne uruchomienie i tak by go ominelo, wiec zasada
# siedzi w KODZIE, nie w harmonogramie.
OKNO_PUBLIKACJI_ET = (6, 22)        # wolno od 6:00 do 21:59 czasu nowojorskiego
WORST_NOTE_DAYS = ("monday", "friday")

# Rozkład na tydzień: pięć notek dziennie, dzień publikacji artykułu ma własny.
# Ile notek promuje jeden artykul i przez ile dni. Decyzja wlasciciela z 20
# sierpnia: TRZY, po jednej dziennie, trzy dni z rzedu ZARAZ po artykule.
# Kilka linkow w jeden dzien to nie promocja, tylko natret; trzy przez trzy dni
# to trzy osobne szanse na trafienie kogos, kto akurat patrzy w kanal.
#
# Bylo piec. Zeszlo do trzech razem ze zmiana kolejnosci: promujemy NAJSWIEZSZY
# artykul, nie najdawniej wstawiony (patrz `artykul_do_promocji`). Przy pieciu
# dniach i artykule tygodniowo kolejka nie nadazala i swiezy tekst czekal za
# starszymi z zimnym juz linkiem.
NOTEK_PROMUJACYCH = 3

# PO ILU DNIACH ARTYKUL PRZESTAJE BYC PROMOWANY, nawet jesli nie wybral swoich
# trzech notek. `artykul_do_promocji` sam nazwal ten problem w docstringu —
# „link juz zimny, artykul dawno zepchniety w dol kanalu" — ale nazwal go tylko
# w komentarzu. W kodzie nie bylo zadnej daty waznosci, wiec artykul z
# niewybranym dniem czekal w kolejce w nieskonczonosc.
#
# Zmierzone 26 sierpnia na produkcji: w kolejce lezaly cztery teksty z epoki
# sprzed zmiany tematu, dwa z nich z niewybranymi dniami. Po wyczerpaniu
# biezacego artykulu kanal wystawilby notke promujaca tekst sprzed tygodnia,
# o czym innym niz publikacja pisze dzisiaj.
#
# Siedem dni, nie trzy: przydzial to trzy dni Z RZEDU zaraz po publikacji, ale
# dzien potrafi wypasc (cichy dzien, wyczerpany limit notek), wiec okno musi
# miec zapas na nadrobienie. Tydzien miesci trzy dni plus cztery na poslizg i
# konczy sie, zanim link zdazy ostygnac.
OKNO_PROMOCJI_DNI = 7

# DZIEN, W KTORYM TO KONTO OSTATNI RAZ ZMIENILO TEMAT.
#
# Nie jest to data historyczna dla ozdoby — czyta ja `stages.wez_kandydatow`
# i odrzuca kazdego kandydata dopisanego wczesniej. Indeks kandydatow
# przezywa zmiane niszy i trzyma material obu pism naraz. Zmierzone
# 30 sierpnia 2026 na 119 wolnych kandydatach jednego konta:
#     przed zmiana niszy   65 pozycji, z tego 1 w nowej niszy
#     po zmianie niszy     54 pozycje, z tego 46 w nowej niszy
# Rozdzial jest ostry, wiec data dziala jak filtr, a nie jak przyblizenie.
#
# TA SAMA KLASA WADY, CO STARY ARTYKUL W KOLEJCE PROMOCYJNEJ: rzeczy
# z poprzedniego pisma nie znikaja same, tylko czekaja, az cos po nie siegnie.
#
# STALA DATA W KODZIE BYLA TU BLEDEM I WARTO WIEDZIEC JAKIM. Stal tu konkretny
# dzien z historii jednego konta. Dla kazdej innej instalacji byla to CUDZA
# data — a jesli pozniejsza niz jej wlasne pierwsze przebiegi, indeks odrzucal
# wszystko, co ta instalacja zdazyla zebrac. Bez sladu: brak kandydatow wyglada
# dokladnie tak samo jak brak kandydatow.
#
# PUSTY NAPIS ZNACZY „NIGDY NIE ZMIENIALEM TEMATU" i przepuszcza cala spizarnie.
# To jest poprawna odpowiedz dla nowego konta i domyslna tutaj — filtr wlacza
# sie dopiero wtedy, gdy jest co odcinac.
DATA_PRZESTAWIENIA = ""

# Jaka czesc banku moze niesc znacznik „na artykul".
#
# Pytany po kolei „czy to unioslo by artykul", model mowi tak prawie zawsze —
# ta sama degeneracja, co przy notach. Zmierzone na dwoch partiach: 7 z 13
# (54%) i 14 z 21 (67%), przy prompcie mowiacym wprost „wiekszosc kandydatow
# to notki". Znacznik u dwoch trzecich banku nie niesie informacji, a decyduje,
# co idzie na DROZSZA sciezke.
#
# Jedna trzecia nie jest wrozeniem: przy piecu notkach dziennie i artykule co
# kilka dni nawet tyle jest zapasem z gora. Kto ma niesc — rozstrzyga ranking.
BANK_UDZIAL_ARTYKULOW = 0.33


# --- BANK POMYSLOW: BUFOR, NIE MAGAZYN --------------------------------------
#
# Wlasciciel, 30 sierpnia: „nie moze byc tak, ze mamy za duzo tematow w banku,
# bo sie okaze, ze po czasie beda same stare tematy dawac, bo wszystko bedzie
# z banku szlo, bo sie nazbieralo".
#
# Ryzyko jest prawdziwe i sam je stworzylem, podlaczajac bank. Uzupelnianie
# rusza dopiero, gdy bank pustoszeje — wiec przy duzym zapasie `znajdz_
# ciekawostki` nie odpala sie NIGDY i zaden nowy temat nie wchodzi. Ranking
# sortuje po sile, wiec mocny temat sprzed dwoch tygodni bezterminowo
# wyprzedza slabszy, ale DZISIEJSZY. Bank kostnieje.
#
# Zmierzone: bank mial 53 wolne pozycje przy zuzyciu pieciu na dobe. Dziesiec
# dni zapasu — dokladnie ten stan.
#
# SUFIT ZAPASU. Powyzej tej liczby nie szukamy nowych faktow. Cztery doby
# to dosc, zeby wiekszosc przebiegow nie placila za szukanie, i za malo, zeby
# bank zaczal zyc wlasnym zyciem. Oszczednosc i tak zostaje: bez banku kazdy
# z pieciu przebiegow placil za wlasne szukanie.
BANK_MAKS_WOLNYCH = 20

# ILE RAZY NA DOBE WOLNO DOBIERAC MATERIAL DO BANKU.
#
# Bylo: przy kazdym z pieciu przebiegow. Zmierzone 1 wrzesnia 2026 na
# produkcji: srednio 266 517 tokenow wejscia i 14,6 wyszukan w sieci na jedno
# wywolanie, 46 wywolan przez osiem dni — okolo 13,6 USD miesiecznie, przy
# banku, w ktorym 58 z 69 pozycji lezalo NIEUZYTYCH.
#
# Sufit banku (`BANK_MAKS_WOLNYCH`) mial to zatrzymywac i przez trzy dni nie
# zatrzymal ANI RAZU, bo obchodzila go regula o wielkim wydarzeniu — a
# wydarzeniem bylo za kazdym razem to samo: premiera ACME 5.3 sprzed kilku dni.
SZUKANIE_BANKU_NA_DOBE = 1

# JAK DLUGO TO SAMO WYDARZENIE NIE OTWIERA FURTKI DRUGI RAZ.
#
# Wlasciciel: „chce napisac o tym w tym samym dniu, max dzien po". Dwie doby
# pokrywaja to okno dokladnie. Po nich ten sam rdzen moze wrocic — jesli
# temat naprawde odzyl, zasluguje na drugie podejscie.
WYDARZENIE_WAZNE_DNI = 2
# ILE RAZY PROBUJEMY DOBRAC MATERIAL DO JEDNEGO WYDARZENIA, zanim uznamy je za
# zamkniete mimo braku materialu. Od 2 wrzesnia 2026 furtke zamyka SKUTEK, nie
# zamiar — a bez tego licznika wydarzenie, przy ktorym szukanie pada w kolko,
# otwieraloby ja przy kazdym z pieciu przebiegow dziennie. To dokladnie ta
# petla kosztowa, ktora 1 wrzesnia kosztowala 13,6 USD miesiecznie.
WYDARZENIE_PROB_MAKS = 3

# TERMIN WAZNOSCI W BANKU, liczony od dnia dopisania — osobny od wieku ZRODLA.
# To sa dwa rozne pytania: dokument kontrolny mowi, czy fakt jest nadal
# PRAWDZIWY, a to mowi, czy jest jeszcze AKTUALNY jako temat. Fakt sprzed
# tygodnia bywa prawdziwy i martwy zarazem — korpus obserwowanych kanalow
# obraca sie w dniach, wiec w szybkiej dziedzinie tydzien to zamierzchlosc.
# Publikacja o czyms, co zmienia sie wolniej, powinna te liczbe podniesc.
# ILE WPISOW ZATRZYMUJE BANK TEMATOW. Powyzej tej liczby najstarsze wypadaja
# przy KAZDYM zapisie indeksu — po cichu, bez wpisu w logu i bez statusu
# `przeterminowany`, wiec `audyt_systemu` nie policzy ich jako zmarnowanych.
#
# BYLA TO LICZBA W KROJENIU LISTY (`indeks[-600:]` w `stages.zapisz_indeks`)
# i TRZY jej kopie w `audyt_systemu` — cztery wystapienia w dwoch plikach,
# ani jednej nazwy. Audyt raportowal „bank daleko od sufitu" wobec liczby
# przepisanej z pamieci, wiec zmiana krojenia zostawilaby go mierzacego
# wobec szescset i meldujacego spokoj.
BANK_MAKS_WPISOW = 600

BANK_MAKS_DNI = 7

# MIESZANKA DNIA. Ostatnia pozycja to MYSL — notka bez zadnego dowodu.
#
# Powod jest w NOTE_TYPES przy samym typie: wszystkie pozostale wymagaja karty
# dowodowej, a konta, ktore wlasciciel wskazal jako wzor, zbieraja rozmowe
# notkami bez ani jednego faktu. Jedna na dzien, nie wiecej — wlasciciel
# powiedzial wprost "nie maja byc wszystkie takie", i ma racje: feed samych
# rozmyslan bez pokrycia to inne konto, nie nasze.
NOTE_MIX_ARTICLE_DAY = ("ARTYKUL", "ARTYKUL", "CIEKAWOSTKA", "SPROSTOWANIE", "MYSL")

# KSZTALTY NOTKI TYPU MYSL. Losowane w kodzie i podawane jako PRZYDZIAL.
#
# Powod jest zmierzony: opis typu wymienial pytanie i obserwacje jako dwie
# mozliwosci, a model wybral obserwacje SZESC RAZY NA SZESC i szesc razy
# zaczal od slowa "I". Notki byly dobre, ksztalt byl jeden.
#
# To ta sama choroba, co samooceny wracajace zawsze 1.0 i watki zawsze po
# szesc — postawiony przed wyborem, model zbiega do stalej. I to samo
# lekarstwo, co przy ruchu koncowym artykulu i formie notki: losowac w kodzie.
#
# Notka wlasciciela z pietnastoma komentarzami — najwiecej ze wszystkiego, co
# pokazal — byla PYTANIEM. Czyli ksztaltem, ktorego model nie wybral ani razu.
KSZTALTY_MYSLI = {
    "PYTANIE": (
        "Ask something nobody can settle, in earnest, and mean the question. "
        "Name two or three ways it could go underneath — that is the part "
        "people answer. You are not holding a hidden answer: if you know how "
        "it comes out, this is the wrong shape. End on the open end, not on a "
        "resolution. Do NOT open with the question and then quietly answer it."
    ),
    "OBSERWACJA": (
        "Name something everyone who deals with this subject has felt and "
        "nobody has said out loud, then say what you think it means. First "
        "person, specific, about a habit or a moment rather than about the "
        "industry."
    ),
    "TEZA": (
        "State a position you would defend out loud, then the reasoning that "
        "got you there, then the part of it you are least sure about. Give "
        "the reader something precise to disagree with. No hedging into "
        "mush — a clearly stated wrong opinion is better than a safe one."
    ),
    "CUDZE_ZDANIE": (
        "Somebody else's take that you keep turning over — argued with, not "
        "reported. Say what it gets right, then where you come off it. Do not "
        "name or quote anyone: you have no evidence card, so the position is "
        "described in your own words as a position, never attributed."
    ),
}


def losowy_ksztalt_mysli() -> str:
    """Ktory ksztalt dostaje ta MYSL. Losowany, bo wybor zbiega do stalej."""
    import random
    return random.choice(list(KSZTALTY_MYSLI))
NOTE_MIX_OTHER_DAY = ("CIEKAWOSTKA", "CIEKAWOSTKA", "DYSKUSJA", "SPROSTOWANIE", "MYSL")

# LICZBA SLOTOW NOTEK NA DOBE — jedna dla obu rodzajow dnia. Wyprowadzona
# z miksu, a nie wpisana obok niego: `konfiguracja.zastosuj` ustawia ja RAZEM
# z obiema listami (`wolumeny.notki_dziennie`), wiec nie ma jak sie z nimi
# rozjechac. Zero znaczy: notki wylaczone.
NOTKI_DZIENNIE = len(NOTE_MIX_OTHER_DAY)

# --- zachowanie spoleczne: widelki, nie stale liczby -------------------------
# Stala liczba dziennie wyglada jak robot, bo czlowiek nie ma normy. Losujemy
# w tych granicach, osobno na kazdy dzien.
#
# UCZCIWIE O POCHODZENIU TYCH LICZB: Substack nie publikuje swoich limitow.
# To NIE sa zmierzone progi, tylko tempo aktywnego czlowieka. Sa celowo niskie,
# bo kosztem przesady nie jest ostrzezenie, tylko utrata konta, na ktorym stoi
# caly projekt. Podniesiemy je dopiero, gdy zobaczymy wlasne dane.
# PRZEJRZANE NA WLASNYCH DANYCH 2026-08-20 (piec dni dziennika). Do tej pory
# byly to liczby wziete z wyobrazenia o tempie czlowieka. Teraz wiemy, ile
# agent NAPRAWDE robi, i widelki maja to opisywac, a nie zyczyc sobie tego.
#
# Budzet, ktorego nigdy nie da sie wydac, nie jest budzetem: klamie w logu,
# psuje dzielenie normy na przebiegi i ukrywa, ze jakis blok w ogole nie chodzi.
#
#   zmierzone (srednia z 5 dni)   bylo w konfiguracji   ustawiam
#   lajki        9,6              12-20                 10-16
#   komentarze   7,0              15-20                 8-12
#   obserwacje   0,0 (!)          30-44/mies            10-16/mies (1 wrzesnia)
#   subskrypcje  ~0,8/dzien       6-12/mies             12-20/mies (1 wrzesnia)
#   restacki     0,4              2-4/dzien             1-2/dzien
#
# WYKRZYKNIK PRZY OBSERWACJACH BYL JEDYNYM PRAWDZIWYM SYGNALEM W TEJ TABELI
# i przez trzy dni nikt nie umial go odczytac. 23 sierpnia wpisano tu „0 (nie
# ma przycisku)" — na podstawie prawdziwego pomiaru i falszywego wniosku —
# i wykrzyknik zniknal razem z problemem. 1 wrzesnia 2026 widelki wracaja;
# powod stoi przy samej stalej `FOLLOW_MIESIECZNIE`.
LAJKI_DZIENNIE = (10, 16)
# Osiemnascie komentarzy dziennie pod cudzymi tekstami to nie jest tempo
# czytelnika, tylko podpis bota — i kosztuje najwiecej po pisaniu, bo kazdy to
# trzy warianty plus sprawdzenie faktow, okolo trzech centow. Przy dwunastu
# dziennie wychodzi ~11 USD miesiecznie samych komentarzy.
#
# PODNIESIONE 30 sierpnia 2026 decyzja wlasciciela z (8, 12) do (15, 23).
# Rachunek kosztu zostaje wazny — okolo trzech centow za komentarz, wiec przy
# dziewietnastu dziennie to ~17 USD miesiecznie. Zmienil sie natomiast argument
# o „podpisie bota": nie chodzi o LICZBE, tylko o ODSTEPY. Osiemnascie
# komentarzy przez czternascie godzin to czytelnik; osiemnascie w kwadrans to
# maszyna. Dlatego razem z ta zmiana odstep komentarza poszedl z 3-8 na 5-15
# minut (patrz ODSTEPY) i doszly dwa przebiegi na dobe — bez tego norma nie
# miala gdzie sie zmiescic w czasie.
# NIEAKTUALNE OD 2 WRZESNIA 2026 stalo tu: „0 jest dozwolone: milczenie bije
# slaby komentarz". Zmierzone na dzienniku systemowym za 18 dni: 60 kandydatow
# na 588 zamilklo, ZERO z realnego powodu — ani jednego posta po innym jezyku,
# ani jednej proby sterowania kontem, ani jednego golego emoji. Wszystkie 60 to
# „to aforyzm, nie ma z czym dyskutowac", a osiem celow przepadlo przez to
# w calosci. Cisza jest teraz dopuszczona w pieciu wyliczonych przypadkach
# (`prompts/komentarz.md`), a nie jako domyslna odpowiedz.
KOMENTARZE_DZIENNIE = (15, 23)
# ZEROWANE 2026-08-23, PRZYWROCONE 2026-09-01 — BO WNIOSEK BYL FALSZYWY.
#
# Stalo tu `(0, 0)` z uzasadnieniem „Substack zdjal Follow ze stron
# profilowych". POMIAR, NA KTORYM TO STALO, BYL PRAWDZIWY: na szesciu profilach
# slowo „Follow" nie wystepowalo w HTML ani razu i nie bylo go tez na
# `/@kto/notes`. FALSZYWY BYL WNIOSEK. Przycisk jest — siedzi w menu pod
# kolkiem „..." obok „Subscribe" i „Message", a to menu Substack dorysowuje
# DOPIERO PO KLIKNIECIU. W HTML zamknietej strony nie ma go i byc nie moze,
# wiec tamten pomiar nie mogl go zobaczyc.
#
# Zmierzone ponownie 2026-09-01 na zywej sesji, na szesciu profilach: menu
# oddaje „Follow" tam, gdzie nie obserwujemy, i „Unfollow" tam, gdzie juz
# obserwujemy. Etykiety w obu jezykach i lista sprawdzonych profili stoja
# przy `browser.obserwuj_profil`.
#
# Zero kosztowalo dziewiec dni bez ani jednej obserwacji, a najgorsze bylo to,
# ze nie wygladalo na awarie: `norma.NIEWYKONALNE` tlumaczylo je tym samym
# nieprawdziwym zdaniem.
#
# WIDELKI NIE SA POWROTEM DO STANU SPRZED WYCOFANIA — to swiadome
# podniesienie, decyzja wlasciciela z 1 wrzesnia 2026. Prawdziwa historia
# tej stalej z `git log -S`: (10,20) -> (20,30) w `227c266` 20 sierpnia ->
# (0,0) w `ca55ce0` 23 sierpnia przy wycofaniu. Czyli ostatnia wartoscia,
# ktora NAPRAWDE chodzila w produkcji, bylo (20,30) — i tylko przez trzy dni.
# Para (30,44) do 1 wrzesnia nie istniala w kodzie ani razu: zyla wylacznie
# w opisach przy `browser.obserwuj_profil` i `run.py`, ktore przez caly ten
# czas mowily o widelkach, jakich stala nigdy nie miala.
#
# Wybor (30,44) zamiast (20,30) podnosi wolumen o okolo polowe, do ~1,2
# obserwacji na dobe. Ryzyko jest po stronie tempa, nie poprawnosci:
# obserwowanie ma potwierdzanie skutku, a profil juz obserwowany zapisuje
# sie jako `obserwacja_pominieta` i nie zjada slotu. Jesli tempo okaze sie
# za wysokie, obniz TU i nigdzie indziej.
#
# --- ODWROCONE TEGO SAMEGO DNIA, 1 WRZESNIA 2026, PO ZMIERZENIU SKUTKU -----
#
# Wpis wyzej stoi w calosci, bo opisuje, dlaczego obserwacje w ogole wrocily
# z zera — i to nadal jest prawda. Nieprawdziwe bylo to, po co je podnosilismy.
#
# UZASADNIENIE OBU STALYCH MOWILO O NASZYM KOSZCIE, NIE O SKUTKU. Przy
# `SUBSKRYPCJE_MIESIECZNIE` stalo doslownie „laduje w skrzynce wlasciciela,
# wiec waskie", a przy `FOLLOW_MIESIECZNIE` — „obserwacja nie przysyla nic
# mailem". Obie liczby byly wiec dobrane wedlug tego, co NAS mniej kosztuje,
# i wyszlo z tego trzy i pol raza wiecej dzialania w kanale, ktory dziala
# gorzej. To jest optymalizacja przeciw wlasnemu celowi.
#
# CZTERY POMIARY Z 1 WRZESNIA 2026, na ktorych stoja nowe liczby:
#
# 1. ODZEW WPROST. Cudzy eksperyment na 120 kontach: obserwacja -> 20% odzewu,
#    ale tylko 3,4% subskrypcji zwrotnych; subskrypcja -> 15% odzewu i 11,5%
#    subskrypcji. Ludzie odwdzieczaja sie DOSLOWNIE tym samym. To POSZLAKA
#    (jeden autor, nie dane platformy) i jedyna liczba tutaj, ktora nie jest
#    nasza — dlatego caly rachunek nizej jest podany tak, zeby dalo sie go
#    przeliczyc innym wspolczynnikiem.
# 2. NASZE WLASNE ZERO. Z 12 kont, ktorym dalismy subskrypcje, odwzajemnilo sie
#    ZERO. Mediana ich wielkosci ~5300 subskrybentow (skrajne 348 000
#    i 111 000) — celowalismy w duze i to jest osobna wada, ktora naprawia
#    kryterium doboru celu w `run.py`, a nie te widelki.
# 3. SKAD NAPRAWDE BIORA SIE CZYTELNICY. 11 z 19 naszych czytelnikow zostawilo
#    wczesniej slad interakcji z nami (wpisy `rodzaj="skutek"` w dzienniku:
#    199 rekordow, 69 roznych osob). 0 z 19 to konto, ktore MY zasubskrybowalismy.
# 4. ILE TE STALE DAJA NAPRAWDE. Nie „srodek widelek": przepuszczone przez
#    prawdziwe `stages.budzet_dnia` (`z_miesiaca` losuje ulamek dnia osobno,
#    a rozbieg scina gorna polowe widelek) przez 365 dni poza rozbiegiem
#    i 30 dni w rozbiegu.
#
#       stale        follow/mies  sub/mies  dzialan  oczekiwani subskrybenci
#       (30,44)+(6,12)     37,23      8,38     45,6  1,27 + 0,96 = 2,23
#       (10,16)+(12,20)    12,74     15,37     28,1  0,43 + 1,77 = 2,20
#       to samo, rozbieg    7,00     16,00     23,0  0,24 + 1,84 = 2,08
#
#    Czyli TEN SAM oczekiwany wynik (2,23 -> 2,20, roznica 1,3%) przy 38 procent
#    mniejszej liczbie dzialan na cudzych profilach. Sprawdzalem tez warianty
#    ostrzejsze — (8,12)+(16,24) daje 2,53 przy 29,2 dzialaniach — i ich NIE
#    biore: rachunek stoi na jednej poszlace z punktu 1, wiec nie ma podstaw
#    zeby na niej optymalizowac do drugiego miejsca po przecinku. Bierzemy
#    liczby, ktore przy tej samej pracy sa wyraznie ostrozniejsze.
#
# KOSZT, KTOREGO NIE ZNOSIMY I NIE UDAJEMY, ZE ZNOSIMY. Kazda subskrypcja to
# poczta w skrzynce wlasciciela, a nowe widelki podnosza ja z ~8 do ~15 maili
# miesiecznie z nowych zrodel. Sprawdzone 1 wrzesnia w calym `agent-v2`:
# NIE MA w kodzie zadnego ustawienia wyciszania powiadomien przy subskrybowaniu
# (`_klik_na_profilu` klika „Subscribe" i nic wiecej; jedyne „wycisz"
# w repozytorium to `CICHY_DZIEN_WYCISZA`, ktore dotyczy NASZEGO nadawania,
# oraz „Mute" w menu cudzego profilu, ktorego swiadomie nie tykamy). Nie
# dorabiam go tutaj — to zmiana w cudzym pliku i osobna decyzja. Do tego czasu
# to jest znany, przyjety koszt, a nie przeoczenie.
#
# CO MUSI ZAJSC, ZEBY TO ODWROCIC. Jesli po miesiacu `norma.py` pokaze, ze
# subskrypcje nadal daja zero nowych czytelnikow, to nie widelki sa wtedy zle,
# tylko DOBOR CELU — i poprawka idzie do `run.cele_wedlug_pierwszenstwa`,
# nie tutaj.
FOLLOW_MIESIECZNIE = (10, 16)      # 12,7/mies realnie; 0 z 19 czytelnikow stad
SUBSKRYPCJE_MIESIECZNIE = (12, 20)  # 15,4/mies realnie; 3,4x lepsza konwersja


def normy_dzienne() -> dict[str, float]:
    """Ile czego POWINNO wychodzic dziennie — srodek widelek.

    Liczone z tych samych stalych, ktore rozdzielaja budzet, zeby nie powstala
    druga lista liczb do rozjechania. Klucze sa takie, jak `rodzaj` w dzienniku
    dzialan — inaczej licznik porownywalby normy z niczym.

    PO CO. Przez osiem dni agent wystawil 23 notki przy normie 5 dziennie,
    czyli 58 procent, komentarzy 55, restackow 33 — i nikt tego nie wiedzial,
    bo nikt nie liczyl. Licznik `zrobione` zyl w pamieci jednego przebiegu,
    drukowal sie na koncu i ginal. Norma bez pomiaru jest zyczeniem.
    """
    return {
        "notka": float(len(NOTE_MIX_OTHER_DAY)),
        "polubienie": sum(LAJKI_DZIENNIE) / 2,
        "komentarz": sum(KOMENTARZE_DZIENNIE) / 2,
        "restack": sum(RESTACK_DZIENNIE) / 2,
        "subskrypcja": sum(SUBSKRYPCJE_MIESIECZNIE) / 2 / 30,
        # NAZWA MUSI BYC TAKA, JAK `rodzaj` W DZIENNIKU. Bylo tu "follow",
        # a `browser.obserwuj_profil` zapisuje "obserwacja" — licznik
        # porownywal wiec norme z niczym i zglaszal 0% przy dzialajacym
        # bloku. Dokladnie ta klasa bledu, ktora ten licznik ma lapac.
        "obserwacja": sum(FOLLOW_MIESIECZNIE) / 2 / 30,
    }


# Ponizej ilu procent normy uznajemy, ze cos jest zepsute, a nie po prostu
# chudsze. Prog jest niski celowo: budzety sa LOSOWANE z widelek i dzielone
# na przebiegi, wiec wahania rzedu kilkunastu procent to normalna praca.
# Polowa normy utrzymujaca sie przez tydzien to juz nie wahanie.
PROG_ALARMU_WOLUMENU = 60
# ODBLOKOWANE decyzja wlasciciela 2026-08-19. Restack cudzej notki z wlasnym
# zdaniem trafia do kanalu NASZYCH obserwujacych, powiadamia autora oryginalu
# i stawia nasze zdanie obok jego — za cene jednego zdania, nie calej notki.
#
# Wasko celowo. Restack jest publicznym aktem na cudzej tresci: przy dziesieciu
# dziennie konto wyglada jak wzmacniacz, a nie jak ktos, kto czyta. Jeden-dwa
# to tyle, ile czlowiek naprawde uzna za warte podania dalej.
# --- ciche dni ---------------------------------------------------------------
# Publikacja nadajaca identycznie codziennie czyta sie jak kanal, a nie jak
# ktos, kto mysli. To byl ostatni wyrazny podpis automatu na tym profilu:
# siedem dni z rzedu, ten sam rytm, zadnej przerwy.
#
# Ale cichy dzien wycisza NADAWANIE, nigdy ODPOWIADANIE. Nieodpisanie komus,
# kto sie do nas odezwal, nie jest cisza tylko lekcewazeniem — i akurat to
# widac natychmiast.
#
# Decyzja musi byc TA SAMA dla wszystkich przebiegow tego samego dnia. Losowanie
# per przebieg dalo by dzien, w ktorym rano jest cicho, a wieczorem nie — czyli
# gorzej niz brak ciszy. Dlatego liczymy ja z daty, deterministycznie.
CICHY_DZIEN_NA_ILE = 8          # srednio jeden na osiem dni
CICHE_DNI_WLACZONE = True

# CO WYCISZA CICHY DZIEN — jedna lista, dwoch czytelnikow.
#
# `run.py` zeruje przydzial na te pozycje; `norma.py` nie wlicza takich dni do
# sredniej. Bez wspolnej listy te dwa miejsca sie rozjezdzaja i licznik krzyczy
# „0/5, ponizej progu" w dniu, w ktorym system zachowal sie dokladnie tak, jak
# zaprojektowano. Alarm, ktory myli sie regularnie, uczy ignorowania siebie.
#
# WYCISZAMY TO, CO NADAJEMY. Komentarze, polubienia i odpowiedzi zostaja, bo to
# czytanie cudzych rzeczy — a nieodpisanie komus, kto sie odezwal, nie jest
# cisza, tylko lekcewazeniem.
#
# Dwie nazwy tej samej rzeczy, bo budzet mowi w liczbie mnogiej, a dziennik w
# pojedynczej. Zgodnosc obu krotek pilnuje test.
CICHY_DZIEN_WYCISZA = ("notki", "restacki")

# NAZWA W BUDZECIE -> NAZWA W DZIENNIKU. Dwie konwencje istnieja naprawde:
# budzet mowi „ile czego dzis wolno" (liczba mnoga), dziennik notuje pojedyncze
# zdarzenia (liczba pojedyncza). Dopoki to tlumaczenie siedzialo w glowie, dwa
# miejsca w kodzie mialy wlasne kopie i jedno z nich sie rozjechalo — licznik
# porownywal norme „follow" z dziennikiem, ktory zapisuje „obserwacja", i
# meldowal 0% przy dzialajacym bloku.
BUDZET_NA_RODZAJ = {
    "notki": "notka",
    "komentarze": "komentarz",
    "lajki": "polubienie",
    "restacki": "restack",
    "subskrypcje": "subskrypcja",
    "follow": "obserwacja",
}

# Wyprowadzone, NIE przepisane recznie — zeby nie dalo sie rozjechac.
CICHY_DZIEN_WYCISZA_RODZAJE = tuple(BUDZET_NA_RODZAJ[k]
                                    for k in CICHY_DZIEN_WYCISZA)


def _cisza_z_hasza(dzien: str) -> bool:
    import hashlib

    liczba = int(hashlib.sha256(("%s|cisza" % dzien).encode("utf-8")).hexdigest()[:8], 16)
    return liczba % CICHY_DZIEN_NA_ILE == 0


def cichy_dzien(kiedy=None) -> bool:
    """Czy dzis nie nadajemy. Ta sama odpowiedz przez caly dzien.

    Sam hasz daje SKUPISKA: na dwoch latach wypadly cztery ciche dni z rzedu,
    a to juz nie jest przerwa na myslenie, tylko porzucone konto. Wiec dzien
    jest cichy tylko wtedy, gdy poprzedni nie byl — deterministycznie, bez
    zadnego stanu do zapamietania, i nadal identycznie dla wszystkich
    przebiegow tej samej doby.
    """
    from datetime import datetime, timedelta, timezone

    if not CICHE_DNI_WLACZONE or CICHY_DZIEN_NA_ILE < 2:
        return False
    kiedy = kiedy or datetime.now(timezone.utc)
    dzis = kiedy.strftime("%Y-%m-%d")
    wczoraj = (kiedy - timedelta(days=1)).strftime("%Y-%m-%d")
    return _cisza_z_hasza(dzis) and not _cisza_z_hasza(wczoraj)


# Zjechane z 2-4 na 1-2 (2026-08-20). Restack stawia NASZE nazwisko obok
# cudzego tekstu — to najmocniejszy gest w calym repertuarze i jedyny, ktory
# firmuje czyjes zdanie. Cztery dziennie to nie czytanie, tylko rozdawanie
# poparcia. Zmierzone wykonanie i tak wynosilo 0,4 dziennie.
RESTACK_DZIENNIE = (1, 2)

# Dopisek do cudzej notki. Powyzej tego to juz nie dopisek, tylko wlasna notka
# doczepiona do czyjegos tekstu — a wtedy lepiej napisac wlasna notke.
RESTACK_MAX_SLOW = 40

# Pierwszy miesiac na dolnej polowie widelek. Nowe konto z jednym artykulem,
# ktore nagle obserwuje dwadziescia osob, wyglada dokladnie jak farma.
# Ile razy dziennie odpala sie agent. Dzienny przydzial dzieli sie na tyle
# przebiegow, zeby notki rozkladaly sie na GODZINY, a nie wychodzily jedna po
# drugiej w odstepie trzech minut — to wlasciciel zauwazyl na profilu.
# PIEC OD 30 sierpnia 2026, bylo trzy. Nie dlatego, ze agent ma robic wiecej
# rzeczy na raz, tylko dlatego, ze normy nie mialy gdzie sie zmiescic w czasie.
# Policzone: 19 komentarzy przy odstepie srednio 10 min to 236 min samego
# czekania, notki potrzebuja kolejnych ~190. Razem 426 min przy pojemnosci
# 3 x 150 = 450 — zero zapasu, wiec pierwsze potkniecie zabieralo norme.
# Przy pieciu przebiegach na przebieg przypadaja 4 komentarze i 1 notka, co
# miesci sie z zapasem.
PRZEBIEGOW_DZIENNIE = 5

# --- HARMONOGRAM Z KONFIGURACJI, NIE Z SZABLONU ZEGARA ----------------------
#
# Do 2026-09-05 godziny przebiegow staly WYLACZNIE w `systemd/nia-agent.timer`,
# a dzien artykulu w `systemd/nia-artykul.timer`. `PRZEBIEGOW_DZIENNIE` mialo
# sie z zegarem zgadzac, ale nic go z zegara nie wyprowadzalo, a generator
# jednostek podstawial tylko katalog, uzytkownika i marke (W2 audytu). Preset
# z inna liczba przebiegow dostawal wiec zegar o piecu godzinach.
#
# Teraz to sa pola presetu (`harmonogram.*`), a `narzedzia/jednostki.py`
# buduje `OnCalendar=` z `zegar_agenta_on_calendar()` i
# `zegar_artykulu_on_calendar()`. Wartosci ponizej to dotychczasowy zegar,
# zapisany jawnie — patrz komentarze w szablonach `.timer` o tym, skad sie
# wziely te godziny.
GODZINY_PRZEBIEGOW_UTC = ("11:20", "17:00", "19:20", "21:30", "23:40")

# ILE ARTYKULOW NA TYDZIEN I W KTORE DNI. Zero wylacza sciezke artykulu:
# zegar artykulu nie powstaje, `artykul_z_puli.py` odmawia, promocja nie ma
# czego promowac. Dni w postaci, ktora rozumie systemd (`Mon`..`Sun`).
ARTYKULY_TYGODNIOWO = 1
DNI_ARTYKULU = ("Tue",)
GODZINA_ARTYKULU_UTC = "14:00"


def dzis_dzien_artykulu(kiedy=None) -> bool:
    """Czy dzis (UTC) jest dzien artykulu wedlug harmonogramu presetu."""
    from datetime import datetime, timezone

    kiedy = kiedy or datetime.now(timezone.utc)
    dzien = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[kiedy.weekday()]
    return ARTYKULY_TYGODNIOWO > 0 and dzien in DNI_ARTYKULU


def zegar_agenta_on_calendar() -> list[str]:
    """Linie `OnCalendar=` zegara rutyny dnia, z harmonogramu presetu."""
    import konfiguracja as _k
    return _k.on_calendar_agenta(GODZINY_PRZEBIEGOW_UTC)


def zegar_artykulu_on_calendar() -> list[str]:
    """Linie `OnCalendar=` zegara artykulu; pusta lista, gdy artykulow nie ma."""
    import konfiguracja as _k
    return _k.on_calendar_artykulu(DNI_ARTYKULU, GODZINA_ARTYKULU_UTC, ARTYKULY_TYGODNIOWO)

# ILE CZASU MA PRZEBIEG. Musi zgadzac sie z `TimeoutStartSec` w pliku uslugi —
# to jedyne miejsce, gdzie ta sama liczba stoi dwa razy, i pilnuje tego test,
# bo rozjazd wychodzilby dopiero przy realnym przebiegu.
#
# 16 sierpnia systemd ubil przebieg po 2,5 h, bo mial do wystawienia szesnascie
# komentarzy przy odstepach 3-8 minut. Zabity SIGTERM-em proces nic nie zapisal,
# wiec wiersz wisial w bazie jako RUNNING do najblizszej kontroli zdrowia.
# Agent ma teraz konczyc SAM, zanim zegar go zetnie w polowie zdania.
# ILE RAZY PROBUJEMY WYSTAWIC GOTOWY ARTYKUL W JEDNYM PRZEBIEGU.
#
# ZMIERZONE 2 wrzesnia 2026 na odtworzeniu: przebieg z UDANA publikacja
# i przebieg z NIEUDANA zapisywaly sie w bazie IDENTYCZNIE — `DONE`, notatka
# pusta — a trzy nieudane z rzedu nie budzily alarmu ani razu. `wystaw_artykul`
# lapie kazdy wyjatek u siebie i oddaje slownik, a `_napisz_i_zapisz` konczylo
# BEZWARUNKOWYM `return 0`.
#
# Tekst jest juz napisany i oplacony (1,4-2,1 USD), a ponowienie kosztuje jedno
# wejscie przegladarka i ZERO dolarow. Podwojnej publikacji nie ma jak zrobic:
# `wystaw_artykul` zaczyna od `potwierdz_artykul` i przy tekscie, ktory jednak
# wyszedl, oddaje `pominiete=True`.
PROB_PUBLIKACJI_ARTYKULU = 3
PRZERWA_MIEDZY_PROBAMI_ARTYKULU_S = 120

# ILE RAZY RUTYNA DNIA PROBUJE DOWIEZC ZALEGLY ARTYKUL, zanim przestanie.
# Piec przebiegow dziennie razy dwanascie prob to dwa i pol dnia dobijania sie.
# TO NIE JEST BRAMKA: tekst zostaje na dysku, znacznik zostaje, alarm krzyczy.
# To jest tylko koniec petli, ktora dowiodla, ze nie dziala.
PROB_ZALEGLEGO_ARTYKULU = 12

LIMIT_CZASU_PRZEBIEGU_S = 9000
# Zapas na domkniecie: ostatnia publikacja, zamkniecie przebiegu, alarm.
ZAPAS_CZASU_S = 900

# Jaka czesc tematow skauta ma wychodzic z kanalow, ktore konto obserwuje.
#
# Decyzja wlasciciela z 30 sierpnia, po pomiarze: przed nia z kanalow
# pochodzilo PIEC tematow na dwadziescia (25%), a pozostale pietnascie z pamieci
# modelu. Pamiec dala niemal wylacznie historie sadowe — wszystkie osiem tematow
# artykulowych bylo pozwem, nakazem regulatora albo ugoda, ani jeden nie mowil o
# tym, co maszyna robi.
#
# Kanaly sa jedynym zrodlem, ktore mowi o RZECZY SAMEJ — o tym, co w tej
# dziedzinie sie buduje, mierzy i wycenia — a nie o sporach wokol niej. Kwota
# naprawia wiec dwie rzeczy naraz: aktualnosc i to, ze konto przestalo pisac
# o wlasnej niszy.
#
# PROG, NIE OBCIECIE. Ponizej progu mowimy glosno w logu i ustawiamy zakotwiczone
# na czele kolejki, ale nie kasujemy reszty: tydzien, w ktorym kanaly mowia samymi
# naglowkami, jest mozliwy i nie jest wina skauta.
SKAUT_UDZIAL_Z_KANALOW = 0.75

ROZBIEG_DNI = 30

# Odstepy miedzy dzialaniami, w sekundach. Pietnascie polubien w dziewiecdziesiat
# sekund to nie jest czytanie i kazdy system to widzi.
# Odstepy ROZNE dla roznych czynnosci, bo czlowiekowi roznie dlugo zajmuja.
# Jeden wspolny odstep 45-180 s dawal notke po notce w trzy minuty — a nikt tak
# nie publikuje. Polubienie co minute jest za to zupelnie naturalne.
#
# W sekundach, losowane w tych granicach osobno przy kazdym dzialaniu.
ODSTEPY = {
    # 45-90 MIN, nie 10-25. Zmierzone na profilu: notki wychodzily PARAMI
    # kilkanascie minut po sobie, potem cisza na trzy i pol godziny, i tak trzy
    # razy dziennie. To nie byl rytm czlowieka, tylko ksztalt PRZEBIEGU widoczny
    # na osi czasu: zegar budzil agenta, ten robil swoje dwie notki jedna po
    # drugiej i zasypial. Nikt nie musial analizowac stylu — wystarczylo
    # spojrzec na profil.
    #
    # Gorna granica jest przycieta do przebiegu: dwie notki po 90 minut mieszcza
    # sie w limicie czasu, trzy juz nie — i wtedy `zostal_czas` uczciwie konczy
    # dzien krocej, zamiast dac sie przeciac w polowie.
    # PRZYCIETE 30 sierpnia 2026 po policzeniu, dlaczego norma notek stala na
    # 57 procent przez pietnascie dni. Arytmetyka byla bezlitosna: budzet na
    # notki w przebiegu to 81 min, dwie notki przy odstepie 68 min potrzebuja
    # 76 min — a zwloka przed pierwsza notka zjadala srednio kolejne 20 min,
    # o czym planista nie wiedzial. 76 + 20 = 96 min przy budzecie 81, wiec
    # druga notka NIE MIALA PRAWA sie zmiescic. Trzy przebiegi po jednej notce
    # to 3 dziennie; zmierzona srednia wynosila 2,9.
    #
    # 35-65 min zamiast 45-90: dwie notki potrzebuja teraz 58 min i mieszcza sie
    # z zapasem, a rytm nadal nie jest rytmem maszyny — pol godziny do godziny
    # przerwy miedzy notkami czyta sie jak czlowiek wracajacy do tematu.
    "notka":      (2100, 3900),  # 35-65 min
    # CO NAJMNIEJ PIEC MINUT — decyzja wlasciciela z 30 sierpnia: „zeby nie
    # wygladal jak bot nakurwiajacy 10 komentarzy w 10 sekund". Dolna granica
    # byla 3 min i to za malo: przy serii komentarzy trzyminutowe odstepy widac
    # na osi czasu tak samo dobrze, jak sekundowe.
    "komentarz":  (300, 900),    #  5-15 min: przeczytac cudzy tekst i odpowiedziec
    # WYDLUZONE Z 2-7 NA 5-15 MIN, 30 sierpnia 2026 — z pomiaru, nie z ostroznosci.
    #
    # Odpowiedzi i komentarze pod NOTKAMI ida ta sama sciezka (`wystaw_odpowiedz`),
    # i to ona sie psula: komentarz pod postem przepadal w 7 procentach, pod notka
    # w 30, odpowiedz pod notka w 15. Rozbite na pozycje w serii wyszlo tak:
    #
    #     pierwsza akcja  39 prob   4 porazki   10%
    #     druga           16        5           31%
    #     trzecia          8        2           25%
    #     czwarta          4        2           50%
    #
    # Awaryjnosc potraja sie PO PIERWSZEJ AKCJI, przy odstepie srednio czterech
    # minut. Cel nie ma z tym nic wspolnego — to samo tempo. Sprawdzone osobno:
    # 0 z 7 zgubionych odpowiedzi wyladowalo gdziekolwiek na naszym profilu, wiec
    # nie chodzi o klikniecie w zly element, tylko o to, ze wysylka nie przechodzi.
    #
    # PROBKI SA MALE (16, 8, 4) i to trzeba pamietac: kierunek jest wyrazny,
    # dokladne liczby nie. Wracamy do pomiaru po tygodniu na nowym odstepie.
    "odpowiedz":  (300, 900),    #  5-15 min
    "lajk":       (30, 90),      # 0,5-1,5 min: przewijanie kanalu
    # Restack wymaga PRZECZYTANIA cudzej notki i napisania wlasnego zdania.
    # Kilkanascie sekund miedzy jednym a drugim znaczyloby, ze nie czytalismy
    # zadnej — a to widac na profilu tak samo, jak widac bylo notki parami.
    "restack":    (600, 1800),   # 10-30 min
}
ODSTEP_MIEDZY_DZIALANIAMI = (45, 180)   # zapas dla czynnosci bez wlasnego wpisu

# ZWLOKA PRZED PIERWSZA NOTKA PRZEBIEGU. Bez niej pierwsza notka wychodzila
# zawsze kilka minut po starcie zegara, wiec piec razy dziennie o tej samej
# porze co do kwadransa. Losowa zwloka rozmywa sam moment startu — godziny
# zostaja te, ktore wybralismy, ale minuty przestaja byc przewidywalne.
# PRZYCIETE 30 sierpnia 2026 z (0, 2400). Zwloka jest OZDOBNA — rozmywa moment
# startu — ale wydawana byla z tego samego budzetu, co notki, i planista o niej
# nie wiedzial: `zmiesci_sie` liczylo miejsce na dwie notki PRZED odespaniem
# sredniego kwadransa. Przy budzecie 81 min i dwoch notkach za 58 min zapas
# wynosi 23 min, wiec zwloka do 15 min go nie zjada, a nadal robi swoje.
ZWLOKA_PRZED_NOTKAMI = (0, 900)         # 0-15 min

# ILE CZASU PRZEBIEGU WOLNO ZJESC SAMYM NOTKOM.
#
# Rozdzielnik dzienny nie wiedzial nic o czasie: dzielil norme tak, jakby
# dzialania byly natychmiastowe. Po wydluzeniu odstepow do 45-90 minut wieczorna
# rutyna dostala CZTERY notki, czyli od trzech do szesciu godzin samego czekania
# przy budzecie dwoch godzin pietnastu minut. Po 2h17 miala jedna notke i spala,
# a do czternastu zaplanowanych komentarzy nie doszla wcale.
#
# Notki maja pierwszenstwo, bo sa rzadsze i wazniejsze — ale nie caly przebieg.
UDZIAL_CZASU_NA_NOTKI = 0.60

# Ile trwa samo dzialanie poza przerwa: napisanie, sprawdzenie faktow,
# wystawienie i potwierdzenie u zrodla. Z realnych przebiegow.
CZAS_DZIALANIA_S = 240
# USUNIETE 2026-08-20: MAX_DZIALAN_NA_GODZINE = 12 nie bylo egzekwowane nigdzie.
# Tempo wyznaczaja ODSTEPY miedzy dzialaniami i nic poza nimi. Nie dopisuje
# limitu godzinowego przy okazji audytu — nowy, nieprzetestowany ogranicznik
# w srodku przegladu to gorszy pomysl niz uczciwe przyznanie, ze go nie ma.

# USUNIETE 2026-08-20: MAX_KOMENTARZY_NA_PUBLIKACJE = 2 nie bylo egzekwowane
# przez ZADNA linie kodu. Sam powolalem sie na nie tego samego dnia jako na
# istniejace zabezpieczenie — i to jest cala szkoda, jaka robi martwa stala:
# czyta sie ja jak gwarancje, ktorej nie ma.
#
# Zabezpieczenie istnieje i jest OSTRZEJSZE: `_za_niedawno_u_nich` w kanal.py
# odsiewa publikacje, u ktorych komentowalismy w ostatnich
# ODSTEP_DNI_NA_PUBLIKACJE dniach — czyli raz na cztery dni, nie dwa razy
# dziennie.

# NIE KOMENTUJEMY SWIEZYCH POSTOW. Wlasciciel opisal to najlepiej: napisal notke
# i piec sekund pozniej ktos odpisal ogolnikowa zgoda — i to zdradza bota
# natychmiast, zanim ktokolwiek przeczyta tresc odpowiedzi. Czlowiek najpierw
# musi tekst ZOBACZYC i PRZECZYTAC.
#
# Losujemy prog dla kazdego posta osobno, w minutach.
MIN_WIEK_POSTA_MIN = (90, 900)      # od poltorej godziny do pietnastu

# NOTKA TO NIE ARTYKUL i zyje godziny, nie dni. Ten sam prog co dla artykulow
# oznaczal, ze pod notki wchodzilismy zawsze PO koncu rozmowy: przeglad pokazal
# dwa cele na przebieg, oba z zerem odpowiedzi, i trzy odrzucone jako za swieze.
# Nadal czekamy — bo odpowiedz piec sekund po notce zdradza automat, i to
# wlasciciel zauwazyl pierwszy — ale tyle, ile trwa przeczytanie, nie pol dnia.
MIN_WIEK_NOTKI_MIN = (20, 90)       # od dwudziestu minut do poltorej godziny

# ILU KOMENTARZY POD CELEM JESZCZE NIE UWAZAMY ZA TLOK. Wyszukiwarka oddawala
# posty ze srednio 45 komentarzami, jeden ze 126 — a komentarz sto dwudziesty
# siodmy jest niewidoczny. Swieze konto nie wygrywa glosnoscia, tylko byciem
# wczesnie tam, gdzie rozmowa dopiero sie zaczyna.
KOMFORTOWO_KOMENTARZY = 25

# Ile dni odstepu przed kolejnym komentarzem pod TA SAMA publikacja. Komentarz
# pod kazdym kolejnym tekstem tej samej osoby to drugi najczytelniejszy sygnal
# automatu — czlowiek nie czyta wszystkiego, co ktos wypuszcza.
ODSTEP_DNI_NA_PUBLIKACJE = 4

# HASLA, KTORYMI AGENT SZUKA NOWYCH KONT. Kanal czytelnika pokazuje tylko to,
# co juz znamy, wiec sam z siebie nie przyprowadzi nikogo nowego — a wlasnie
# o nowych ludzi chodzi. Wyszukiwarka Substacka oddaje konta spoza naszego kregu.
#
# DZIESIATY RAZ TA SAMA CHOROBA: ZOSTALOSC PO EPOCE PRZEDMIOTOW.
#
# Do 31 sierpnia 2026 wszystkie osiemnascie hasel opisywalo POPRZEDNIE pismo:
# „food labeling rules", „packaging regulation", „building codes regulation",
# „transport standards"... ANI JEDNO nie dotyczylo nowej niszy — piec dni po
# przestawieniu konta i po poprawieniu dwudziestu blokow w dziewieciu promptach,
# po wyczyszczeniu banku tematow i po zaostrzeniu reguly celow.
#
# SKUTEK BYL DOKLADNIE ODWROTNY DO WYGLADU. Agent szukal „przepisow
# o etykietowaniu zywnosci", dostawal posty o etykietowaniu zywnosci, po czym
# regula `cele.md` — poprawnie — odrzucala je wszystkie, bo byly poza nisza.
# W logu wygladalo to na wybrednosc modelu:
#     [cele] warte komentarza: 0/15
#     [cele] warte komentarza: 1/13
# a bylo szukaniem nie tego, czego trzeba. System nie zawodzil w znajdowaniu;
# szukal zlej rzeczy i poprawnie odrzucal to, co znalazl.
#
# Hasla opisuja teraz NASZ rewir: nisze i to, co ona zmienia w pracy, prawie,
# pieniadzach i zaufaniu. Nie sama technike — pod postem czysto technicznym nie
# mamy nic do dodania. Losujemy kilka przy kazdym przebiegu, zeby nie wracac
# ciagle do tej samej niszy.
# --- nisza: JEDNO ZRODLO PRAWDY O TYM, O CZYM JEST TO KONTO ------------------
# Do 2026-09-03 nisza nie miala w kodzie zadnej nazwy. Byla rozsypana po
# dwudziestu czterech haslach szukania, czterdziestu szesciu dziedzinach,
# czternastu promptach, czterech stalych systemowych — i po SZESCIU TESTACH,
# ktore mialy ja wpisana w cialo. Zmiana tematu oblewala wiec szesc testow
# z powodu, ktory nie mial nic wspolnego z kodem.
#
# NISZA jest zdaniem podawanym modelowi.
#
# ZNAKI_NISZY TO RUBRYKA, NIE FILTR. Stalo tu, ze sa to „slowa, po ktorych KOD
# rozpoznaje, ze cudzy post (...) nalezy do naszego rewiru" — i to samo mowily
# kreator oraz dwa pliki dokumentacji. Nieprawda: komplet czytelnikow tej
# stalej to `konfiguracja.py` (wczytanie), `narzedzia/audyt.py`,
# `narzedzia/kreator.py`, `tests/test_szukanie_celow.py` i dokumentacja.
# Zaden modul agenta nie odsiewa po niej ani jednego posta.
#
# Sluzy do JEDNEGO: sprawdzenia, czy HASLA_SZUKANIA trzymaja sie tematu,
# ktory operator sam opisal. Zlamanie tej spojnosci ma zmierzony skutek —
# agent szuka po haslach, dostaje posty, a `prompts/cele.md` odrzuca je co do
# jednego jako spoza rewiru; w logu wyglada to na wybrednosc modelu.
#
# O TYM, CZY KONKRETNY POST JEST „NA TEMAT", DECYDUJE MODEL wedlug
# `prompts/cele.md`. Przestawienie tej listy nie zmieni tego wyboru ani o krok;
# zmieni to, czy audyt i test spojnosci przechodza.
#
# Lista jest jawna i krotka celowo: ma sie dac przeczytac i zakwestionowac.
#
# SILNIK NIE MA TEMATU. Do 2026-09-05 stala tu nisza jednego konta z 22
# znakami rewiru — i byla „domyslna", czyli wlaczala sie po usunieciu
# konfiguracji (C1 audytu). Pusty napis znaczy dokladnie to, co mowi: brak
# tematu. Temat przychodzi z presetu (`temat.nisza`), a bez presetu `run.py`
# odmawia startu, wiec te pustki nie maja jak trafic do modelu.
NISZA = ""

ZNAKI_NISZY: tuple[str, ...] = ()

# Obszary, ktore rewir ma pokrywac. Dwadziescia hasel o tym samym daje te sama
# garstke kont, co trzy. Mapa obszarow nalezy do presetu tak samo jak hasla;
# silnik nie wie, jakie strony ma temat, ktorego nie zna.
OBSZARY_REWIRU: dict[str, tuple[str, ...]] = {}

# SLOWA, KTORE W TWOJEJ NISZY PADAJA W CO DRUGIM ZDANIU.
#
# `stages._slowa` wycina je przed porownywaniem tekstow, bo inaczej dwa
# dowolne fakty z tej samej dziedziny maja wspolne rdzenie, zanim ktokolwiek
# spojrzy na ich temat. Wykrywacz powtorek zglaszalby wtedy blizniaki, ktore
# nimi nie sa, a kazdy falszywy alarm kosztuje jedna notke.
#
# DO 2026-09-04 TA LISTA BYLA WPISANA W KOD i dostrojona do jednej niszy:
# „america", „american", „federal", „government", „national", „states",
# „united", „regulation", „standard". Konto o czym innym traci przez to
# dokladnie te rdzenie, ktore u niego ODROZNIAJA tematy — publikacja
# o polityce miejskiej przestalaby odrozniac notke o stanie od notki o rzadzie.
#
# Slowa funkcyjne angielszczyzny („that", „from", „with") zostaly w kodzie:
# sa te same w kazdej niszy i nie ma o czym decydowac.
#
# PUSTA LISTA JEST POPRAWNA ODPOWIEDZIA i tak zaczyna kazda instalacja: lepiej
# dopisac slowo, gdy sie zobaczylo, ze wywoluje trzeci falszywy alarm, niz
# zgadywac z gory.
#
# MYLI SIE PRZY TYM W OBIE STRONY I ZADNA NIE JEST GLOSNA.
#
# Za duzo slow: rdzenie odrozniajace tematy znikaja, wiec powtorka przechodzi
# jako nowy temat. Konto o polityce miejskiej, ktore wpisze tu „state"
# i „government", przestanie odrozniac notke o stanie od notki o rzadzie.
#
# Za malo slow — czyli takze przy pustej liscie, ktora jest domyslna: wspolne
# jest wszystko, co sie powtarza w SPOSOBIE PISANIA, nie w temacie. Zmierzone
# 2026-09-04 na `tests/test_indeks_kandydatow.py`: dwanascie faktow o zupelnie
# roznych rzeczach konczylo sie tym samym zwrotem, mialo przez to cztery
# wspolne rdzenie — a `stages._zderzenie` uznaje teksty za ten sam temat juz
# przy dwoch. Indeks oddawal po jednym kandydacie na przebieg zamiast po trzy.
#
# Odrzucony kandydat nie jest awaria i nigdzie nie zapala sie lampka. Jesli
# `[indeks] przyjete` regularnie mocno przewyzsza to, co da sie wyjac, to jest
# pierwsze miejsce do sprawdzenia.
PUSTE_SLOWA_NISZY: tuple[str, ...] = ()

# KAT REDAKCYJNY — czym to konto zajmuje sie W NISZY. Do 2026-09-03 stal
# wpisany w DZIEWIECIU promptach, w szesciu jako „what these systems actually
# do", czyli publikacja byla zamknieta na technologie niezaleznie od tego, co
# stalo w `NISZA`. Konto o pieczeniu chleba dostawalo brief o systemach.
#
# Zdanie jest doklejane po myslniku zaraz za nisza, wiec ma sie zaczynac mala
# litera i konczyc kropka. Pusty: kat redakcyjny jest decyzja presetu, nie
# silnika — „domyslny" kat byl linia jednego konta podawana kazdemu (C2 audytu).
KAT_REDAKCYJNY = ""

# --- PRZYKLADY Z NISZY, KTORE DO 2026-09-03 BYLY WPISANE W PROMPTY ----------
# `NISZA` przestawiala JEDNO ZDANIE na gorze promptu, a nizej ten sam prompt
# przez szescset linii argumentowal o poprzednim temacie: wymienial jego
# oklepane tezy, jego typowe urzadzenia, jego slynne sprawy. Konto przestawione
# na inna nisze dostawalo brief, ktory mowil „pisz o X" i zaraz potem
# „a oto czego NIE pisac o Y", z trzynastoma przykladami z Y.
#
# Dlatego przyklady wychodza z promptow do konfiguracji. Kazda lista jest
# OPCJONALNA: pusta znaczy „model ma wyprowadzic odpowiednik dla `NISZA` sam",
# co jest zawsze lepsze niz lista z cudzej dziedziny. Wypelnienie ich podnosi
# jakosc, bo model dostaje konkret zamiast polecenia.
#
# Sklad kazdej listy — po jednym zdaniu, bo trafiaja do promptu doslownie:
#   kanon        — tezy tak ograne, ze ich powtorzenie nie jest tematem
#   rzeczy       — co czytelnik z tej niszy widzial albo mial w rekach
#   seam         — miejsca, gdzie regula powstala PO tym, jak cos poszlo zle
#   przekonania  — przekonania szeroko wyznawane i nieprawdziwe
#   precedensy   — publiczne sprawdziany tej dziedziny, ktore cos zmienily
PRZYKLADY_NISZY: dict[str, tuple[str, ...]] = {
    "kanon": (),
    "rzeczy": (),
    "seam": (),
    "przekonania": (),
    "precedensy": (),
}

# PULA HASEL NALEZY DO PRESETU (`temat.hasla_szukania`). Stala tu pula
# jednego konta jako „przyklad do przestawienia" — i byla tym, czym agent
# szukal, gdy nikt jej nie przestawil. Wymogi strukturalne (pula szersza niz
# jeden przebieg, kazde haslo ze znakiem niszy) sprawdza `preset.sprawdz`
# przy podlaczaniu, a nie test na wartosciach silnika, ktorych juz nie ma.
HASLA_SZUKANIA: tuple[str, ...] = ()
# PIEC, NIE TRZY. Przy trzech haslach na przebieg i osiemnastu w puli agent
# ogladal jedna szosta rewiru na raz — a po zaostrzeniu reguly celow (tylko
# posty w niszy) waska pula zamieniala sie w zero kandydatow. Zmierzone 31 sierpnia:
# 13-17 obejrzanych, 0-3 warte komentarza, przy planie pietnastu.
ILE_HASEL_NA_PRZEBIEG = 5

# ILE RAZY SZUKAC CELOW W JEDNYM PRZEBIEGU, zanim odpuscimy.
#
# „Niech szuka, az znajdzie" bez ogranicznika znaczy „w nieskonczonosc", a kazda
# runda to jedno platne wywolanie oceny celow (~3 centy). Cztery rundy przy
# pieciu haslach kazda to dwadziescia hasel na przebieg — cala pula — wiec
# piata i tak nie miala by czego dolozyc.
#
# Petla konczy sie WCZESNIEJ, gdy wyszukiwarka przestaje oddawac nowe adresy
# albo gdy skonczy sie czas przebiegu. Ogranicznik jest sufitem, nie celem.
RUNDY_SZUKANIA_CELOW = 4

# Odpowiedzi POD WLASNYMI tresciami sa poza limitami dziennymi. Decyzja
# wlasciciela i jest sluszna: limit chroni przed wygladaniem na spamera u obcych,
# a u siebie jest sie gospodarzem. Pytanie bez odpowiedzi pod wlasnym artykulem
# szkodzi bardziej niz dziesiec komentarzy za duzo — czytelnik, ktory poswiecil
# czas i nie dostal odpowiedzi, nie wraca.
ODPOWIEDZI_POZA_LIMITEM = True

# Do ilu komentarzy odpowiadamy BEZ wybierania. Przy dwoch odpowiada sie obu.
# Przy dwustu odpowiedz pod kazdym wyglada jak maszyna — nawet gdy kazda jest
# dobra — wiec powyzej tego progu agent wybiera najwazniejsze, z pierwszenstwem
# dla niezgody: nieodpowiedziany zarzut zostaje ostatnim slowem.
# POLITYKA ZALEZNA OD SKALI, decyzja wlasciciela.
#
# Swieze konto zyje z rozmowy: ktos komentuje, my odpowiadamy, watek rosnie
# i algorytm to lubi. Przy pieciu komentarzach odpowiada sie WSZYSTKIM i to jest
# najtansza rzecz, jaka male konto moze zrobic dla swojego zasiegu.
#
# Przy pieciudziesieciu odpowiedz pod kazdym wyglada jak maszyna i przestaje byc
# rozmowa. Wtedy bierzemy te NAJBARDZIEJ ZYWE: najwiecej polubien i najwiecej
# odpowiedzi pod soba, bo tam siedzi dyskusja, ktora warto ciagnac.
ODPOWIADAJ_WSZYSTKIM_DO = 5      # male konto: kazdemu, bez wyjatku
WYBIERAJ_POWYZEJ = 20            # powyzej tego liczy sie juz popularnosc watku
MAX_ODPOWIEDZI_MALE = 6
MAX_ODPOWIEDZI_DUZE = 8


# Zapas na myślenie dostają WSZYSTKIE etapy, nie tylko Claude'owe: modele
# DeepSeek v4 też rozumują, a tokeny rozumowania liczą się do sufitu wyjścia.
# Odsiew ucięło na 2057 tokenach dokładnie z tego powodu.
MAX_TOKENS = {
    purpose: ceiling + THINKING_HEADROOM_TOKENS
    for purpose, ceiling in MAX_TOKENS.items()
}

# --- terminy -----------------------------------------------------------------
# Termin musi pokryć własny sufit tokenów. Zmierzone: mediana 16,08 ms na token
# wyjściowy (19 rozliczonych przebiegów, R² 0,98). Poprzedni agent ustawił 60 s
# przy suficie 4096 tokenów, co jest arytmetycznie niemożliwe (65,9 s potrzebne).

MS_PER_OUTPUT_TOKEN = 16.08
TIMEOUT_MARGIN = 1.5


# Twardy sufit na JEDNO wywolanie. Bez niego wyliczenie z sufitu tokenow dawalo
# 965 sekund, a przy wyszukiwaniu razy trzy — 48 MINUT. Jedno zawieszone
# wywolanie blokowaloby caly dzien, a systemd ubilby przebieg po godzinie
# w polowie roboty, zostawiajac dzien zrobiony do polowy.
MAX_TIMEOUT_S = 300


def timeout_for(max_tokens: int) -> float:
    """Termin w sekundach, który realnie pokrywa podany sufit tokenów.

    Ograniczony twardo: wyliczenie z sufitu dawało 965 sekund, a przy
    wyszukiwaniu razy trzy — 48 minut na JEDNO wywołanie. Jedno zawieszenie
    blokowałoby cały dzień, a `systemd` ubiłby przebieg po godzinie w połowie
    roboty. Lepiej stracić jedną notkę niż resztę dnia.
    """
    return min(round(max_tokens * MS_PER_OUTPUT_TOKEN / 1000 * TIMEOUT_MARGIN, 1),
               MAX_TIMEOUT_S)


# --- pobieranie --------------------------------------------------------------
# Odpowiedź 200 bywa nie dokumentem, tylko wyzwaniem. Te frazy złapały trzy realne
# odmowy przy pierwszym przebiegu starego agenta. Blokadę wykrywamy i zapisujemy
# jako nieudane pobranie — NIGDY jej nie omijamy.

REFUSAL_PHRASES = (
    "you have been blocked",
    "access denied",
    "are you a robot",
    "verify you are human",
    "enable javascript and cookies",
    "unusual traffic",
    "captcha",
    "request has been flagged",
    "programmatic access to these sites is limited",
)

FETCH_TIMEOUT_S = 30.0

# ODSTEP MIEDZY POBRANIAMI Z TEGO SAMEGO HOSTA.
#
# Dotyczy WYLACZNIE powtorzonego hosta — rozne serwisy nie czekaja na siebie,
# bo to jedno zadanie na serwis i nikomu nie szkodzi.
#
# Powod jest zapisany we wlasnej liscie ponowien: sa na niej `HTTP 429`
# i `HTTP 503`, czyli „za duzo zadan". Naprawiono objaw (ponow po chwili),
# nie przyczyne — a ponowienie po blokadzie to kolejne zadanie do serwisu,
# ktory wlasnie powiedzial „przestan".
#
# Skala ryzyka: `DISCOVERY_MAX_RESULTS` to dziesiec zrodel na runde
# i dwadziescia z druga, a nic nie ogranicza, ile z nich pochodzi z jednego
# urzedu. Bez odstepu szlo to jedno po drugim, w kilka sekund.
#
# Dwie sekundy to nie jest pomiar, tylko OSTROZNOSC: dolna granica tego, co
# powszechnie uchodzi za grzeczne. Kosztuje sekundy w przebiegu, ktory i tak
# trwa minuty.
ODSTEP_TEN_SAM_HOST_S = 2.0
# ILE ZNAKOW MUSI ODDAC STRONA, ZEBY LICZYC SIE JAKO ZRODLO.
#
# Bylo 400 i to bylo za malo w sposob, ktory widac dopiero na przebiegu.
# Zmierzone 25 sierpnia 2026 na jednym artykule, dziewiec zrodel — pokazuje
# tylko RZEDY WIELKOSCI, bo o nie tu chodzi:
#
#     duza organizacja pozarzadowa    146038 znakow   12 fragmentow   2 liczby
#     druga taka                       81669           11             10
#     repozytorium uczelniane           7891
#     serwis partii politycznej         3275
#     urzad ochrony danych               716            3              0
#     drugie repozytorium                483            2              0
#
# Obie strony ponizej tysiaca znakow oddaly ZERO liczb, a mimo to weszly do
# bilansu jako pelnoprawne zrodla pierwotne — jedna z nich dostala nawet
# trafnosc 0.80. To sa banery zgody i strony tytulowe repozytoriow, z ktorych
# klasyfikator wyciaga "fragmenty" ze stopki.
#
# Prog 1500 lezy w przerwie: odrzuca obie zajawki, przepuszcza najmniejsze
# realne zrodlo z tego przebiegu (3275). Nie stawiam go wyzej, bo krotkie
# dokumenty urzedowe — zawiadomienie, postanowienie, nota — bywaja prawdziwe.
FETCH_MIN_CHARS = 1500
# NAGLOWEK, KTORY WIDZI KAZDA ODWIEDZONA STRONA — i jedyne miejsce, w ktorym
# bot przedstawia sie z nazwy. Skladany z `NAZWA_MARKI`, nie wpisany: stala
# z wpisana nazwa marki jest dokladnie tym, co przy zmianie konta zostaje
# w kodzie i przedstawia nowa publikacje nazwiskiem poprzedniej.
#
# Zbijamy spacje i znaki spoza ASCII, bo naglowek HTTP musi byc jednym
# tokenem — nazwa marki bywa wielowyrazowa i z polskimi znakami.
def _znacznik_klienta(marka: str) -> str:
    import re as _re
    czyste = _re.sub(r"[^A-Za-z0-9]+", "", (marka or "").strip())
    return czyste or "EditorialBot"


# --- JEDNOSTKI SYSTEMD ------------------------------------------------------
#
# NAZWA JEDNOSTKI NALEZY DO INSTALACJI, nie do bota: kto postawi go pod wlasna
# marka, nazwie pliki inaczej (`narzedzia/jednostki.py` buduje je z szablonow).
# Kod, ktory podaje nazwe z pamieci, wypisuje wtedy rade, ktora po wklejeniu
# nie zadziala — a rada nieaktualna w mailu alarmowym uczy, ze maile alarmowe
# sa nieaktualne.
#
# JEDNO MIEJSCE, BO INACZEJ ZARAZ BEDA DWA. `norma.py` szukalo zegara wlasnym
# kodem, `alarm.py` mial nazwe wpisana w tresc maila; obie potrzeby sa tej
# samej wielkosci co cztery kopie daty przestawienia konta.
# --- PLIKI, KTORE MA CZYTAC TYLKO WLASCICIEL --------------------------------
#
# Dwa pliki w `data/` niosa cudze albo krytyczne dane: kopia listy subskrybentow
# (cudze adresy e-mail) i `storage-state.json` (ciastko sesji, czyli prawo do
# publikowania jako to konto). Domyslne prawa na serwerze to 0644 albo 0664 —
# czytelne dla KAZDEGO konta na maszynie.
#
# W calym repozytorium byl DOKLADNIE JEDEN `chmod`, przy kopii subskrybentow,
# i to LINIJKE PO zapisaniu pliku — czyli po otwarciu okna, w ktorym plik jest
# czytelny dla wszystkich. Sesja przegladarki nie miala go wcale.
_BEZ_PRAW_POWIEDZIANE = False


def tylko_dla_wlasciciela(sciezka) -> None:
    """Prawa 0600 na tym pliku — a gdzie sie nie da, MOWI o tym raz.

    Windows nie ma praw POSIX i to nie jest powod, zeby stracic plik, wiec
    bledu nie podnosimy. Ale CISZA byla tu wada.

    `SECURITY.md` twierdzil bezwarunkowo, ze ciastko sesji i eksporty
    subskrybentow sa pisane `0600`, „czytelne tylko dla konta, ktore je
    posiada". Zmierzone na Windowsie: `storage-state.json` ma `0666`. Zdanie
    bylo prawdziwe na serwerze i falszywe na maszynie, na ktorej ktos wlasnie
    zaklada sesje — a to jest ten plik, ktory daje PELNA WLADZE nad kontem.

    Zabezpieczenie, ktore milczy, gdy go nie ma, jest gorsze od jego braku:
    operator czyta dokumentacje i uwaza, ze jest chroniony. Mowimy wiec RAZ NA
    PROCES, zeby nie zagluszyc reszty logu.
    """
    try:
        _os.chmod(str(sciezka), 0o600)
    except OSError:
        pass
    global _BEZ_PRAW_POWIEDZIANE
    if _os.name == "nt" and not _BEZ_PRAW_POWIEDZIANE:
        _BEZ_PRAW_POWIEDZIANE = True
        print("  ! PRAWA 0600 NIE DZIALAJA NA WINDOWSIE. Pliki z sekretami"
              " (ciastko sesji, eksporty subskrybentow) sa czytelne dla kazdego"
              " konta na tej maszynie. Na serwerze POSIX dzialaja normalnie;"
              " tutaj chroni je tylko konto systemowe i szyfrowanie dysku.",
              flush=True)


def otworz_tylko_dla_wlasciciela(sciezka, tryb: str = "w"):
    """Otwiera plik do zapisu TWORZAC GO od razu z prawami 0600.

    `write_text` tworzy plik z prawami domyslnymi i dopiero potem mozna je
    zwezic — miedzy jednym a drugim istnieje okno, w ktorym cudze adresy
    e-mail sa czytelne dla kazdego konta na maszynie. Tutaj okna nie ma:
    `os.open` dostaje prawa przy TWORZENIU.
    """
    flagi = _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC
    if hasattr(_os, "O_BINARY") and "b" in tryb:
        flagi |= _os.O_BINARY
    fd = _os.open(str(sciezka), flagi, 0o600)
    # Na plikach juz istniejacych `os.open` praw NIE zmienia — stad drugi krok.
    tylko_dla_wlasciciela(sciezka)
    return _os.fdopen(fd, tryb, encoding=None if "b" in tryb else "utf-8",
                      newline=None if "b" in tryb else "")


# --- STAN DZIEDZINY: CO JEST AKTUALNE DZISIAJ -------------------------------
#
# Model nie ma jak zauwazyc, ze fakt sie przeterminowal: jego wiedza konczy sie
# kilka miesiecy temu, a nieaktualny fakt czyta sie od srodka dokladnie tak samo
# jak biezacy. Jedyne wyjscie to PYTAC SWIATA, nie siebie — `aktualne_modele.py`
# robi to raz na dobe, z wyszukiwaniem, i wynik idzie do promptu.
#
# PYTANIE BYLO WPISANE I DOTYCZYLO WYLACZNIE MODELI JEZYKOWYCH, z nazwami
# osmiu laboratoriow w tresci. Konto o dowolnej innej dziedzinie placilo wiec
# codziennie za liste modeli AI i dostawalo ja do promptu jako „stan swojej
# dziedziny". Mechanizm jest ogolny, pytanie nie bylo.
#
# PUSTE PYTANIE ZNACZY „ZBUDUJ Z NISZY" — patrz `pytanie_o_stan_dziedziny()`.
STAN_DZIEDZINY_PYTAJ = True
STAN_DZIEDZINY_PYTANIE = ""


def pytanie_o_stan_dziedziny() -> str:
    """O co pytamy, sprawdzajac stan dziedziny.

    Wlasne pytanie z konfiguracji, a gdy go nie ma — zbudowane z `NISZA`.
    Domyslne jest celowo szerokie: w kazdej dziedzinie sa rzeczy, ktore
    wchodza, wychodza i zmieniaja nazwe, i to o nie chodzi.
    """
    wlasne = (STAN_DZIEDZINY_PYTANIE or "").strip()
    if wlasne:
        return wlasne
    return ("what is CURRENT right now in %s: what has recently appeared, what "
            "has changed name, version or price, and what has been withdrawn, "
            "discontinued or scheduled to end" % (NISZA or "this field"))


# --- KANALY YOUTUBE, KTORE ROBIA DOBOR TEMATOW W TEJ NISZY -------------------
#
# Identyfikatory kanalow (`UC...`), ktore od lat wybieraja, o czym w tej
# dziedzinie warto mowic. `korpus_kanalow` czyta z nich RSS i szuka rzeczy,
# o ktorych mowi NARAZ kilka roznych kanalow — to jest jedyny sygnal
# „wielkiego wydarzenia", ktory liczy KOD, a nie model.
#
# PUSTY SLOWNIK NIE ZABIJA PRZEBIEGU: `stages.zaczyn_z_kanalow` oddaje wtedy
# jawne „(nothing fetched today)", a prompt radzi sobie sama siatka dziedzin.
#
# BYLO WPISANE W `korpus_kanalow.KANALY`, a `konfiguracja.POLA` mialo pole
# `zrodla.kanaly_youtube` z adnotacja „obsluzone osobno w `zastosuj`" —
# i `zastosuj` tego pola NIE OBSLUGIWALO. Konfigurator pytal, operator
# odpowiadal, wartosc szla do pliku, przechodzila sprawdzenie i byla cicho
# wyrzucana. Caly korpus kanalow byl przez to martwy u kazdego operatora
# i nie dalo sie go wlaczyc.
#
# JAK ZDOBYC IDENTYFIKATOR: `youtube.com/@uchwyt` przekierowuje na sciane
# zgody i nie oddaje niczego; oEmbed dziala tylko dla FILMOW. Dziala zapytanie
# HTTP z ciasteczkiem `CONSENT=YES+cb...` i `SOCS=CAI`, a potem szukanie
# `"externalId":"(UC...)"` w HTML. Sam kanal RSS zgody NIE wymaga.
KANALY_YOUTUBE: dict[str, str] = {}

# KANALY RSS/ATOM — blogi laboratoriow, listy publikacji, serwisy. Ta sama
# rola co kanaly YouTube: ZACZYN tematow (co sie dzieje w tym tygodniu), nigdy
# zrodlo. `korpus_kanalow` czyta oba rodzaje i sklada w jeden korpus, po
# rowno ze zrodel — inaczej lista publikacji o piecdziesieciu wpisach
# dziennie zaglusza dziesiec kanalow wideo. Nazwa -> adres kanalu.
KANALY_RSS: dict[str, str] = {}

# HOSTY, NA KTORYCH LEZA DOKUMENTY PIERWOTNE TEJ DZIEDZINY — podpowiedz dla
# dyskoverii („szukaj najpierw tu"), nie filtr. Preset publikacji o nauce
# wskaze archiwum preprintow i strony laboratoriow; publikacja o przepisach
# wskaze rejestry urzedowe. Pusta krotka znaczy „bez podpowiedzi".
DOMENY_PREFEROWANE: tuple[str, ...] = ()


# --- SEKCJA ZRODEL POD ARTYKULEM --------------------------------------------
#
# Naglowek pisze KOD (`stages.save` i sciezka ratunku), a potem rozdziela po nim
# tresc od odnosnikow WSZYSTKO, co mierzy artykul: akapity dla bramek formy,
# zdania z liczba, glebokosc akapitu w tekscie, dlugosci w audycie, a takze
# `browser` szukajacy naglowka w edytorze.
#
# BYL WPISANY W OSMIU MIEJSCACH. Gdy jedno przestanie pasowac — a wystarczy
# zmiana `ARTICLE_LANGUAGE`, ktora JEST polem konfiguracji — pomiary po cichu
# zaczynaja liczyc takze liste odnosnikow: same adresy i liczby. Bramka liczb
# dostaje wtedy cyfry z URL-i, akapitow przybywa o cala liste, a „ostatnia
# trzecia tekstu" przesuwa sie o dlugosc sekcji zrodel. Zaden z osmiu
# fragmentow nie wyglada przy tym na zepsuty.
#
# TYTUL OSOBNO OD NAGLOWKA, bo `browser` szuka w edytorze samego tytulu
# (element `h2` z tekstem), a nie linii markdownu.
TYTUL_SEKCJI_ZRODEL = "Sources"
NAGLOWEK_ZRODEL = "## " + TYTUL_SEKCJI_ZRODEL


KATALOG_JEDNOSTEK = AGENT_DIR / "systemd"


def usluga_agenta() -> str:
    """Nazwa pliku uslugi, ktora uruchamia dzien agenta — po TRESCI, nie nazwie.

    Pytamy o to, CO JEDNOSTKA URUCHAMIA: usluga agenta to ta, ktorej
    `ExecStart` wola `run.py`. Gdy nie da sie tego rozstrzygnac, oddajemy pusty
    napis, a wolajacy ma powiedziec „sprawdz jednostke agenta" zamiast podac
    zla nazwe.
    """
    try:
        pliki = sorted(KATALOG_JEDNOSTEK.glob("*.service"))
    except OSError:
        return ""
    for p in pliki:
        try:
            tresc = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for linia in tresc.splitlines():
            if linia.startswith("ExecStart=") and "run.py" in linia:
                return p.name
    return ""


def zegar_agenta():
    """Sciezka do jednostki zegara agenta albo None."""
    nazwa = usluga_agenta()
    if not nazwa:
        return None
    zegar = KATALOG_JEDNOSTEK / (nazwa[: -len(".service")] + ".timer")
    return zegar if zegar.exists() else None


def _naglowek_klienta() -> str:
    """Naglowek User-Agent zlozony z BIEZACEJ nazwy marki.

    Wolany PO wczytaniu konfiguracji — patrz koniec tego pliku. Stala
    policzona tutaj trzymalaby nazwe domyslna, bo `konfiguracja.toml`
    wchodzi piecset linii nizej.
    """
    return ("Mozilla/5.0 (compatible; %s/1.0; +editorial research)"
            % _znacznik_klienta(NAZWA_MARKI))


# Wartosc domyslna; przeliczana po wczytaniu konfiguracji.
FETCH_USER_AGENT = _naglowek_klienta()

# --- zapora przed platnym wywolaniem z testu ---------------------------------
# `tests/conftest.py` chroni przed platnymi testami TYLKO POD PYTESTEM. A nasze
# darmowe testy chodza petla po plikach (`tests/URUCHOM.md`):
#
#     for t in agent-v2/tests/test_*.py; do python "$t"; done
#
# W tej petli conftest NIE WYKONUJE SIE WCALE. Test, ktory zapomni podstawic
# atrape pod `llm.call`, siega wiec po prawdziwy klucz z `.env` i placi — a
# jedynym sladem jest wiersz w tabeli `calls`, ktorego nikt nie oglada. To jest
# ta sama klasa bledu co „ostrzezenie w dokumencie nie jest bramka", opisana
# w samym conftescie.
#
# Rozpoznajemy po SCIEZCE URUCHOMIONEGO PROGRAMU, a nie po zmiennej srodowiskowej,
# bo zmienna trzeba pamietac, a sciezka jest faktem. Testy platne leza w
# `tests/platne/` i maja placic — te przechodza.
def _w_darmowym_tescie() -> bool:
    """Czy uruchomiony program to test, ktory NIE MA prawa placic."""
    import sys as _sys
    try:
        sciezka = Path(_sys.argv[0]).resolve()
    except Exception:
        return False
    czesci = [c.lower() for c in sciezka.parts]
    return "tests" in czesci and "platne" not in czesci


# Jedna nazwa, dwie zapory. Wykrywanie sluzy juz nie tylko pieniadzom: darmowy
# test nie ma tez prawa DOPISYWAC DO PRODUKCYJNYCH DANYCH.
#
# Zmierzone 2 wrzesnia 2026 na serwerze: `agent-v2/data/tematy_przegrane.json`
# mial 400 wpisow (czyli sufit `ILE_PRZEGRANYCH_TRZYMAMY`), z czego 294 to byly
# ATRAPY Z TESTOW — „A", „B", „Example Article Seven" i trzy inne, po
# 49 sztuk kazda. `test_wybor_tematu.py` wola `stages.pick_topic`, ta wola
# `zapisz_przegranych`, a sciezka byla liczona z `config.DATA_DIR`. Kazde
# uruchomienie zestawu na serwerze wypychalo z bufora prawdziwe przegrane
# tematy. Odcisk calego katalogu przed i po pokazal, ze to JEDYNY taki plik na
# 68 — ale jeden wystarczy, zeby dziennik diagnostyczny przestal cokolwiek
# znaczyc.
W_TESCIE = _w_darmowym_tescie()

# Test platny albo swiadomy skrypt moze to podniesc: `config.WOLNO_WOLAC_MODEL = True`.
WOLNO_WOLAC_MODEL = not W_TESCIE

# Trzecia zapora tej samej rodziny: darmowy test nie ma prawa OTWORZYC
# produkcyjnej bazy. Patrz `uzyj_katalogu_danych` i `db.connect`.
WOLNO_TKNAC_PRODUKCYJNA_BAZE = not W_TESCIE


# --- jedno przekierowanie zamiast dwudziestu recznych ------------------------
# CO BYLO ZLE. `DB_PATH` jest liczone RAZ, przy imporcie, z `DATA_DIR`. Test,
# ktory podstawia `config.DATA_DIR = katalog_tymczasowy`, NIE zmienia przez to
# `config.DB_PATH` — ta nadal celuje w produkcyjna baze. Zmierzone 2 wrzesnia
# 2026 na tym repozytorium: 21 plikow testowych przestawialo `DATA_DIR`, a tylko
# 4 przestawialy takze `DB_PATH`.
#
# I NIE CHODZI TYLKO O BAZE. Stalych liczonych przy imporcie z `DATA_DIR` jest
# w tym kodzie 25 poza `config.py` — jedenascie w `stages.py`, siedem
# w `browser.py`, reszta w `alarm.py`, `norma.py`, `kanal.py`, `run.py`,
# `aktualne_modele.py` i `kopia_subskrybentow.py`. Kazda z nich to ta sama
# pulapka co `DB_PATH`: przestawienie `DATA_DIR` po imporcie nie rusza zadnej.
# Dokladnie tedy weszly atrapy do `tematy_przegrane.json`
# (`stages.PRZEGRANE_TEMATY`).
#
# DLATEGO NIE MA TU LISTY NAZW. Lista wymaga pamietania o dopisaniu do niej, a
# ten projekt ma udokumentowane, ze proba w dokumencie nie jest bramka.
# Zamiast tego przechodzimy po JUZ ZAIMPORTOWANYCH modulach projektu i
# przestawiamy KAZDA sciezke lezaca pod starym katalogiem danych. Nowa stala
# pochodna dopisana jutro w `stages.py` przeniesie sie sama, bez zmiany tutaj.


def pod_produkcyjnymi_danymi(sciezka) -> bool:
    """Czy ta sciezka lezy w PRAWDZIWYM katalogu danych (takze w podkatalogu).

    Swiadomie szerzej niz `stages._pisze_do_produkcji`, ktore porownuje samego
    rodzica: baza moglaby zostac przeniesiona do podkatalogu i zapora
    przestalaby ja widziec, nie mowiac o tym ani slowa.
    """
    try:
        s = Path(sciezka).resolve()
    except Exception:
        return False
    korzen = Path(PRODUKCYJNY_KATALOG_DANYCH).resolve()
    return s == korzen or korzen in s.parents


def _moduly_projektu():
    """Zaimportowane moduly z `agent-v2/`, bez samych testow."""
    import sys as _sys

    korzen = AGENT_DIR.resolve()
    testy = (korzen / "tests").resolve()
    for modul in list(_sys.modules.values()):
        plik = getattr(modul, "__file__", None)
        if not plik:
            continue
        try:
            p = Path(plik).resolve()
        except Exception:
            continue
        if korzen not in p.parents:
            continue
        if testy == p.parent or testy in p.parents:
            continue
        yield modul


def uzyj_katalogu_danych(katalog, utworz: bool = True):
    """Przestawia `DATA_DIR` I KOMPLET sciezek z niego policzonych.

    Jedyna poprawna droga do podstawienia katalogu danych w tescie. Oddaje
    zdjecie poprzednich wartosci — podaj je `przywroc_katalog_danych`, zeby
    cofnac zmiane w `finally`.

        stare = config.uzyj_katalogu_danych(kat)
        try:
            ...
        finally:
            config.przywroc_katalog_danych(stare)

    `utworz=False` dla testow, ktore sprawdzaja zachowanie przy BRAKUJACYM
    katalogu danych — inaczej samo przekierowanie tworzylo by katalog i test
    mierzylby cos innego, niz mysli.

    Rusza trzy rzeczy: stale w `config`, sciezki-atrybuty w zaimportowanych
    modulach projektu i nic wiecej. Sciezki spoza katalogu danych (`PROMPTS_DIR`,
    `STYLE_CORPUS`, `ENV_PATH`) zostaja nietkniete celowo — nie sa danymi konta.
    """
    global DATA_DIR, DB_PATH, ARTICLES_DIR

    nowy = Path(katalog).resolve()
    if utworz:
        nowy.mkdir(parents=True, exist_ok=True)
    stary = Path(DATA_DIR).resolve()

    def przeniesiona(wartosc):
        """Ta sama sciezka wzgledem NOWEGO katalogu — albo None, gdy nie nasza."""
        try:
            p = Path(wartosc).resolve()
        except Exception:
            return None
        if p == stary:
            return nowy
        if stary in p.parents:
            return nowy / p.relative_to(stary)
        return None

    zdjecie = {"__config__": {}, "__moduly__": []}

    for nazwa in ("DATA_DIR", "DB_PATH", "ARTICLES_DIR"):
        zdjecie["__config__"][nazwa] = globals()[nazwa]
    DATA_DIR = nowy
    DB_PATH = przeniesiona(zdjecie["__config__"]["DB_PATH"]) or (nowy / "agent-v2.db")
    ARTICLES_DIR = przeniesiona(zdjecie["__config__"]["ARTICLES_DIR"]) or (nowy / "articles")

    for modul in _moduly_projektu():
        if modul.__name__ == "config":
            continue
        for nazwa, wartosc in list(vars(modul).items()):
            if not isinstance(wartosc, Path):
                continue
            cel = przeniesiona(wartosc)
            if cel is None:
                continue
            zdjecie["__moduly__"].append((modul, nazwa, wartosc))
            setattr(modul, nazwa, cel)

    return zdjecie


def przywroc_katalog_danych(zdjecie) -> None:
    """Cofa `uzyj_katalogu_danych`. Bez tego nastepny test dziedziczy podmiane."""
    global DATA_DIR, DB_PATH, ARTICLES_DIR

    if not zdjecie:
        return
    for modul, nazwa, wartosc in zdjecie.get("__moduly__", []):
        setattr(modul, nazwa, wartosc)
    stale = zdjecie.get("__config__", {})
    if "DATA_DIR" in stale:
        DATA_DIR = stale["DATA_DIR"]
    if "DB_PATH" in stale:
        DB_PATH = stale["DB_PATH"]
    if "ARTICLES_DIR" in stale:
        ARTICLES_DIR = stale["ARTICLES_DIR"]


# --- naprawa zamiast blokady i zamiast ciecia --------------------------------
# 1 wrzesnia 2026 o 19:46 poszla notka z liczba, ktora nasze wlasne sprawdzenie
# faktow obalilo PRZED wysylka. W logu stalo „! OBALONE: <twierdzenie
# obalone przez zrodlo>", notka i tak wyszla, a rachunek z jej wlasnych
# liczb dawal wynik trzy razy inny niz podany. Notka typu SPROSTOWANIE i formy LICZBA
# opublikowala zla liczbe.
#
# Byly do wyboru trzy drogi i dwie sa zamkniete decyzja wlasciciela: BLOKADA
# (notka nie wychodzi — nic nie ma czekac na czlowieka) oraz CIECIE (zdanie
# znika — nic nie ma byc wycinane). Zostaje trzecia: NAPRAWIC. Model dostaje
# wlasny tekst, zarzut i material dowodowy, i oddaje to samo zdanie prawdziwe.
#
# NAPRAWIAMY WYLACZNIE TO, CZEMU ZAPIS PRZECZY — `refuted` i `outdated`. NIE
# naprawiamy `unverified`, i to jest najwazniejsza granica w tym bloku:
# „nie znalazlem potwierdzenia" nie daje modelowi zadnego materialu, wiec
# polecenie „popraw to" jest zaproszeniem do WYMYSLENIA liczby, ktora przejdzie.
# Naprawa bez dowodu produkuje falsz pewniejszy siebie niz ten, ktory naprawia.
# `unverified` zostaje wiec tym, czym byl: linia w logu.
NAPRAWA_OBALONYCH = True

# Ile napraw najwyzej w jednym przebiegu. Kazda to dwa platne wywolania
# (przepisanie plus PONOWNE sprawdzenie), wiec bez sufitu zly dzien potrafi
# dolozyc do rachunku wiecej niz caly etap, ktory naprawia.
NAPRAW_NA_PRZEBIEG = 4

# --- bramki jakości ----------------------------------------------------------
# NIC NIE BLOKUJE. Bramki są zgłaszane właścicielowi jako uwagi do przeczytania;
# artykuł powstaje zawsze i trafia do szuflady. („Te cztery" stało tu do
# 1 września 2026 i przeczyło zdaniu trzy wiersze niżej: bramek jest trzynaście
# deterministycznych i cztery obserwacyjne.)

# USUNIETA 2026-08-20 lista FLAGGED_GATES. Wymieniala CZTERY bramki, nie byla
# przez nic czytana, a bramek jest dzis trzynascie deterministycznych i cztery
# obserwacyjne. Nieaktualna lista, ktorej nikt nie uzywa, jest gorsza niz jej
# brak: opisuje system, ktory przestal istniec. Zrodlem prawdy jest
# `gates.deterministic_floors`.

# Jedno podejście. Bez przepisywania — to tam paliły się pieniądze i tam dwie
# bramki starego agenta odpowiedziały różnie na to samo pytanie. Zasada zostaje,
# stala ATTEMPTS = 1 usunieta 2026-08-20: nic nie petlilo, wiec nie bylo czego
# ograniczac, a liczba sugerowala mechanizm, ktorego nie ma.


# --- ruch koncowy i szerokosc drugiego aktu --------------------------------
# Dwa artykuly napisane zaraz PO poprzedniej poprawce (jeden "Example Article
# Ten", drugi "Example Article Eleven") wyszly z identycznym szkieletem: ten sam
# drogowskaz przed paralelami ("once you see this shape, it turns up
# everywhere"), dokladnie trzy paralele, akapit o granicach zapowiedziany
# meta-zdaniem, zamkniecie "sprawdz to u siebie". Zaden z tych ruchow nie jest
# bledem osobno; bledem jest to, ze wypadaja za kazdym razem tak samo, bo
# pisarz.md je zamowil. Powtarzalna FORMA jest sygnalem maszyny dokladnie tak
# samo jak powtarzana TRESC. Wiec losujemy — tak jak przy notkach z NOTE_FORM.
RUCHY_KONCOWE = {
    "DO_SPRAWDZENIA": (
        "Close by handing the reader something observable in their own life — "
        "a thing to look at, count or compare, where the mechanism will show "
        "through. Do not promise what they will find."
    ),
    "GDZIE_KONCZY_SIE_ZAPIS": (
        "Close on the boundary of what is documented: name the one question "
        "the record does not answer and say plainly why nobody answering it "
        "publicly is a fact about the arrangement, not an accident."
    ),
    "KTO_NA_TYM_STOI": (
        "Close on the party the arrangement serves. Not an accusation — just "
        "the plain sentence naming who carries the cost and who is spared it, "
        "left standing without commentary."
    ),
    "GDYBY_INACZEJ": (
        "Close by describing the version of this that could have been built "
        "instead, and what it would have cost whom. Make the current design "
        "visible as a choice by putting one alternative next to it."
    ),
    "POWROT_DO_ZACZEPU": (
        "Close by returning to the exact image or belief you opened with and "
        "showing it changed — same object, different thing to look at now. No "
        "summary of the argument in between."
    ),
    "CENA_MECHANIZMU": (
        "Close on what this costs when it fails or when it is applied to "
        "someone it was not designed for. One case, concrete, then stop."
    ),
}

RUCH_KONCOWY_MIX = ("DO_SPRAWDZENIA", "KTO_NA_TYM_STOI", "POWROT_DO_ZACZEPU",
                    "GDZIE_KONCZY_SIE_ZAPIS", "CENA_MECHANIZMU", "GDYBY_INACZEJ")

# Ile paraleli w drugim akcie. Trzy wyliczone po kolei czytaja sie jak lista;
# jedna rozwinieta na dwa akapity czyta sie jak mysl. Chcemy obu, na zmiane.
ILE_PARALELI_WAGI = {1: 4, 2: 4, 3: 3}

OPIS_LICZBY_PARALELI = {
    # ZERO BYLO NIEWYRAZALNE. Slownik zaczynal sie od jedynki, a wagi nie mialy
    # zera na ZADNEJ glebokosci — wiec kazdy artykul dostawal nakaz porownania
    # z inna dziedzina, takze wtedy, gdy karta miala `parallel_mechanisms: []`.
    # Model, ktory nie ma drugiej dziedziny w materiale, a ma polecenie ja
    # rozwinac, musi ja wymyslic. To nie jest usterka stylu, tylko zaproszenie
    # do zmyslania — i to w miejscu, ktore sprawdzacz faktow lapie dopiero po
    # oplaceniu calego artykulu.
    0: ("NO outside parallel. This card has no second domain in it, so do not "
        "reach for one: an invented comparison would be the least supported "
        "thing in the article. Spend that room on the mechanism you can "
        "actually document — what it is, what it rests on, where it stops."),
    1: ("ONE parallel, developed properly — two paragraphs on a single other "
        "domain where this logic runs, close enough to follow all the way "
        "down. One thought, not a catalogue."),
    2: ("TWO parallels, a paragraph each. Pick two that fail differently, so "
        "the pair says something a single example could not."),
    3: ("THREE parallels, briskly — but they must escalate. If the third is "
        "interchangeable with the first, you have written a list; cut it to "
        "two."),
}


def losowy_ruch_koncowy() -> tuple[str, str]:
    """Czym konczy sie TEN artykul. Rowne szanse, bez powtarzania formuly."""
    import random

    nazwa = random.choice(RUCH_KONCOWY_MIX)
    return nazwa, RUCHY_KONCOWE[nazwa]


def losowa_liczba_paraleli(glebokosc: str = "RICH",
                           dostepne: int | None = None) -> tuple[int, str]:
    """Ile paraleli w drugim akcie. Krotki artykul nigdy nie bierze trzech,
    a zaden artykul nie bierze wiecej, niz karta niesie."""
    import random

    wagi = dict(ILE_PARALELI_WAGI)
    if (glebokosc or "").upper() != "RICH":
        wagi = {1: 5, 2: 3}
    # SUFITEM JEST MATERIAL, NIE LOSOWANIE. `dostepne` to liczba mechanizmow
    # rownoleglych na karcie. Nie zamawiamy dwoch porownan z karty, ktora ma
    # jedno, ani jednego z karty, ktora nie ma zadnego.
    if dostepne is not None:
        wagi = {k: v for k, v in wagi.items() if k <= max(0, int(dostepne))}
        if not wagi:
            return 0, OPIS_LICZBY_PARALELI[0]
    ile = random.choices(list(wagi), weights=list(wagi.values()), k=1)[0]
    return ile, OPIS_LICZBY_PARALELI[ile]


# --- generatory tematow ------------------------------------------------------
# Mielismy 52 DZIEDZINY, czyli odpowiedz na pytanie GDZIE szukac, i zero
# wzorcow, czyli zadnej odpowiedzi na pytanie CZEGO. Model dostawal „przyroda,
# finanse, prawo" i sam musial zgadnac, co w tych obszarach jest ciekawe.
#
# Sprawdzone na wlasnych tekstach: szesc naszych artykulow trafia w PIEC
# roznych wzorcow ponizej, wiec siatka pokrywa to, co juz umiemy, i nazywa
# kilka, ktorych nie tknelismy. Generator x dziedzina to kilkaset komorek,
# a kazda produkuje kandydatow.
GENERATORY = {
    "MEASUREMENT": "A number that looks like a measurement but is a ratio, a band "
                   "or marketing. Probe: what number does this domain print on "
                   "things, and what is it actually the ratio of?",
    "MIRROR": "Two jurisdictions, opposite rules, each internally correct. Probe: "
              "where does another country do the exact opposite, and why is each "
              "one right at home?",
    "FAILURE": "An incident where the system behaved exactly as designed, and that "
               "is why it broke. Probe: what is the famous outage or accident here, "
               "and what did it reveal that was always true?",
    "DECIDER": "Someone chose this. They have a name and a date. Nobody knows "
               "either. Probe: who signed this off, in what year, and what were "
               "they optimising for?",
    "FOSSIL": "The constraint disappeared, the shape stayed. Probe: what is here "
              "only because of a machine or a law that no longer exists?",
    "MARGIN": "A limit that reads as stinginess is exactly what the calculation "
              "requires. Probe: what looks under-provisioned, and what calculation "
              "makes it precisely enough?",
    "FRAUD": "The feature is a fossil of one specific crime. Probe: what does this "
             "defend against, and who was the criminal that caused it to exist?",
    "QUEUE": "An order you did not know was designed. Probe: what is the invisible "
             "ordering here, and what is it optimising that is not your convenience?",
    "CONFESSION": "The standard admits its own imprecision, in writing. Probe: "
                  "where does the rulebook say 'this is approximate', and why did "
                  "it have to?",
    "SUBSIDY": "One price hides a transfer between groups. Probe: who is overpaying "
               "so that someone else can be served at all?",
    "ROUND_NUMBER": "The threshold is round because a committee rounded it. Probe: "
                    "is this a natural break or a negotiated one, and who was in "
                    "the room?",
    "BOUNDARY": "The system must rule on a moment that does not exist. Probe: what "
                "happens exactly at the edge — midnight, the date line, the instant "
                "of payment?",
    # DWA WZORCE POD WIELKIE PYTANIA, dopisane 25 sierpnia 2026.
    #
    # POMIAR, KTORY TO WYMUSIL. Ostatni przebieg ciekawostek oddal cztery dobre
    # fakty: cztery fakty z twardym decydentem i data, kazdy sprawdzalny
    # w dokumencie. Kazdy z nazwanym decydentem i data. I ZERO z czterech stoi
    # pod pytaniem, ktore czytelnik zadaje sam z siebie („czy to rozumie", „czy
    # potrafi klamac") — a wlasnie takich pyta wlasciciel, wskazujac kanaly,
    # ktore w tej niszy zbieraja najwiecej rozmowy.
    #
    # Przyczyna jest w siatce, nie w modelu: dwanascie wzorcow powyzej pyta
    # o LICZBE, JURYSDYKCJE, DECYDENTA i AWARIE. Zaden nie pyta o ZACHOWANIE
    # SAMEGO SYSTEMU, wiec model nie mial jak trafic tam nawet przypadkiem.
    #
    # DLACZEGO TO NIE SA DUPLIKATY — sprawdzone po kolei wobec calej dwunastki:
    #   SEEMING vs MEASUREMENT: MEASUREMENT startuje z liczby wydrukowanej na
    #     rzeczy i pyta, czego jest ilorazem. SEEMING startuje z ZACHOWANIA
    #     i pyta, czy w ogole istnieje liczba, ktora je rozstrzyga. Przeciwne
    #     kierunki, a druga polowa przypadkow nie ma zadnej liczby na wejsciu.
    #   UNBIDDEN vs FAILURE: FAILURE to „zachowal sie DOKLADNIE jak
    #     zaprojektowano i dlatego pekl". UNBIDDEN to dokladnie odwrotnie —
    #     nikt tego nie zaprojektowal. Wspolny jest tylko incydent.
    #   UNBIDDEN vs CONFESSION: CONFESSION wymaga, zeby regulamin sam sie
    #     przyznal NA PISMIE. UNBIDDEN obejmuje takze przypadek, w ktorym nikt
    #     sie nie przyznal i zachowanie znalazl ktos z zewnatrz.
    # Trzeciego nie dokladam: DECIDER („kto ustawil prog odmowy, nazwisko
    # i rok") juz obsluguje pytanie „czy model ma wlasne cele" od strony
    # czlowieka, ktory te cele wpisal, i nie potrzebuje blizniaka.
    # KONCOWKA PRZEPISANA PO KRYTYCE. Stalo tu „— or is there no such test yet,
    # and who says so?", czyli sonda zamawiala doslownie to, czego akapit obok
    # w prompcie zabrania: „jesli najmocniejsze, co masz pod spodem, to ze
    # ludzie sie nie zgadzaja, znalazles spor, a spory sa za darmo".
    # Brak testu jest dobrym znaleziskiem, ale musi byc UDOKUMENTOWANY brakiem
    # w dokumencie — pusta rubryka w karcie systemowej, zestaw ewaluacji, ktory
    # tego nie mierzy — a nie czyjas opinia, ze testu nie ma.
    "SEEMING": "Something that reads as one thing and measures as another. "
               "Probe: what here looks like the impressive explanation, which "
               "published test separates the appearance from the thing, and "
               "where does the paperwork visibly leave that box empty?",
    "UNBIDDEN": "The thing does something nobody specified, and the people who "
                "built it found out afterwards. Probe: what behaviour appeared "
                "that was not designed, who noticed it first, and what did "
                "they change once they had?",
}

ILE_GENERATOROW_NA_PRZEBIEG = 4

# Ile kandydatow-jednolinijkowcow zamawiamy, zanim cokolwiek napiszemy.
# Nadprodukcja jest obowiazkowa: piec notek z piatki pomyslow to mediana,
# piec z dwudziestu piatki to wybor.
KANDYDATOW_NA_PRZEBIEG = 25


def losowe_generatory(ile: int = 0) -> list[str]:
    """Ktore wzorce w tym przebiegu. Ten sam generator dwa dni z rzedu daje
    jednolity ksztalt, a jednolity ksztalt to podpis maszyny."""
    import random

    return random.sample(list(GENERATORY), k=min(ile or ILE_GENERATOROW_NA_PRZEBIEG,
                                                 len(GENERATORY)))


# --- co czytelnik trzyma w reku W TYM MIESIACU -------------------------------
# Najtansza dzwignia, jaka mamy, i nie mielismy jej wcale. Zwykla rzecz,
# ktorej ktos WLASNIE dotyka, bije zwykla rzecz w ogole — dlatego tekst
# o czyms sezonowym trafia lepiej w swoim sezonie niz poza nim.
#
# RYTM ROKU NALEZY DO PRESETU (`temat.rytm_roku`, miesiac -> co sie wtedy
# dzieje w tej dziedzinie). Stal tu kalendarz instytucji jednego profilu
# (budzety, sprawozdania, konsultacje, polkula polnocna) podawany kazdej
# publikacji jako jej wlasny sezon (C2 audytu). Pusty slownik znaczy „bez
# podpowiedzi sezonowej": prompt dostaje wtedy jawne „(nothing seasonal
# listed)", a nie cudzy kalendarz.
W_TYM_MIESIACU: dict[int, str] = {}


def co_teraz_w_reku(kiedy=None, kalendarz=None) -> str:
    """Rzeczy, ktorych czytelnik dotyka wlasnie teraz.

    Kalendarz jest tematem, wiec przychodzi z kartridza (`[temat.rytm_roku]`);
    silnik ma go pusty i wtedy oddaje pusty napis — prompt dostaje wprost
    „nic sezonowego", a nie zmyslony sezon. `kalendarz` mozna podac jawnie
    (testy, podglad), domyslnie bierze sie aktualna stala.
    """
    from datetime import datetime, timezone

    kiedy = kiedy or datetime.now(timezone.utc)
    if kalendarz is None:
        kalendarz = W_TYM_MIESIACU
    return kalendarz.get(kiedy.month, "")


# --- konfiguracja z pliku ----------------------------------------------------
# `konfiguracja.toml` obok tego pliku nadpisuje wartosci powyzej. Wczytanie
# stoi TUTAJ, na samym koncu, a nie na gorze — bo nadpisywac mozna tylko to,
# co juz istnieje, a polowa stalych w tym pliku jest WYLICZANA z innych.
#
# Plik jest OPCJONALNY. Jego brak znaczy „zostaw wartosci z tego pliku", wiec
# istniejaca instalacja nie zmienia zachowania przez samo pojawienie sie tej
# sekcji.
#
# Zla wartosc ZATRZYMUJE START. Konfiguracja, ktora po cichu ignoruje literowke
# w nazwie pola, jest gorsza od jej braku: bot chodzi, robi co innego, niz
# napisano, i nikt tego nie zauwaza.
import konfiguracja as _konf   # noqa: E402
import preset as _preset       # noqa: E402

KONFIGURACJA_PLIK = _konf.sciezka(AGENT_DIR)

# `AGENT_V2_BEZ_KONFIGURACJI=1` — DLA GENERATOROW DOKUMENTACJI I NARZEDZI, NIE DLA BOTA.
#
# `narzedzia/mapa_tozsamosci.py` wypisuje do repozytorium, GDZIE siedzi
# tozsamosc konta. Uruchomiony u operatora czytal jego `konfiguracja.toml`
# i wpisywal do `docs/IDENTITY_MAP.md` JEGO uchwyt, JEGO marke i JEGO nisze —
# czyli narzedzie tropiace tozsamosc samo ja publikowalo. Zlapane, gdy mapa
# w repozytorium zaczela opisywac konto testowe, ktorym sprawdzalem kreator.
#
# Furtka jest zmienna srodowiskowa, nie polem konfiguracji, i to jest celowe:
# ma byc widoczna w wywolaniu i niemozliwa do wlaczenia przez przypadek
# w pliku, ktory sama wylacza. `narzedzia/presety.py` ustawia ja u siebie,
# zeby przymierzac presety na NEUTRALNYM silniku, a nie na podlaczonym.
_BEZ_KONFIGURACJI = _env("AGENT_V2_BEZ_KONFIGURACJI", "0").lower() in {"1", "true", "yes"}

# NEUTRALNA BAZA SILNIKA — zdjecie stalych konta ZANIM cokolwiek je nadpisze.
# Od niej kompiluje sie kazdy preset: przywroc baze, naloz preset. Bez tego
# preset B dziedziczyl po A kanaly, przyklady, pisarza i pytanie o stan
# dziedziny (proba T02 audytu). Uzywane takze przez `narzedzia/presety.py`
# do pokazania, ktora wartosc pochodzi z pliku, a ktora z silnika.
DOMYSLNE_SILNIKA = _konf.zdjecie(sys.modules[__name__])

# --- AKTYWNY PRESET ----------------------------------------------------------
#
# JEDEN SILNIK, JEDNA INSTANCJA NARAZ, KONTEKST ROZWIAZANY PRZED STARTEM.
# `agent-v2/aktywny_preset.json` (pisany przez `narzedzia/presety.py podlacz`)
# mowi, ktory plik presetu i z jakim odciskiem jest podlaczony oraz w ktorym
# katalogu leza dane tej instancji. Preset zmieniony po aktywacji zatrzymuje
# start — ma byc podlaczony jeszcze raz, swiadomie. Bez wskaznika bot nie ma
# tematu ani planu i `run.py` odmawia (`preset.wymagaj_aktywnego`).
#
# STARY `konfiguracja.toml` jest czytany TYLKO, gdy nie ma presetu — sciezka
# zgodnosci na czas przejscia; przy aktywnym presecie jest ignorowany (jedno
# zrodlo prawdy). W DARMOWYM TESCIE wskaznik nie jest czytany wcale: testy
# maja pracowac na silniku, a nie na tym, co operator akurat podlaczyl.
# Jawna zmienna `AGENT_V2_PRESET=<plik>` dziala takze w tescie i sluzy
# podgladowi promptow oraz sprawdzaniu presetow bez ich podlaczania.
PRESET = None              # `preset.Preset` albo None
PRESET_AKTYWACJA = None    # `preset.Aktywacja` albo None
INSTANCJA = ""             # identyfikator instancji; pusty = brak presetu

# BLOKI PROMPTOW Z PRESETU (`presety/<nazwa>/prompty/*.md`): linia redakcyjna,
# glos artykulu, notki i komentarza, tozsamosc okladki, kogo szukamy,
# oswiadczenie o autorstwie. Silnik trzyma METODE (kontrakty, format
# odpowiedzi, bramki); preset trzyma to, co odroznia jedna publikacje od
# drugiej. `stages._pola_wspolne` wstrzykuje je do briefow; brak bloku daje
# jawne zdanie zastepcze, nie pustke. Patrz `preset.BLOKI`.
PRESET_BLOKI: dict[str, str] = {}


def _aktywacja_przy_starcie():
    if _BEZ_KONFIGURACJI:
        return None
    if W_TESCIE and not _env(_preset.ZMIENNA):
        return None
    return _preset.aktywacja(AGENT_DIR)


_aktywacja = _aktywacja_przy_starcie()
if _aktywacja is not None:
    KONFIGURACJA_ZMIENILA = _preset.zastosuj(_aktywacja.preset, sys.modules[__name__],
                                             DOMYSLNE_SILNIKA)
    PRESET = _aktywacja.preset
    PRESET_AKTYWACJA = _aktywacja
    INSTANCJA = _aktywacja.instancja
    # KATALOG DANYCH INSTANCJI. Nic jeszcze nie jest zaimportowane poza tym
    # plikiem, wiec kazda sciezka pochodna w innych modulach policzy sie juz
    # z nowego `DATA_DIR`. Zapory testowe pytaja o TEN katalog — to on jest
    # teraz produkcja tej instancji.
    uzyj_katalogu_danych(_aktywacja.katalog_danych,
                         utworz=(_aktywacja.zrodlo == "wskaznik"))
    PRODUKCYJNY_KATALOG_DANYCH = DATA_DIR
    _dane_konfiguracji = {}
    if KONFIGURACJA_PLIK.exists() and not _w_darmowym_tescie():
        print("  [preset] %s istnieje, ale przy podlaczonym presecie NIE jest czytany"
              % KONFIGURACJA_PLIK.name, flush=True)
else:
    _dane_konfiguracji = {} if _BEZ_KONFIGURACJI else _konf.wczytaj(KONFIGURACJA_PLIK)
    KONFIGURACJA_ZMIENILA = _konf.zastosuj(_dane_konfiguracji, sys.modules[__name__])

# --- STALE POCHODNE, PRZELICZANE PO WCZYTANIU KONFIGURACJI -------------------
#
# Ten plik opisuje te pulapke przy `DB_PATH`: stala policzona RAZ, przy
# imporcie, nie zmienia sie, gdy zrodlo pod nia sie zmieni. Konfiguracja
# wchodzi na samym koncu pliku, wiec KAZDA stala wyliczona wyzej z pola
# konfiguracji trzyma wartosc domyslna.
#
# Pierwszy taki przypadek: `FETCH_USER_AGENT`. Naglowek widzi KAZDA odwiedzona
# strona i jest jedynym miejscem, w ktorym bot przedstawia sie z nazwy —
# konto z wlasna nazwa przedstawialoby sie nazwa domyslna.
#
# BLOK MA ZOSTAC KROTKI. Kazda nowa stala wyprowadzona z pola konfiguracji
# dopisuje sie TUTAJ, a nie liczy sie drugi raz gdzie indziej. Pilnuje tego
# `tests/test_pochodne_po_konfiguracji.py`.
FETCH_USER_AGENT = _naglowek_klienta()

# Sufit na dzis: baza z konfiguracji, pomnozona tylko w dniu podniesienia.
DAILY_LIMIT_USD = sufit_dnia(_dzis_utc())

# Tor testowy nigdy powyzej produkcyjnego — patrz `TEST_LIMIT_USD_BAZA`.
TEST_LIMIT_USD = min(TEST_LIMIT_USD_BAZA, DAILY_LIMIT_USD)

# DOBA MUSI ZMIESCIC ARTYKUL. Kreator pyta o oba sufity osobno i nie zestawia
# ich ze soba, wiec para w rodzaju (doba 1,00; przebieg 0,60) zapisuje sie bez
# slowa sprzeciwu — a znaczy tyle, ze artykul tygodniowy nie powstanie NIGDY:
# potrzebuje calego przebiegu, a doba nie udzwignie dwoch. Agent milczalby
# o przyczynie, bo kazdy pojedynczy etap miescilby sie w limicie.
#
# Ostrzezenie, nie wyjatek: to konfiguracja operatora i ma prawo byc dziwna.
# Ale ma o tym wiedziec w chwili wczytania, a nie z oblanego testu.
if DAILY_LIMIT_USD < RUN_LIMIT_USD * 2 and not _w_darmowym_tescie():
    print("  [konfiguracja] UWAGA: sufit dobowy %.2f USD nie zmiesci dwoch "
          "przebiegow po %.2f — artykul tygodniowy nie powstanie"
          % (DAILY_LIMIT_USD, RUN_LIMIT_USD), flush=True)

if PRESET is not None and not _w_darmowym_tescie():
    print("  [preset] %s (instancja %s, dane %s): przestawiono %d pozycji"
          % (PRESET.nazwa, INSTANCJA, DATA_DIR, len(KONFIGURACJA_ZMIENILA)), flush=True)
elif KONFIGURACJA_ZMIENILA and not _w_darmowym_tescie():
    print("  [konfiguracja] %s: przestawiono %d pozycji"
          % (KONFIGURACJA_PLIK.name, len(KONFIGURACJA_ZMIENILA)), flush=True)
