# -*- coding: utf-8 -*-
"""Audyt przed wydaniem: czy w drzewie nie ma tozsamosci, sekretow i sprzecznosci.

Ten plik istnieje, bo skany robione recznie mialy dziury, i to nie teoretyczne:

  * skan po nazwie konta NIE ZNALAZL jej w `SCOUT_SYSTEM`, gdzie byla rozbita
    miedzy dwa literaly pythonowe (`'Nothing Is "` + `"Accidental'`);
  * skan po frazie tematu NIE ZNALAZL jej w promptach, gdzie byla przecieta
    koncem linii (`artificial\\nintelligence`);
  * skan `git ls-files` nie widzi HISTORII, a w niej lezalo 12 zacommitowanych
    baz danych, ktorych nie ma w zadnej galezi.

Kazda z tych dziur ma tutaj wlasna sekcje. Audyt sprawdza CZTERY drogi:
po zrodle, po WARTOSCI sklejonych literalow, po nazwach plikow i po historii.

Uruchomienie:
    python narzedzia/audyt.py           # drzewo robocze
    python narzedzia/audyt.py --historia  # takze cala historia gita (wolne)
"""
from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import unicodedata
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent

# --- tozsamosc: wzorce UNIWERSALNE i te wlasne ------------------------------
#
# Wzorce ponizej sa niezalezne od konta: adresy IP, logowanie po ssh, nazwy
# kluczy. Sa tu, bo nie zdradzaja niczyjej tozsamosci, a lapia jej wyciek.
TOZSAMOSC_UNIWERSALNA = [
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b(?<!0\.0\.0\.0)(?<!127\.0\.0\.1)",
     "adres IP w drzewie"),
    (r"ssh\s+(?:-i\s+\S+\s+)?[a-z_][a-z0-9_-]*@[\w.-]+", "polecenie ssh na konkretny host"),
    (r"id_(?:rsa|ed25519|ecdsa)_\w+", "nazwa konkretnego klucza SSH"),
    (r"[a-z_][a-z0-9_-]*@(?:\d{1,3}\.){3}\d{1,3}", "logowanie uzytkownik@adres"),
]

# WZORCE WLASNE — poprzednia nazwa konta, adres serwera, tytuly opublikowanych
# tekstow. NIE STOJA W REPOZYTORIUM i to jest cala rzecz: narzedzie pilnujace
# przeciekow nie moze samo byc przeciekiem.
#
# Do 2026-09-03 stala tu wpisana nazwa poprzedniego konta jako wzorzec do
# szukania. Dzialalo — i jednoczesnie znaczylo, ze ta nazwa jest w publicznym
# repozytorium i da sie ja znalezc wyszukiwarka. Dla kogokolwiek innego
# pilnowanie CUDZEGO starego uchwytu i tak nie ma sensu.
#
# Wzorzec: `narzedzia/dawne-tozsamosci.example.txt`. Plik roboczy jest
# w .gitignore.
PLIK_WLASNYCH = pathlib.Path(__file__).resolve().parent / "dawne-tozsamosci.txt"


def tozsamosc_wlasna() -> list[tuple[str, str]]:
    """Wzorce z pliku poza repozytorium. Brak pliku = pusta lista."""
    if not PLIK_WLASNYCH.exists():
        return []
    out = []
    for nr, linia in enumerate(
            PLIK_WLASNYCH.read_text(encoding="utf-8").splitlines(), 1):
        linia = linia.strip()
        if not linia or linia.startswith("#"):
            continue

        # ZNAK STERUJACY W WZORCU TO WZORZEC MARTWY, KTORY WYGLADA NA ZYWY.
        #
        # Zmierzone: linia 100 tego pliku brzmiala `\x08o1\x08` — „o1"
        # otoczone backspace'ami, ktore wjechaly przy wklejaniu. Wzorzec
        # KOMPILUJE SIE poprawnie (backspace to zwykly znak), stoi na liscie,
        # jest liczony w podsumowaniu — i nie moze dopasowac sie do niczego,
        # bo w zadnym pliku zrodlowym backspace nie wystepuje.
        #
        # Audyt raportowal wiec „brak: wzorzec o1" na zielono nad plikiem,
        # ktory to `o1` zawieral. Znalezione czytaniem `stages.py`, nie
        # audytem — bo audyt byl tu wlasnie sluszny i wlasnie bezuzyteczny.
        sterujace = sorted({c for c in linia if ord(c) < 32})
        if sterujace:
            raise SystemExit(
                "%s linia %d: wzorzec %r zawiera znaki sterujace (%s).\n"
                "Taki wzorzec kompiluje sie i NIE LAPIE NICZEGO — wyglada\n"
                "na dzialajacy, a jest martwy. Przepisz go recznie."
                % (PLIK_WLASNYCH.name, nr, linia,
                   ", ".join("\\x%02x" % ord(c) for c in sterujace)))

        try:
            re.compile(linia)
        except re.error as exc:
            raise SystemExit("%s linia %d: zly wzorzec %r (%s)"
                             % (PLIK_WLASNYCH.name, nr, linia, exc))
        out.append((linia, "wzorzec wlasny z %s" % PLIK_WLASNYCH.name))
    return out


# Pliki, ktorych NIGDY nie moze byc w repozytorium.
ZAKAZANE_PLIKI = [
    (r"(^|/)\.env$", "plik z kluczami"),
    (r"storage-state", "sesja przegladarki"),
    # DANE, nie modul. Pierwsza wersja brzmiala `subskryben` i trafiala
    # w `agent-v2/kopia_subskrybentow.py` — czyli w NARZEDZIE robiace kopie,
    # a nie w kopie. Audyt krzyczacy na wlasny kod uczy ignorowania audytu.
    (r"subskrybenci.*\.(csv|json|txt)$", "lista subskrybentow (cudze adresy e-mail)"),
    (r"(^|/)konfiguracja\.toml$", "konfiguracja instalacji (uchwyt konta)"),
    (r"\.db$", "baza danych"),
    (r"dziennik\.jsonl$", "dziennik dzialan"),
    (r"(^|/)kopie/", "kopie list subskrybentow"),
]

# Prawdziwe klucze API. Atrapy w testach musza przechodzic, wiec wzorzec
# wymaga DLUGOSCI, jaka ma prawdziwy klucz.
SEKRETY = [
    (r"sk-ant-[A-Za-z0-9_-]{40,}", "klucz Anthropic"),
    (r"sk-proj-[A-Za-z0-9_-]{40,}", "klucz OpenAI"),
    (r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----", "klucz prywatny"),
]

NIGDY_NIE_PASUJE = r"(?!x)x"

POMIN_SUFIKSY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".db", ".pyc"}
zdane = oblane = 0
uwagi: list[str] = []


def uwaga(nazwa: str, szczegol: object = "") -> None:
    """Trzeci glos: nie awaria, tylko dwa pola operatora, ktore sie rozjechaly.

    Audyt umial dotad powiedziec wylacznie OK albo BLAD, wiec kazde
    niedopasowanie CUDZEJ konfiguracji szlo jako BLAD i kod wyjscia 1 — czyli
    narzedzie oblewalo na poprawnej instalacji. To jest najkrotsza droga do
    tego, ze operator przestaje je uruchamiac.

    UWAGA JEST WIDOCZNA I POLICZONA — nie zmienia tylko kodu wyjscia. Cicha
    byla by gorsza od oblanej: udawalaby dowod.
    """
    uwagi.append(nazwa)
    print("  UWAGA %s   %s" % (nazwa, szczegol))


def sprawdz(nazwa: str, warunek: bool, szczegol: object = "") -> None:
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def sledzone() -> list[pathlib.Path]:
    out = subprocess.run(["git", "-C", str(KORZEN), "ls-files"],
                         capture_output=True, text=True, encoding="utf-8")
    return [KORZEN / n for n in out.stdout.splitlines() if n.strip()]


# Zawiniecie wiersza w komentarzu (`#`), w cytacie Markdown (`>`)
# i w bloku dokumentacyjnym (` * `). Znak wiodacy razem z otaczajaca
# spacja znika, a w jego miejsce wchodzi JEDNA spacja.
LAMANIE = re.compile(r"[ \t]*\r?\n[ \t]*(?:#+|>+|\*)?[ \t]*")


def bez_lamania(t: str) -> str:
    return LAMANIE.sub(" ", t)


# Znaki, ktore nigdy nie stoja W SRODKU nazwy, ale potrafia stanac miedzy
# jej czesciami w zrodle: cudzyslow, apostrof, backtick, plus, ukosnik.
SKLEJKI = re.compile(r"[\"'`+\\]+")


def bez_sklejek(t: str) -> str:
    return re.sub(r"[ \t]{2,}", " ", SKLEJKI.sub("", bez_lamania(t)))


def teksty() -> list[tuple[pathlib.Path, str]]:
    out = []
    for p in sledzone():
        if p.suffix.lower() in POMIN_SUFIKSY or not p.is_file():
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # SKLEJONA KOPIA DOKLEJONA DO ORYGINALU. Wzorce maja `\s+`
        # zamiast spacji, zeby przezyc zawiniecie wiersza — ale
        # w KOMENTARZU nastepna linia zaczyna sie od `#`, ktory bialym
        # znakiem nie jest. Tak przezyl w `run.py` tytul prawdziwego
        # artykulu, zlamany po slowie „Was": stalo tam `Was` + koniec
        # linii + wciecie + `#` + ` Never`, a wzorzec szukal `Was\s+Never`.
        # Audyt swiecil na zielono nad jawnym tytulem przez cala serie
        # przebiegow. Skanujemy oryginal ORAZ wersje bez lamania —
        # trafienie w ktorejkolwiek jest bledem.
        # TRZECI WIDOK: bez cudzyslowow, apostrofow, backtickow, plusow
        # i ukosnikow. Bez niego nazwa konta przezyla W OPISIE TEGO, JAK
        # SIE CHOWALA — komentarz cytowal rozbity literal w calosci,
        # a miedzy slowami stalo `" "`, wiec ani wzorzec ze `\s+`, ani
        # sklejanie zawiniec go nie widzialo. Czlowiek czytal nazwe
        # bez wysilku; skan nie.
        out.append((p, "\n".join((t, bez_lamania(t), bez_sklejek(t)))))
    return out


def wzgledna(p: pathlib.Path) -> str:
    return str(p.relative_to(KORZEN)).replace("\\", "/")


def main() -> int:
    pliki = teksty()
    ten_plik = pathlib.Path(__file__).resolve()
    # PLIKI, KTORE WZORCE TOZSAMOSCI ZAWIERAJA Z DEFINICJI, bo ich SZUKAJA.
    # Bez tego audyt zglasza sam siebie i workflow CI, a audyt dajacy zawsze
    # cztery falszywe alarmy przestaje byc czytany.
    # PLIKI, KTORE ZAWIERAJA WZORCE Z DEFINICJI. Po dolozeniu widoku
    # `bez_sklejek` doszedl trzeci: przyklad w pliku-wzorcu zapisany jako
    # `203\.0\.113\.42` po zdjeciu ukosnikow jest poprawnym adresem IP.
    # Sam adres pochodzi z zakresu RFC 5737, zarezerwowanego wlasnie do
    # dokumentacji — nie prowadzi donikad.
    SZUKAJACE = {ten_plik,
                 (KORZEN / ".github/workflows/testy.yml").resolve(),
                 (KORZEN / "narzedzia/dawne-tozsamosci.example.txt").resolve()}

    print("=== 1. TOZSAMOSC W ZRODLE ===")
    print("    przeszukane pliki: %d" % len(pliki))
    wlasne = tozsamosc_wlasna()
    if wlasne:
        print("    wzorcow wlasnych z %s: %d" % (PLIK_WLASNYCH.name, len(wlasne)))
    else:
        print("    (brak %s — sprawdzam tylko wzorce uniwersalne;"
              % PLIK_WLASNYCH.name)
        print("     wzorzec: %s)" % (PLIK_WLASNYCH.name + ".example" if False
                                     else "dawne-tozsamosci.example.txt"))
    for wzorzec, opis in TOZSAMOSC_UNIWERSALNA + wlasne:
        traf = [(wzgledna(p), t) for p, t in pliki
                if p.resolve() not in SZUKAJACE and re.search(wzorzec, t, re.I)]
        # NAZWA WZORCA W KOMUNIKACIE. Bez tego raport dawal piecdziesiat
        # linii „brak: wzorzec wlasny z dawne-tozsamosci.txt" — nie do
        # odroznienia od siebie — i przy trafieniu nie bylo wiadomo, CZEGO
        # szukac w pliku. Zajelo mi to osobne dochodzenie, ktore raport
        # powinien byl oszczedzic.
        etykieta = opis if opis != "wzorzec wlasny z %s" % PLIK_WLASNYCH.name             else "wzorzec %s" % wzorzec[:34]
        sprawdz("brak: %s" % etykieta, not traf, [f for f, _ in traf][:4])

    print()
    print("=== 2. TOZSAMOSC W SKLEJONYCH LITERALACH ===")
    # `"Nothing Is " "Accidental"` to dwa literaly. Grep po zrodle ich nie
    # zlaczy; `ast.literal_eval` tak. Ta sekcja istnieje dokladnie dlatego,
    # ze taka nazwa raz przezyla caly przebieg czyszczenia.
    # Sklejone literaly sprawdzamy TYMI SAMYMI wzorcami wlasnymi — bo to
    # wlasnie one przezyly czyszczenie, rozbite miedzy dwa literaly.
    wlasne_wz = [w for w, _ in tozsamosc_wlasna()]
    if not wlasne_wz:
        print("    (brak wzorcow wlasnych — ta sekcja nie ma czego szukac)")
    wzorzec = re.compile("|".join(wlasne_wz) if wlasne_wz else NIGDY_NIE_PASUJE,
                         re.I)
    znalezione = []
    zbadane = 0
    for p, t in pliki:
        if p.suffix != ".py" or p.resolve() in SZUKAJACE:
            continue
        try:
            drzewo = ast.parse(t, filename=str(p))
        except SyntaxError:
            continue
        zbadane += 1
        for n in ast.walk(drzewo):
            if isinstance(n, ast.Assign):
                try:
                    v = ast.literal_eval(n.value)
                except Exception:                      # noqa: BLE001
                    continue
                if isinstance(v, str) and wzorzec.search(v):
                    znalezione.append("%s:%d" % (wzgledna(p), n.lineno))
    print("    zbadane moduly: %d" % zbadane)
    sprawdz("zadna sklejona stala nie niesie tozsamosci", not znalezione, znalezione)

    print()
    print("=== 2b. PISMO, KTOREGO TEN KOD NIE POTRZEBUJE ===")
    # Slowo „pre<cyrylickie r>ejestrowany" przezylo siedem przeczesywek
    # i czytanie linia po linii. Wyglada jak polskie slowo i nie znajdzie go
    # zadne szukanie po jego lacinskim zapisie.
    #
    # To ta sama klasa, co znaki sterujace w liscie wzorcow: napis, ktory
    # wyglada normalnie i nie da sie go dopasowac. Tedy tez wchodza tu nazwy
    # ludzi — wklejone imie przyjezdza razem z pismem rodzimym.
    #
    # NIE ZABRANIAMY OBCYCH LITER. Substack ma interfejs po niemiecku i kod
    # slusznie szuka „Veröffentlichen". Oblewamy tylko na pismach, ktorych
    # zadna potrzeba tego kodu nie tlumaczy; zachodnioeuropejskie znaki
    # wypisujemy jako ostrzezenie, bo tam mieszkaja i UI, i nazwiska.
    ZAKRESY_OBCE = (
        (0x0370, 0x03FF, "greka"), (0x0400, 0x04FF, "cyrylica"),
        (0x0530, 0x058F, "ormianski"), (0x0590, 0x05FF, "hebrajski"),
        (0x0600, 0x06FF, "arabski"), (0x0900, 0x097F, "dewanagari"),
        (0x0E00, 0x0E7F, "tajski"), (0x3040, 0x30FF, "kana"),
        (0x3400, 0x9FFF, "hanzi"), (0xAC00, 0xD7AF, "hangul"),
    )

    def _obce(znak: str) -> str:
        k = ord(znak)
        for od, do, nazwa in ZAKRESY_OBCE:
            if od <= k <= do:
                return nazwa
        return ""

    POLSKIE = set("ĄĆĘŁŃÓŚŻŹąćęłńóśżź")
    twarde, miekkie = [], []
    for p, _ in pliki:
        if p.resolve() in SZUKAJACE:
            continue
        # Trzy widoki tu nie pomagaja i zaciemniaja numer linii — czytamy plik.
        try:
            surowy = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for nr, linia in enumerate(surowy.splitlines(), 1):
            for znak in linia:
                if ord(znak) < 128 or znak in POLSKIE:
                    continue
                if not unicodedata.category(znak).startswith("L"):
                    continue          # myslniki, cudzyslowy, strzalki
                pismo = _obce(znak)
                gdzie = "%s:%d  %r" % (wzgledna(p), nr, znak)
                (twarde if pismo else miekkie).append(
                    "%s %s" % (gdzie, pismo or "lacinka rozszerzona"))
    if miekkie:
        print("    do obejrzenia (litery lacinskie spoza polskiego): %d"
              % len(miekkie))
        for wiersz in miekkie[:6]:
            print("      %s" % wiersz)
    sprawdz("zadne obce pismo w drzewie", not twarde, twarde[:4])

    print()
    print("=== 2c. IDENTYFIKATORY SUBSTACKA (adres, nie liczba) ===")
    # `note/c-<dziewiec cyfr>` wyglada w tescie jak liczba, a otwiera jedna konkretna
    # notke jednego konkretnego konta. Szukanie po DLUGOSCI liczby tonie
    # w sufitach tokenow i rozmiarach plikow; szukanie po KSZTALCIE adresu ma
    # zero falszywych trafien — i wlasnie dlatego znalazlo cztery sztuki, ktore
    # przeczesywka po liczbach przeoczyla.
    #
    # Atrapy zaczynaja sie od 900000000, bo Substack takich numerow nie wydaje:
    # atrapa ma byc rozpoznawalna jako atrapa bez zagladania do listy.
    ATRAPA_OD = 900000000
    KSZTALT_ID = re.compile(r"\b(?:note|comment|post)/c-(\d{6,})")
    prawdziwe = []
    for p, tekst in pliki:
        if p.resolve() in SZUKAJACE:
            continue
        for m in KSZTALT_ID.finditer(tekst):
            if int(m.group(1)) < ATRAPA_OD:
                prawdziwe.append("%s: %s" % (wzgledna(p), m.group(0)))
    sprawdz("zaden identyfikator notki nie jest prawdziwy",
            not prawdziwe, sorted(set(prawdziwe))[:4])

    print()
    print("=== 3. PLIKI, KTORYCH NIE MOZE BYC ===")
    nazwy = [wzgledna(p) for p in sledzone()]
    for wzorzec, opis in ZAKAZANE_PLIKI:
        traf = [n for n in nazwy if re.search(wzorzec, n)]
        sprawdz("brak: %s" % opis, not traf, traf[:4])

    print()
    print("=== 4. PRAWDZIWE KLUCZE (atrapy w testach maja przechodzic) ===")
    for wzorzec, opis in SEKRETY:
        traf = [wzgledna(p) for p, t in pliki
                if p.resolve() not in SZUKAJACE and re.search(wzorzec, t)]
        sprawdz("brak: %s" % opis, not traf, traf[:4])

    print()
    print("=== 5. SPOJNOSC: CZY GENEROWANE JEST AKTUALNE ===")
    for polecenie, plik in (
            (["python", "narzedzia/mapa_funkcji.py"], "docs/FUNCTION_MAP.md"),
            (["python", "agent-v2/dokumentacja-zrodla/sklej.py"],
             "agent-v2/JAK_ZBUDOWANY_JEST_BOT.md")):
        subprocess.run(polecenie, cwd=KORZEN, capture_output=True)
        roznica = subprocess.run(
            ["git", "-C", str(KORZEN), "diff", "--stat", "--", plik],
            capture_output=True, text=True, encoding="utf-8")
        sprawdz("%s nie rozjechal sie z kodem" % plik,
                not roznica.stdout.strip(), roznica.stdout.strip()[:120])

    print()
    print("=== 6. SPOJNOSC: ZALEZNOSCI ===")
    wynik = subprocess.run(["python", "narzedzia/zaleznosci.py", "--sprawdz"],
                           cwd=KORZEN, capture_output=True, text=True,
                           encoding="utf-8")
    sprawdz("requirements.txt zgadza sie z importami", wynik.returncode == 0,
            (wynik.stdout or "").strip().splitlines()[-1:] )

    print()
    print("=== 7. SPOJNOSC: KONFIGURATOR ===")
    sys.path.insert(0, str(KORZEN / "agent-v2"))
    import config          # noqa: E402
    import konfiguracja    # noqa: E402

    brakujace = [n for n, _ in konfiguracja.POLA.values()
                 if n is not None and not hasattr(config, n)]
    sprawdz("kazde pole konfiguracji wskazuje na istniejaca stala", not brakujace,
            brakujace)
    przyklad = KORZEN / "konfiguracja.example.toml"
    sprawdz("plik przykladowy istnieje i jest w gicie",
            przyklad.exists() and "konfiguracja.example.toml" in nazwy)
    sprawdz("uchwyt konta ma JEDNO zrodlo",
            config.SUBSTACK_HANDLE == __import__("browser").PROFIL_HANDLE)

    # ODWOLANIA DO STALYCH, KTORYCH NIE MA. Znalezione czytaniem `alarm.py`:
    # `config.NOTEK_DZIENNIE` nie istnieje w tym projekcie, a stalo w warunku
    # razem z `getattr(config, "NOTEK_DZIENNIE", None)` — czyli galaz nie mogla
    # sie wykonac ANI RAZU i nic nie protestowalo, bo `getattr` z domyslna
    # wartoscia nie rzuca. Kod czytalo sie jak konfigurowalny.
    #
    # Ta sama klasa, co asercja, ktora sie nie wykonuje: zapis wyglada na
    # dzialajacy, bo nikt nie sprawdzil, czy jest osiagalny.
    martwe = []
    for p in sorted((KORZEN / "agent-v2").rglob("*.py")):
        if "/tests/" in p.as_posix():
            continue
        try:
            drzewo = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for w in ast.walk(drzewo):
            if (isinstance(w, ast.Attribute) and isinstance(w.value, ast.Name)
                    and w.value.id == "config" and w.attr.isupper()
                    and not hasattr(config, w.attr)):
                martwe.append("%s:%d config.%s" % (p.name, w.lineno, w.attr))
            elif (isinstance(w, ast.Call) and isinstance(w.func, ast.Name)
                  and w.func.id == "getattr" and len(w.args) >= 2
                  and isinstance(w.args[0], ast.Name) and w.args[0].id == "config"
                  and isinstance(w.args[1], ast.Constant)
                  and isinstance(w.args[1].value, str)
                  and w.args[1].value.isupper()
                  and not hasattr(config, w.args[1].value)):
                martwe.append("%s:%d getattr(config, %r)"
                              % (p.name, w.lineno, w.args[1].value))
    sprawdz("kod nie siega po stale konfiguracji, ktorych nie ma",
            not martwe, "; ".join(sorted(set(martwe))))

    # SHA, KTORE NIE WSKAZUJA NA NIC. Historie zalozono od nowa, wiec kazdy
    # cytat w rodzaju „(`df3de64`)" jest odnosnikiem, ktorego nie da sie
    # otworzyc — a odnosnik obiecuje, ze da sie sprawdzic.
    #
    # TO NIE JEST OBLANIE: po swiadomym wyczyszczeniu historii ich obecnosc
    # jest spodziewana i policzona w `docs/CLEANING_LOG.md`. Wypisujemy je,
    # zeby liczba byla ZNANA i zeby nie rosla po cichu, a sprawdzamy jedno:
    # czy wyjasnienie w ogole gdzies stoi.
    wiszace: dict[str, set[str]] = {}
    _sha = re.compile(r"\b[0-9a-f]{7,40}\b")
    for p, tekst in pliki:
        if p.suffix.lower() not in (".py", ".md", ".toml", ".yml", ".txt"):
            continue
        for m in _sha.finditer(tekst):
            s = m.group(0)
            if s.isdigit() or s in ("ed25519",):
                continue
            wiszace.setdefault(s, set()).add(wzgledna(p))
    nieznane = {}
    for s, gdzie in wiszace.items():
        if subprocess.run(["git", "cat-file", "-t", s], cwd=KORZEN,
                          capture_output=True).returncode != 0:
            nieznane[s] = gdzie
    if nieznane:
        print("  ..    %d SHA nie wskazuje na nic w tej historii (spodziewane"
              " po jej zalozeniu od nowa):" % len(nieznane))
        for s in sorted(nieznane)[:8]:
            print("        %-12s %s" % (s, ", ".join(sorted(nieznane[s]))[:80]))
        if len(nieznane) > 8:
            print("        (i %d dalszych)" % (len(nieznane) - 8))
    _dziennik = KORZEN / "docs" / "CLEANING_LOG.md"
    _tresc_dziennika = (_dziennik.read_text(encoding="utf-8")
                        if _dziennik.exists() else "")
    sprawdz("wiszace SHA sa wyjasnione w dzienniku czyszczenia",
            not nieznane or "commit hashes" in _tresc_dziennika.lower(),
            "dopisz akapit o SHA z historii produkcyjnej do docs/CLEANING_LOG.md")

    print()
    print("=== 8. SPOJNOSC: PROGI PILNOWANE PRZEZ TESTY ===")
    # PROG 19 TO NASZA LICZBA, NIE REGULA. Asercja PONIZEJ (siatka wzorcow)
    # zostala juz na to naprawiona; ta zostala pominieta i cudza instalacja
    # z trzema haslami dostawala BLAD za stan calkowicie poprawny.
    #
    # Prog niezalezny od konfiguracji jest strukturalny: pula ma byc istotnie
    # szersza niz to, co losujemy na przebieg (`ILE_HASEL_NA_PRZEBIEG`),
    # inaczej kazdy przebieg bierze cala pule i wraca po tych samych kontach.
    _min_hasel = 3 * config.ILE_HASEL_NA_PRZEBIEG
    if (KORZEN / "agent-v2" / "konfiguracja.toml").exists():
        sprawdz("pula hasel jest szersza niz jeden przebieg",
                len(config.HASLA_SZUKANIA) >= _min_hasel,
                "%d hasel przy %d losowanych na przebieg — dopisz do %d, "
                "inaczej kazdy przebieg bierze cala pule"
                % (len(config.HASLA_SZUKANIA), config.ILE_HASEL_NA_PRZEBIEG,
                   _min_hasel))
    else:
        sprawdz("hasel szukania jest >= 19", len(config.HASLA_SZUKANIA) >= 19,
                len(config.HASLA_SZUKANIA))
    # SIATKA ZALEZY OD LICZBY DZIEDZIN, KTORA PODAJE OPERATOR. Prog 400
    # opisuje NASZA pule (14 wzorcow x 46 dziedzin). Przy czterech wlasnych
    # dziedzinach wychodzi 56 i audyt oblewal, nie zglaszajac zadnej awarii —
    # a to jest narzedzie, ktore ma odrozniac awarie od decyzji.
    #
    # Prog niezalezny od konfiguracji jest inny i nizszy: siatka ma dawac
    # z zapasem wiecej komorek niz notek w ciagu doby, inaczej ten sam wzorzec
    # w tej samej dziedzinie wraca po kilku dniach.
    komorki = len(config.GENERATORY) * len(config.DZIEDZINY_CIEKAWOSTEK)
    na_dobe = max(1, len(config.NOTE_MIX_OTHER_DAY))
    if (KORZEN / "agent-v2" / "konfiguracja.toml").exists():
        sprawdz("siatka daje co najmniej 10 komorek na notke",
                komorki >= 10 * na_dobe,
                "%d komorek przy %d notkach na dobe — dopisz dziedziny"
                % (komorki, na_dobe))
    else:
        sprawdz("siatka wzorce x dziedziny >= 400", komorki >= 400, komorki)
    # NIEDOPASOWANIE DWOCH POL OPERATORA TO NIE JEST USTERKA INSTALACJI.
    # Stal tu nagi `BLAD` z lista trafien. `test_szukanie_celow.py` przy tym
    # samym trafieniu mowi, KTOREGO znaku brakuje i co z tym zrobic; audyt
    # ma odsylac tam, a nie zglaszac awarie tam, gdzie jej nie ma.
    poza = [h for h in config.HASLA_SZUKANIA
            if not any(z in h.lower() for z in config.ZNAKI_NISZY)]
    if poza and (KORZEN / "agent-v2" / "konfiguracja.toml").exists():
        uwaga("hasla zgadzaja sie ze znakami niszy",
                "%d hasel bez zadnego znaku (%s) — to dwa TWOJE pola, ktore"
                " sie rozjechaly; `python agent-v2/tests/test_szukanie_celow.py`"
                " mowi, ktorego znaku dopisac"
                % (len(poza), ", ".join(poza[:3])))
    else:
        sprawdz("kazde haslo miesci sie w niszy", not poza, poza)

    print()
    print("=== 9. KONTRDOWOD: CZY TEN AUDYT W OGOLE COKOLWIEK LAPIE ===")
    # F: skan martwych stalych musi umiec zobaczyc odwolanie do nieistniejacej.
    _probka = ast.parse("x = config.STALA_KTOREJ_NIE_MA\n")
    _trafione = [w.attr for w in ast.walk(_probka)
                 if isinstance(w, ast.Attribute) and isinstance(w.value, ast.Name)
                 and w.value.id == "config" and w.attr.isupper()
                 and not hasattr(config, w.attr)]
    sprawdz("F: martwa stala      lapie", _trafione == ["STALA_KTOREJ_NIE_MA"],
            _trafione)
    _zywa = ast.parse("x = config.DATA_DIR\n")
    _trafione2 = [w.attr for w in ast.walk(_zywa)
                  if isinstance(w, ast.Attribute) and isinstance(w.value, ast.Name)
                  and w.value.id == "config" and w.attr.isupper()
                  and not hasattr(config, w.attr)]
    sprawdz("F: zywa stala        NIE lapie", not _trafione2, _trafione2)
    # Audyt, ktory zawsze mowi OK, jest nieodrozninalny od audytu zepsutego.
    # Ta sekcja wstrzykuje TRZY przecieki do tekstu w pamieci i sprawdza, ze
    # kazdy zostaje zlapany. Kazdy odpowiada dziurze, ktora NAPRAWDE zdarzyla
    # sie w tym repozytorium:
    #
    #   A. nazwa w jednym literale       — zwykly skan zrodla ja lapie
    #   B. nazwa ROZBITA miedzy dwa      — skan zrodla NIE lapie, AST tak.
    #      literaly pythonowe              TO PRZEZYLO CALE CZYSZCZENIE
    #      i pierwsze wydanie publiczne.
    #   C. nazwa PRZECIETA koncem linii  — dlatego wzorce uzywaja `\s+`,
    #                                      nie spacji
    WZ = r"Marka\s+Kontrolna"
    PROBKI = [
        ("A: jeden literal", 'X = "Marka Kontrolna"', True),
        ("B: dwa literaly", 'X = ("Marka "\n     "Kontrolna")', False),
        ("C: przeciete linia", "publikacja Marka\nKontrolna i tyle", True),
    ]
    for nazwa, tekst, ma_zlapac_zrodlo in PROBKI:
        zlapane = bool(re.search(WZ, tekst, re.I))
        sprawdz("  %-22s skan zrodla: %s" % (nazwa, "lapie" if zlapane else "NIE lapie"),
                zlapane == ma_zlapac_zrodlo, tekst[:40])

    # I to samo przez drzewo skladni — tu probka B MUSI zostac zlapana,
    # bo inaczej sekcja 2 jest ozdoba.
    zrodlo_b = 'X = ("Marka "\n     "Kontrolna")'
    try:
        drzewo_b = ast.parse(zrodlo_b)
        wartosci = [ast.literal_eval(n.value) for n in ast.walk(drzewo_b)
                    if isinstance(n, ast.Assign)]
    except Exception:                                  # noqa: BLE001
        wartosci = []
    sprawdz("  B przez AST: sklejona wartosc widoczna",
            any(isinstance(v, str) and re.search(WZ, v, re.I) for v in wartosci),
            wartosci)

    # I kontrdowod do kontrdowodu: wzorzec nie moze lapac czegokolwiek.
    sprawdz("  wzorzec nie lapie tekstu bez marki",
            not re.search(WZ, "zwykly tekst bez niczego", re.I))

    # D. HOMOGLIF. Sekcja 2b istnieje przez jedno slowo, w ktorym lacinskie
    # „r" bylo cyrylickie. Kontrdowod musi pokazac OBIE polowy: ze szukanie
    # po zapisie lacinskim tego NIE widzi, i ze sprawdzenie po kodzie znaku
    # widzi. Bez pierwszej polowy druga niczego nie dowodzi.
    podszyte = "preрejestrowany"
    sprawdz("  D: homoglif niewidoczny dla szukania po literach",
            "prerejestrowany" not in podszyte, podszyte)
    sprawdz("  D: i widoczny po kodzie znaku",
            any(0x0400 <= ord(z) <= 0x04FF for z in podszyte), podszyte)

    # E. IDENTYFIKATOR SUBSTACKA. Sekcja 2c istnieje przez cztery numery, ktore
    # przezyly przeczesywke po dlugosci liczby. Kontrdowod musi pokazac, ze
    # wzorzec rozroznia trzy rzeczy: identyfikator o prawdziwym KSZTALCIE,
    # atrape i zwykla liczbe o tej samej dlugosci stojaca bez adresu.
    #
    # PROBKA JEST ZBUDOWANA, NIE WZIETA Z DZIENNIKA. Stal tu numer wyjety
    # z prawdziwej interakcji — otwieral jedna konkretna notke jednego
    # konkretnego konta. Do dowodu wystarczy, ze liczba jest PONIZEJ progu
    # atrap; skad pochodzi, nie ma dla wzorca zadnego znaczenia, a w repozytorium
    # publicznym prawdziwy numer jest wskaznikiem na czyjas notke. Plik audytu
    # jest zwolniony z sekcji 2c (musi zawierac to, czego szuka), wiec zaden
    # inny straznik by tego nie zdjal — to jest wlasnie ten rodzaj miejsca,
    # w ktorym prawdziwa dana przezywa czyszczenie.
    for opis, probka, ma_zlapac in (
            ("prawdziwy ksztalt", "note/c-123456789", True),
            ("atrapa", "note/c-900000021", False),
            ("liczba bez adresu", "sufit 123456789 tokenow", False)):
        m = KSZTALT_ID.search(probka)
        zlapane = bool(m) and int(m.group(1)) < ATRAPA_OD
        sprawdz("  E: %-18s %s" % (opis, "lapie" if ma_zlapac else "NIE lapie"),
                zlapane == ma_zlapac, probka)

    if "--historia" in sys.argv:
        print()
        print("=== 10. HISTORIA GITA (nie tylko drzewo) ===")
        out = subprocess.run(
            ["git", "-C", str(KORZEN), "log", "--all", "--diff-filter=A",
             "--name-only", "--format="],
            capture_output=True, text=True, encoding="utf-8")
        wszystkie = {n for n in out.stdout.splitlines() if n.strip()}
        print("    plikow kiedykolwiek dodanych: %d" % len(wszystkie))
        for wzorzec, opis in ZAKAZANE_PLIKI:
            traf = sorted(n for n in wszystkie if re.search(wzorzec, n))
            sprawdz("w historii brak: %s" % opis, not traf,
                    "%d plikow, np. %s" % (len(traf), traf[:2]) if traf else "")

    print()
    print("=== WYNIK AUDYTU: %d zdanych, %d oblanych%s ===" %
          (zdane, oblane,
           (", %d z uwaga" % len(uwagi)) if uwagi else ""))
    for _u in uwagi:
        print("    uwaga: %s" % _u)
    return 1 if oblane else 0


if __name__ == "__main__":
    sys.exit(main())
