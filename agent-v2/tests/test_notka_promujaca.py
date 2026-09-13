# -*- coding: utf-8 -*-
"""Notka promujaca artykul: wychodzi naprawde, ponad dwie zwykle notki dziennie.

## Pomiar, ktory to wywolal

13 wrzesnia 2026, serwer: w `promocja.json` pieciu opublikowanych artykulow,
kazdy z `wystawione: 0`, w dzienniku ANI JEDNEJ notki promujacej. Kolejka
promocji istniala, ale czytal ja tylko slot `ARTYKUL` starej sciezki notek,
a konto pisze notki persona (`stages.notki_dnia` oddaje wtedy
`personality.notes`, ktore o kolejce nic nie wie). Do tego dwa z pieciu
artykulow zniknely z archiwum publikacji.

Decyzja wlasciciela tego samego dnia: po artykule trzy dni z rzedu po jednej
notce promujacej, PONAD dwie zwykle — w dniu publikacji i dwa kolejne.

## Co ten test sprawdza

1. notka promujaca nie zjada dziennego przydzialu ani normy notek;
2. persona dostaje artykul, jego link i to, co juz o nim powiedziala, a link
   przechodzi walidacje tekstu;
3. blok `run.promuj_artykul`: brak artykulu, artykul zniknal, notka nie
   powstala, brak linku w tekscie, proba sucha, wysylka, nieudana wysylka,
   te same bramki co zwykla notka (okno czytelnikow, cichy dzien) i odlozenie
   na pozniejszy przebieg, gdy zwykla notka juz poszla w tym;
4. blok stoi w dniu zaraz po notkach.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_notka_promujaca.py
"""
import ast
import io
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, "agent-v2")
import browser      # noqa: E402
import config       # noqa: E402
import norma        # noqa: E402
import personality  # noqa: E402
import run          # noqa: E402
import stages       # noqa: E402

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
DZIS = datetime.now(timezone.utc).isoformat(timespec="seconds")
URL = "https://nia1503032.substack.com/p/id-like-the-songwriters-definition"

print("=== 1. PROMOCJA PONAD PRZYDZIALEM ===")
DZ = KAT / "dziennik.jsonl"
DZ.write_text("\n".join(json.dumps(w) for w in (
    {"kiedy": DZIS, "rodzaj": "notka", "udane": True, "typ": "persona"},
    {"kiedy": DZIS, "rodzaj": "notka", "udane": True, "typ": "persona"},
    {"kiedy": DZIS, "rodzaj": "notka", "udane": True, "typ": "promocja"},
)) + "\n", encoding="utf-8")
stary_dziennik = browser.DZIENNIK
browser.DZIENNIK = DZ
try:
    dzis = browser.z_dziennika_dzis()
    sprawdz("licznik dnia widzi dwie zwykle notki, nie trzy", dzis["notki"] == 2, dzis)
    sprawdz("promujaca policzona osobno (kontrola z profilem ja widzi)",
            dzis.get("promocje") == 1, dzis)
finally:
    browser.DZIENNIK = stary_dziennik
stary_norma = norma.DZIENNIK
norma.DZIENNIK = DZ
try:
    zrobione, _ = norma.wczytaj(3)
    dzien = DZIS[:10]
    sprawdz("norma liczy dwie notki, promujaca poza norma",
            zrobione[dzien]["notka"] == 2, dict(zrobione[dzien]))
finally:
    norma.DZIENNIK = stary_norma

print()
print("=== 2. PERSONA DOSTAJE ARTYKUL, LINK I TO, CO JUZ POWIEDZIALA ===")
zlapane = []
oryg_call = personality.llm.call


def atrapa_llm(role, system, user, **kw):
    zlapane.append(user)
    return json.dumps({"text": "A songwriter can't split what nobody wrote down.\n"
                               "Fair is a spreadsheet nobody kept.\n"
                               "Read the rest before you sign anything.\n" + URL,
                       "topic": "promo"})


personality.llm.call = atrapa_llm
stare_dane = config.uzyj_katalogu_danych(KAT / "dane")
try:
    wynik = personality.notka_promujaca(None, None, {
        "url": URL, "tytul": "I'd like the songwriter's definition of fair",
        "tekst": "Full article text about splits.",
        "powiedziane": ["Earlier note about stems."]})
finally:
    personality.llm.call = oryg_call
    config.przywroc_katalog_danych(stare_dane)
prompt = zlapane[0] if zlapane else ""
sprawdz("prompt niesie adres artykulu", URL in prompt)
sprawdz("i to, co powiedziala wczesniejsza notka", "Earlier note about stems." in prompt)
sprawdz("i zadanie notki promujacej", "This Note sends readers to it" in prompt)
sprawdz("link w tekscie przechodzi walidacje (to NASZ adres)",
        wynik["candidates"] and URL in wynik["candidates"][0]["note"], wynik)
sprawdz("wpis ma ksztalt notki do wystawienia",
        wynik.get("promocja_url") == URL and wynik.get("personality", {}).get("rubryka") == "promocja")

print()
print("=== 3. BLOK PROMOCJI ===")
ARTYKUL = {"url": URL, "tytul": "Songwriter", "tekst": "t", "wystawione": 1}
slad = {}


def swiat(artykul=ARTYKUL, wisi=True, tekst="One line.\nAnother.\n" + URL,
          wyslane=True, persona=True, okno=True, cichy=False, przebiegow=3):
    slad.clear()
    slad.update(wystawione=[], odhaczone=[], zakwestionowane=[], zapamietane=0,
                rytm=0)
    oryg = (stages.artykul_do_promocji, browser.artykul_opublikowany,
            personality.notka_promujaca, browser.wystaw_notke, stages.odhacz_promocje,
            stages.zakwestionuj_promocje, personality.remember, run.rytm,
            config.PERSONA_WLACZONA, run._KONIEC_CZASU, config.pora_na_publikacje,
            config.cichy_dzien, run.ile_przebiegow_zostalo)
    stages.artykul_do_promocji = lambda: artykul
    browser.artykul_opublikowany = lambda url: wisi
    personality.notka_promujaca = lambda conn, run_id, a: {
        "promocja_url": a["url"], "personality": {"rubryka": "promocja"},
        "candidates": ([{"note": tekst, "safe_to_post": True, "length_ok": True}]
                       if tekst else [])}
    browser.wystaw_notke = lambda t, wyslij=False, **k: (
        slad["wystawione"].append((t, k)) or {"wyslane": wyslane})
    stages.odhacz_promocje = lambda url, t="": slad["odhaczone"].append((url, t))
    stages.zakwestionuj_promocje = lambda url, powod, skad="": slad["zakwestionowane"].append(skad)
    personality.remember = lambda n, w: slad.update(zapamietane=slad["zapamietane"] + 1)
    run.rytm = lambda co, na_co, stan: slad.update(rytm=slad["rytm"] + 1) or True
    config.PERSONA_WLACZONA = persona
    run._KONIEC_CZASU = None
    config.pora_na_publikacje = lambda kiedy=None: (okno, "atrapa")
    config.cichy_dzien = lambda kiedy=None: cichy
    run.ile_przebiegow_zostalo = lambda conn: przebiegow
    return oryg


def przywroc(oryg):
    (stages.artykul_do_promocji, browser.artykul_opublikowany,
     personality.notka_promujaca, browser.wystaw_notke, stages.odhacz_promocje,
     stages.zakwestionuj_promocje, personality.remember, run.rytm,
     config.PERSONA_WLACZONA, run._KONIEC_CZASU, config.pora_na_publikacje,
     config.cichy_dzien, run.ile_przebiegow_zostalo) = oryg


o = swiat()
try:
    ile = run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("notka poszla", ile == 1, ile)
sprawdz("jako notka typu promocja", slad["wystawione"] and slad["wystawione"][0][1].get("typ") == "promocja",
        slad["wystawione"])
sprawdz("artykul odhaczony z trescia notki", slad["odhaczone"] == [(URL, "One line.\nAnother.\n" + URL)],
        slad["odhaczone"])
sprawdz("persona zapamietala notke", slad["zapamietane"] == 1)

o = swiat(artykul=None)
try:
    ile = run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("bez artykulu w kolejce: nic", ile == 0 and not slad["wystawione"])

o = swiat(wisi=False)
try:
    ile = run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("artykul zniknal z publikacji: bez notki", ile == 0 and not slad["wystawione"])
sprawdz("i zdjety z kolejki z powodem", slad["zakwestionowane"] == ["artykul zniknal"],
        slad["zakwestionowane"])

o = swiat(wisi=None)
try:
    ile = run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("nie da sie sprawdzic archiwum: notka i tak idzie (nie wiem != zniknal)", ile == 1)

o = swiat(tekst="Promo without the link.")
try:
    run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("brak linku w tekscie: link dopisany na koncu",
        slad["wystawione"] and slad["wystawione"][0][0].endswith("\n\n" + URL),
        slad["wystawione"])

o = swiat(tekst="")
try:
    ile = run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("notka nie powstala: nic nie wychodzi i nic nie odhaczone",
        ile == 0 and not slad["wystawione"] and not slad["odhaczone"])

o = swiat()
try:
    ile = run.promuj_artykul(None, 1, False, {})
finally:
    przywroc(o)
sprawdz("proba sucha: bez wysylki i bez odhaczenia",
        ile == 0 and not slad["wystawione"] and not slad["odhaczone"])

o = swiat(wyslane=False)
try:
    ile = run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("nieudana wysylka: artykul NIE odhaczony, jutro sprobuje", ile == 0 and not slad["odhaczone"])

o = swiat(persona=False)
try:
    ile = run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("bez persony blok milczy (stara sciezka ma wlasny slot)", ile == 0 and not slad["wystawione"])

o = swiat(okno=False)
try:
    ile = run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("poza oknem czytelnikow: czeka (jak zwykla notka)", ile == 0 and not slad["wystawione"])

o = swiat(cichy=True)
try:
    ile = run.promuj_artykul(None, 1, True, {})
finally:
    przywroc(o)
sprawdz("cichy dzien: czeka", ile == 0 and not slad["wystawione"])

o = swiat(przebiegow=3)
try:
    ile = run.promuj_artykul(None, 1, True, {"notka": True})
finally:
    przywroc(o)
sprawdz("zwykla notka poszla w tym przebiegu, dzis beda inne: odlozona",
        ile == 0 and not slad["wystawione"] and slad["rytm"] == 0, slad)

o = swiat(przebiegow=1)
try:
    ile = run.promuj_artykul(None, 1, True, {"notka": True})
finally:
    przywroc(o)
sprawdz("ostatni przebieg dnia: idzie, przez odstep `rytm`",
        ile == 1 and slad["rytm"] == 1, slad)

print()
print("=== 4. BLOK W DNIU ===")
ZR = io.open("agent-v2/run.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZR)):
    if isinstance(w, ast.FunctionDef) and w.name == "dzien":
        CIALO = ast.get_source_segment(ZR, w) or ""
i_n, i_p = CIALO.find('("notki", notki)'), CIALO.find('("promocja", promocja)')
sprawdz("blok promocji stoi w dniu", i_p >= 0)
sprawdz("zaraz po notkach", 0 <= i_n < i_p and i_p - i_n < 80, (i_n, i_p))
sprawdz("wynik trafia do podsumowania dnia", '"promocje": 0' in CIALO)
sprawdz("koszt notki promujacej w kanale notek", 'db.kanal("notka")' in ZR.split("def promuj_artykul(")[1][:4000])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
