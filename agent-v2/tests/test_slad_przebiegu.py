"""Agent zapisuje to, co WIE w chwili dzialania — i reaguje w trakcie.

CO SIE STALO. 30 sierpnia 2026 szukalem, czemu komentarze pod notkami
przepadaja w 30 procentach wobec 7 pod postami. Odpowiedz siedziala w POZYCJI
W SERII: pierwsza akcja psula sie w 10 procentach, druga w 31, czwarta w 50.

Zeby to zobaczyc, musialem grupowac wpisy dziennika po odstepach czasu i
zgadywac, gdzie konczy sie jedna seria, a zaczyna druga. Rekonstruowalem
liczbe, ktora agent ZNAL w chwili dzialania i wyrzucal.

CZEGO PILNUJE TEN TEST:
  1. kazde dzialanie zapisuje `nr_w_serii`, `od_poprzedniej_s`, `pod_rzad_zle`,
  2. licznik porazek pod rzad zeruje sie KAZDYM powodzeniem — inaczej mierzylby
     sume dobowa, a nie serie,
  3. `run.rytm` z tego korzysta: dwie porazki pod rzad wydluzaja przerwe, trzy
     koncza blok.

Punkt 3 jest cala roznica miedzy zapisem a reakcja. Zapis, ktorego nikt nie
czyta w trakcie, to kolejny plik do przeczytania po szkodzie.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


KAT = pathlib.Path(tempfile.mkdtemp())
ORYG = browser.DZIENNIK
browser.DZIENNIK = KAT / "dziennik.jsonl"


def wyczysc():
    browser.DZIENNIK.write_text("", encoding="utf-8")
    browser._W_SERII.clear()
    browser._OSTATNIA.clear()
    browser._POD_RZAD_ZLE.clear()


def dzialaj(rodzaj="komentarz", udane=True):
    browser.dopisz_wynik(rodzaj, {"wyslane": udane}, gdzie="https://x/p/y")


def wpisy():
    out = []
    for l in browser.DZIENNIK.read_text(encoding="utf-8").splitlines():
        l = l.strip()
        if l:
            out.append(json.loads(l))
    return out


try:
    print("=== 1. KAZDE DZIALANIE NIESIE POZYCJE W SERII ===")
    wyczysc()
    for _ in range(3):
        dzialaj()
    nr = [w.get("nr_w_serii") for w in wpisy()]
    sprawdz("numery rosna 1,2,3", nr == [1, 2, 3], nr)

    print()
    print("=== 2. POZYCJA JEST OSOBNA DLA KAZDEGO RODZAJU ===")
    # Komentarz i odpowiedz to dwie rozne serie i dwa rozne tempa. Wspolny
    # licznik zlepilby je w jedna i zatarl dokladnie to, co chcemy zobaczyc.
    wyczysc()
    dzialaj("komentarz")
    dzialaj("odpowiedz")
    dzialaj("komentarz")
    pary = [(w["rodzaj"], w["nr_w_serii"]) for w in wpisy()]
    sprawdz("liczone osobno",
            pary == [("komentarz", 1), ("odpowiedz", 1), ("komentarz", 2)], pary)

    print()
    print("=== 3. ODSTEP OD POPRZEDNIEJ ===")
    wyczysc()
    dzialaj()
    dzialaj()
    w = wpisy()
    sprawdz("pierwsza nie ma odstepu (nie ma od czego liczyc)",
            "od_poprzedniej_s" not in w[0], w[0])
    sprawdz("druga ma odstep", "od_poprzedniej_s" in w[1], w[1])
    sprawdz("i jest liczba", isinstance(w[1].get("od_poprzedniej_s"), int),
            w[1].get("od_poprzedniej_s"))

    print()
    print("=== 4. PORAZKI POD RZAD — ZEROWANE KAZDYM POWODZENIEM ===")
    wyczysc()
    dzialaj(udane=False)
    sprawdz("po pierwszej porazce licznik = 1",
            browser.pod_rzad_nieudanych("komentarz") == 1,
            browser.pod_rzad_nieudanych("komentarz"))
    dzialaj(udane=False)
    sprawdz("po drugiej = 2", browser.pod_rzad_nieudanych("komentarz") == 2)
    dzialaj(udane=True)
    sprawdz("powodzenie ZERUJE serie",
            browser.pod_rzad_nieudanych("komentarz") == 0,
            browser.pod_rzad_nieudanych("komentarz"))
    # KONTRDOWOD: gdyby licznik sumowal dobe zamiast serii, po powodzeniu
    # nadal pokazywalby 2 i wycofanie odpalaloby sie bez powodu.
    sprawdz("czyli to seria, nie suma dobowa",
            browser.pod_rzad_nieudanych("komentarz") == 0)

    print()
    print("=== 5. WPIS NIESIE STAN SPRZED SIEBIE ===")
    # `pod_rzad_zle` ma opisywac, ile porazek bylo PRZED ta akcja — inaczej
    # kazda porazka mowilaby o sobie samej i analiza nie mialaby czego liczyc.
    wyczysc()
    dzialaj(udane=False)
    dzialaj(udane=False)
    stany = [w.get("pod_rzad_zle") for w in wpisy()]
    sprawdz("pierwsza porazka widzi 0 przed soba, druga 1", stany == [0, 1], stany)

    print()
    print("=== 6. RYTM NAPRAWDE Z TEGO KORZYSTA ===")
    src = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
    # CIALO FUNKCJI, A NIE OKNO 2600 ZNAKOW. Do 2 wrzesnia stalo tu
    # `src[poczatek:poczatek + 2600]` — wycinek, ktory konczyl sie w polowie
    # `rytm` i dzialal przypadkiem: dopisanie akapitu komentarza wypychalo
    # z okna zdanie o wycofaniu, a asercje oblewaly bez zmiany zachowania.
    # Odwrotnie tez: kod dopisany PO oknie byl dla testu niewidzialny.
    import ast

    _rytm = next(f for f in ast.walk(ast.parse(src))
                 if isinstance(f, ast.FunctionDef) and f.name == "rytm")
    ciało = ast.get_source_segment(src, _rytm) or ""
    sprawdz("cialo `rytm` wyciete w calosci, nie oknem znakow",
            ciało.startswith("def rytm(") and ciało.rstrip().endswith(("True",
                                                                      "False",
                                                                      ")")),
            (ciało[:24], ciało.rstrip()[-24:]))
    # Hamulec liczy porazki TEGO BLOKU, nie wszystkich blokow naraz — patrz
    # `test_hamulec_per_blok.py`. `_pod_rzad_w_bloku` stoi na
    # `browser.pod_rzad_nieudanych`, tylko odejmuje stan z chwili wejscia
    # w blok, wiec to nadal ten sam licznik.
    sprawdz("rytm pyta o porazki pod rzad",
            "_pod_rzad_w_bloku(co, na_co)" in ciało, ciało[:200])
    sprawdz("i liczy je z `browser.pod_rzad_nieudanych`",
            "pod_rzad_nieudanych(co)" in src, "licznik przestal byc tym samym")
    sprawdz("dwie porazki wydluzaja przerwe",
            "przerwa *= 2" in ciało, ciało[-400:])
    sprawdz("trzy koncza blok",
            "pod_rzad >= 3" in ciało and "return False" in ciało, ciało[-500:])
    # Wycofanie musi byc SLYSZALNE, inaczej przebieg cichnie bez powodu
    # i wyglada jak awaria.
    sprawdz("i jest wypisywane w logu", "[wycofanie]" in ciało)
finally:
    browser.DZIENNIK = ORYG

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
