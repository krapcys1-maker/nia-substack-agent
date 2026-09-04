"""Bramki wykrywaja naruszenia, ale zadna nie blokuje artykulu.

Pierwotny wybor wlasciciela z 2026-08-15 wskazywal cztery blokujace bramki,
z udokumentowanym trafieniem kazdej na starym agencie. Biezacy `verdict`
zapisuje jednak wszystkie wyniki jako uwagi i zawsze zwraca status `SAVED`.

Podlogi porownuja tekst z KORPUSEM, nie z alfabetem. Kontrola „czy jest tu
cyfra" daje falszywe alarmy na zdaniach, ktore cytuja material; wlasciwe
pytanie brzmi, czy ta liczba wystepuje w materiale dowodowym.
"""

from __future__ import annotations

import json
import re
from typing import Any

import config
import jezyki

# Zmyślone przeżycie. Celowo NIE łapie pierwszej osoby w ogóle — „my reading",
# „I cannot tell you" to jawne wnioskowanie i jest dozwolone. Łapie czasowniki
# doświadczenia: rzeczy, których model nie mógł zrobić.
FABRICATED_EXPERIENCE = jezyki.wzorzec("ZMYSLONE_PRZEZYCIE", config.ARTICLE_LANGUAGE)

# Powołanie na badanie bez nazwania go. „In a shelf-life study at 8 °C" jest
# w porządku — niesie szczegół z karty. „According to a recent study" nie.
VAGUE_STUDY = jezyki.wzorzec("NIEISTNIEJACE_BADANIE", config.ARTICLE_LANGUAGE)

# --- podlogi z playbooka (2026-08-20) ------------------------------------
# Wszystkie ZAKAZUJA, zadna nie nakazuje pozycji. To rozroznienie jest tu
# najwazniejsze: regula zakazujaca usuwa wade i zostawia przestrzen otwarta,
# regula nakazujaca pozycje wypelnia ja jedna odpowiedzia i po dziesieciu
# tekstach sama staje sie podpisem maszyny. Juz raz na tym poleglismy —
# naprawa wad tresci zamienila sie w wade formy, bo prompt zamawial szkielet.

# Zastrzezenia w pierwszej osobie. Znakowanie wnioskowania jest DOBRE i
# recenzent wprost go chce — ale szesc raz w jednym tekscie to juz tik, nie
# uczciwosc. W tamtym artykule bylo szesc.
ZASTRZEZENIE = jezyki.wzorzec("ZASTRZEZENIE", config.ARTICLE_LANGUAGE)

# Obwieszczona powsciagliwosc. „Nie zmyslę tego" czyta sie jak poklepanie
# samego siebie po ramieniu; luke nazywa sie wprost, bez zapowiedzi cnoty.
POWSCIAGLIWOSC = jezyki.wzorzec("POWSCIAGLIWOSC", config.ARTICLE_LANGUAGE)

# Otwarcia, ktore kaza czytelnikowi isc cos obejrzec zamiast go zatrzymac.
# Lista jest z obserwacji, nie z gustu: jeden z tekstow zaczynal sie od „Turn over almost
# any packaged part" — i to samo zdanie zglosila niezaleznie bramka
# FAKT_BEZ_POKRYCIA, bo „almost any" bylo przesada nie do obrony.
ZAKAZANE_OTWARCIA = jezyki.wzorzec("ZAKAZANE_OTWARCIA", config.ARTICLE_LANGUAGE)

# Zrodlo, ktore nie jest zrodlem. Lapiemy je TYLKO w zdaniu z liczba —
# „in one survey" bez zadnej statystyki jest nieszkodliwe, z liczba jest
# przypisem donikad. tamten tekst: „In one survey, 68% of buyers thought…".
NIBY_ZRODLO = jezyki.wzorzec("NIBY_ZRODLO", config.ARTICLE_LANGUAGE)

# Akapit wyliczajacy niewiadome. Rozny od ZAPOWIEDZ_GRANIC, ktora pyta, czy
# zdanie mowi o sobie samym — ta pyta o POZYCJE. Zbiorcza lista granic pod
# koniec obniza temperature dokladnie tam, gdzie ma rosnac; pojedyncza
# niewiadoma postawiona tam, gdzie powstaje, nie przeszkadza nikomu.
_SYGNAL_NIEWIADOMEJ = jezyki.frazy("SYGNAL_NIEWIADOMEJ", config.ARTICLE_LANGUAGE)

DIGITS = re.compile(r"\d[\d.,]*")


def _digit_tokens(text: str) -> set[str]:
    return {m.group(0).rstrip(".,") for m in DIGITS.finditer(text)}


def _niepobrane(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Twierdzenia oznaczone `not_fetched` — dolozone, nie wyciagniete.

    Wstawia je `artykul_z_puli.py`: fakt z puli ciekawostek, ktory wybral temat,
    ma dojsc do pisarza i do sekcji `## Sources`, ale NIE jest wyciagiem z
    pobranego dokumentu — to wypowiedz modelu z `znajdz_ciekawostki` z
    doklejonym URL-em. Nikt tej strony nie pobral ani nie sklasyfikowal.
    """
    return [c for c in (card.get("confirmed_claims") or [])
            if isinstance(c, dict) and c.get("not_fetched")]


def _korpus_pobranych(card: dict[str, Any]) -> set[str]:
    """Liczby z materialu, ktory NAPRAWDE pobralismy.

    Bez tego korpus szedl z `json.dumps(card)`, czyli obejmowal takze
    twierdzenie dolozone recznie — a wtedy bramka zaczynala akceptowac liczby,
    ktorych nie ma w zadnym pobranym dokumencie. Kontrola liczb bez tej roznicy
    sprawdza sama siebie.

    ZOSTAJE ZNANA WADA, SZERSZA OD TEJ: karta niesie w tym momencie takze
    `ocena_ciekawosci` i `parallel_mechanisms` z banku, czyli wypowiedzi modelu
    z cytatami. Ich liczby nadal wchodza do korpusu. To osobna sprawa niz
    wstrzykniety fakt i osobna decyzja — tu zamykamy tylko to, co sami
    otworzylismy.
    """
    pobrane = dict(card)
    pobrane["confirmed_claims"] = [
        c for c in (card.get("confirmed_claims") or [])
        if not (isinstance(c, dict) and c.get("not_fetched"))]
    return _digit_tokens(json.dumps(pobrane, ensure_ascii=False))


def numbers_outside_corpus(body: str, card: dict[str, Any]) -> list[str]:
    """Liczby w tekście, których nie ma nigdzie w POBRANYM materiale."""
    corpus = _korpus_pobranych(card)
    return sorted(t for t in _digit_tokens(body) if t not in corpus)


def deterministic_floors(body: str, card: dict[str, Any],
                         poprzednie: list[str] | None = None
                         ) -> list[dict[str, str]]:
    """Podłogi bez modelu: 0 USD, milisekundy, zero wywołań.

    `poprzednie` to treści kilku ostatnich artykułów — potrzebne wyłącznie
    bramce `ODCISK_FORMY`. Bez nich reszta działa jak dotąd, więc stary
    sposób wywołania nadal jest poprawny.
    """
    findings: list[dict[str, str]] = []

    for match in FABRICATED_EXPERIENCE.finditer(body):
        findings.append({
            "gate": "ZMYSLONE_PRZEZYCIE",
            "detail": body[max(0, match.start() - 60):match.end() + 60].strip(),
        })
    for match in VAGUE_STUDY.finditer(body):
        findings.append({
            "gate": "NIEISTNIEJACE_BADANIE",
            "detail": body[max(0, match.start() - 60):match.end() + 60].strip(),
        })
    # DWIE UWAGI, NIE JEDNA. Liczba z faktu z puli NIE jest zmyślona — stoi w
    # rekordzie, który ma URL i datę i przeszedł bramkę świeżości. Nie jest
    # jednak w niczym, co pobraliśmy. Wrzucenie jej do korpusu uciszało
    # kontrolę; wrzucenie jej pod `LICZBA_SPOZA_KORPUSU` kazałoby komunikatowi
    # kłamać („nie występuje w materiale dowodowym"). Własna uwaga mówi prawdę
    # i podpowiada, co z nią zrobić.
    _z_puli = _digit_tokens(json.dumps(_niepobrane(card), ensure_ascii=False))
    for token in numbers_outside_corpus(body, card):
        if token in _z_puli:
            findings.append({
                "gate": "LICZBA_TYLKO_Z_PULI",
                "detail": (f"liczba {token!r} stoi wyłącznie na fakcie z puli "
                           "— tego dokumentu nikt nie pobrał, sprawdź ją w źródle"),
            })
        else:
            findings.append({
                "gate": "LICZBA_SPOZA_KORPUSU",
                "detail": f"liczba {token!r} nie występuje w materiale dowodowym",
            })
    for fraza in frazy_z_instrukcji(body):
        findings.append({
            "gate": "FRAZA_Z_INSTRUKCJI",
            "detail": f"{fraza!r} — zdanie z promptu, nie z myślenia",
        })
    zapowiedz = zapowiedziany_akapit_granic(body)
    if zapowiedz:
        findings.append({
            "gate": "ZAPOWIEDZ_GRANIC",
            "detail": "akapit o granicach zapowiada sam siebie: %r" % zapowiedz,
        })
    ile, hosty = szerokosc_podstawy(card)
    if ile < 2:
        findings.append({
            "gate": "WASKA_PODSTAWA",
            "detail": (f"artykuł stoi na {ile} źródle ({', '.join(hosty) or 'brak'})"
                       " — czytelnik zobaczy jeden odnośnik pod tekstem"),
        })

    # --- podlogi z playbooka (2026-08-20) --------------------------------
    zastrz = zastrzezenia(body)
    if len(zastrz) > config.BUDZET_ZASTRZEZEN:
        findings.append({
            "gate": "BUDZET_ZASTRZEZEN",
            "detail": "%d zastrzeżeń przy budżecie %d: %s"
                      % (len(zastrz), config.BUDZET_ZASTRZEZEN,
                         ", ".join(repr(z) for z in zastrz[:6])),
        })
    for m in POWSCIAGLIWOSC.finditer(body):
        findings.append({
            "gate": "OBWIESZCZONA_POWSCIAGLIWOSC",
            "detail": "%r — lukę nazywa się wprost, bez zapowiadania cnoty"
                      % body[max(0, m.start() - 40):m.end() + 20].strip(),
        })
    otwarcie = zakazane_otwarcie(body)
    if otwarcie:
        findings.append({
            "gate": "ZAKAZANE_OTWARCIE",
            "detail": "każe czytelnikowi iść coś obejrzeć: %r" % otwarcie,
        })
    for zdanie in statystyki_bez_zrodla(body):
        findings.append({
            "gate": "STATYSTYKA_BEZ_ZRODLA",
            "detail": "liczba bez przypisu: %r" % zdanie,
        })
    granice = niewiadome_na_koncu(body)
    if granice:
        findings.append({
            "gate": "NIEWIADOME_NA_KONCU",
            "detail": "zbiorcza lista granic w ostatniej trzeciej — %s" % granice,
        })
    ksztalt = powtorzona_forma(body, poprzednie or [])
    if ksztalt:
        findings.append({"gate": "ODCISK_FORMY", "detail": ksztalt})
    return findings


def _akapity(body: str) -> list[str]:
    return [a.strip() for a in re.split(r"\n\s*\n", body.split("## Sources")[0])
            if a.strip() and not a.strip().startswith(("#", "*", "-"))]


def zastrzezenia(body: str) -> list[str]:
    """Zastrzezenia w pierwszej osobie. Budzet: jedno na tekst."""
    return [m.group(0) for m in ZASTRZEZENIE.finditer(body)]


def zakazane_otwarcie(body: str) -> str:
    """Pierwsze zdanie, jesli kaze czytelnikowi isc cos obejrzec."""
    akapity = _akapity(body)
    if not akapity:
        return ""
    pierwsze = re.split(r"(?<=[.!?])\s+", akapity[0])[0]
    return pierwsze[:160] if ZAKAZANE_OTWARCIA.match(pierwsze) else ""


def statystyki_bez_zrodla(body: str) -> list[str]:
    """Zdania, ktore niosa liczbe i udaja, ze maja na nia zrodlo."""
    znalezione: list[str] = []
    for zdanie in re.split(r"(?<=[.!?])\s+", body.split("## Sources")[0]):
        if NIBY_ZRODLO.search(zdanie) and DIGITS.search(zdanie):
            znalezione.append(" ".join(zdanie.split())[:150])
    return znalezione


def niewiadome_na_koncu(body: str) -> str:
    """Zbiorczy akapit o niewiadomych w ostatniej trzeciej tekstu.

    To NIE to samo co `zapowiedziany_akapit_granic`, ktora pyta, czy zdanie
    mowi o samym sobie. Ta pyta wylacznie o POZYCJE. Powod jest prosty:
    lista granic pod koniec obniza temperature dokladnie tam, gdzie ma
    rosnac. Pojedyncza niewiadoma postawiona tam, gdzie powstaje, nikomu nie
    przeszkadza — dlatego wymagamy DWOCH sygnalow w jednym akapicie, czyli
    passusu, a nie jednego uczciwego przyznania sie.

    Tamten artykul mial taki akapit na 82% glebokosci, z czterema sygnalami.
    """
    korpus = body.split("## Sources")[0]
    akapity = _akapity(body)
    for a in akapity:
        niski = a.lower()
        if sum(1 for s in _SYGNAL_NIEWIADOMEJ if s in niski) < 2:
            continue
        poczatek = korpus.find(a[:60])
        if poczatek < 0:
            continue
        glebokosc = poczatek / max(1, len(korpus))
        if glebokosc >= 2 / 3:
            return "%.0f%% głębokości: %s" % (100 * glebokosc,
                                              " ".join(a.split())[:120])
    return ""


def odcisk_formy(body: str) -> dict[str, Any]:
    """Zgrubny szkielet tekstu — do porownania z poprzednimi, nie do oceny.

    Cechy sa CELOWO zgrubne. Nie chodzi o to, zeby dwa teksty roznily sie
    w szczegolach, tylko zeby nie mialy tego samego ksztaltu: tego samego
    otwarcia, tego samego miejsca na zwrot do czytelnika, tej samej dlugosci
    i tego samego rozkladu akapitow.

    Powod istnienia tej funkcji: dokladamy kilkadziesiat regul dotyczacych
    formy. Kazda z osobna poprawia tekst, wszystkie razem moga wyprodukowac
    szablon — a to jest ta sama wada, ktora juz raz zrobilismy, naprawiajac
    tresc i zamawiajac przy okazji szkielet.
    """
    korpus = body.split("## Sources")[0]
    akapity = _akapity(body)
    slowa = korpus.split()

    def kubelek(u: float | None) -> str:
        if u is None:
            return "brak"
        return ("0-25", "25-50", "50-75", "75-100")[min(3, int(u * 4))]

    ty = re.search(r"\byou(r)?\b", korpus, re.I)
    granice = niewiadome_na_koncu(body)

    return {
        "otwarcie": (akapity[0].split()[0].lower().strip('"“,.')
                     if akapity else ""),
        "liczba_w_otwarciu": bool(DIGITS.search(" ".join(slowa[:50]))),
        "pozycja_ty": kubelek(ty.start() / max(1, len(korpus)) if ty else None),
        "granice_na_koncu": bool(granice),
        "akapitow": len(akapity) // 3,
        "dlugosc": len(slowa) // 200,
    }


def powtorzona_forma(body: str, poprzednie: list[str],
                     prog: int = 5) -> str:
    """Czy ten tekst ma ksztalt ktoregos z poprzednich.

    `prog` to ile z szesciu cech musi sie zgodzic, zeby uznac ksztalt za
    powtorzony. Piec z szesciu, bo cztery zdarzaja sie przypadkiem przy
    tak zgrubnych kubelkach, a szesc zlapaloby dopiero blizniaka.
    """
    if not poprzednie:
        return ""
    moj = odcisk_formy(body)
    najlepsze, ktory = 0, -1
    trzon = " ".join(body.split())
    for i, inny in enumerate(poprzednie):
        # TEN SAM TEKST TO NIE POWTORZONA FORMA, tylko ten sam plik. W
        # przebiegu bramka woła się przed zapisem, więc do porównania nie
        # trafia — ale opieranie poprawności na kolejności dwóch linijek
        # w innym module jest za cienkie. Przy pierwszym uruchomieniu na
        # zapisanym już artykule wychodzi 6 z 6 cech i wygląda jak alarm.
        if " ".join(inny.split()) == trzon:
            continue
        wspolne = sum(1 for k, v in moj.items() if odcisk_formy(inny).get(k) == v)
        if wspolne > najlepsze:
            najlepsze, ktory = wspolne, i
    if najlepsze < prog:
        return ""
    return ("ten sam szkielet co %d. z ostatnich tekstów — %d z %d cech "
            "wspólnych (%s)" % (ktory + 1, najlepsze, len(moj),
                                ", ".join("%s=%s" % (k, v) for k, v in moj.items())))


def uwagi_z_formy(obserwacja: dict[str, Any], body: str) -> list[dict[str, str]]:
    """Zamienia obserwacje modelu w uwagi. MODEL OBSERWUJE, KOD ROZSTRZYGA.

    Model oddaje cytaty i odpowiedzi tak/nie. Liczenie beatów, dzielenie przez
    długość i szukanie pozycji w tekście robimy tutaj, bo to arytmetyka, a
    arytmetyka modelu jest niesprawdzalna.

    JEDNA SWIADOMA ROZNICA WOBEC PLAYBOOKA. Playbook chce, zeby moment
    przylapania czytelnika stal miedzy 25 a 40 procentem glebokosci. Nie
    zglaszamy pozycji — zglaszamy wylacznie BRAK. Powod: regula nakazujaca
    pozycje wypelnia ja jedna odpowiedzia i po dziesieciu tekstach sama staje
    sie podpisem maszyny, a to jest dokladnie ta wada, ktora juz raz zrobilismy,
    naprawiajac tresc i zamawiajac przy okazji szkielet. Pozycje LICZYMY i
    zapisujemy jako informacje dla wlasciciela, ale nie jest wada.
    """
    uwagi: list[dict[str, str]] = []
    korpus = body.split("## Sources")[0]
    slow = max(1, len(korpus.split()))

    przekonania = obserwacja.get("beliefs") or []
    wsparcie = obserwacja.get("support_only") or []
    if przekonania:
        na_beat = slow / max(1, len(przekonania))
        if na_beat > config.SLOW_NA_BEAT:
            powtorki = [str(w.get("quote", ""))[:70] for w in wsparcie]
            uwagi.append({
                "gate": "GESTOSC_BEATOW",
                "detail": ("%d przekonań na %d słów — jedno co %.0f słów "
                           "przy progu %d; samo wsparcie: %s"
                           % (len(przekonania), slow, na_beat,
                              config.SLOW_NA_BEAT,
                              " | ".join(powtorki[:3]) or "brak")),
            })

    if obserwacja.get("same_register") is True:
        twardy = (obserwacja.get("hardest_fact") or {}).get("quote", "")
        proceduralne = (obserwacja.get("procedural_nearby") or {}).get("quote", "")
        uwagi.append({
            "gate": "BRAK_ESKALACJI",
            "detail": ("najmocniejszy fakt idzie tym samym tonem co szczegół "
                       "proceduralny — %r obok %r"
                       % (twardy[:80], proceduralne[:70])),
        })

    moment = obserwacja.get("reader_moment")
    if not moment or not (moment or {}).get("quote"):
        uwagi.append({
            # TRESC KOMUNIKATU OPISYWALA KONTRAKT, KTOREGO JUZ NIE MA.
            # `forma.md` przestal wymagac fizycznego przedmiotu („It does not
            # have to be a thing they can pick up"), bo pod AI wiekszosc
            # artykulow zadnego nie ma; bramka sprawdza wylacznie obecnosc
            # `quote`. Zachowanie sie nie zmienilo, ale wlasciciel czytajacy
            # `.uwagi.md` dostawal opis reguly z epoki przedmiotow.
            "gate": "CZYTELNIK_NIEPRZYLAPANY",
            "detail": ("nigdzie nie ma zwrotu do TEGO czytelnika z jedna "
                       "rzecza z jego wlasnego zycia — odpowiedz, ktora dostal, "
                       "cena, ktora zaplacil, decyzja o nim; statystyka o "
                       "innych to nie to"),
        })

    otwarcie = obserwacja.get("opening_claim") or {}
    if otwarcie.get("already_familiar"):
        uwagi.append({
            "gate": "OTWARCIE_ZNANE",
            "detail": ("pierwszy akapit stoi na twierdzeniu, które czytelnik "
                       "zna: %r" % str(otwarcie.get("quote", ""))[:90]),
        })
    return uwagi


def pozycja_w_tekscie(cytat: str, body: str) -> float | None:
    """Gdzie w tekście stoi ten cytat, jako ułamek długości. Informacja, nie ocena."""
    if not cytat:
        return None
    korpus = body.split("## Sources")[0]
    i = korpus.find(cytat[:60].strip())
    if i < 0:
        zwarty = " ".join(cytat.split()[:8])
        i = korpus.find(zwarty)
    return None if i < 0 else i / max(1, len(korpus))


def szerokosc_podstawy(card: dict[str, Any]) -> tuple[int, list[str]]:
    """Na ilu ODREBNYCH serwisach stoja potwierdzone twierdzenia.

    Artykul 0020 („The Fossil of a Vote") byl najlepszy z serii i mial pod
    soba JEDEN odnosnik — nekrolog z Columbii. Tekst byl skrupulatny wobec
    tego, co zapis mowi, ale post z jednym zrodlem wyglada cienko niezaleznie
    od tego, jak dobrze jest napisany. To uwaga, nie blokada: czasem jedno
    zrodlo to cala dokumentacja, jaka w ogole istnieje.

    NIE LICZYMY HOSTA, KTOREGO NIKT NIE POBRAL. Sciezka artykulu z puli doklada
    do karty fakt, ktory wybral temat — z URL-em, ale bez pobrania i bez
    klasyfikacji. Liczony razem z reszta dawal drugiego hosta z niczego, wiec
    `WASKA_PODSTAWA` MILCZALA na artykule stojacym realnie na jednym zrodle.
    Uwaga, ktora zamyka sie sama od dolozonego wpisu, nie jest uwaga.

    Odnosnik i tak trafia pod tekst — `stages.save` sklada sekcje `## Sources`
    z tych samych `confirmed_claims`, a ona nie pyta o `not_fetched`. Czytelnik
    widzi wiec dwa odnosniki, a wlasciciel dostaje uwage, ze pobrany jest jeden.
    """
    from urllib.parse import urlparse

    hosty: list[str] = []
    for c in card.get("confirmed_claims", []) or []:
        if isinstance(c, dict) and c.get("not_fetched"):
            continue
        url = c.get("url")
        if not url:
            continue
        host = (urlparse(url).netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host and host not in hosty:
            hosty.append(host)
    return len(hosty), hosty


def frazy_z_instrukcji(body: str, dlugosc: int = 6) -> list[str]:
    """Czy pisarz wklein do tekstu wlasne polecenie.

    W 0020 wyszlo „in the simplest sentence that is still true" — dokladnie
    tak, jak stoi w `pisarz.md`. Czytelnik tego nie rozpozna, ale to nie jest
    zdanie z myslenia, tylko echo instrukcji, i wracajac w kolejnych tekstach
    staje sie podpisem maszyny.

    Porownujemy ciagi szesciu slow. Prompt to sam metatekst, wiec kazde takie
    pokrycie jest przeciekiem, nie zbiegiem okolicznosci — a sprawdzenie samo
    sie utrzymuje, gdy prompt sie zmieni.
    """
    def slowa_z(tekst: str) -> list[str]:
        return re.findall(r"[a-z]+", tekst.lower())

    def ciagi(slowa: list[str]) -> list[tuple[str, ...]]:
        return [tuple(slowa[i:i + dlugosc])
                for i in range(len(slowa) - dlugosc + 1)]

    try:
        instrukcja = (config.PROMPTS_DIR / "pisarz.md").read_text(encoding="utf-8")
    except OSError:
        return []
    z_promptu = set(ciagi(slowa_z(instrukcja)))
    slowa = slowa_z(body)
    trafione = [i for i, c in enumerate(ciagi(slowa)) if c in z_promptu]

    # Jedna wklejka daje kilka zachodzacych na siebie ciagow. Skladamy je
    # z powrotem w jedna, najdluzsza fraze — inaczej jeden blad wyglada jak piec.
    trafienia: list[str] = []
    i = 0
    while i < len(trafione):
        koniec = i
        while koniec + 1 < len(trafione) and trafione[koniec + 1] == trafione[koniec] + 1:
            koniec += 1
        fraza = " ".join(slowa[trafione[i]:trafione[koniec] + dlugosc])
        if fraza not in trafienia:
            trafienia.append(fraza)
        i = koniec + 1
    return trafienia


def verdict(findings: list[dict[str, str]]) -> tuple[str, str | None]:
    """Artykuł powstaje ZAWSZE. Decyzja właściciela z 2026-08-15.

    Skoro temat przeszedł odsiew, a research jest opłacony i zrobiony, nie ma
    stanu „zablokowany i koniec". Uwagi wracają do właściciela do przeczytania
    i ewentualnej poprawki — ale tekst istnieje. Zablokowany artykuł to czysta
    strata 1,30 USD researchu i zero informacji w zamian.
    """
    return "SAVED", None


# Slowa, po ktorych poznac, ze zdanie mowi O AKAPICIE, a nie o temacie.
_META_GRANIC = jezyki.frazy("META_GRANIC", config.ARTICLE_LANGUAGE)


def zapowiedziany_akapit_granic(body: str) -> str:
    """Czy akapit o granicach zaczyna sie od zdania o samym sobie.

    Zakazywanie konkretnych fraz nie dziala: przy kazdym zakazie nastepny
    artykul znajdowal nowy sposob na to samo. Trzy zaobserwowane warianty
    tej samej wady, kolejno: „a few things this evidence does not settle",
    „what the record here does not establish deserves saying once",
    „what the regulation and the proposed rule leave open is worth stating
    plainly".

    Wiec sprawdzamy STRUKTURE: zdanie otwierajace akapit, ktory wylicza
    granice, ma zaczynac sie od granicy, nie od zapowiedzi. Szukamy akapitow
    mowiacych o tym, czego zapis NIE ustala, i patrzymy na ich pierwsze zdanie.
    """
    for akapit in re.split(r"\n\s*\n", body):
        a = akapit.strip()
        if len(a.split()) < 25:
            continue
        # Czy to w ogole akapit o granicach.
        niski = a.lower()
        if not any(z in niski for z in ("does not", "do not", "not establish",
                                        "leaves open", "not settled", "nothing here")):
            continue
        pierwsze = re.split(r"(?<=[.!?])\s+", a)[0]
        # Tylko POCZATEK zdania. Zdanie moze legalnie wspomniec o zapisie
        # w drugiej polowie — "converting it into minutes is the reader's
        # invention, not the record's" jest poprawne i konkretne. Wada polega
        # na tym, ze zdanie ZACZYNA sie od mowienia o akapicie.
        poczatek = " ".join(pierwsze.lower().split()[:10])
        if any(w in poczatek for w in _META_GRANIC):
            return pierwsze[:150]
    return ""
