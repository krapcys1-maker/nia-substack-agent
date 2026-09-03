"""Test roznorodnosci otwarc komentarza i zapisu przydzielonego otwarcia."""
import hashlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
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


PILNOWANE = [config.DB_PATH, config.DATA_DIR / "zuzyte_fakty.json",
             config.DATA_DIR / "promocja.json", config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

print("=== 1. ostatnie_otwarcia CZYTA WLASCIWY RODZAJ ===")

kat = pathlib.Path(tempfile.mkdtemp())
_zdjecie = config.uzyj_katalogu_danych(kat)
try:
    (kat / "dziennik.jsonl").write_text("\n".join(json.dumps(x) for x in [
        {"kiedy": "2026-08-18T10:00:00+00:00", "rodzaj": "notka", "udane": True,
         "tekst": "The stop sign is octagonal."},
        {"kiedy": "2026-08-18T10:05:00+00:00", "rodzaj": "komentarz", "udane": True,
         "tekst": "The piece gets the mechanics right."},
        {"kiedy": "2026-08-18T10:06:00+00:00", "rodzaj": "komentarz", "udane": True,
         "tekst": "Zoning produces monopoly rent for incumbents."},
        {"kiedy": "2026-08-18T10:07:00+00:00", "rodzaj": "odpowiedz", "udane": True,
         "tekst": "Different kind entirely."},
    ]) + "\n", encoding="utf-8")

    kom = stages.ostatnie_otwarcia("komentarz")
    notki = stages.ostatnie_otwarcia("notka")
    print("    otwarcia komentarzy: %s" % kom)
    print("    otwarcia notek:      %s" % notki)
    sprawdz("czyta otwarcia KOMENTARZY", kom == ["the", "zoning"], kom)
    sprawdz("nie miesza z notkami", notki == ["the"], notki)
    sprawdz("nie liczy odpowiedzi", "different" not in kom, kom)
    sprawdz("domyslny rodzaj to nadal notka",
            stages.ostatnie_otwarcia() == ["the"])

    print()
    print("=== 2. WYBOR KANDYDATA NA KOMENTARZ ===")

    zajete = set(kom)

    def powtarza(d):
        s = (d.get("comment") or "").split()
        return bool(s) and s[0].strip("\"'.,").lower() in zajete

    kandydaci = [
        {"comment": "The bundle wasn't just goods, it was a hedge."},
        {"comment": "Delivery charges are the margin batteries capture."},
        {"comment": "Zoning produces rent for whoever got there first."},
    ]
    kandydaci.sort(key=powtarza)
    print("    po sortowaniu pierwszy: %r" % kandydaci[0]["comment"][:44])
    sprawdz("na czolo idzie kandydat z NIEUZYWANYM otwarciem",
            kandydaci[0]["comment"].startswith("Delivery"), kandydaci[0]["comment"][:24])
    sprawdz("powtarzajacy nie znika, tylko czeka", len(kandydaci) == 3)
    sprawdz("STARY sposob wzialby 'The bundle...' (test rozroznia)",
            kandydaci[0]["comment"] != "The bundle wasn't just goods, it was a hedge.")

    wszyscy = [{"comment": "The one."}, {"comment": "The two."}]
    wszyscy.sort(key=powtarza)
    sprawdz("gdy wszyscy powtarzaja, lista zostaje nietknieta",
            [d["comment"] for d in wszyscy] == ["The one.", "The two."], wszyscy)

    config.uzyj_katalogu_danych(kat / "nie-ma", utworz=False)
    sprawdz("brak dziennika nie wywala", stages.ostatnie_otwarcia("komentarz") == [])
finally:
    config.przywroc_katalog_danych(_zdjecie)

print()
print("=== 3. KOD NAPRAWDE TEGO UZYWA ===")

zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("comment_on pobiera ostatnie otwarcia komentarzy",
        'ostatnie_otwarcia("komentarz")' in zrodlo)
sprawdz("comment_on sortuje kandydatow", "candidates.sort(key=powtarza_otwarcie)" in zrodlo)
sprawdz("comment_on oddaje przydzielone otwarcie", '"otwarcie": otwarcie,' in zrodlo)
zrodlo_run = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("run.py zapisuje otwarcie do dziennika",
        'out.get("otwarcie")' in zrodlo_run)

print()
print("=== 4. NASZE DANE POTWIERDZAJA PROBLEM ===")

NASZE = ["The bundle wasn't just", "Your own 1948-1973 baseline", "2023 is the counterexample",
         "The piece rightly notes", "Delivery charges are the", "The piece gets the",
         "The utilities proposing the", "Was the $40bn shortfall", "What surprised me is",
         "Cody is a paid", "The Listeria recall being", "Zoning produces monopoly rent",
         "An IZ ordinance lets"]
import collections  # noqa: E402
licz = collections.Counter(t.split()[0].lower() for t in NASZE)
print("    otwarcia trzynastu komentarzy: %s" % dict(licz.most_common(4)))
sprawdz("'the' powtorzone co najmniej 4 razy", licz["the"] >= 4, licz["the"])
sprawdz("osiem roznych polecen otwarcia istnieje w konfiguracji",
        len(config.OTWARCIA) >= 8, len(config.OTWARCIA))

print()
print("=== 5. PROFIL OSOBOWOSCI: ROZKLAD, NIE ROTACJA ===")

import collections as _c  # noqa: E402
import random as _r       # noqa: E402

_r.seed(11)
proba = _c.Counter(config.losowa_postawa()[0] for _ in range(4000))
for n, ile in proba.most_common():
    print("    %-24s %5.1f%%" % (n, 100 * ile / 4000))

sprawdz("kazda postawa ma opis i wage",
        all(isinstance(v, tuple) and len(v) == 2 and v[0] > 0 and v[1]
            for v in config.POSTAWY_KOMENTARZA.values()))
sprawdz("postaw jest co najmniej szesc", len(config.POSTAWY_KOMENTARZA) >= 6,
        len(config.POSTAWY_KOMENTARZA))

udzial = {n: ile / 4000 for n, ile in proba.items()}
sprawdz("CIEKAWOSC jest najczestsza (to rejestr domu)",
        max(udzial, key=udzial.get) == "CIEKAWOSC", max(udzial, key=udzial.get))
sprawdz("KOREKTA jest RZADKA (ponizej 8%)", udzial.get("KOREKTA", 1) < 0.08,
        udzial.get("KOREKTA"))
sprawdz("ZGODA jest RZADKA (ponizej 8%)",
        udzial.get("ZGODA_Z_DOPOWIEDZENIEM", 1) < 0.08,
        udzial.get("ZGODA_Z_DOPOWIEDZENIEM"))
sprawdz("korekta i zgoda razem to mniej niz jedna dziesiata",
        udzial.get("KOREKTA", 0) + udzial.get("ZGODA_Z_DOPOWIEDZENIEM", 0) < 0.10)
sprawdz("SPRZECIW istnieje, ale nie dominuje",
        0 < udzial.get("SPRZECIW", 0) < 0.15, udzial.get("SPRZECIW"))
sprawdz("kazda postawa wypada choc raz na 4000 (zadna nie jest martwa)",
        len(proba) == len(config.POSTAWY_KOMENTARZA), len(proba))

# KONTRDOWOD: rownomierna rotacja daloby korekcie 1/8, czyli 12,5%
sprawdz("ROWNOMIERNA rotacja daloby korekcie 12,5%% — wiecej niz chcemy (test rozroznia)",
        1 / len(config.POSTAWY_KOMENTARZA) > udzial.get("KOREKTA", 0))

print()
print("=== 6. PROMPT NIESIE POSTAWE I RAMKE TRZECIEJ OSOBY ===")

szablon = pathlib.Path("agent-v2/prompts/komentarz.md").read_text(encoding="utf-8")
sprawdz("prompt ma miejsce na nazwe postawy", "{postawa}" in szablon)
sprawdz("prompt ma miejsce na opis postawy", "{postawa_opis}" in szablon)
sprawdz("prompt nazywa oba bledy: korygujacy i potakiwacz",
        "The corrector" in szablon and "The nodder" in szablon)
sprawdz("prompt podaje post jako MATERIAL, nie czyjes przekonanie",
        "artefact to be examined" in szablon)

for nazwa, (waga, opis) in config.POSTAWY_KOMENTARZA.items():
    gotowy = stages._prompt("komentarz.md", cel_slow=30, otwarcie="x",
                            postawa=nazwa, postawa_opis=opis, language="English",
                            author="a", title="t", body="b")
    if nazwa not in gotowy:
        sprawdz("postawa %s sklada sie w prompcie" % nazwa, False)
        break
else:
    sprawdz("KAZDA postawa sklada sie w prompcie bez bledu", True)

zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("comment_on losuje postawe", "config.losowa_postawa()" in zrodlo)
sprawdz("comment_on oddaje postawe", '"postawa": postawa,' in zrodlo)
sprawdz("run.py zapisuje postawe do dziennika",
        'out.get("postawa")' in pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8"))

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    t = odcisk(p)
    ok = t == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %s zdanych, %s oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
