"""Głos redakcyjny: korpus próbek i dwa profile stylu.

Jedyna rzecz odróżniająca to konto od tysiąca innych. Korpus jest przypięty
hashem SHA-256 i loader ODMAWIA, jeśli się nie zgadza — nie po to, żeby było
formalnie, tylko żeby nikt po cichu nie podmienił głosu, na który właściciel
się zgodził.

Do promptu trafia 3-5 krótkich fragmentów dobranych wg funkcji retorycznej,
nigdy cały korpus. Fragment ilustruje RUCH, nie frazę do przepisania — dlatego
wszystko dłuższe niż 900 znaków jest odrzucane.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import config

MIN_EXAMPLE_CHARS = 150
MAX_EXAMPLE_CHARS = 900

# Funkcje retoryczne, po jednym akapicie na każdą. Nazwy są kontraktem między
# tym modułem, `przypnij_styl.py` i promptem pisarza.
FUNKCJE_STYLU = ("OPENING", "CONCRETE_TO_SYSTEM", "MECHANISM",
                 "COUNTERARGUMENT", "ENDING")

# PRZYPIĘCIA WYSZŁY Z KODU DO PLIKU OBOK KORPUSU.
#
# Stała `APPROVED_EXAMPLES` trzymała numery akapitów i skróty treści dla
# JEDNEGO konkretnego korpusu — a ten korpus był cudzą, opublikowaną
# publicystyką i musiał wyjść z repozytorium. Numer akapitu 65 nie znaczy nic
# w korpusie, którego nikt poza autorem tamtego pliku nie ma.
#
# Zabezpieczenie zostaje co do joty: korpus wciąż musi zgadzać się ze skrótem,
# a każdy przykład wciąż ma przypięty numer ORAZ skrót treści, więc edycja
# przesuwająca akapit zatrzymuje pisarza zamiast po cichu zmienić głos.
# Zmieniło się tylko to, GDZIE te wartości stoją: w `przypiecia.json` obok
# korpusu, generowanym przez `narzedzia/przypnij_styl.py`.
NAZWA_PRZYPIEC = "przypiecia.json"


def _plik_przypiec() -> Path:
    return config.STYLE_CORPUS.parent / NAZWA_PRZYPIEC


class StyleError(RuntimeError):
    pass


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_paragraphs(raw: bytes) -> tuple[str, ...]:
    """Deterministyczny podział na akapity; styl końca linii nie zmienia numeracji."""
    normalized = bajty_kanoniczne(raw).decode("utf-8")
    blocks = [block.strip() for block in normalized.split("\n\n")]
    return tuple(block for block in blocks if block)


def bajty_kanoniczne(raw: bytes) -> bytes:
    """Bajty korpusu niezależne od tego, jak git zmaterializował plik.

    Pin dotyczy TREŚCI, nie ustawienia `core.autocrlf` konkretnej maszyny.
    Na Windowsie ten sam tekst wychodzi z checkoutu z CRLF i daje inny skrót —
    a `split_paragraphs` tuż niżej i tak normalizuje końce linii, mówiąc wprost
    „styl końca linii nie zmienia numeracji". Plik przeczył więc sam sobie:
    dwa wiersze niżej końce linii były bez znaczenia, a przy skrócie
    rozstrzygały o tym, czy pisarz w ogóle ruszy.

    KOSZTOWAŁO TO OPŁACONY RESEARCH. Przebieg 13 (18 sierpnia) stoi w bazie
    produkcyjnej jako FAILED na etapie `write` z powodem „korpus stylu nie
    zgadza się z przypiętym hashem" — research zapłacony, artykułu nie ma.

    Normalizujemy WYŁĄCZNIE zakończenia linii. Każda inna różnica bajtowa
    nadal zatrzymuje pisarza i tak ma zostać: korpus stylu to jedyna rzecz
    odróżniająca to konto od tysiąca innych.
    """
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def wczytaj_przypiecia() -> dict:
    """Przypięcia korpusu z pliku obok niego. Brak pliku = czytelny błąd.

    KOMUNIKAT MA MÓWIĆ, CO ZROBIĆ. Poprzedni brzmiał „brak korpusu stylu:
    <ścieżka>" i zostawiał operatora z pustym katalogiem oraz pytaniem, co
    tam właściwie ma trafić. To jedyne miejsce w całym agencie, gdzie
    instalacja wymaga materiału, którego kod nie może dostarczyć.
    """
    plik = _plik_przypiec()
    if not plik.exists():
        raise StyleError(
            "korpus stylu nie jest przypięty — brak %s\n"
            "\n"
            "  1. wrzuć swój korpus (.txt, akapity oddzielone pustą linią) do %s\n"
            "  2. python narzedzia/przypnij_styl.py --pokaz\n"
            "  3. python narzedzia/przypnij_styl.py --wybor OPENING=...,ENDING=...\n"
            "\n"
            "Szczegóły w %s/README.md. Korpus MUSI być twój albo taki, do\n"
            "którego masz prawa — nie cudza opublikowana publicystyka."
            % (plik, plik.parent, plik.parent))
    try:
        dane = json.loads(plik.read_text(encoding="utf-8"))
    except Exception as exc:                              # noqa: BLE001
        raise StyleError("%s jest nieczytelny (%s: %s) — przypnij korpus od nowa"
                         % (plik, type(exc).__name__, exc))
    for pole in ("korpus_sha256", "przyklady"):
        if pole not in dane:
            raise StyleError("%s: brak pola %r — przypnij korpus od nowa"
                             % (plik, pole))
    return dane


def load_examples() -> list[dict[str, str]]:
    """Zwraca zatwierdzone fragmenty stylu albo rzuca, jeśli korpus się nie zgadza."""
    path = config.STYLE_CORPUS
    przypiecia = wczytaj_przypiecia()
    if not path.exists():
        raise StyleError(
            "przypięcia są (%s), ale samego korpusu nie ma: %s\n"
            "Plik nazywał się %r. Wróć nim na miejsce albo przypnij korpus od nowa."
            % (_plik_przypiec(), path, przypiecia.get("plik", "?")))
    raw = path.read_bytes()
    digest = hashlib.sha256(bajty_kanoniczne(raw)).hexdigest()
    if digest != przypiecia["korpus_sha256"]:
        raise StyleError(
            "korpus stylu nie zgadza się z przypiętym hashem — odmawiam uczenia "
            f"pisarza nieprzejrzanego głosu.\n  oczekiwano: {przypiecia['korpus_sha256']}"
            f"\n  jest:       {digest}"
            "\n  (jeśli zmiana była zamierzona: python narzedzia/przypnij_styl.py)"
        )

    paragraphs = split_paragraphs(raw)
    wybrane = {p["funkcja"]: p for p in przypiecia["przyklady"]}
    brak = [f for f in FUNKCJE_STYLU if f not in wybrane]
    if brak:
        raise StyleError("przypięcia nie mają funkcji: %s — przypnij korpus od nowa"
                         % ", ".join(brak))

    examples: list[dict[str, str]] = []
    for function in FUNKCJE_STYLU:
        ordinal = wybrane[function]["akapit"]
        pinned = wybrane[function]["skrot"]
        if ordinal >= len(paragraphs):
            raise StyleError(f"korpus ma {len(paragraphs)} akapitów, brak {ordinal}")
        text = paragraphs[ordinal]
        if _sha256(text)[:10] != pinned:
            raise StyleError(
                f"akapit {ordinal} ({function}) nie zgadza się z przypiętym skrótem: "
                f"{_sha256(text)[:10]} zamiast {pinned}"
            )
        if not MIN_EXAMPLE_CHARS <= len(text) <= MAX_EXAMPLE_CHARS:
            raise StyleError(
                f"akapit {ordinal} ma {len(text)} znaków, poza {MIN_EXAMPLE_CHARS}"
                f"-{MAX_EXAMPLE_CHARS}"
            )
        examples.append({"function": function, "text": text})
    return examples


def load_profiles() -> tuple[str, str]:
    """Profil pozytywny i negatywny stylu artykułu."""
    base = config.STYLE_PROFILES_DIR
    positive = base / "ARTICLE_STYLE_PROFILE_V1.md"
    negative = base / "ARTICLE_NEGATIVE_STYLE_PROFILE_V1.md"
    for path in (positive, negative):
        if not path.exists():
            raise StyleError(f"brak profilu stylu: {path}")
    # NAZWA MARKI PODSTAWIANA, NIE WPISANA. Oba profile zaczynaly sie od
    # zdania „Zakres: artykuly marki <NAZWA>" z nazwa wpisana w tresc — czyli
    # przy zmianie konta trzeba bylo pamietac o dwoch plikach, ktore nie
    # wygladaja na konfiguracje. Mapa `docs/IDENTITY_MAP.md` wskazala je jako
    # miejsca, do ktorych nie siega zadne pole.
    #
    # Podstawienie robimy TUTAJ, a nie przez `stages._prompt`: tresc profilu
    # jest do promptu WSTAWIANA jako wartosc, wiec `str.format` juz jej nie
    # dotyka i `{marka}` w srodku zostaloby doslownie.
    return (
        _z_marka(positive.read_text(encoding="utf-8")),
        _z_marka(negative.read_text(encoding="utf-8")),
    )


def _z_marka(tekst: str) -> str:
    """Podstawia `{marka}` w profilu stylu. Profil bez pola zostaje bez zmian."""
    return tekst.replace("{marka}", config.NAZWA_MARKI)


# USUNIETE: `corpus_words()`.
#
# Funkcja bez ANI JEDNEGO wolajacego — sprawdzone skanem po calym drzewie
# (kod, testy, narzedzia). Zwracala wszystkie slowa korpusu stylu, a jej
# docstring opisywal zasade „podloga porownuje tekst z KORPUSEM, nie
# z alfabetem".
#
# Zasada zyje i jest wykonywana — tyle ze gdzie indziej i przeciwko innemu
# korpusowi: `gates.numbers_outside_corpus` porownuje liczby z MATERIALEM
# DOWODOWYM artykulu, a nie z probkami stylu. Do tamtego pytania korpus stylu
# jest zlym zbiorem: to piec akapitow cudzej prozy, a nie zrodla tego tekstu.
#
# Do tego funkcja wywracalaby sie na swiezej instalacji: `STYLE_CORPUS`
# czesto jeszcze nie istnieje, a `read_bytes()` nie pyta o to.
#
# Zostawiona jako komentarz, a nie skasowana bez sladu, bo nastepny czytelnik
# ma wiedziec, ze pytanie „czy ta liczba jest w korpusie" JEST zadawane —
# w `gates`, i o wlasciwy korpus.
