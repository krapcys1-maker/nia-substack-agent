# -*- coding: utf-8 -*-
"""Reakcja na nasza tresc niesie UCHWYT, a nie sama nazwe wyswietlana.

## Co bylo zepsute

`browser.dopisz_skutki` czyta kanal aktywnosci i ma pod reka CALY obiekt
uzytkownika (`kanal["users"]`). Zapisywalo z niego wylacznie `name`.

Zmierzone 1 wrzesnia 2026 na produkcyjnym dzienniku serwera
(`agent-v2/data/dziennik.jsonl`, 635 wierszy, 199 wpisow `rodzaj="skutek"`,
69 roznych osob w polu `kto`):

  * przez `czytelnicy.jsonl` — jedyna mapa nazwa -> uchwyt, jaka mamy —
    rozwiazuje sie 11 nazw z 69, i sa to DOKLADNIE nasi obecni czytelnicy
    (Maria Trzynasta, Publikacja Podrozna, Publikacja Chaosu, CourseManagement System,
    Grzegorz Siodmy, Filip Szosty, Leonard, Publikacja Lustrzana AI,
    Halina Osma, Publikacja Drogowa: Founder, sidharth chandra), wiec jako
    cele sa bezuzyteczni — juz ich mamy;
  * przez rownosc slugu nazwy ze slugiem hosta z `gdzie_komentowalismy.json`
    (94 hosty) trafia 7 z 69: annanowak.blog, eunnurilee.substack.com,
    fatemaraja.substack.com, igordziewiaty.substack.com, ixcarus.substack.com,
    raportbranzowy.substack.com, www.jankowalski.com — z czego po odsianiu
    wszystkiego sprzed przestawienia konta na AI (2026-08-25) zostaja TRZY.

Czyli poziom pierwszenstwa celow zbudowany na NAJMOCNIEJSZYM sygnale, jaki
mamy, dzialal dla trzech kont. 62 osoby z 69 przepadaly nie dlatego, ze ich
nie ma, tylko dlatego, ze uchwyt byl wyrzucany o jedna linijke wczesniej.

Tempo, w jakim to sie odbudowuje: 69 roznych osob w 18 dniach (15 sierpnia —
1 wrzesnia), a w ostatnim tygodniu pomiaru 27 nowych osob w 7 dniach, czyli
okolo 3,9 nowego reagujacego na dobe.

## Najgrozniejsza mozliwa pomylka w tej poprawce — i dlaczego ma wlasna sekcja

Nazwy i uchwyty to DWIE LISTY. Wystarczy, ze jedna przejdzie inny odsiew niz
druga, i `kto[1]` dostaje uchwyt osoby trzeciej. Powstaje wtedy cel, ktory
wyglada na zmierzony — „ta osoba zareagowala na nasza tresc" — a nie jest
nim. To gorzej niz brak uchwytu: brak widac, rozjazd nie.

Stary kod odsiewal nadawcow bez nazwy (`[k for k in kto if k][:5]`), wiec
dopisanie uchwytow OBOK, ta sama petla po `recent_sender_ids`, ale bez tego
odsiewu, daje rozjazd przy pierwszym nadawcy bez nazwy i przy szostym
nadawcy w zdarzeniu. Sekcja 3 odtwarza te regule i pokazuje, ze produkcja
tak NIE robi.

## Co ten test mierzy

ZACHOWANIE `browser.dopisz_skutki` puszczonej na atrapie kanalu aktywnosci:
dziennik jest prawdziwy, tylko przekierowany do katalogu tymczasowego. Zero
asercji po tresci zrodel, zero sieci, zero przegladarki, zero wywolan modelu.

KONTRDOWOD JEST ODTWARZANY, NIE OPISANY. Sekcja 4 puszcza ten sam kanal przez
`dopisz_skutki` wyjete z `git show 6ed4e7d:agent-v2/browser.py` — wersja
odniesienia PRZYPIETA DO SHA, nie do HEAD, bo kontrdowod mierzony wzgledem
HEAD gasnie w chwili commita, ktorego strzeze.

Test nie zalezy od dzisiejszej daty: wszystkie daty w atrapie sa stale.
"""

import ast
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

KORZEN = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KORZEN / "agent-v2"))

import browser        # noqa: E402
import config         # noqa: E402
import run            # noqa: E402
import wzajemnosc     # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU — patrz `historia.py`.
import historia   # noqa: E402
historia.wymaga_historii("6ed4e7d")

ODNIESIENIE = "6ed4e7d"        # wersja SPRZED poprawki, przypieta na stale

zdane = 0
oblane = 0


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


PILNOWANE = [config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "czytelnicy.jsonl",
             config.DATA_DIR / "wzrost.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}


# --- ATRAPA KANALU AKTYWNOSCI ------------------------------------------------
#
# Ksztalt przepisany z tego, co `dopisz_skutki` naprawde czyta: `activityItems`
# z `recent_sender_ids` i `sender_count`, obok worek `users`. Ludzie sa tak
# dobrani, zeby uderzyc w kazdy sposob, w jaki dwie rownolegle listy moga sie
# rozjechac.
LUDZIE = [
    {"id": 1, "name": "Igor Dziewiaty", "handle": "igordziewiaty"},
    # NADAWCA BEZ NAZWY. Stary kod wycinal go z `kto`; jesli uchwyty leca
    # osobna petla, to od TEGO miejsca kazda para jest przesunieta.
    {"id": 2, "handle": "duchbeznazwy"},
    {"id": 3, "name": "Jan Dziesiaty", "handle": "jankowalski"},
    # KONTO BEZ UCHWYTU W ODPOWIEDZI. Ma byc `None`, nie pusty napis.
    {"id": 4, "name": "Lech Dwunasty"},
    # UCHWYT PUSTY I UCHWYT Z BIALYMI ZNAKAMI — jedno i drugie to „nie wiem".
    {"id": 5, "name": "Pusty Uchwyt", "handle": ""},
    {"id": 6, "name": "Spacja", "handle": "   "},
    {"id": 7, "name": "Szosty", "handle": "szosty"},
    {"id": 8, "name": "Siodmy", "handle": "siodmy"},
]
PO_ID = {u["id"]: u for u in LUDZIE}

KANAL = {
    "activityItems": [
        # Zdarzenie, w ktorym nadawca nr 2 nie ma nazwy — pulapka na rozjazd.
        {"id": "note_like:900", "type": "note_like", "target_comment_id": 100,
         "sender_count": 3, "recent_sender_ids": [1, 2, 3],
         "created_at": "2026-08-27T20:02:21.000Z"},
        # Osoba bez uchwytu obok osoby z uchwytem.
        {"id": "comment_reply:901", "type": "comment_reply",
         "target_comment_id": 101, "sender_count": 2,
         "recent_sender_ids": [4, 1],
         "created_at": "2026-08-28T23:49:31.000Z"},
        # Uchwyt pusty i uchwyt ze spacji.
        {"id": "note_reply:902", "type": "note_reply", "target_comment_id": 102,
         "sender_count": 2, "recent_sender_ids": [5, 6],
         "created_at": "2026-08-29T11:09:39.000Z"},
        # OSMIU NADAWCOW przy limicie piatki — obie listy musza byc przyciete
        # tak samo i w tej samej kolejnosci.
        {"id": "note_restack:903", "type": "note_restack",
         "target_comment_id": 103, "sender_count": 8,
         "recent_sender_ids": [1, 2, 3, 4, 5, 6, 7, 8],
         "created_at": "2026-08-30T09:00:00.000Z"},
        # Zdarzenie BEZ NADAWCOW — „nie bylo nikogo", co jest czyms innym niz
        # „byl ktos, kogo nie umiemy nazwac uchwytem".
        {"id": "follow:904", "type": "follow", "sender_count": 0,
         "created_at": "2026-08-31T06:25:10.000Z"},
    ],
    "users": LUDZIE,
}


class Nic:
    def new_page(self):
        return self

    def close(self):
        pass

    def stop(self):
        pass


def wpisy_z(sciezka):
    return [json.loads(l) for l in
            pathlib.Path(sciezka).read_text(encoding="utf-8").splitlines()
            if l.strip()]


def puscic(funkcja, kanal, dziennik, przestrzen=None):
    """Puszcza `dopisz_skutki` (nowa albo stara) na atrapie i oddaje wpisy.

    `przestrzen` podaje sie dla funkcji WYJETEJ ze starego commita: jej
    globalne nazwy to osobny slownik, wiec podmiana `browser.podlacz_sie`
    sama w sobie do niej nie dociera i stara wersja probowalaby wystartowac
    prawdziwa przegladarke.
    """
    o_api, o_pod, o_ses = (browser.api_json, browser.podlacz_sie,
                           browser.wymagaj_sesji)
    o_dz = browser.DZIENNIK
    atrapy = {
        "wymagaj_sesji": lambda: None,
        "podlacz_sie": lambda: (Nic(), Nic(), Nic()),
        "api_json": (lambda page, sciezka, baza=None:
                     kanal if "activity-feed-web" in sciezka else None),
        "DZIENNIK": pathlib.Path(dziennik),
    }
    try:
        for nazwa, co in atrapy.items():
            setattr(browser, nazwa, co)
        if przestrzen is not None:
            przestrzen.update(atrapy)
        ile = funkcja()
    finally:
        (browser.api_json, browser.podlacz_sie,
         browser.wymagaj_sesji) = o_api, o_pod, o_ses
        browser.DZIENNIK = o_dz
    return ile, wpisy_z(dziennik)


ROBOCZY = pathlib.Path(tempfile.mkdtemp())

print("=== 1. UCHWYT LADUJE W DZIENNIKU ===")
ile, wpisy = puscic(browser.dopisz_skutki, KANAL, ROBOCZY / "nowy.jsonl")
sprawdz("dopisane wszystkie piec zdarzen", ile == 5, ile)
po_kluczu = {w["zdarzenie"]: w for w in wpisy}

lajk = po_kluczu["note_like:900"]
sprawdz("uchwyty sa w zapisie", "uchwyty" in lajk, sorted(lajk))
sprawdz("i niosa prawdziwe konta, nie nazwy",
        lajk["uchwyty"] == ["igordziewiaty", "jankowalski"], lajk)

print()
print("=== 2. NAZWA I UCHWYT TO TA SAMA OSOBA ===")
# Sprawdzamy to PARA PO PARZE wobec atrapy, a nie na oko: dla kazdego wpisu
# i kazdego indeksu nazwa z `kto` musi nalezec do tego samego uzytkownika,
# co uchwyt z `uchwyty`. To jest jedyna asercja, ktora wylapie cichy rozjazd.
nazwa_do_uchwytu = {}
for u in LUDZIE:
    if u.get("name"):
        nazwa_do_uchwytu[u["name"]] = (str(u.get("handle") or "").strip()
                                       or None)
rozjazdy = []
for w in wpisy:
    kto, uchwyty = w.get("kto") or [], w.get("uchwyty")
    if uchwyty is None or len(kto) != len(uchwyty):
        rozjazdy.append((w["zdarzenie"], "dlugosci", kto, uchwyty))
        continue
    for n, u in zip(kto, uchwyty):
        if nazwa_do_uchwytu.get(n) != u:
            rozjazdy.append((w["zdarzenie"], n, u, nazwa_do_uchwytu.get(n)))
sprawdz("kazda para nazwa-uchwyt dotyczy tej samej osoby",
        not rozjazdy, rozjazdy[:3])
sprawdz("listy sa rownej dlugosci w KAZDYM wpisie",
        all(len(w.get("kto") or []) == len(w.get("uchwyty") or [])
            for w in wpisy),
        [(w["zdarzenie"], len(w.get("kto") or []),
          len(w.get("uchwyty") or [])) for w in wpisy])

# Nadawca bez nazwy wypada tak samo, jak wypadal przedtem — czyli `kto` sie
# nie zmienilo i czytajacy je moduly nie widza nowego ksztaltu.
sprawdz("nadawca bez nazwy dalej wypada z obu list",
        lajk["kto"] == ["Igor Dziewiaty", "Jan Dziesiaty"], lajk["kto"])

print()
print("=== 2b. LIMIT PIATKI TNIE OBIE LISTY TAK SAMO ===")
restack = po_kluczu["note_restack:903"]
sprawdz("nie wiecej niz piec nazw", len(restack["kto"]) == 5, restack["kto"])
sprawdz("i dokladnie tyle samo uchwytow",
        len(restack["uchwyty"]) == 5, restack["uchwyty"])
# Osmiu nadawcow, jeden bez nazwy (nr 2) -> po odsiewie zostaje siedmiu,
# a piatka to nadawcy 1,3,4,5,6.
sprawdz("piatka to PIERWSZE piec osob z nazwa, w kolejnosci kanalu",
        restack["kto"] == ["Igor Dziewiaty", "Jan Dziesiaty", "Lech Dwunasty",
                           "Pusty Uchwyt", "Spacja"], restack["kto"])
sprawdz("a uchwyty stoja przy nich",
        restack["uchwyty"] == ["igordziewiaty", "jankowalski", None, None, None],
        restack["uchwyty"])
sprawdz("`ilu` dalej mowi, ilu bylo NAPRAWDE, mimo przyciecia",
        restack["ilu"] == 8, restack["ilu"])

print()
print("=== 2c. BRAK UCHWYTU JEST ODROZNIALNY OD BRAKU LUDZI ===")
odp = po_kluczu["comment_reply:901"]
sprawdz("konto bez pola `handle` -> None, nie pusty napis",
        odp["uchwyty"] == [None, "igordziewiaty"], odp["uchwyty"])
sprawdz("None nie jest pustym napisem",
        odp["uchwyty"][0] is None and odp["uchwyty"][0] != "", odp["uchwyty"])
puste = po_kluczu["note_reply:902"]
sprawdz("uchwyt pusty i uchwyt ze spacji tez sa None",
        puste["uchwyty"] == [None, None], puste["uchwyty"])
nikt = po_kluczu["follow:904"]
sprawdz("zdarzenie bez nadawcow -> pusta lista, nie [None]",
        nikt["uchwyty"] == [] and nikt["kto"] == [], nikt)

print()
print("=== 3. KONTRDOWOD A: NAIWNE DWIE PETLE DAJA CICHY ROZJAZD ===")
# REGULA, NIE PLIK. Tak wygladalaby poprawka napisana wprost „dolozyc uchwyty
# obok": ta sama petla po `recent_sender_ids`, ale bez odsiewu po nazwie
# i bez `[:5]`. Na `6ed4e7d` takiego kodu nie ma — jest do odtworzenia,
# bo to jest wlasnie blad, ktorego ten test pilnuje.
ludzie_po_id = {i: PO_ID[i] for i in PO_ID}
for zdarzenie, oczekiwane in (("note_like:900",
                               ["Igor Dziewiaty", "Jan Dziesiaty"]),
                              ("note_restack:903", None)):
    z = [x for x in KANAL["activityItems"] if x["id"] == zdarzenie][0]
    naiwne_kto = [(ludzie_po_id.get(i) or {}).get("name")
                  for i in (z.get("recent_sender_ids") or [])]
    naiwne_kto = [k for k in naiwne_kto if k][:5]
    naiwne_uchwyty = [(ludzie_po_id.get(i) or {}).get("handle")
                      for i in (z.get("recent_sender_ids") or [])]
    pary_naiwne = list(zip(naiwne_kto, naiwne_uchwyty))
    zle = [(n, u) for n, u in pary_naiwne if nazwa_do_uchwytu.get(n) != u]
    sprawdz("NAIWNA wersja rozjezdza pary w %s (test rozroznia)" % zdarzenie,
            bool(zle), pary_naiwne)
    if oczekiwane:
        sprawdz("  konkretnie: 'Jan Dziesiaty' dostaje uchwyt kogos innego",
                dict(pary_naiwne).get("Jan Dziesiaty") == "duchbeznazwy",
                pary_naiwne)
    else:
        sprawdz("  i przy osmiu nadawcach listy maja rozne dlugosci",
                len(naiwne_kto) != len(naiwne_uchwyty),
                (len(naiwne_kto), len(naiwne_uchwyty)))

print()
print("=== 4. KONTRDOWOD B: WERSJA Z %s NIE ZAPISUJE UCHWYTU ===" % ODNIESIENIE)


def zrodlo_browser(commit):
    proc = subprocess.run(["git", "-C", str(KORZEN), "show",
                           "%s:agent-v2/browser.py" % commit],
                          capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("nie dostalem browser.py z %s: %s"
                         % (commit, proc.stderr.decode("utf-8", "replace")[:200]))
    return proc.stdout.decode("utf-8")


def wytnij(src, nazwa):
    for w in ast.walk(ast.parse(src)):
        if isinstance(w, ast.FunctionDef) and w.name == nazwa:
            linie = src.splitlines()[w.lineno - 1:w.end_lineno]
            wciecie = len(linie[0]) - len(linie[0].lstrip())
            return "\n".join(x[wciecie:] if x[:wciecie].strip() == "" else x
                             for x in linie)
    raise SystemExit("nie znalazlem funkcji %s" % nazwa)


stary_kod = wytnij(zrodlo_browser(ODNIESIENIE), "dopisz_skutki")
przestrzen = dict(browser.__dict__)
exec(compile(stary_kod, "<%s:browser.py>" % ODNIESIENIE, "exec"), przestrzen)
stara_funkcja = przestrzen["dopisz_skutki"]

ile_st, wpisy_st = puscic(stara_funkcja, KANAL, ROBOCZY / "stary.jsonl",
                          przestrzen=przestrzen)
sprawdz("stara wersja tez dopisuje wszystkie zdarzenia", ile_st == 5, ile_st)
sprawdz("ale ZADEN jej wpis nie ma uchwytu (test rozroznia)",
        all("uchwyty" not in w for w in wpisy_st),
        [sorted(w) for w in wpisy_st[:1]])
sprawdz("wiec z 5 zdarzen da sie wyprowadzic 0 kont",
        sum(len([u for u in (w.get("uchwyty") or []) if u])
            for w in wpisy_st) == 0)
sprawdz("a z nowych — piec wskazan na konkretne konta",
        sum(len([u for u in (w.get("uchwyty") or []) if u])
            for w in wpisy) == 5,
        [w.get("uchwyty") for w in wpisy])
# I to jest cala roznica dla wyboru celu: te same nazwy, ta sama liczba
# zdarzen, tylko w jednej wersji wiadomo, do kogo napisac.
sprawdz("nazwy w obu wersjach identyczne — zmienil sie tylko uchwyt",
        [w.get("kto") for w in wpisy_st] == [w.get("kto") for w in wpisy],
        ([w.get("kto") for w in wpisy_st], [w.get("kto") for w in wpisy]))

print()
print("=== 5. STARE WPISY BEZ TEGO POLA DALEJ SIE CZYTAJA ===")
# 199 wpisow `skutek` na produkcji nie ma pola `uchwyty` i nigdy nie dostanie.
# Czytaja je `run.kogo_juz_dotknelismy` i `wzajemnosc` — musza przezyc
# dziennik, w ktorym polowa wpisow jest stara, a polowa nowa.
MIESZANE = pathlib.Path(tempfile.mkdtemp())
MIESZANY = MIESZANE / "dziennik.jsonl"
with MIESZANY.open("w", encoding="utf-8") as f:
    for w in wpisy_st:                     # wpisy w STARYM ksztalcie
        f.write(json.dumps(w, ensure_ascii=False) + "\n")
    for w in wpisy:                        # i w nowym, jeden plik
        f.write(json.dumps(w, ensure_ascii=False) + "\n")

o_dz = browser.DZIENNIK
try:
    browser.DZIENNIK = MIESZANY
    dotkneli = run.kogo_juz_dotknelismy()
    sprawdz("run.kogo_juz_dotknelismy nie wywala sie na mieszance",
            isinstance(dotkneli, set) and dotkneli, sorted(dotkneli)[:4])
    sprawdz("i widzi nazwy z OBU polowek",
            "igordziewiaty" in dotkneli and "jankowalski" in dotkneli,
            sorted(dotkneli))
finally:
    browser.DZIENNIK = o_dz

_zdjecie_data = wzajemnosc.config.uzyj_katalogu_danych(MIESZANE)
try:
    reakcje, nieznane = wzajemnosc._reakcje()
    sprawdz("wzajemnosc._reakcje czyta mieszany dziennik bez wyjatku",
            isinstance(reakcje, list), type(reakcje))
    # Kazde zdarzenie jest w pliku dwa razy (raz stare, raz nowe) — obie
    # polowki musza dojsc na te sama kupke, czyli nowe pole niczego nie
    # przestawia w czyjejs klasyfikacji.
    sprawdz("stary i nowy ksztalt daja te same kubelki",
            len(reakcje) % 2 == 0
            and sorted(r["typ"] for r in reakcje[:len(reakcje) // 2])
            == sorted(r["typ"] for r in reakcje[len(reakcje) // 2:]),
            [r["typ"] for r in reakcje])
finally:
    wzajemnosc.config.przywroc_katalog_danych(_zdjecie_data)

print()
print("=== PRODUKCJA: bez zmian ===")
zle = 0
for p in PILNOWANE:
    t = odcisk(p)
    ok = t == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-30s %s" % (pathlib.Path(p).name,
                          "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
