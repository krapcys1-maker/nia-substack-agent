"""Artykul bierze temat z tej samej puli, co notki.

DLACZEGO TO POWSTALO. Tor artykulu mial wlasnego skauta z wlasna teoria:
temat zasluguje na tysiac slow, gdy ma co najmniej dwa udokumentowane
PRECEDENSY — przeszle katastrofy, po ktorych zmieniono przepis („regulamin to
blizna").

Ta teoria jest dobra dokladnie tak dlugo, jak dlugo nisza ma duzo SPISANYCH
katastrof. Gdy ich nie ma, daje MONOKULTURE — i tak sie stalo: w rewirze,
w ktorym tylko trzy obszary mialy po dwie udokumentowane awarie, trzy artykuly
z rzedu wyszly o tych samych trzech obszarach. Publikacja pisala o
instytucjach, a nie o rzeczy, ktorej dotyczy.

Tymczasem pula ciekawostek — ta sama, z ktorej biora sie notki — produkuje
tematy, ktorych wlasciciel chce, a kazdy z nich ma juz zrodlo i date.
Zmierzone na jednym przebiegu: szesc faktow, kazdy z nazwana instytucja,
liczba i dokumentem za nia. ZADEN nie mial dwoch katastrof i kazdy niosl
artykul.

Wiec artykul nie wymysla tematu od zera i nie sprawdza, czy ma dwie
katastrofy — bierze SWIEZY fakt z tej puli i drazy go dalej.

Reszta lancucha zostaje bez zmian: dyskoveria, pobieranie, klasyfikacja,
synteza, bramka warto_pisac, pisarz, recenzent, forma, zapis, grafika.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config      # noqa: E402
import db          # noqa: E402
import llm         # noqa: E402
import preset      # noqa: E402
import stages      # noqa: E402

# WYJATKI, KTORYCH ZADNA OSLONA W TYM PLIKU NIE MA PRAWA POLKNAC.
#
# `llm.BudgetExceeded` i `llm.PreflightFailed` dziedzicza po `RuntimeError`,
# wiec kazde `except Exception` lapalo je razem ze zwyklymi awariami etapu.
# Roznica jest zasadnicza: `ValueError` z `llm.parse_json` mowi „ten jeden
# etap nie oddal JSON-a", a te dwa mowia „ZADNE nastepne platne wywolanie sie
# nie uda" — budzet wyczerpany (`RUN_LIMIT_USD` 1,60 / `DAILY_LIMIT_USD`)
# albo `KILL_SWITCH=true`. Oslona, ktora to poklyka, zamienia zatrzymanie
# w ciche pominiecie kontroli.
#
# ZMIERZONA SZKODA. Pisanie na Fable to okolo 0,76 USD, czyli prawie polowa
# sufitu przebiegu — `_preflight` przepuszcza pisarza i wywraca sie dopiero na
# recenzji. Przed oslonami `BudgetExceeded` wychodzil z `_napisz_i_zapisz`,
# `main` zamykal przebieg jako ERROR i nic nie szlo na Substacka. Z oslonami
# raport recenzji byl pusty, obserwacja formy tez, a `stages.zweryfikuj` na TYM
# SAMYM bledzie budzetu oddaje `safe_to_post: True` z uzasadnieniem „puszczam
# na pierwszej siatce" — gdzie pierwsza siatka to recenzja, ktora przed chwila
# padla po cichu. Artykul bez recenzji i bez sprawdzenia faktow wychodzil na
# zewnatrz.
#
# `llm.Truncated` NIE jest tu wymieniony celowo: odpowiedz ucieta na suficie
# tokenow to awaria jednego wywolania, ktora powtorka albo kolejny etap moga
# przezyc, i budzet po niej nadal istnieje.
PRZERYWAJA = (llm.BudgetExceeded, llm.PreflightFailed)

SYSTEM = (
    "You turn a documented fact into the question an article will answer. "
    "Return only valid JSON."
)

PYTANIE = """Today is {dzis}.

## This publication's editorial direction

{linia_redakcyjna}

Here is a documented fact this publication has verified, with its source:

  FACT: {fact}
  WHAT PEOPLE ASSUME INSTEAD: {mit}
  WHAT IS ACTUALLY TRUE: {prawda}
  WHO DECIDED IT, AND WHEN: {decyzja}
  WHAT IT MEANS FOR THE READER: {skutek}
  SOURCE: {url} (published {data})

Turn it into an article brief. The article is about **this subject**
and runs about a thousand words, so the question has to be worth that length:
not "what happened" — that is the note — but **why it happens, who arranged it
that way, and what else runs on the same arrangement.**

The reader has no stake in the specific system. Before writing the question,
answer privately: what does someone who will never touch this thing now know?

Treat the supplied fact as a research lead. Do not strengthen it: a documented
outcome does not prove an undocumented implementation or motive. A price or
legal conclusion retains its date, territory, eligibility and exceptions.
Sub-questions request evidence; their wording must not pretend we already
found it. Keep the question within the editorial direction above.

Return only valid JSON:

{{"title": "<the working title, a noun phrase, no colon>",
  "question": "<the one question the article answers, ending in a question mark>",
  "broken_belief": "<a specific assumption the source contradicts, or empty if no documented assumption is available; do not invent what everyone believes>",
  "why_they_believe_it": "<one sentence on where that belief comes from, or empty>",
  "the_moment": "<the concrete moment a reader can picture, one sentence>",
  "search_terms": ["<3-6 phrases a researcher should search to document this properly>"],
  "sub_questions": ["<4-6 questions THE ARTICLE MUST ANSWER. Not search phrases — questions, each ending in a question mark. Together they should be the skeleton of the piece: what is the arrangement, who set it up, what does it cost and to whom, where else does it run, what would have to change for it to stop. A note answers one of these; an article answers most of them.>"],
  "second_act": "<what happened AFTER the fact itself — a consequence, a reversal, a court case, an amendment, a company changing course. Empty string if nothing did.>",
  "beyond_one_place": "<where the same arrangement runs OUTSIDE the one company, country or product in the fact. Name it concretely. Empty string if it is confined to one place.>"}}

## Before you answer: is this an article at all?

Be honest in `second_act` and `beyond_one_place`, and leave them EMPTY when the
record gives you nothing. A fact with neither is a good NOTE and a bad article:
complete in two sentences, and a thousand words of it would be padding.

You are not being asked to justify writing this. Something else decides that,
and it decides on those two fields. Filling them with hedges to be helpful is
the one thing that breaks this.
"""


def temat_z_faktu(conn, run_id, fakt: dict) -> dict:
    """Zamienia udokumentowany fakt w brief artykulu."""
    from datetime import datetime, timezone

    tekst = llm.call(
        "wybor", SYSTEM,
        PYTANIE.format(
            dzis=datetime.now(timezone.utc).strftime("%d %B %Y"),
            linia_redakcyjna=stages._blok_presetu("linia_redakcyjna"),
            fact=fakt.get("fact", ""),
            mit=fakt.get("wrong_belief", ""),
            prawda=fakt.get("actually", ""),
            decyzja=fakt.get("decision", ""),
            skutek=fakt.get("consequence", ""),
            url=fakt.get("url", ""),
            data=fakt.get("source_date", "brak daty")),
        conn=conn, run_id=run_id)
    brief = llm.parse_json(tekst)
    if not isinstance(brief, dict) or not brief.get("question"):
        raise ValueError("brief bez pytania: %r" % str(tekst)[:200])
    # Pola, ktorych oczekuje reszta lancucha.
    brief.setdefault("kind", "BROKEN_BELIEF" if brief.get("broken_belief")
                     else "SYSTEM_UNDER_TEST")
    brief["zrodlo_faktu"] = fakt.get("url", "")
    brief["data_zrodla"] = fakt.get("source_date", "")
    brief["fakt_wyjsciowy"] = fakt.get("fact", "")
    return brief


# Glebokosc, gdy bramka `warto_pisac` PADLA — nie gdy powiedziala „nic tu nie
# ma". Brak odpowiedzi to nie jest odpowiedz „THIN": THIN znaczy „material na
# dwa zdania" i skraca artykul do 420 slow, a po awarii bramki nie wiemy o
# materiale nic. Fakt przeszedl juz `uniesie_artykul`, wiec ma drugi akt albo
# zasieg poza jedno miejsce — srodkowe pasmo jest jedynym, ktore niczego nie
# zmysla. Patrz `config.DLUGOSC_WG_GLEBOKOSCI`: SINGLE to 650 slow (480-820).
GLEBOKOSC_BEZ_OCENY = "SINGLE"


def glebokosc_z_oceny(ocena: dict) -> str:
    """RICH / SINGLE / THIN — liczone z tego, co `warto_pisac` ZOBACZYLO.

    SYGNAL BYL MARTWY. Kod czytal `ocena.get("depth")`, a kontrakt
    `warto_pisac.md` pola `depth` NIE MA — produkuje je `wykonalnosc.md`, etap,
    ktorego sciezka z puli w ogole nie wola. Wiec `glebokosc` bylo ZAWSZE
    „RICH": pisarzowi zawsze kazano pisac najglebsza forme, niezaleznie od tego,
    czy fakt to unosi. Jedyny mechanizm, ktory mogl skrocic chudy artykul,
    cicho defaultowal na najdluzszy. Pole czytane, nigdy nieustawiane.

    MODEL OBSERWUJE, KOD DECYDUJE — dlatego nie dopisuje `depth` do promptu i
    nie pytam modelu drugi raz o to samo. `warto_pisac` juz odpowiada na piec
    pytan tak/nie z uzasadnieniem; glebokosc jest ICH SUMA, a suma to robota
    dla kodu. Samoocena „jak gleboki jest ten material" degeneruje do stalej,
    tak samo jak wszystkie inne samooceny w tym potoku.

    Progi: cztery lub piec filarow to RICH, dwa lub trzy SINGLE, jeden albo
    zero THIN. Piec filarow to zlamane przekonanie, nazwany decydent, odczuwalna
    liczba, druga dziedzina i nierozstrzygniety wynik — i to wlasnie ich brak
    daje „lanie wody", bo pisarz nie ma czym wypelnic tysiaca slow poza
    powtarzaniem tezy.

    LICZYMY WERDYKT KODU, NIE SUROWE `present` MODELU. Bralismy filary wprost
    z pol modelu (`ocena["contradicted_belief"]["present"]`), a `warto_pisac`
    czesc z nich UNIEWAZNIA i zapisuje wynik OBOK, w `o["przekonanie"]`,
    `o["stawka"]` i `o["filary"]` — zagniezdzone `present` zostaje `True`.
    Uniewaznia w trzech sytuacjach, wszystkie realne: przekonanie zaznaczone,
    ale nienazwane (`the_belief` krotsze niz 4 slowa), nierozstrzygniety wynik
    bez pytania, oraz wynik, ktorego „regula" zaprzecza istnieniu reguly.

    Skutek starej wersji: karta z werdyktem ODLOZ — czyli „ani luki, ani
    stawki" — mogla dostac cztery filary z surowych pol i wyjsc jako RICH,
    a wiec cel 1075 slow. To jest dokladnie ta usterka, dla ktorej tabela
    `DLUGOSC_WG_GLEBOKOSCI` powstala, tylko wejsciem innym drzwiami.

    Surowe pola zostaja jako droga awaryjna, gdy dostaniemy ocene bez pol
    dokladanych przez kod (np. z zapisanej karty albo z testu).
    """
    def _surowy(pole: str) -> bool:
        blok = ocena.get(pole)
        return bool(isinstance(blok, dict) and blok.get("present"))

    filary_kodu = ocena.get("filary")
    if not isinstance(filary_kodu, dict):
        filary_kodu = {}

    def _filar(pole: str) -> bool:
        if pole in filary_kodu:
            return bool(filary_kodu[pole])
        return _surowy(pole)

    przekonanie = (bool(ocena["przekonanie"]) if "przekonanie" in ocena
                   else _surowy("contradicted_belief"))
    stawka = (bool(ocena["stawka"]) if "stawka" in ocena
              else _surowy("unsettled_outcome"))
    ile = sum((przekonanie, stawka, _filar("named_decider"),
               _filar("felt_number"), _filar("second_domain")))
    if ile >= 4:
        return "RICH"
    return "SINGLE" if ile >= 2 else "THIN"


def uniesie_artykul(brief: dict) -> tuple[bool, str]:
    """Czy z tego faktu da sie napisac TYSIAC SLOW, czy tylko dwa zdania.

    MODEL OBSERWUJE, KOD DECYDUJE. Prompt briefu prosil o „pytanie warte tej
    dlugosci" i to bylo wszystko — a prosba w prompcie nie jest bramka.
    Wlasciciel nazwal ryzyko wprost: „notatka moze byc o jednej malej kwestii,
    cala informacja w dwoch zdaniach i za bardzo nie ma co rozwijac, a artykul
    jakby wzial te info, to byloby lanie wody".

    Dwa warunki, oba brane z tego, co model ZOBACZYL w rekordzie, a nie z jego
    oceny, czy warto:

    DRUGI AKT — czy po samym fakcie cos jeszcze sie stalo. Skutek, odwrocenie,
    sprawa w sadzie, nowelizacja, firma zmieniajaca kurs. Fakt bez drugiego
    aktu jest kompletny w jednym zdaniu i rozbicie go na akapity daje
    rozdmuchana notke.

    ZASIEG POZA JEDNO MIEJSCE — czy ten sam uklad chodzi gdzies poza jedna
    firma, krajem albo produktem. Bez tego czytelnik bez zwiazku z ta jedna
    rzecza nie ma po co czytac tysiaca slow.

    JEDEN WYSTARCZY, nie oba. Wymaganie obu odrzucaloby dobre tematy: prawo,
    ktore dopiero weszlo, nie ma jeszcze drugiego aktu, ale ma zasieg; awaria
    w jednej firmie nie ma zasiegu, ale ma ciag dalszy, ktory jest cala
    historia. Zadnego z dwoch — to jest notka.

    Ta sama zasada, co przy `warto_pisac`, tylko PRZED researchem: tam ocena
    przychodzi po wydaniu 0,32 USD i tak nic nie blokuje.
    """
    drugi = " ".join(str(brief.get("second_act") or "").split())
    zasieg = " ".join(str(brief.get("beyond_one_place") or "").split())

    # Krotkie wypelniacze („none", „n/a", „unclear") to puste pole napisane
    # inaczej. Model proszony o uczciwosc czasem zamiast pustki wpisuje slowo.
    def _pusty(s: str) -> bool:
        return len(s.split()) < 4 or s.lower().rstrip(".") in {
            "none", "n/a", "na", "unclear", "unknown", "nothing", "not stated"}

    ma_drugi = not _pusty(drugi)
    ma_zasieg = not _pusty(zasieg)
    if ma_drugi or ma_zasieg:
        return True, ("drugi akt: %s" % drugi[:70]) if ma_drugi else (
            "zasieg: %s" % zasieg[:70])
    return False, ("ani drugiego aktu, ani zasiegu poza jedno miejsce — "
                   "to jest notka, nie artykul")


def wybierz_fakt(conn, run_id, ile: int = 8) -> dict:
    """Swiezy fakt z puli ciekawostek, ktory NIE powtarza zadnego artykulu.

    Pula juz przeszla bramke swiezosci (zrodlo nie starsze niz 90 dni dla
    twierdzen o stanie teraz, zadnych wycofywanych modeli, zadnych wersji bez
    potwierdzenia). Tu odsiewamy tylko to, o czym juz pisalismy dluga forma.
    """
    # NAJPIERW SPIZARNIA, DOPIERO POTEM ZAKUPY — tak samo jak w `notki_dnia`.
    #
    # Podlaczylem indeks do notek 30 sierpnia i zostawilem sciezke artykulu na
    # swiezym szukaniu. Zywy test tego samego wieczora pokazal, ile to kosztuje:
    # jedno wywolanie `curiosity`, 18 wyszukiwan, 450 tys. tokenow wejscia i
    # 0,127 USD — po to, zeby wybrac jeden fakt, podczas gdy w indeksie lezaly
    # gotowe, juz oplacone i juz przepuszczone przez bramke.
    #
    # Zmierzone: kazde wyszukiwanie to 10-19 tys. tokenow wejscia, bo serwer
    # prowadzi petle u siebie i rozlicza kazda runde osobno. Nie da sie tego
    # ograniczyc parametrem (`max_uses` i `max_tool_calls` sa ignorowane), wiec
    # jedyny sposob na tanszy artykul to NIE SZUKAC, kiedy nie trzeba.
    # NA ARTYKUL, WIEC PROSIMY O KANDYDATOW NA ARTYKUL. Bez tego
    # argumentu ta funkcja brala pierwszy fakt bez kolizji z historia,
    # a pole `na_artykul` — ocena, za ktora sedzia banku dostal
    # zaplacone — nie mialo zadnego czytelnika.
    fakty = stages.wez_kandydatow(ile, na_artykul=True)
    if fakty:
        print("  [temat] z indeksu: %d kandydatow (bez wyszukiwania)"
              % len(fakty), flush=True)
    else:
        # `na_artykul=True` — sciezka artykulu nie podlega dobowemu limitowi
        # szukania. Limit jest dla notek; tutaj kosztowal caly tygodniowy
        # artykul, bo dwa przebiegi notek chodza przed wtorkowym 14:00 i mogly
        # zuzyc jedyne dobowe szukanie, zanim artykul w ogole ruszyl.
        fakty = stages.znajdz_ciekawostki(conn, run_id, ile=ile, na_artykul=True)
    if not fakty:
        raise ValueError("pula ciekawostek pusta")

    # DWIE PAMIECI, NIE JEDNA — i to kosztowalo caly artykul.
    #
    # Pierwsza wersja pytala tylko o poprzednie ARTYKULY. Rano poszla notka
    # oparta na jednym fakcie z puli, a po poludniu artykul wzial z puli
    # DOKLADNIE TEN SAM fakt i napisal o nim tysiac slow. Zaden artykul o tym
    # nie byl, wiec straznik milczal.
    #
    # Konto ma jednego czytelnika, nie dwoch. Dla niego notka i artykul o tym
    # samym w jeden dzien to po prostu dwa razy to samo.
    wczesniej = list(stages.tematy_do_porownania(conn))
    notki = stages.ostatnie_notki(1000)
    wczesniej.extend(notki)
    print("  [temat] pamiec: %d artykulow + %d notek"
          % (len(wczesniej) - len(notki), len(notki)), flush=True)

    for f in fakty:
        opis = "%s %s" % (f.get("domain") or "", f.get("fact") or "")
        kolizja = next((w for w in wczesniej if w and stages._o_tym_samym(
            opis, w, **stages.POWTORKA_TEMATU)), None)
        if kolizja:
            print("  [temat] pomijam, juz o tym bylo: %s"
                  % (f.get("fact") or "")[:60], flush=True)
            print("          zderza sie z: %s"
                  % " ".join(str(kolizja).split())[:80], flush=True)
            continue
        # RESZTA WRACA DO PULI. Bierzemy osiem, uzywamy jednego — a
        # `wez_kandydatow` oznaczylo jako zuzyte wszystkie osiem. Bez tego
        # kazdy przebieg artykulu palil siedem oplaconych kandydatur.
        stages.zwroc_kandydatow([x for x in fakty if x is not f])
        return f
    print("  [temat] wszystko koliduje — biore pierwszy", flush=True)
    stages.zwroc_kandydatow(fakty[1:])
    return fakty[0]


@stages._na_kanal("artykul")
def main() -> int:
    """Otwiera przebieg, oddaje robote i ZAMYKA go — takze przy wyjatku.

    KANAL NA WEJSCIU, NIE PRZY ETAPACH. Ten plik ma jedno wejscie
    (`nia-artykul.service` wola `artykul_z_puli.py --wyslij`) i wszystko, co
    ono zaplaci, sluzy jednemu artykulowi — takze etapy, ktore SAME w sobie
    sluza dwom kanalom i dlatego wlasnego dekoratora miec nie moga:
    `znajdz_ciekawostki` (przez `wybierz_fakt`) szuka materialu takze na
    notki, a `zweryfikuj` (przez `_napisz_i_zapisz`) sprawdza takze notki
    i komentarze. Znacznik postawiony tutaj obejmuje je bez zgadywania.

    PRZEBIEG BYL OTWIERANY I NIGDY NIE ZAMYKANY. `start_run` bylo, `finish_run`
    NIE BYLO ANI RAZU (dla porownania `run.py` wola je piec razy). Skutek:
    kazdy przebieg artykulu zostawal w stanie RUNNING na zawsze, a po trzech
    godzinach `alarm.zawieszone` zamykal go jako STALE i wysylal wlascicielowi
    maila „przebiegi wisialy w RUNNING".

    Zmierzone 31 sierpnia: alarm zglosil cztery takie przebiegi — 85, 94, 95, 96
    — z czego 94, 95 i 96 to trzy podejscia do artykulu z poprzedniego wieczora,
    w tym TO, KTORE SIE UDALO I OPUBLIKOWALO.

    To gorsze niz smiec w tabeli: alarm o zawieszeniu odzywal sie po KAZDEJ
    publikacji, wiec prawdziwe zawieszenie utoneloby w szumie. Alarm, ktory
    klamie regularnie, uczy ignorowac alarmy.
    """
    # BRAMA PRESETU — przed baza i przed pierwszym platnym wywolaniem. Patrz
    # `run.main` i `preset.wymagaj_aktywnego`.
    import run as runner
    import call_runtime, time
    call_runtime.RUN_DEADLINE = time.monotonic() + 3600
    try:
        _lock = runner.zajmij_zamek()
    except runner.JuzDziala as exc:
        print(str(exc), flush=True)
        return 0
    try:
        preset.wymagaj_aktywnego(config, "artykul_z_puli.py")
    except preset.BrakPresetu as exc:
        print(str(exc), flush=True)
        return 3
    # PLAN Z PRESETU, NIE Z ZEGARA. Zegar odpala ten plik w dniu artykulu,
    # ale zegar bywa stary (jednostki zbudowane pod poprzedni preset) albo
    # reczny. Preset z zerem artykulow na tydzien nie pisze nigdy; preset
    # z innym dniem nie pisze dzis — chyba ze czlowiek powie `--wymus`.
    if config.PRESET is not None and "--wymus" not in sys.argv:
        if config.ARTYKULY_TYGODNIOWO <= 0:
            print(">> preset %r ma 0 artykulow na tydzien — nie pisze. "
                  "(`--wymus` omija plan)" % config.PRESET.nazwa, flush=True)
            return 1
        if not config.dzis_dzien_artykulu():
            print(">> dzis nie jest dzien artykulu wedlug presetu %r (dni: %s) — "
                  "nie pisze. (`--wymus` omija plan)"
                  % (config.PRESET.nazwa, ", ".join(config.DNI_ARTYKULU)), flush=True)
            return 1
    conn = db.connect()
    run_id = db.start_run(conn, "artykul-z-puli")
    try:
        kod = _przebieg(conn, run_id)
    except BaseException as exc:
        # BaseException, nie Exception: przerwanie z klawiatury albo SIGTERM
        # tez ma zostawic zamkniety przebieg, a nie wiszacy.
        #
        # SLAD PO URATOWANYM TEKSCIE IDZIE TU, ZARAZ ZA NAZWA WYJATKU. Plik
        # lezy poza katalogiem artykulow i nie ma wiersza w `articles`, wiec
        # `runs.note` jest JEDYNYM miejscem w bazie, z ktorego czlowiek moze
        # sie o nim dowiedziec — a `alarm.sprawdz_przebiegi_i_ostrzez`
        # (alarm.py:158) wkleja te note do maila, przycieta do 120 znakow.
        # Dlatego nazwa pliku stoi PRZED trescia bledu: ogon i tak odpada.
        uwaga = type(exc).__name__
        if URATOWANE:
            uwaga += " [tekst uratowany: %s]" % URATOWANE[-1].name
        db.finish_run(conn, run_id, "ERROR", "artykul",
                      f"{uwaga}: {exc}"[:200])
        raise
    # TRZY WYNIKI, TRZY STATUSY. `NIEOPUBLIKOWANY` nie nalezy do
    # ("DONE", "SAVED"), wiec `alarm.sprawdz_przebiegi_i_ostrzez` widzi go od
    # razu, bez zmiany w kodzie alarmu. `Restart=` NIE jest dodawany: ponowienie
    # calego przebiegu kosztowaloby nowy platny research, a tekst juz istnieje.
    if kod == KOD_NIEOPUBLIKOWANY:
        db.finish_run(conn, run_id, "NIEOPUBLIKOWANY", "artykul",
                      "tekst gotowy, publikacja nie potwierdzona")
    elif kod == KOD_ZATRZYMANY:
        db.finish_run(conn, run_id, "ZATRZYMANY", "artykul",
                      "bramka artefaktow zatrzymala tekst przed publikacja")
    else:
        db.finish_run(conn, run_id, "DONE" if kod == 0 else "SKIPPED", "artykul")
    return kod


def _zrob_miejsce_na_fakt(card: dict) -> None:
    """Robi miejsce na wstrzykniete twierdzenie, nie tracac zadnego ZRODLA.

    DZIEWIATE TWIERDZENIE. `config.CARD_MAX_CONFIRMED` to 8 i `stages.synthesis`
    przycina do tylu (`claims[: config.CARD_MAX_CONFIRMED]`). Wstrzykniecie
    dokladalo dziewiate, a `audyt_researchu.py:158-161` liczy srednia na karte
    i przy przekroczeniu sufitu meldowal „UWAGA — karta rozdeta".

    SUFIT ZOSTAJE, MIEJSCE ROBIMY TUTAJ — i powod jest rzeczowy, a nie
    organizacyjny. Stalo tu „`config.py` jest zajety przez innego agenta",
    czyli fakt prawdziwy przez kwadrans, zapisany jako uzasadnienie na zawsze.
    Wlasciwy powod: sufit opisuje, ILE TWIERDZEN UNIESIE KARTA dla pisarza,
    i jest wspolny dla wszystkich sciezek. Podniesienie go dla jednego
    wstrzyknietego faktu rozluznialoby go takze tam, gdzie nikt o to nie
    prosil.

    NIE TNIEMY OSTATNIEGO NA SLEPO. Ostatnie twierdzenie bywa jedynym z
    czwartego hosta, a wtedy wycinajac je zwezalibysmy podstawe artykulu i
    kasowali odnosnik z sekcji `## Sources` — czyli naprawiajac liczbe pozycji,
    psulibysmy to, czego ta liczba pilnuje. Wypada wiec OSTATNIE twierdzenie,
    ktorego host wystepuje jeszcze gdzies indziej: znika powtorka, nie zrodlo.

    Gdy kazde twierdzenie ma wlasny host, karta wychodzi z dziewiatka i mowimy
    to glosno. Sufit, ktory tnie po cichu, wyglada jak ocena modelu.
    """
    from urllib.parse import urlparse

    claims = card.get("confirmed_claims")
    if not isinstance(claims, list) or len(claims) < config.CARD_MAX_CONFIRMED:
        return

    def _host(c) -> str:
        if not isinstance(c, dict):
            return ""
        h = (urlparse(str(c.get("url") or "")).netloc or "").lower()
        return h[4:] if h.startswith("www.") else h

    for i in range(len(claims) - 1, -1, -1):
        host = _host(claims[i])
        if host and any(_host(c) == host for j, c in enumerate(claims) if j != i):
            usuniete = claims.pop(i)
            opis = str(usuniete.get("claim") or "")[:70]
            print("  [karta] sufit %d twierdzen — wypada powtorka z %s: %s"
                  % (config.CARD_MAX_CONFIRMED, host, opis), flush=True)
            return
    print("  [karta] sufit %d twierdzen, ale kazde ma wlasny host — karta "
          "wychodzi z %d, zeby nie stracic zrodla"
          % (config.CARD_MAX_CONFIRMED, len(claims) + 1), flush=True)


def _rozszerz_najstarsze(card: dict, data_faktu) -> None:
    """Data wstrzyknietego zrodla wazy — ale TYLKO w strone ostrzezenia.

    POLE BYLO MARTWE. Wstrzykniete twierdzenie nioslo `source_date`, a
    `stages.swiezosc_karty` (stages.py:~1427) czyta wylacznie
    `card["source_dates"]`, wiec data zrodla, od ktorego caly temat sie zaczal,
    nie wazyla na nic. Sygnal produkowany i wyrzucany.

    ROZSZERZAMY `oldest`, NIGDY `newest`. To nie jest symetryczne i nie moze
    byc. `newest` decyduje o uwadze `CALY_MATERIAL_STARY` i o tym, czy
    `stages.karta_dla_pisarza` skasuje note o wieku — podniesienie go data
    dokumentu, ktorego nikt nie pobral, UCISZALOBY ostrzezenie. `oldest` moze
    tylko dolozyc uwage `ZRODLO_SPRZED_LAT`. Kierunek, ktory potrafi wylacznie
    ostrzec, jest bezpieczny; kierunek, ktory potrafi uciszyc, nie jest.

    Nie tworzymy `source_dates` od zera: karta bez dat ma dostac
    `KARTA_BEZ_DAT`, a nie date jedynego niepobranego zrodla.
    """
    daty = card.get("source_dates")
    data = str(data_faktu or "").strip()[:10]
    if not isinstance(daty, dict) or not data:
        return
    stare = str(daty.get("oldest") or "").strip()[:10]
    if stare and stare <= data:
        return
    daty["oldest"] = data
    print("  [karta] najstarsze zrodlo cofniete na %s (fakt z puli)" % data,
          flush=True)


def _przebieg(conn, run_id: int) -> int:
    print("== artykul z puli ciekawostek ==", flush=True)

    # --- SCIEZKA Z ZATWIERDZONEJ KARTY ------------------------------------
    #
    # `--z-karty` pomija szukanie tematu i caly research: wczytuje karte
    # zapisana przez `--do-karty` i rusza od pisarza. Dzieki temu obejrzenie
    # materialu przed napisaniem kosztuje 0,38 USD RAZ, a nie dwa razy.
    if "--z-karty" in sys.argv:
        import json as _json
        _plik = config.DATA_DIR / "karta_do_zatwierdzenia.json"
        if not _plik.exists():
            print("BRAK zatwierdzonej karty — najpierw --do-karty", flush=True)
            return 1
        _zapis = _json.loads(_plik.read_text(encoding="utf-8"))
        card = _zapis["card"]
        brief = _zapis["brief"]
        print("  karta wczytana: %s" % brief.get("title"), flush=True)
        print("  pytanie: %s" % str(brief.get("question"))[:130], flush=True)
        return _napisz_i_zapisz(conn, run_id, brief, card)

    fakt = wybierz_fakt(conn, run_id)
    print()
    print("  FAKT:   %s" % (fakt.get("fact") or "")[:200], flush=True)
    print("  ZRODLO: %s (%s)" % (fakt.get("url", "")[:70],
                                 fakt.get("source_date", "brak daty")), flush=True)

    brief = temat_z_faktu(conn, run_id, fakt)
    print()
    print("  TYTUL:  %s" % brief.get("title"), flush=True)
    print("  PYTANIE: %s" % brief.get("question"), flush=True)
    print("  ZLAMANE PRZEKONANIE: %s" % (brief.get("broken_belief") or "(brak)"),
          flush=True)

    # BRAMKA ARTYKULOWA — PRZED RESEARCHEM, bo po nim jest juz za pozno.
    # Odrzucony fakt WRACA DO PULI jako material na notke: nie jest zly, tylko
    # nie unosi tysiaca slow. Probujemy kolejnych, zamiast poddawac sie na
    # pierwszym — dokladnie tak, jak `wybierz_fakt` robi to przy powtorkach.
    unosi, powod = uniesie_artykul(brief)
    proby = 1
    # ODDAJEMY PO PETLI, NIE W SRODKU — i to jest naprawa regresu, ktory sam
    # tu wpisalem. `zwroc_kandydatow([fakt])` stalo WEWNATRZ petli, wiec
    # odwracalo status odrzuconego na „nowy" ZANIM `wybierz_fakt` siegnelo po
    # nastepnego. `wez_kandydatow` sortuje deterministycznie po
    # `(not z_kanalu, ranga)`, a oddanie nie rusza ani rangi, ani pozycji w
    # indeksie — wiec oddany fakt wracal na to samo miejsce i byl wybierany
    # ponownie.
    #
    # ZMIERZONE na prawdziwej parze `wez_kandydatow`/`zwroc_kandydatow`
    # (indeks w katalogu tymczasowym, osiem kandydatow, `ranga` 0-7):
    #     z oddaniem w petli:  1. MiastoA | 2. MiastoA | 3. MiastoA
    #     bez oddania w petli: 1. MiastoA | 2. FirmaC | 3. UczelniaB
    # Czyli cztery oplacone wywolania `temat_z_faktu` na TYM SAMYM fakcie,
    # kandydaci 2-8 nietknieci, a ekran drukowal „-- proba N: nastepny fakt --".
    #
    # Oba cele daja sie pogodzic tylko przez odroczenie: w petli odrzucony
    # zostaje „uzyty" (wiec nie wraca pod reke), a po petli wszystkie wracaja
    # do puli jako material na notke. Jedno wywolanie na koniec, wiec nic nie
    # jest oddawane dwa razy.
    odrzucone: list[dict] = []
    while not unosi and proby < 4:
        print("  ODPADA: %s" % powod, flush=True)
        print("  (fakt zostaje w puli jako material na notke)", flush=True)
        print("   — wroci do niej po zakonczeniu prob, zeby petla siegnela"
              " po NASTEPNEGO kandydata, a nie po tego samego", flush=True)
        odrzucone.append(fakt)
        proby += 1
        print()
        print("-- proba %d: nastepny fakt --" % proby, flush=True)
        try:
            fakt = wybierz_fakt(conn, run_id)
        except ValueError as exc:
            # Pula wyschla w polowie petli — to, co juz odrzucilismy, i tak
            # musi wrocic, inaczej wyjatek kasuje oplacone kandydatury.
            if odrzucone:
                stages.zwroc_kandydatow(odrzucone)
            print("  %s — koncze" % exc, flush=True)
            return 1
        brief = temat_z_faktu(conn, run_id, fakt)
        print("  TYTUL:  %s" % brief.get("title"), flush=True)
        print("  PYTANIE: %s" % brief.get("question"), flush=True)
        unosi, powod = uniesie_artykul(brief)
    if not unosi:
        print("  ODPADA: %s" % powod, flush=True)
        # Ostatni odrzucony wraca tak samo jak trzy poprzednie — inaczej zdanie
        # ponizej („pula zostaje na notki") byloby nieprawda o tym wlasnie
        # fakcie, ktorym przebieg sie skonczyl.
        odrzucone.append(fakt)
    if odrzucone:
        stages.zwroc_kandydatow(odrzucone)
    if not unosi:
        print(">> po %d probach zaden fakt nie uniesie artykulu — nie pisze."
              " Pula zostaje na notki." % proby, flush=True)
        return 1
    print("  UNIESIE: %s" % powod, flush=True)

    pod = [q for q in (brief.get("sub_questions") or []) if str(q).strip()]
    if pod:
        print()
        print("  PYTANIA, NA KTORE ARTYKUL MA ODPOWIEDZIEC (%d):" % len(pod),
              flush=True)
        for q in pod:
            print("    - %s" % str(q)[:110], flush=True)

    if "--tylko-temat" in sys.argv:
        return 0

    # --- dalej JUZ ISTNIEJACY lancuch, bez zmian ---------------------------
    print()
    print("-- dyskoveria --", flush=True)
    recent = db.recent_domains(conn, config.DIVERSITY_LOOKBACK)
    # PODPYTANIA IDA DO DYSKOVERII, nie tylko do pisarza. Bez tego byly by
    # ozdoba: model wypisalby szesc pytan, research szedlby po jednym glownym,
    # a pisarz dostalby karte, ktora odpowiada na jedno z szesciu. Wlasciciel
    # prosil wprost o to, zeby temat artykulu byl BARDZIEJ ZBADANY niz temat
    # notki — a to znaczy wiecej pytan na wejsciu researchu, nie wiecej slow
    # na wyjsciu pisarza.
    pytanie_do_researchu = brief["question"]
    if pod:
        pytanie_do_researchu = (
            brief["question"]
            + "\n\nThe article must also answer:\n"
            + "\n".join("- %s" % q for q in pod))
    sources = stages.discovery(conn, run_id, pytanie_do_researchu, recent)

    print()
    print("-- pobieranie --", flush=True)
    corpus = stages.fetch(conn, run_id, sources)
    # DRUGA RUNDA — teraz naprawde tak samo jak w run.py.
    #
    # Komentarz mowil „tak samo jak w run.py" i to bylo nieprawda w dwoch
    # miejscach naraz, a to TEN plik stoi na wtorkowym zegarze i pisze
    # produkcyjny artykul:
    #
    #   1. Warunek pytal wylacznie o LICZBE pobranych, nie o to, czy wsrod nich
    #      jest jakikolwiek DOKUMENT. `run.py` dokladal `bez_rekordow` po tym,
    #      jak zmierzono przebiegi z dziewiecioma pobranymi zrodlami i JEDNYM
    #      pierwotnym — pisarz dostawal dziewiec tekstow o dokumencie i ani
    #      jednego dokumentu. Tutaj ta poprawka nigdy nie dotarla.
    #   2. Brakowalo `tylko_pierwotne`, wiec nawet gdy runda sie odpalala,
    #      dyskoveria szukala czegokolwiek zamiast rekordow.
    #
    # Przy okazji: `4` bylo wpisane obok stalej, ktora znaczy dokladnie to samo
    # (`MIN_ZRODEL_DO_PISANIA`). Dwie kopie jednej liczby zawsze sie rozjezdzaja.
    pobrane = [c for c in corpus if c.get("text")]
    pierwotnych = sum(1 for s in corpus if s.get("class") == "PRIMARY")
    za_chudo = len(pobrane) < config.MIN_ZRODEL_DO_PISANIA
    bez_rekordow = pierwotnych < config.MIN_PRIMARY_SOURCES
    if za_chudo or bez_rekordow:
        print()
        print("-- druga runda: pobranych %d/%d, pierwotnych %d/%d --"
              % (len(pobrane), config.MIN_ZRODEL_DO_PISANIA,
                 pierwotnych, config.MIN_PRIMARY_SOURCES), flush=True)
        juz = {c.get("url") for c in corpus}
        dodatkowe = [s for s in stages.discovery(conn, run_id,
                                                 pytanie_do_researchu, recent,
                                                 tylko_pierwotne=bez_rekordow)
                     if s.get("url") not in juz]
        if dodatkowe:
            corpus = corpus + stages.fetch(conn, run_id, dodatkowe)

    print()
    print("-- klasyfikacja --", flush=True)
    evidence = stages.classify(conn, run_id, brief["question"], corpus)

    print()
    print("-- synteza --", flush=True)
    try:
        card = stages.synthesis(conn, run_id, brief["question"], evidence)
    except PRZERYWAJA:
        # Ta sama zasada, co przy trzech oslonach w `_napisz_i_zapisz`: karta
        # zapasowa ma sens po awarii JEDNEGO wywolania, a nie wtedy, gdy budzet
        # sie skonczyl — bo wtedy pisarz zaraz za nia to najdrozszy etap
        # przebiegu i tak samo sie wywroci.
        #
        # I NIE MA TU CZEGO RATOWAC. `_ratuj_tekst` stoi przy recenzji i
        # obserwacji formy, czyli za pisarzem. Tutaj tekstu jeszcze nie ma —
        # zapisanie karty jako „artykulu" wsadziloby do `articles` pusta
        # skorupe, ktora `stages.tematy_do_porownania` policzy jako temat juz
        # napisany i zablokuje go na przyszlosc. Uratowalibysmy zero slow i
        # stracili temat.
        raise
    except Exception as exc:
        print("  synteza padla (%s) — karta zapasowa" % type(exc).__name__,
              flush=True)
        card = stages.fallback_card(brief["question"], evidence)

    # FRAGMENTY, KTORYCH ARTYKUL NIE ZUZYL — zaplacone i do tej pory nieczytane
    # na TEJ sciezce.
    #
    # `run.py` ustawia to pole od poczatku; `artykul_z_puli.py` nie ustawial go
    # nigdy, a to WLASNIE ON stoi na wtorkowym zegarze i pisze produkcyjny
    # artykul. Skutek: `stages.bank_fragmentow` czyta `articles.evidence.
    # unused_evidence`, wiec dla kazdego artykulu z tej sciezki widzial pustke —
    # galaz DOLOZ konczyla sie na „bank pusty", bibliotekarz nie ruszal ani razu,
    # a kilkadziesiat ocytowanych fragmentow na artykul szlo do kosza mimo ze
    # kosztowaly tyle samo, co te uzyte.
    #
    # NIE MYLIC z komentarzem przy `_ratuj_tekst` (~linia 822): tam brak tego
    # pola jest SWIADOMA cena za niewstawianie wiersza do `articles`, opisana
    # wprost. Tu nie bylo zadnego powodu, tylko brakujaca linia.
    #
    # Przy `--z-karty` karta przychodzi z pliku i tego pola nie ma — i tak ma
    # byc: material zostal juz raz przypisany do swojego artykulu.
    card["unused_evidence"] = [
        {"url": s["url"], "publisher": s.get("publisher"),
         "excerpts": s["excerpts"], "numbers": s["numbers"]}
        for s in (evidence if isinstance(evidence, list) else [])
        if isinstance(s, dict) and s.get("url")
    ]

    # Fakt wyjsciowy zostaje w karcie: to on byl powodem, dla ktorego ten temat
    # w ogole wybralismy, i pisarz ma go widziec razem z reszta dowodow.
    card.setdefault("broken_belief", brief.get("broken_belief") or "")
    card.setdefault("why_they_believe_it", brief.get("why_they_believe_it") or "")

    # KOMENTARZ WYZEJ BYL OBIETNICA BEZ POKRYCIA. Do karty szly wylacznie te
    # dwa pola; sam fakt, jego URL i data szly do `brief` (`fakt_wyjsciowy`,
    # `zrodlo_faktu`, `data_zrodla`) i NIE BYLY CZYTANE NIGDZIE — sprawdzone
    # grepem po calym repo: trzy przypisania, zero odczytow.
    #
    # Skutek byl podwojny. Pisarz nie widzial zdania, ktore uzasadnilo wybor
    # tematu (widzi wylacznie `card_json`). Sekcja `## Sources` w zapisanym
    # pliku sklada sie z URL-i `confirmed_claims`, wiec zrodlo faktu nie
    # trafialo do artykulu, mimo ze to od niego wszystko sie zaczelo.
    #
    # TRZECI POWOD, KTORY SAM TU WPISALEM, BYL BLEDNY: „liczby z tego faktu
    # bramka `LICZBA_SPOZA_KORPUSU` uznawala za zmyslone, wiec dobrze, ze
    # wejda do korpusu". To nie jest zaleta, tylko rozbrojenie kontroli —
    # patrz akapit nizej i `gates._korpus_pobranych`.
    #
    # Wchodzi jako `confirmed_claims`, a nie jako osobne pole, bo tylko tak
    # dosiega wszystkich trzech miejsc naraz. Fakt jest udokumentowany: pula
    # przepuscila go przez bramke swiezosci razem ze zrodlem i data.
    #
    # ALE NIE JAKO ZWYKLE TWIERDZENIE — i to jest poprawka po kontroli.
    # `confirmed_claims` to zbior, NA KTORYM STOJA DWIE BRAMKI
    # DETERMINISTYCZNE, a fakt z puli nie jest wyciagiem z pobranego
    # dokumentu: to wypowiedz modelu z `znajdz_ciekawostki` z doklejonym
    # URL-em. Nikt tej strony nie pobral ani nie sklasyfikowal.
    #
    # Bez znacznika rozbrajal obie:
    #   `gates.szerokosc_podstawy` liczylo host, ktorego nikt nie pobral, wiec
    #     `WASKA_PODSTAWA` milczala na artykule stojacym realnie na jednym
    #     zrodle — a ta uwaga powstala dokladnie po takim artykule, ktory mial
    #     w calej sekcji `## Sources` JEDEN odnosnik;
    #   `gates.numbers_outside_corpus` bierze korpus z `json.dumps(card)`, wiec
    #     liczby z tego faktu stawaly sie „obecne w materiale dowodowym".
    #
    # DLATEGO `not_fetched`, a nie kolejne martwe pole. Obie bramki teraz je
    # CZYTAJA (patrz `gates.szerokosc_podstawy` i `gates._korpus_pobranych`):
    # host sie nie liczy, a liczba stad idzie pod wlasna uwaga
    # `LICZBA_TYLKO_Z_PULI`, ktora mowi prawde — nie „zmyslona", tylko
    # „niepobrana, sprawdz w zrodle". Klucz po angielsku, bo ta karta jedzie
    # do pisarza jako `card_json` i ma sie tlumaczyc sama.
    _fakt_txt = " ".join(str(brief.get("fakt_wyjsciowy") or "").split())
    _fakt_url = str(brief.get("zrodlo_faktu") or "").strip()
    if _fakt_txt and _fakt_url:
        _juz = {str(c.get("url") or "")
                for c in (card.get("confirmed_claims") or [])
                if isinstance(c, dict)}
        if _fakt_url not in _juz:
            # `evidence` BYLO KOPIA `claim` — ten sam napis dwa razy. To
            # jedyne twierdzenie w karcie, ktorego „cytat" nie jest wyciagiem
            # ze zrodla, czyli dokladnie wzorzec, przed ktorym stoi regula
            # `MUST CARRY THE WHOLE CLAIM` w `synteza.md` i caly
            # `test_cytat_niesie_twierdzenie.py`. Zaden kod tego nie sprawdza,
            # wiec przechodzilo cicho.
            #
            # Rekord z puli niesie DWA osobne zdania: `control_fact` (co mowi
            # dokument kontrolny) i `actually` (co jest naprawde prawda wedlug
            # zrodla). Ktorekolwiek z nich jest odrebnym zdaniem, a nie echem
            # twierdzenia. Gdy nie ma zadnego, zostaje sam fakt — ale wtedy
            # `not_fetched` mowi wprost, ze to nie jest cytat.
            _wyciag = " ".join(str(fakt.get("control_fact")
                                   or fakt.get("actually") or "").split())
            _zrob_miejsce_na_fakt(card)
            card.setdefault("confirmed_claims", []).insert(0, {
                "claim": _fakt_txt,
                "evidence": _wyciag or _fakt_txt,
                "url": _fakt_url,
                "not_fetched": True,
            })
            print("  fakt wyjsciowy dolozony do karty: %s (%s)"
                  % (_fakt_url[:60], brief.get("data_zrodla") or "brak daty"),
                  flush=True)
            _rozszerz_najstarsze(card, brief.get("data_zrodla"))

    # --- HAMULEC PRZED NAJDROZSZYM ETAPEM ---------------------------------
    #
    # `--do-karty` konczy tu, po syntezie, przed pisarzem. Kosztuje okolo
    # 0,38 USD zamiast 1,40, bo samo pisanie to 0,76.
    #
    # POWOD JEST POLICZONY. 25 sierpnia zaplacilem CZTERY pisania po 0,76 USD
    # i ani jedna znaleziona wada nie byla w pisaniu:
    #   przebieg 1 — powtorzony temat (wybor tematu)
    #   przebieg 2 — powtorzony temat, tym razem z dzisiejsza notka
    #   przebieg 3 — metaanaliza cytowana z drugiej reki (dyskoveria)
    #                oraz okladka z przedmiotem spoza tematu (grafika)
    #   przebieg 4 — filtr adresow blokowal zrodla pierwotne (dyskoveria)
    #
    # Trzy z czterech widac bylo na karcie dowodowej: jakie zrodla, jakiej
    # daty, czy sa pierwotne. Czwarta — powtorke tematu — jeszcze wczesniej,
    # przy samym tytule.
    #
    # 3,04 USD na pisanie, z ktorego nic nie wynikalo poza tym, ze wada byla
    # gdzie indziej.
    if "--do-karty" in sys.argv:
        print()
        print("=" * 72)
        print("KARTA DOWODOWA — STOP PRZED PISARZEM")
        print("=" * 72)
        print("TEZA:", str(card.get("working_thesis", ""))[:400])
        print()
        daty = card.get("source_dates") or {}
        print("DATY ZRODEL: najnowsze %s, najstarsze %s"
              % (daty.get("newest", "?"), daty.get("oldest", "?")))
        if daty.get("note"):
            print("   uwaga:", str(daty["note"])[:200])
        for u in stages.swiezosc_karty(card):
            print("   [%s] %s" % (u.get("gate"), str(u.get("detail"))[:130]))
        print()
        print("LICZBY DO CYTOWANIA (%d):" % len(card.get("citable_numbers") or []))
        for n in (card.get("citable_numbers") or [])[:8]:
            print("   - %s" % str(n)[:170])
        print()
        print("ZRODLA W KORPUSIE:")
        widziane = set()
        for c in (evidence if isinstance(evidence, list) else []):
            h = str(c.get("url") or "")[:70]
            if h and h not in widziane:
                widziane.add(h)
                print("   %-10s %s" % (c.get("class", "?"), h))
        print()
        print("CZEGO NIE USTALONO:")
        for x in (card.get("not_established") or [])[:5]:
            print("   - %s" % str(x)[:150])

        # KARTA ZAPISANA, ZEBY NIE PLACIC DYSKOVERII DRUGI RAZ.
        #
        # Pierwsza wersja hamulca konczyla tu i tyle — a wtedy napisanie
        # zatwierdzonego artykulu wymagalo puszczenia calego lancucha od nowa,
        # czyli oplacenia szukania tematu, dyskoverii, pobierania, klasyfikacji
        # i syntezy PO RAZ DRUGI. Hamulec, ktory oszczedza 0,76 na pisaniu i
        # kaze zaplacic 0,38 na research, oszczedza polowe tego, co obiecuje.
        #
        # `--z-karty` wczytuje ten plik i rusza od pisarza.
        import json as _json
        _plik = config.DATA_DIR / "karta_do_zatwierdzenia.json"
        try:
            _plik.parent.mkdir(parents=True, exist_ok=True)
            _plik.write_text(_json.dumps(
                {"card": card, "brief": brief, "fakt": fakt},
                ensure_ascii=False, indent=1), encoding="utf-8")
            print()
            print(">> karta zapisana: %s" % _plik)
            print(">> zeby napisac TEN artykul bez placenia researchu drugi raz:")
            print("   .venv/bin/python agent-v2/artykul_z_puli.py --z-karty")
        except OSError as exc:
            print("   (karty nie zapisalem: %s)" % exc)
        return 0

    # NORMALNA SCIEZKA — bez `--do-karty` idziemy prosto do pisarza.
    #
    # Ta linia byla przez chwile OSIEROCONA: wyladowala za koncem
    # `_napisz_i_zapisz`, wiec `main` przelatywalo przez `if` powyzej i wypadalo
    # z funkcji, zwracajac None. Przebieg konczyl sie KODEM 0 i bez artykulu —
    # bez wyjatku, bez ostrzezenia, z opłaconym researchem za 0,40 USD i pustym
    # katalogiem. Zlapane zywym przebiegiem 30 sierpnia, nie testem: zaden test
    # nie wolal `main()`, wiec nieosiagalny kod nie mial jak sie ujawnic.
    return _napisz_i_zapisz(conn, run_id, brief, card)


# GDZIE LADUJE URATOWANY TEKST — I DLACZEGO NIE W `ARTICLES_DIR`.
#
# Pierwsza wersja ratunku wolala `stages.save`, czyli pisala `.md` i `.uwagi.md`
# do `config.ARTICLES_DIR` i wstawiala wiersz do `articles`. Tekst przezywal —
# i wchodzil do korpusu, po ktorym globuje i selectuje reszta systemu. Zmierzone
# SZESC czytelnikow, ktorzy zaczynali go liczyc jako artykul; zaden z nich NIE
# FILTRUJE po statusie, wiec `NIESPRAWDZONY` nie zatrzymywal ani jednego:
#
#   `stages.ostatnie_uwagi` (stages.py:190, ile=2, mtime malejaco) — uratowany
#     `.uwagi.md` jest z definicji najswiezszy, wiec ZAWSZE zajmowal jedno z
#     dwoch miejsc petli zwrotnej do pisarza, a wnosil ZERO linii: obie jego
#     notatki (`RECENZJA`, `DLUGOSC`) odsiewa stages.py:208.
#   `stages.poprzednie_teksty` (stages.py:237) — jedno z czterech miejsc
#     (`ILE_TEKSTOW_DO_POROWNANIA_FORMY`) materialu bramki ODCISK_FORMY, i to
#     miejsce MARTWE: ramka blokujaca przestawia `gates.odcisk_formy` w dwoch
#     cechach z szesciu (`otwarcie` = „>" zamiast pierwszego slowa akapitu,
#     `liczba_w_otwarciu` = True, bo w ramce stoi „0,76 USD"), a
#     `gates.powtorzona_forma` wymaga pieciu zgodnych z szesciu. Taki wpis nie
#     moze sie odezwac NIGDY i wypycha tekst, ktory by mogl.
#   `audyt_systemu.py:323/330/334` — TRWALE rozbrojenie kontrdowodu na martwa
#     bramke. `:323` zwieksza `z_uwagami` za kazdy artykul z niepustymi `notes`
#     (uratowany ma zawsze dwie), `:330` przy zliczaniu bramek pomija dokladnie
#     `DLUGOSC` i `RECENZJA`. Mianownik rosnie, licznik nie, wiec warunku
#     `i == z_uwagami` z `:334` nie spelni juz ZADNA bramka — i nie przez jeden
#     dzien, tylko dopoki wiersz siedzi w `articles`, czyli zawsze.
#   `stages.tematy_do_porownania` (stages.py:115) — `topic/title/body` ze
#     WSZYSTKICH wierszy, bez filtra statusu; to pamiec powtorek `wybierz_fakt`.
#     Nieopublikowany tekst spalalby swoj wlasny temat na zawsze.
#   `stages.recent_angles` (stages.py:74) — to samo po `topic`: jedno z pieciu
#     miejsc listy „katow juz zajetych", ktora dostaje skaut.
#   `audyt_researchu.py:138` — srednie po `evidence`, liczone jak dla artykulu,
#     ktory przeszedl kontrole.
#
# CEL RATUNKU TEGO NIE WYMAGA. Chodzi o zachowanie tekstu, za ktory zaplacono
# okolo 0,76 USD, zeby czlowiek mogl go dokonczyc — a nie o to, zeby bral
# udzial w korpusie, w petli zwrotnej, w bramkach formy i w audytach. Poprawki
# po stronie tych szesciu czytelnikow siedza w `stages.py` i `audyt_systemu.py`,
# czyli w plikach, ktorych ta zmiana nie tyka.
#
# WIEC RATUNEK NIE UZYWA JUZ `stages.save`. Pisze wlasny komplet plikow do
# SIOSTRZANEGO katalogu i NIE WSTAWIA WIERSZA DO `articles`. `_ratuj_tekst` nie
# dostaje juz nawet `conn` — brak polaczenia jest tu wlasnoscia, nie
# niedopatrzeniem: funkcja bez uchwytu do bazy nie ma jak niczego do niej
# dopisac, ani teraz, ani po nastepnej przerobce.
#
# CENA, JAWNIE: bez wiersza w `articles` `stages.bank_fragmentow` (stages.py:4635)
# nie zobaczy `unused_evidence` z tej karty. Dlatego karta ladzie obok tekstu
# jako `.karta.json`, w DOKLADNIE tym ksztalcie, ktory czyta `--z-karty`
# (linia ~441): material nie jest skasowany, tylko czeka na swiadoma decyzje
# czlowieka zamiast wchodzic do obiegu sam.
NAZWA_KATALOGU_RATUNKU = "artykuly-przerwane"
NAZWA_SPISU = "CZYTAJ_TO.txt"


def _katalog_ratunku() -> Path:
    """Katalog OBOK `ARTICLES_DIR`, nigdy w nim.

    Liczony z `ARTICLES_DIR`, a nie wpisany na sztywno w `config` — i to jest
    wlasnosc warta wiecej niz jedna stala: test, ktory przestawia katalog
    artykulow na tymczasowy, przestawia TYM SAMYM katalog ratunku, wiec nie ma
    jak zapisac niczego do produkcyjnego `data/` przez zapomnienie.

    (Stalo tu jeszcze „`config.py` jest zajety przez innego agenta" — fakt
    prawdziwy przez kwadrans, zapisany jako uzasadnienie na zawsze. Uzasadnienie
    bez daty waznosci przezywa swoj powod i broni stanu, ktorego juz nie ma.)
    """
    return config.ARTICLES_DIR.parent / NAZWA_KATALOGU_RATUNKU


# SCIEZKI URATOWANE W TYM PROCESIE — czyta je `main`, zeby wpisac je do
# `runs.note`. Zmienna modulu, bo `_ratuj_tekst` siedzi trzy ramki glebiej niz
# `main` i nie ma jak nic zwrocic: miedzy nimi leci `raise`. Proces obsluguje
# JEDEN przebieg, wiec lista nie ma jak sie przeciac miedzy przebiegami.
# KOD WYJSCIA DLA „TEKST GOTOWY, PUBLIKACJA NIE POSZLA".
# Rozny od 0 (udane) i rozny od reszty (pominiete, brak tematu), bo `main`
# musi umiec ODROZNIC te trzy rzeczy w statusie przebiegu.
KOD_NIEOPUBLIKOWANY = 3
# TEKST ZATRZYMANY PRZEZ BRAMKE ARTEFAKTOW: zostaje na dysku z powodem, nie idzie
# na konto i NIE jest ponawiany przez rutyne dnia (to nie awaria publikacji,
# tylko odmowa). Patrz `gates.artefakty_w_tekscie`.
KOD_ZATRZYMANY = 4

URATOWANE: list[Path] = []


def _opublikuj(sciezka: Path) -> dict:
    """Wystawia gotowy artykul, probujac wiecej niz raz. NIE JEST BRAMKA.

    Nie ma tu ani jednego warunku, ktory moglby publikacji ZABRONIC. Jedyne,
    co ta funkcja doklada do `browser.wystaw_artykul`, to POWTORZENIE proby
    i PRAWDA O WYNIKU.

    DLACZEGO POWTORZENIE JEST TANIE I BEZPIECZNE. Tekst jest juz napisany
    i oplacony; ponowienie to jedno wejscie przegladarka. `wystaw_artykul`
    zaczyna od `potwierdz_artykul` i przy tekscie, ktory jednak wyszedl,
    oddaje `pominiete=True, wyslane=True` — druga proba nie ma jak wystawic
    tego samego dwa razy.

    DLACZEGO WLASNY `except`, skoro `wystaw_artykul` lapie wyjatki u siebie:
    `wymagaj_sesji` i `podlacz_sie` stoja PRZED tamtym `try`, wiec padnieta
    przegladarka rzuca, zanim slownik wyniku w ogole powstanie.
    """
    import time
    import browser

    wynik: dict = {"wyslane": False, "blad": "nie probowano"}
    for proba in range(1, config.PROB_PUBLIKACJI_ARTYKULU + 1):
        try:
            wynik = browser.wystaw_artykul(sciezka, wyslij=True)
        except Exception as exc:
            wynik = {"wyslane": False,
                     "blad": "%s: %s" % (type(exc).__name__, exc)}
        print(">> proba %d/%d: %s%s"
              % (proba, config.PROB_PUBLIKACJI_ARTYKULU,
                 "OPUBLIKOWANY" if wynik.get("wyslane") else "NIE POSZEDL",
                 "  " + str(wynik.get("blad")) if wynik.get("blad") else ""),
              flush=True)
        if wynik.get("wyslane"):
            return wynik
        if proba < config.PROB_PUBLIKACJI_ARTYKULU:
            time.sleep(config.PRZERWA_MIEDZY_PROBAMI_ARTYKULU_S)
    return wynik

# STATUS TEKSTU URATOWANEGO Z PRZERWANEGO PRZEBIEGU.
#
# Od kiedy ratunek nie pisze do `articles`, ten napis nie jest juz wartoscia
# kolumny — jest ETYKIETA w plikach, ktore czyta czlowiek. Zostaje ta sama, bo
# mowi to, co trzeba: nikt niczego nie zablokowal (to znaczylo `BLOCKED`, stan
# zniesiony 15 sierpnia 2026), tylko ZADNA kontrola sie nie odbyla.
STATUS_URATOWANY = "NIESPRAWDZONY"

# Pierwsza linia pliku. `browser.rozbierz_artykul` (browser.py:2383-2384) bierze
# `linie[0]` jako TYTUL, wiec dopoki ta ramka stoi, recznie wystawiony szkic
# mialby tytul „NIE PUBLIKOWAC..." — awaria widoczna zamiast cichej.
RAMKA_BLOKUJACA = "# NIE PUBLIKOWAC"


def _ramka(powod: str, brak: list[str], katalog: Path) -> str:
    """Ostrzezenie, ktore idzie na POCZATEK `.md`, a nie tylko obok niego.

    `stages.save` pisze plik CELOWO gotowy do wklejenia: tytul, podtytul, tresc,
    zrodla — bez statusu, bo „status i tak siedzi w tabeli `articles`". Tu nie
    ma nawet wiersza w tabeli, a tekst nie przeszedl ZADNEJ kontroli. Ramka idzie
    do `.md`, bo obok juz raz nie wystarczylo: adnotacja „recenzja niedostepna"
    ladowala w `.uwagi.md` artykulu, ktory chwile pozniej i tak wychodzil na
    Substacka (patrz komentarz nad oslona recenzji).

    `brak` to lista kontroli, ktore sie NIE odbyly — wyliczona przez wolajacego
    z tego, dokad przebieg doszedl, a nie wpisana na sztywno. Ramka mowiaca
    „bez recenzji" nad tekstem, ktory recenzje przeszedl, byla by falszem w
    ostrzezeniu, czyli dokladnie tym, czego to ostrzezenie ma pilnowac.

    Ramka mowi tez, GDZIE lezy — plik bez czytelnika to ten sam sygnal
    produkowany i wyrzucany, ktory tepimy w calym tym audycie.
    """
    return "\n".join([
        RAMKA_BLOKUJACA + " — TEKST NIESPRAWDZONY",
        "",
        "> %s" % powod,
        "> Kontrole, ktore sie NIE odbyly: %s." % ", ".join(brak),
        "> Zapisany, bo pisanie jest najdrozszym pojedynczym wywolaniem",
        "> przebiegu, a zapis jest darmowy — wyrzucenie gotowego tekstu",
        "> byloby strata bez zadnej korzysci.",
        "> Etykieta: %s. Ten tekst NIE MA wiersza w tabeli `articles` i NIE"
        % STATUS_URATOWANY,
        "> lezy w katalogu artykulow — celowo, zeby nie liczyl sie jako artykul",
        "> napisany. Lezy w `%s`; obok stoi `%s`." % (katalog, NAZWA_SPISU),
        "> Zeby to opublikowac, trzeba SWIADOMIE usunac te ramke i przepuscic",
        "> tekst przez kontrole. Dopoki stoi, jest pierwsza linia pliku, a",
        "> `browser.rozbierz_artykul` bierze pierwsza linie jako tytul.",
        "",
        "---",
        "",
        "",
    ])


SPIS = """TEKSTY Z PRZEBIEGOW, KTORE SIE NIE DOKONCZYLY

Kazdy plik `.md` w tym katalogu to artykul NAPISANY I OPLACONY, ktorego przebieg
przerwal budzet albo wylacznik ZANIM odbyla sie recenzja, bramki jakosci
i sprawdzenie faktow. Pisanie jest najdrozszym pojedynczym wywolaniem calego
przebiegu — ile dokladnie kosztowalo TWOJE, mowi tabela `calls` w bazie.

ZADEN Z NICH NICZEGO NIE PRZESZEDL. Kazdy zaczyna sie ramka „%s"
i ta ramka ma tam zostac, dopoki czlowiek nie przeczyta tekstu.

To NIE jest katalog artykulow (`data/articles/`) i nie jest nim celowo. Nic
stad nie trafia do korpusu stylu, do petli zwrotnej pisarza, do bramki
ODCISK_FORMY, do pamieci powtorek tematu ani do audytow — dopoki czlowiek sam
czegos stad nie przeniesie.

CO Z TYM ZROBIC — dwie drogi:

  1. Przeczytac `.md`, poprawic recznie, usunac ramke i wystawic samemu.
     Uwagi z przerwanego przebiegu leza obok, w `.uwagi.txt`.

  2. Napisac ten artykul jeszcze raz, NIE placac researchu drugi raz:
       cp <plik>.karta.json agent-v2/data/karta_do_zatwierdzenia.json
       .venv/bin/python agent-v2/artykul_z_puli.py --z-karty
     `.karta.json` ma dokladnie ten ksztalt, ktorego oczekuje `--z-karty`,
     wiec przebieg rusza od pisarza. Temat NIE jest spalony: skoro wiersza w
     `articles` nie ma, pamiec powtorek o nim nie wie.

Gdy plik jest juz niepotrzebny — skasowac caly komplet (`.md`, `.uwagi.txt`,
`.karta.json`). Nic w kodzie tego katalogu nie czyta.
""" % RAMKA_BLOKUJACA


def _zrodla(card: dict) -> str:
    """Sekcja `## Sources` — bez pytania bazy o nazwy zrodel.

    `stages.save` podmienia URL na tytul przez `_nazwa_zrodla(conn, url)`.
    Ratunek `conn` juz nie dostaje (patrz komentarz nad `NAZWA_KATALOGU_RATUNKU`),
    wiec bierze host. Adres i tak jest calym, sprawdzalnym odnosnikiem, a
    ladniejsza nazwa nie jest warta oddawania ratunkowi uchwytu do bazy.
    """
    from urllib.parse import urlparse

    urls = list(dict.fromkeys(
        c.get("url") for c in (card.get("confirmed_claims") or [])
        if isinstance(c, dict) and c.get("url")))
    return "\n".join(
        "- [%s](%s)" % (urlparse(u).netloc.replace("www.", "") or u, u)
        for u in urls)


def _ratuj_tekst(run_id, brief, card, draft, etap: str, exc,
                 raport=None) -> None:
    """Gotowy tekst na dysk, gdy budzet albo wylacznik przerywa PO pisaniu.

    DECYZJA WLASCICIELA: zapisac, nie wyrzucac. Zapis jest darmowy, a pisanie
    na Fable kosztuje okolo 0,76 USD — prawie polowe sufitu przebiegu
    (`RUN_LIMIT_USD` 1,60). `stages.review` stalo w linii ~891, a `stages.save`
    dopiero ~953, wiec `raise` z recenzji leci PRZED zapisem i oplacony tekst
    nie trafial nawet na dysk.

    CZEGO TA FUNKCJA NIE ROBI, i to jest wazniejsze niz to, co robi:
      nie wola NICZEGO PLATNEGO. `stages.grafika` i `stages.zweryfikuj` to
        wywolania modelu, wiec przy wyczerpanym budzecie wywroca sie na tym
        samym `_preflight`, tylko po drodze zaplacone. Zapisujemy sam tekst;
      nie wola bramek. `gates.deterministic_floors` jest darmowe, ale stoimy
        w obsludze wyjatku — jego wlasna awaria zabralaby ratunek I zaslonila
        pierwotne przerwanie. Ocena i tak jest bez wartosci, skoro recenzji
        nie bylo;
      nie dotyka BAZY. Nie ma `conn`, wiec nie ma wiersza w `articles` —
        dlaczego, patrz dlugi komentarz nad `NAZWA_KATALOGU_RATUNKU`;
      nie pisze do `ARTICLES_DIR`. Komplet idzie do katalogu siostrzanego,
        po ktorym nikt nie globuje;
      nie podnosi wyjatku. Wolajacy robi `raise` zaraz po nas, wiec przebieg
        konczy sie ERROR-em tak samo jak dotad. Blad z ratunku nie ma prawa
        podmienic `BudgetExceeded` na `OSError` — alarm patrzy na nazwe wyjatku;
      nie otwiera zadnej drogi do `browser.wystaw_artykul`. Publikacja stoi
        ~50 linii nizej, za `raise` wolajacego, i bierze `sciezka` z lokalnej
        zmiennej tego samego przebiegu — nigdy z katalogu ani z bazy.

    NOTATKI IDA POD `RECENZJA` I `DLUGOSC` — nazwy zostaja te same, co przy
    zwyklym zapisie, zeby czlowiek czytal jeden format, a nie dwa. Nic ich juz
    nie odsiewa, bo nikt ich nie czyta: `.uwagi.txt` nie jest `.uwagi.md` i nie
    lezy w `ARTICLES_DIR`, wiec `stages.ostatnie_uwagi` go nie widzi.

    `raport` to wynik recenzji, gdy ta zdazyla przejsc (przerwanie dopiero na
    obserwacji formy). Rozroznienie bierzemy z NIEGO, nie z nazwy etapu:
    ostrzezenie „bez recenzji" nad tekstem, ktory recenzje przeszedl, byloby
    falszem — a to jest ostrzezenie, wiec falsz w nim kosztuje najwiecej.
    """
    import json as _json
    import re as _re

    powod = "Przebieg przerwany na etapie %s: %s: %s" % (
        etap, type(exc).__name__, " ".join(str(exc).split())[:120])
    # Bramki jakosci (`gates.deterministic_floors`, `gates.uwagi_z_formy`,
    # `stages.swiezosc_karty`) i sprawdzenie faktow (`stages.zweryfikuj`) stoja
    # ZAWSZE ponizej obu tych przerwan, wiec ich brak jest pewny w obu
    # przypadkach. Recenzja zalezy od tego, dokad przebieg doszedl.
    brak = ["bramki jakosci", "sprawdzenie faktow przed publikacja"]
    if raport is None:
        brak.insert(0, "recenzja")
        brak.insert(1, "obserwacja formy")
        recenzja = "NIE ODBYLA SIE — " + powod
    else:
        brak.insert(0, "obserwacja formy")
        recenzja = "przeszla, ale jej uwag nikt nie zestawil z bramkami — %s" % (
            " ".join(str(raport.get("summary") or "").split())[:150] or "bez podsumowania")
    tresc = str((draft or {}).get("body") or "").strip()
    if not tresc:
        # Nie ma czego ratowac, a pusty plik jest gorszy niz brak: kaze
        # czlowiekowi otworzyc go i przekonac sie, ze nic w nim nie ma.
        print("  [ratunek] nie ma tekstu do uratowania — nie zapisuje pustego"
              " artykulu", flush=True)
        return
    notatki = [
        {"gate": "RECENZJA", "detail": recenzja},
        {"gate": "DLUGOSC", "detail": "%d slow" % len(tresc.split())},
    ]
    # WSZYSTKO PONIZEJ JEST W `try`, LACZNIE Z LICZENIEM SCIEZKI. Pierwsza
    # wersja liczyla katalog i slug PRZED `try` — a wtedy awaria w tych dwoch
    # linijkach wychodzila z ratunku na wylot i PODMIENIALA `BudgetExceeded` na
    # `OSError`. `alarm` i `finish_run` patrza na nazwe wyjatku, wiec
    # przerwanie budzetowe znikneloby z dziennika przez blad zapisu pliku.
    # Zlapane testem (sekcja 11), nie rozumowaniem.
    sciezka = None
    try:
        katalog = _katalog_ratunku()
        slug = _re.sub(r"[^a-z0-9]+", "-",
                       (draft.get("title") or "artykul").lower()).strip("-")
        sciezka = katalog / ("%04d-%s.md" % (run_id, slug[:60]))
        katalog.mkdir(parents=True, exist_ok=True)
        # JEDEN ZAPIS, RAMKA JUZ W SRODKU. Wczesniej plik pisal `stages.save`,
        # a ramke dopisywalo osobne przejscie — miedzy nimi istniala chwila,
        # w ktorej gotowy tekst lezal na dysku BEZ ostrzezenia, i awaria
        # dopisania zostawiala go w tym stanie na stale.
        sciezka.write_text(
            _ramka(powod, brak, katalog)
            + "# %s\n\n*%s*\n\n%s\n\n---\n\n" + config.NAGLOWEK_ZRODEL
            + "\n\n%s\n"
            % (draft.get("title", ""), draft.get("subtitle", ""),
               draft["body"], _zrodla(card)),
            encoding="utf-8")
        sciezka.with_suffix(".uwagi.txt").write_text(
            "# Uwagi wewnetrzne — %s\n\nStatus: %s — %s\n\nTemat: %s\n\n%s\n"
            % (draft.get("title", ""), STATUS_URATOWANY, powod,
               (brief or {}).get("title") or "",
               "\n".join("- %s" % n for n in notatki)),
            encoding="utf-8")
        # KARTA W KSZTALCIE, KTORY CZYTA `--z-karty` (linia ~441). To jedyna
        # rekompensata za brak wiersza w `articles`: research za okolo 0,40 USD
        # nie jest skasowany, tylko czeka na decyzje czlowieka.
        sciezka.with_suffix(".karta.json").write_text(
            _json.dumps({"card": card, "brief": brief}, ensure_ascii=False,
                        indent=1), encoding="utf-8")
        (katalog / NAZWA_SPISU).write_text(SPIS, encoding="utf-8")
    except Exception as blad:      # noqa: BLE001 — patrz docstring
        # `Exception`, nie `OSError`: nie tylko dysk. Zly typ w `draft`,
        # nieserializowalna karta, katalog tylko do odczytu — kazde z nich
        # wyszloby stad jako INNY wyjatek niz ten, ktory przerwal przebieg.
        print("  [ratunek] ZAPIS SIE NIE UDAL (%s: %s) — tekst przepadl"
              % (type(blad).__name__, str(blad)[:120]), flush=True)
        return
    URATOWANE.append(sciezka)
    print("  [ratunek] tekst URATOWANY (%d slow): %s"
          % (len(tresc.split()), sciezka), flush=True)
    print("  [ratunek] obok: %s (uwagi) i %s (karta do `--z-karty`)"
          % (sciezka.with_suffix(".uwagi.txt").name,
             sciezka.with_suffix(".karta.json").name), flush=True)
    print("  [ratunek] SZUKAJ TEGO W: %s — opis w %s"
          % (katalog, NAZWA_SPISU), flush=True)
    print("  [ratunek] %s, NIE do publikacji: nic nie poszlo na zewnatrz, nie"
          " ma wiersza w `articles` i nie lezy w katalogu artykulow"
          % STATUS_URATOWANY, flush=True)


def _napisz_i_zapisz(conn, run_id, brief, card) -> int:
    """Od bramki „warto pisac" do zapisu i grafiki.

    Wydzielone, zeby `--z-karty` mogl tu wejsc z zatwierdzona karta bez
    placenia researchu drugi raz.
    """
    print()
    print("-- czy jest tu luka --", flush=True)
    # BRAMKA JEST DORADCZA — I DOTAD MOGLA ZABIC CALY PRZEBIEG.
    #
    # `run.py` opakowuje dokladnie to wywolanie i pisze dlaczego: „Jej awaria
    # nie moze kosztowac oplaconego researchu". Tu stalo golo, mimo ze NICZEGO
    # nie blokuje — wiec jeden `ValueError` z `llm.parse_json` wyrzucal do kosza
    # dyskoverie, pobieranie, klasyfikacje i synteze, czyli okolo 0,40 USD.
    # To nie hipoteza: `llm.parse_json` dokumentuje taka awarie z 25 sierpnia
    # 2026 — „`warto_pisac` padlo na `Extra data: line 1 column 1866`".
    # Lamalo to takze regule wlasciciela z `gates.py`: artykul powstaje ZAWSZE.
    ocena: dict = {}
    try:
        ocena = stages.warto_pisac(conn, run_id, card)
        # WERDYKT SIEDZI POD `werdykt`, NIE POD `verdict`. Kontrakt
        # `prompts/warto_pisac.md` zwraca `one_line_verdict`, a wlasciwy werdykt
        # sklada KOD w `stages.warto_pisac` i zapisuje po polsku. Czytanie
        # `verdict` dawalo zawsze None, wiec log drukowal surowy `repr` calego
        # slownika uciety na 200 znakach — czyli nie mowil nic.
        print("   filary: %d z 3 (%s)"
              % (ocena.get("ile_filarow", 0),
                 ", ".join(k for k, v in (ocena.get("filary") or {}).items() if v)
                 or "zaden"), flush=True)
        print("   werdykt: %s — %s"
              % (ocena.get("werdykt"), str(ocena.get("powod") or "")[:160]),
              flush=True)
        # ZAPISUJEMY OD RAZU, NIE ZA GALEZIA BANKU. Ta linia stala PO calym
        # bloku DOLOZ, wiec awaria `bank_fragmentow` albo `bibliotekarz`
        # wyrzucala z `try` i karta szla do zapisu BEZ `ocena_ciekawosci` —
        # mimo ze sama ocena byla juz policzona i kilka linii nizej decydowala
        # o glebokosci. Karta w `articles.evidence` jest jedynym miejscem, z
        # ktorego bank fragmentow cokolwiek czyta; „ocena jest, ale w karcie
        # jej nie ma" to znowu sygnal policzony i wyrzucony.
        card["ocena_ciekawosci"] = ocena

        if ocena.get("werdykt") == "DOLOZ":
            # TO JEST MOMENT, DLA KTOREGO BANK ISTNIEJE — cytat z `run.py`,
            # ktory te galaz ma. Ta sciezka NIE MIALA JEJ WCALE: werdykt DOLOZ
            # znaczy „luka jest, ale materialu za malo", i bez banku szedl do
            # pisarza dokladnie tak samo jak PISZ. Bibliotekarz szuka pary
            # w juz zaplaconych resztkach z innej dziedziny — tak powstal
            # najlepszy tekst serii.
            print("   szukam pary w banku...", flush=True)
            bank = stages.bank_fragmentow(conn)
            if not bank:
                print("   bank pusty — pisarz dostaje karte jak jest", flush=True)
            else:
                grupy = stages.bibliotekarz(conn, run_id, bank).get("groups") or []
                dolozone = [{"domain": ", ".join(g.get("dziedziny", [])),
                             "mechanism": g.get("mechanism", ""), "z_banku": True}
                            for g in grupy[:2]]
                if dolozone:
                    card.setdefault("parallel_mechanisms", []).extend(dolozone)
                    print("   dolozono %d mechanizmow z banku:" % len(dolozone),
                          flush=True)
                    for d in dolozone:
                        print("     • [%s] %s"
                              % (d["domain"], d["mechanism"][:110]), flush=True)
                else:
                    print("   bank nie ma pary — pisarz dostaje karte jak jest",
                          flush=True)
    except PRZERYWAJA:
        # Budzet albo wylacznik — na wylot, patrz `PRZERYWAJA`. Gdyby zostalo
        # polkniete tutaj, pisarz ponizej i tak by sie wywrocil na tym samym
        # bledzie, tylko juz pod druga oslona, i tak dalej az do publikacji.
        #
        # BEZ RATUNKU: pisarz jeszcze nie ruszyl, `draft` nie istnieje.
        # Przerwanie w tym miejscu nic nie kosztowalo poza researchem, a
        # researchu na dysk nie zapisujemy jako artykulu.
        raise
    except Exception as exc:
        print("  [awaria] bramka ciekawosci padla (%s: %s) — pisze bez niej"
              % (type(exc).__name__, str(exc)[:120]), flush=True)
        # OCENA ZOSTAJE, JESLI TO NIE ONA PADLA. Gdy wywrocil sie dopiero bank
        # albo bibliotekarz, filary sa juz policzone i glebokosc ma z czego
        # powstac — kasowanie ich zeslaloby dobry material na srodkowe pasmo.
        # Kasujemy wylacznie ksztalt, ktorego nie da sie policzyc.
        if not isinstance(ocena, dict):
            ocena = {}

    print()
    print("-- pisanie --", flush=True)
    # GLEBOKOSC BEZ OCENY. `glebokosc_z_oceny({})` daje THIN, czyli cel 420
    # slow — i tak ma byc, gdy bramka POWIEDZIALA, ze filarow nie ma. Ale gdy
    # bramka PADLA, nie wiemy nic, a THIN znaczy „material na dwa zdania".
    # Fakt przeszedl juz `uniesie_artykul`, wiec ma drugi akt albo zasieg;
    # srodkowe pasmo (650 slow) nie udaje wiedzy w zadna strone.
    glebokosc = glebokosc_z_oceny(ocena) if ocena else GLEBOKOSC_BEZ_OCENY
    print("   glebokosc: %s" % glebokosc, flush=True)
    try:
        draft = stages.write(conn, run_id, card, glebokosc)
    except PRZERYWAJA:
        # POWTORKA NA OPUSIE NIE MA PRAWA RUSZYC PRZY WYCZERPANYM BUDZECIE.
        # Opus jest DROZSZY od tego, co wlasnie padlo, wiec oslona podwajalaby
        # wydatek dokladnie w chwili, gdy `_preflight` powiedzial, ze pieniedzy
        # nie ma. Przy `KILL_SWITCH=true` powtorka i tak wroci z tym samym
        # `PreflightFailed` — czyli jedno wywolanie po nic i wyjatek na koniec.
        # Ten `except` musi stac PRZED ogolnym, bo Python bierze pierwszy
        # pasujacy.
        #
        # BEZ RATUNKU, i to jest ten sam powod, dla ktorego nie ma powtorki:
        # pisarz sie NIE UDAL, wiec `draft` nie istnieje. Gdyby istnial choc
        # kawalek, ratunek by tu byl — ale `stages.write` albo oddaje caly
        # obiekt, albo rzuca.
        raise
    except Exception as exc:
        # Jedno powtorzenie na pisarzu zapasowym Z PRESETU, tak jak w `run.py`:
        # tu ginie caly oplacony research. Pusty `modele.zapasowy_pisarz`
        # znaczy „zatrzymaj sie" i wyjatek idzie dalej.
        if not config.ZAPASOWY_PISARZ:
            print("  [awaria] pisarz (%s) padl: %s — preset nie ma pisarza "
                  "zapasowego, zatrzymuje" % (config.MODEL_FOR.get("write"),
                                             str(exc)[:120]), flush=True)
            raise
        print("  [awaria] pisarz (%s) padl: %s — powtarzam na %s"
              % (config.MODEL_FOR.get("write"), str(exc)[:120],
                 config.ZAPASOWY_PISARZ),
              flush=True)
        # NADPISANIE NA CZAS JEDNEGO WYWOLANIA — patrz ten sam blok
        # w `run.py`. Globalna zmiana konfiguracji uzyta jako lokalne
        # nadpisanie i niecofnieta klamie potem o tym, co operator wpisal
        # w `konfiguracja.toml`, i wysyla kazde nastepne `write` na model
        # najdrozszy bez decyzji.
        _pisarz = config.MODEL_FOR["write"]
        try:
            config.MODEL_FOR["write"] = config.ZAPASOWY_PISARZ
            draft = stages.write(conn, run_id, card, glebokosc)
        finally:
            config.MODEL_FOR["write"] = _pisarz
    print()
    print("   tytul: %s" % draft.get("title"), flush=True)
    print("   podtytul: %s" % draft.get("subtitle", ""), flush=True)
    # ZAKRES RAZEM Z LICZBA. Sama liczba slow nie mowi, czy artykul jest za
    # krotki — a pasma sa trzy i roznia sie dwuipolkrotnie. `run.py` drukowal
    # tu przez dlugi czas staly cel 1075, czyli wartosc sprzed skalowania.
    _dl = config.dlugosc_dla(glebokosc)
    print("   dlugosc: %d slow (cel %d, zakres %d-%d dla %s)"
          % (len(draft["body"].split()), _dl["cel"], _dl["min"], _dl["max"],
             glebokosc), flush=True)

    print()
    print("-- recenzja --", flush=True)
    # RECENZJA NIC NIE BLOKUJE, WIEC JEJ BRAK TEZ NIE MOZE. `gates.verdict`
    # zwraca SAVED niezaleznie od raportu; padniecie tego etapu wyrzucalo do
    # kosza gotowy, oplacony tekst (samo pisanie to 0,76 USD).
    #
    # „SZUFLADA" TO BYLO ZDANIE NIEPRAWDZIWE, i tak tu stalo. `run.py` konczy
    # przebieg na zapisie, ale `systemd/nia-artykul.service` wola TEN plik jako
    # `artykul_z_puli.py --wyslij`, a `--wyslij` prowadzi przez `stages.save`,
    # `stages.grafika` i `stages.zweryfikuj` prosto do
    # `browser.wystaw_artykul(..., wyslij=True)`. Zadna szuflada po drodze nie
    # stoi: adnotacja „recenzja niedostepna" ladowala w uwagach zapisanego
    # artykulu, ktory chwile pozniej i tak wychodzil na Substacka.
    #
    # Dlatego polykamy tu WYLACZNIE awarie samej recenzji (zly JSON, timeout,
    # odmowa jednego wywolania). Wyczerpany budzet i wylacznik ida na wylot —
    # przy nich `stages.zweryfikuj` tez padnie i odda `safe_to_post: True`,
    # czyli publikacja poszlaby bez ANI JEDNEJ dzialajacej kontroli.
    try:
        raport = stages.review(conn, run_id, card, draft)
    except PRZERYWAJA as exc:
        # TEKST JUZ ISTNIEJE I JUZ ZA NIEGO ZAPLACONO — ratujemy go na dysk,
        # zanim wyjatek poleci dalej. To jedyna roznica wobec poprzedniej
        # wersji: `raise` byl tu goly, a `stages.save` stoi 60 linii nizej,
        # wiec przerwanie na recenzji kasowalo okolo 0,76 USD gotowego pisania.
        # Zapis NIE zmienia niczego innego: publikacja jest za tym `raise`, a
        # ratunek pisze POZA `ARTICLES_DIR` i bez wiersza w `articles`, wiec
        # zaden z szesciu czytelnikow korpusu go nie widzi.
        _ratuj_tekst(run_id, brief, card, draft, "recenzji", exc)
        raise
    except Exception as exc:
        print("  [awaria] recenzja padla (%s: %s) — zapisuje bez niej"
              % (type(exc).__name__, str(exc)[:120]), flush=True)
        raport = {"sentences": [], "unsupported_facts": [],
                  "summary": "recenzja niedostepna: %s" % type(exc).__name__}
    # Dwa zrodla nieopartych faktow, tak jak w run.py: jawna lista recenzenta
    # ORAZ zdania sklasyfikowane jako FACT z `supported: false`. Recenzent
    # wypelnia raz jedno, raz drugie, i branie tylko jednego gubi polowe.
    bez_pokrycia = list(raport.get("unsupported_facts") or [])
    znane = {str(x.get("text", ""))[:60] for x in bez_pokrycia}
    for s in raport.get("sentences") or []:
        if s.get("class") != "FACT" or s.get("supported") is not False:
            continue
        if str(s.get("text", ""))[:60] in znane:
            continue
        bez_pokrycia.append({"text": s.get("text", ""), "why": s.get("why", "")})

    try:
        forma = stages.ocen_forme(conn, run_id, draft)
    except PRZERYWAJA as exc:
        # Czwarta oslona, tej samej klasy co trzy powyzej. Gdy budzet konczy
        # sie dopiero tutaj (recenzja jeszcze przeszla), polkniecie prowadzi
        # do tej samej publikacji bez sprawdzenia faktow: `stages.zweryfikuj`
        # jest kolejnym platnym wywolaniem i padnie na tym samym bledzie.
        #
        # RATUNEK TAKI SAM JAK PRZY RECENZJI — tekst jest napisany i oplacony.
        # `raport` idzie dalej, bo recenzja TU JUZ PRZESZLA: ramka ma wyliczyc
        # to, czego naprawde nie bylo, a nie straszyc na zapas.
        _ratuj_tekst(run_id, brief, card, draft, "obserwacji formy", exc,
                     raport=raport)
        raise
    except Exception as exc:
        print("  [awaria] obserwacja formy padla (%s) — ide dalej"
              % type(exc).__name__, flush=True)
        forma = {}

    # BRAMKI JAKOSCI — dokladnie te, co w run.py. Pierwsza wersja tego
    # sterownika ich NIE WOLALA: sprawdzala `hasattr(stages, "uwagi_z_formy")`,
    # a ta funkcja mieszka w `gates`, wiec warunek byl zawsze falszywy i uwagi
    # cicho znikaly. Skrot, ktory wylaczal kontrole, nie wygladajac na to.
    import gates
    uwagi = gates.deterministic_floors(
        draft["body"], card,
        poprzednie=stages.poprzednie_teksty(pomin_tresc=draft["body"]))
    uwagi.extend(gates.uwagi_z_formy(forma, draft["body"]))
    # WIEK MATERIALU — jedyne sprawdzenie daty na tej sciezce. Patrz
    # `stages.swiezosc_karty`.
    uwagi.extend(stages.swiezosc_karty(card))
    for item in bez_pokrycia:
        uwagi.append({"gate": "FAKT_BEZ_POKRYCIA", "detail": item.get("text", "")})

    print()
    print("-- uwagi (nic nie blokuje) --", flush=True)
    for u in uwagi:
        print("   [%s] %s" % (u.get("gate"), str(u.get("detail"))[:150]), flush=True)
    if not uwagi:
        print("   czysto — zadna uwaga", flush=True)

    # STOPKA Z DATA ZRODEL WSTAWIANA PRZEZ KOD, NIE PRZEZ MODEL.
    # Karta zna te date (`source_dates["newest"]`), a prompt kazal MODELOWI
    # przepisac ja z pamieci — i trzy razy z rzedu przepisal zla, po czym
    # bramka faktow obalala za to caly gotowy artykul. Patrz
    # `stages.wstaw_date_zrodel`. Przed liczeniem dlugosci, zeby licznik slow
    # dotyczyl tekstu, ktory naprawde pojdzie.
    draft["body"] = stages.wstaw_date_zrodel(draft["body"], card)

    # OSTATNIA BRAMKA — PO STOPCE Z DATA, PRZED OKLADKA I PRZEGLADARKA.
    # Zmierzone 2026-09-06: artykul 0006 poszedl na konto ze zdaniem „Figures
    # checked against sources to unknown." i z pierwsza osoba o wyciagach.
    # Zaden etap ponizej nie umie tego cofnac, wiec pytanie pada tutaj —
    # i pada PRZED okladka, zeby nie placic za obraz do tekstu, ktory nie wyjdzie.
    artefakty = gates.artefakty_w_tekscie(
        "%s\n\n%s" % (draft.get("title", ""), draft["body"]))
    if artefakty:
        print()
        print("-- ZATRZYMANY: artefakty w tekscie --", flush=True)
        for a in artefakty:
            print("   [%s] %s" % (a["gate"], a["detail"][:170]), flush=True)
        sciezka = stages.save(conn, run_id, brief, card, draft, "ZATRZYMANY",
                              "; ".join(a["detail"] for a in artefakty)[:400],
                              [*uwagi, *artefakty])
        print(">> zapisano bez publikacji: %s" % sciezka, flush=True)
        return KOD_ZATRZYMANY

    if '--wyslij' in sys.argv:
        import json
        draft, audyt = stages.przygotuj_artykul_do_publikacji(conn, run_id, draft, card, raport)
        if not audyt.get('safe_to_post') or audyt.get('nie_sprawdzone'):
            sciezka = stages.save(conn, run_id, brief, card, draft, 'ZATRZYMANY',
                'FACTCHECK', [*uwagi, {'gate':'FACTCHECK', 'detail':json.dumps(audyt, ensure_ascii=False)}])
            print('>> odlozono ten artykul po kontroli faktow: %s' % sciezka, flush=True)
            return KOD_ZATRZYMANY

    status, blokada = gates.verdict(uwagi)
    notatki = [*uwagi,
               {"gate": "DLUGOSC", "detail": "%d slow" % len(draft["body"].split())},
               {"gate": "RECENZJA", "detail": raport.get("summary", "")}]

    # `blocked_by` to NAPIS, nie lista — sqlite nie przyjmie listy i caly
    # artykul przepada po zaplaceniu za niego. Zdarzylo sie raz, 25 sierpnia.
    sciezka = stages.save(conn, run_id, brief, card, draft, status,
                          blokada or "", notatki)
    print()
    print(">> zapisano: %s" % sciezka, flush=True)

    stages.grafika(conn, run_id, draft, sciezka_artykulu=sciezka)

    # --- PUBLIKACJA -------------------------------------------------------
    #
    # DLACZEGO TO TU DOSZLO. Sciezka artykulu byla rozdarta na dwie polowy i
    # zadna nie umiala calej roboty:
    #   `run.py --wyslij` publikuje i ma bramke faktow, ale bierze temat od
    #     skauta — a wlasnie skaut dawal monokulture (patrz naglowek tego
    #     pliku: trzy artykuly z rzedu o tych samych trzech obszarach),
    #   ten plik bierze temat z puli, ma bramke „uniesie artykul", podpytania
    #     i glebokosc z filarow — i nie umial opublikowac ani jednej linijki.
    # `nia-artykul.service` wskazywal caly czas na te pierwsza. Zastepnik
    # napisano, uzywano recznie i nigdy nie wpieto w zegar.
    #
    # DOMYSLNIE WYLACZONE. Bez `--wyslij` artykul konczy na dysku, tak jak dotad.
    if "--wyslij" not in sys.argv:
        print(">> bez --wyslij: artykul zostaje na dysku", flush=True)
        return 0

    import browser

    # SPRAWDZENIE FAKTOW JEST WPISEM W LOGU, NIE BRAMKA — i ten komentarz
    # przez chwile twierdzil co innego.
    #
    # Stal tu akapit „ta sama bramka, co w `run.py`. (...) Blokujemy wylacznie
    # wyjscie na zewnatrz", opisujacy zachowanie, ktore usunieto akapit nizej.
    # Czytajacy od gory dowiadywal sie, ze publikacja jest zablokowana przy
    # obalonym zdaniu — a nie jest. W miejscu dotyczacym tego, co wychodzi na
    # zewnatrz, nieaktualny opis kosztuje wiecej niz gdziekolwiek indziej.
    #
    # `zweryfikuj` przy wlasnej awarii przepuszcza — zepsuta weryfikacja nie
    # jest dowodem falszu.
    #
    # OBALONE ZDANIE NIE KONCZY PRZEBIEGU — WYPADA I TEKST IDZIE JESZCZE RAZ.
    #
    # Stalo tu `return 0` z komunikatem „do decyzji wlasciciela". To bylo
    # czekanie na czlowieka w systemie, ktorego CELEM jest zero zgod czlowieka,
    # i nikt tej gałęzi nie zamawial. 1 wrzesnia 2026 zatrzymala gotowy artykul
    # za JEDNO zdanie — stopke z data zrodel — przy audycie, ktory w tym samym
    # zdaniu napisal, ze wszystkie twierdzenia merytoryczne sa potwierdzone.
    #
    # Naprawa idzie u ZRODLA, a nie po fakcie: `wstaw_date_zrodel` kaze kodowi
    # napisac stopke z data z karty, wiec ta konkretna linijka — ta, ktora
    # blokowala trzy artykuly z rzedu — nie ma juz jak byc falszywa.
    #
    # WYCINANIA OBALONYCH ZDAN NIE MA I NIE MA BYC. Bylo zbudowane i zostalo
    # cofniete tego samego dnia na wyrazne polecenie wlasciciela: tekst z
    # wycietym zdaniem w srodku akapitu urywa sie w polowie mysli, a to jest
    # gorsze dla czytelnika niz jedno slabe zdanie. Sprawdzenie faktow zostaje
    # WYLACZNIE jako wpis w logu — widac, co model zakwestionowal, i tyle.
    print()
    print("-- fakty sprawdzone; publikacja gotowego materialu --", flush=True)
    print("-- publikacja --", flush=True)
    wynik = _opublikuj(sciezka)
    if wynik.get("wyslane"):
        print(">> OPUBLIKOWANY", flush=True)
        stages.zapomnij_niewystawiony()
        return 0

    # NIC SIE TU NIE ZATRZYMUJE I NIC NIE CZEKA NA CZLOWIEKA. Tekst lezy na
    # dysku, przebieg konczy sie normalnie. Zmienia sie WYLACZNIE to, co ten
    # przebieg o sobie mowi — i to, ze zostawia adres pliku rutynie dnia,
    # ktora chodzi PIEC RAZY DZIENNIE zamiast raz w tygodniu.
    #
    # ZMIERZONE PRZED NAPRAWA: przebieg z nieudana publikacja i przebieg
    # z udana zapisywaly sie w bazie IDENTYCZNIE — `DONE`, notatka pusta —
    # a trzy takie z rzedu nie budzily `sprawdz_przebiegi_i_ostrzez` ani razu.
    # Stalo tu BEZWARUNKOWE `return 0`.
    powod = str(wynik.get("blad") or "Substack nie potwierdzil publikacji")
    stages.zapamietaj_niewystawiony(sciezka, powod)
    print(">> ARTYKUL NIE POSZEDL: %s" % powod[:200], flush=True)
    print(">> tekst zostaje w %s — rutyna dnia sprobuje dalej" % sciezka,
          flush=True)
    return KOD_NIEOPUBLIKOWANY





if __name__ == "__main__":
    raise SystemExit(main())
