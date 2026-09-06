# -*- coding: utf-8 -*-
"""Nasz wlasny kartridz ma przejsc reguly, ktore stawiamy KAZDEMU operatorowi.

## Po co ten plik istnieje

`test_przyklad_konfiguracji.py` pilnuje, ze przyklad konfiguracji ma komplet
pol i wczytuje sie bez bledu, i mowi wprost, ze WARTOSCI nie sprawdza.

Osobne pytanie: CZY NASZ WLASNY KARTRIDZ PRZESZEDLBY NASZE WLASNE REGULY.
Jesli nie przechodzi, to znaczy jedno z dwojga i oba sa wada:

  * kartridz jest zly — czlowiek skopiuje go i dostanie odmowe przy
    `podlacz`, zanim cokolwiek zdazy zrobic; albo
  * REGULA JEST NASZA, a nie powszechna — czyli prog z jednej instalacji
    podany jako prawo natury.

Drugie zdarzylo sie 2026-09-04 i kosztowalo szesc oblanych asercji na
instalacji calkowicie poprawnej („co najmniej 19 hasel", polska mapa
rewiru). Od 2026-09-06 silnik nie ma zadnego tematu, wiec jedynym miejscem,
w ktorym reguly tematu maja co mierzyc, sa kartridze w `presety/`. Reguly
stoja w JEDNYM miejscu — `preset.sprawdz` — i to samo miejsce blokuje
`podlacz`, wiec test i podlaczenie nie moga sie rozjechac.

Regula, ktora tu stoi, MUSI byc niezalezna od niszy — inaczej ten plik
powtorzy blad, ktory ma lapac. Kazda wywodzi sie ze STRUKTURY (ile losujemy
na przebieg, ile notek na dobe), nigdy z liczby wpisanej recznie.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_przyklad_przechodzi_reguly.py
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2/tests")
import wlasna_konfiguracja  # noqa: E402

wlasna_konfiguracja.pomin_gdy_bez_tomllib(
    "czy kartridz `ai` przechodzi reguly stawiane kazdemu")

sys.path.insert(0, "agent-v2")
import config           # noqa: E402
import konfiguracja     # noqa: E402
import preset           # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


KARTRIDZ = pathlib.Path("presety/ai")
BAZA = dict(config.DOMYSLNE_SILNIKA)

print("=== 1. KARTRIDZ `ai` WCZYTUJE SIE I PRZECHODZI SPRAWDZENIE W CALOSCI ===")
sprawdz("presety/ai/preset.toml istnieje", (KARTRIDZ / "preset.toml").is_file())
ai = preset.wczytaj(KARTRIDZ)
# Konto jest instalacji, nie presetu (test_konto_z_env): `ai` ma placeholder,
# a instalacja podaje uchwyt i marke w .env — tu udajemy taka instalacje.
KONTO = {"SUBSTACK_HANDLE": "ktos", "NAZWA_MARKI": "Ktos Pisze"}
bledy, uwagi = preset.sprawdz(ai, config, BAZA, srodowisko=dict(KONTO))
_uwagi_bez_konta = preset.sprawdz(ai, config, BAZA, srodowisko={})[1]
sprawdz("bez konta w srodowisku uwaga mowi, co wpisac do .env (placeholder zostaje w repo)",
        any("SUBSTACK_HANDLE" in u and "NAZWA_MARKI" in u for u in _uwagi_bez_konta), _uwagi_bez_konta)
sprawdz("zero bledow sprawdzenia", not bledy, bledy)
_uwagi_bez_kluczy = [u for u in uwagi if "brak w srodowisku" not in u]
sprawdz("uwagi tylko o swiadomie wylaczonych dzialaniach",
        all(any(s in u for s in ("wylaczone", "wylaczona")) for u in _uwagi_bez_kluczy),
        _uwagi_bez_kluczy)

print()
print("=== 2. TE SAME REGULY POLICZONE TU, ZEBY BYLO WIDAC LICZBY ===")
hasla = [str(h).lower() for h in ai.pola.get("temat.hasla_szukania", ())]
znaki = [str(z).lower() for z in ai.pola.get("temat.znaki_niszy", ())]
dziedziny = list(ai.pola.get("temat.dziedziny", ()))
minimum = 3 * config.ILE_HASEL_NA_PRZEBIEG
sprawdz("pula hasel szersza niz jeden przebieg (>= %d)" % minimum,
        len(hasla) >= minimum, "%d hasel" % len(hasla))
poza = [h for h in hasla if not any(z in h for z in znaki)]
sprawdz("kazde haslo niesie znak rewiru z tego samego kartridza", not poza, poza[:5])
notki = int(ai.pola.get("wolumeny.notki_dziennie", 0))
komorki = len(config.GENERATORY) * len(dziedziny)
sprawdz("siatka >= 10 komorek na notke (%d wzorcow x %d dziedzin = %d przy %d notkach)"
        % (len(config.GENERATORY), len(dziedziny), komorki, notki),
        komorki >= 10 * notki)
# TRZY STRONY TEMATU, zeby dwadziescia hasel nie bylo o jednym. Strony
# pochodza z kartridza (znaki), nie z polskiej mapy w silniku.
_strony = {"pomiar": ("benchmark", "eval", "hallucinat", "reproduc"),
           "pieniadze": ("token", "gpu", "compute", "chip", "training"),
           "odpowiedzialnosc": ("regulat", "ai act", "copyright", "licen", "liabil", "deepfake")}
for strona, slowa in _strony.items():
    sprawdz("  hasla dotykaja strony: %s" % strona,
            any(any(s in h for s in slowa) for h in hasla))

print()
print("=== 3. BLOKI I STYL SA Z KARTRIDZA, NIE Z SILNIKA ===")
sprawdz("wszystkie bloki promptow sa dostarczone",
        set(ai.bloki) == set(preset.BLOKI), sorted(set(preset.BLOKI) - set(ai.bloki)))
sprawdz("zaden blok nie ma znacznika szablonu",
        not any("<<" in t for t in ai.bloki.values()))
proba, _ = preset.rozwiaz(ai, config, BAZA)
sprawdz("profile stylu wskazuja do katalogu kartridza",
        pathlib.Path(proba.STYLE_PROFILE_POSITIVE).resolve().parent == (KARTRIDZ / "styl").resolve()
        and pathlib.Path(proba.STYLE_PROFILE_NEGATIVE).is_file(),
        proba.STYLE_PROFILE_POSITIVE)
sprawdz("w gicie zostaje placeholder konta, nie prawdziwy uchwyt",
        ai.pola.get("konto.uchwyt") == "your-handle", ai.pola.get("konto.uchwyt"))

# KORPUS STYLU KARTRIDZA: przypiety, o wolnej licencji, z manifestem. Pisarz
# artykulu odmawia bez przypietego korpusu (`styl.wymagaj_korpusu = true`),
# wiec kartridz, ktory deklaruje korpus, musi go miec w stanie gotowym do
# uzycia — inaczej pierwszy artykul konczy sie na etapie `write`.
import style  # noqa: E402

_korpus = pathlib.Path(proba.STYLE_CORPUS)
sprawdz("kartridz deklaruje korpus w swoim katalogu i plik istnieje",
        _korpus.is_file() and _korpus.parent == (KARTRIDZ / "styl").resolve(), _korpus)
sprawdz("obok korpusu lezy manifest zrodel z licencjami",
        (_korpus.parent / "KORPUS_ZRODLA.md").is_file()
        and "CC BY" in (_korpus.parent / "KORPUS_ZRODLA.md").read_text(encoding="utf-8"))
_stan = (config.STYLE_CORPUS, config.STYL_WYMAGAJ_KORPUSU)
try:
    config.STYLE_CORPUS = _korpus
    config.STYL_WYMAGAJ_KORPUSU = True
    try:
        _przyklady = style.load_examples()
        _blad = ""
    except style.StyleError as exc:
        _przyklady, _blad = [], str(exc)
    sprawdz("korpus jest przypiety i loader oddaje piec funkcji retorycznych",
            [e["function"] for e in _przyklady] == list(style.FUNKCJE_STYLU), _blad[:160])
    sprawdz("kazdy przypiety akapit miesci sie w widelkach loadera",
            all(style.MIN_EXAMPLE_CHARS <= len(e["text"]) <= style.MAX_EXAMPLE_CHARS for e in _przyklady))
    # KONTRDOWOD: korpus podmieniony o jeden znak przestaje sie zgadzac ze skrotem.
    import hashlib  # noqa: E402
    _skrot = hashlib.sha256(style.bajty_kanoniczne(_korpus.read_bytes() + b" ")).hexdigest()
    sprawdz("kontrdowod: dopisana spacja zmienia skrot, ktory loader sprawdza",
            _skrot != style.wczytaj_przypiecia()["korpus_sha256"])
finally:
    config.STYLE_CORPUS, config.STYL_WYMAGAJ_KORPUSU = _stan

print()
print("=== 4. KONTRDOWOD: SZABLON I ZATRUTY KARTRIDZ MUSZA TU POLEC ===")
szablon = pathlib.Path("presety") / preset.NAZWA_SZABLONU
try:
    _sz = preset.wczytaj(szablon)
    _bledy_sz, _ = preset.sprawdz(_sz, config, BAZA, srodowisko={})
except preset.BladPresetu as exc:
    _bledy_sz = [str(exc)]
sprawdz("szablon NIE przechodzi (znaczniki <<...>>)", bool(_bledy_sz), _bledy_sz[:1])
sprawdz("  i mowi o znacznikach do uzupelnienia",
        any("<<" in b for b in _bledy_sz), _bledy_sz[:1])
_ciasny = preset.wczytaj_tekst(
    '[preset]\nnazwa = "ciasny"\n[konto]\nuchwyt = "x"\nnazwa_marki = "X"\n'
    '[temat]\nnisza = "x"\nkat_redakcyjny = "x."\njezyk = "English"\n'
    'znaki_niszy = ["regulat"]\nhasla_szukania = ["bread regulation"]\n'
    'dziedziny = ["x"]\n[styl]\nwymagaj_korpusu = false\n'
    'profil_pozytywny = "style-profiles/ARTICLE_STYLE_PROFILE_V1.md"\n'
    'profil_negatywny = "style-profiles/ARTICLE_NEGATIVE_STYLE_PROFILE_V1.md"\n',
    "ciasny.toml")
_bledy_c, _ = preset.sprawdz(_ciasny, config, BAZA, srodowisko={})
sprawdz("jedno haslo przy pieciu losowanych NIE przechodzi",
        any("hasel szukania" in b for b in _bledy_c), _bledy_c)
sprawdz("jedna dziedzina przy dwoch notkach NIE przechodzi",
        any("siatka" in b for b in _bledy_c), _bledy_c)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
