# -*- coding: utf-8 -*-
"""Ten sam autor nie wraca do restacka codziennie.

## Pomiar

11 wrzesnia 2026, caly dziennik: TRZYNASCIE udanych restackow, DZIESIECIU
roznych autorow.

    Publikacja A   3     (09-10T14:58, 09-10T19:49, 09-11T12:34)
    pozostali osmiu         po 1
    bez zapisanego autora   2

Trzy z trzynastu to jedna publikacja, i akurat drugi projekt wlasciciela.
Z boku konto wyglada wtedy jak tuba jednego zrodla, a nie jak ktos, kto czyta
kanal. Wlasciciel: „restacki zwykle te same konta sa restackowane".

## Skad sie to bralo

Kanal ma stala kolejnosc, a petla bierze PIERWSZEGO kandydata, ktory przejdzie
rewir i ocene. Kto stoi wysoko i pisze na temat, ten wraca codziennie. Zadna
czesc kodu nie pytala, czy juz go w tym tygodniu podawalismy.

## Granica

Siedem dni, nie „nigdy wiecej". Dobry autor ma wracac, tylko nie co dzien.

## Dlaczego takze odcisk tresci

Dwa z trzynastu wpisow nie maja zapisanego autora. Sam odpoczynek po nazwisku
nie rozpoznalby ich nigdy, wiec obok nazwiska pamietamy odcisk cudzej notki.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_restack_nie_wraca_do_tego_samego.py
"""
import ast
import io
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "agent-v2")
import browser          # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def kiedy(dni_temu):
    return (datetime.now(timezone.utc) - timedelta(days=dni_temu)).isoformat()


print("=== 1. AUTOR Z TEGO TYGODNIA JEST PAMIETANY ===")
with tempfile.TemporaryDirectory() as kat:
    plik = Path(kat) / "dziennik.jsonl"
    wpisy = [
        {"rodzaj": "restack", "udane": True, "komu": "Publikacja A",
         "kiedy": kiedy(1)},
        {"rodzaj": "restack", "udane": True, "komu": "Unmesh Shah",
         "kiedy": kiedy(0)},
        # Starszy niz tydzien — ma wrocic do gry.
        {"rodzaj": "restack", "udane": True, "komu": "Benjamin Laval",
         "kiedy": kiedy(9)},
        # Nieudany restack nikogo nie blokuje: nic nie poszlo w swiat.
        {"rodzaj": "restack", "udane": False, "komu": "Chelsea Salamone",
         "kiedy": kiedy(0)},
        # Bez autora, ale z odciskiem cudzej notki.
        {"rodzaj": "restack", "udane": True, "komu": "",
         "zrodlo": "sixty seven people answered this and not one of us knows",
         "kiedy": kiedy(2)},
    ]
    plik.write_text("\n".join(json.dumps(w) for w in wpisy) + "\n",
                    encoding="utf-8")
    with patch.object(browser, "DZIENNIK", plik):
        byli = browser.kogo_juz_restackowalismy()
    sprawdz("wczorajszy autor odpoczywa",
            "publikacja a" in byli, sorted(byli)[:3])
    sprawdz("dzisiejszy autor odpoczywa", "unmesh shah" in byli)
    sprawdz("sprzed dziewieciu dni WRACA do gry",
            "benjamin laval" not in byli)
    sprawdz("nieudany restack nikogo nie blokuje",
            "chelsea salamone" not in byli)
    sprawdz("odcisk notki bez autora tez pamietany",
            "sixty seven people answered this and not one of us knows" in byli)

print()
print("=== 2. OKNO DA SIE ZMIENIC, I MA ROZSADNA WARTOSC ===")
sprawdz("stala istnieje", hasattr(browser, "DNI_ODPOCZYNKU_AUTORA"))
sprawdz("siedem dni", browser.DNI_ODPOCZYNKU_AUTORA == 7,
        browser.DNI_ODPOCZYNKU_AUTORA)
with tempfile.TemporaryDirectory() as kat:
    plik = Path(kat) / "dziennik.jsonl"
    plik.write_text(json.dumps(
        {"rodzaj": "restack", "udane": True, "komu": "Ktos",
         "kiedy": kiedy(5)}) + "\n", encoding="utf-8")
    with patch.object(browser, "DZIENNIK", plik):
        sprawdz("okno trzech dni juz go przepuszcza",
                "ktos" not in browser.kogo_juz_restackowalismy(dni=3))
        sprawdz("okno siedmiu dni jeszcze go trzyma",
                "ktos" in browser.kogo_juz_restackowalismy(dni=7))

print()
print("=== 3. BRAK DZIENNIKA TO PUSTA WIEDZA ===")
with tempfile.TemporaryDirectory() as kat:
    with patch.object(browser, "DZIENNIK", Path(kat) / "nie-ma.jsonl"):
        sprawdz("pusty zbior bez wyjatku",
                browser.kogo_juz_restackowalismy() == set())
with tempfile.TemporaryDirectory() as kat:
    plik = Path(kat) / "dziennik.jsonl"
    plik.write_text("{zepsute\n\n{}\n", encoding="utf-8")
    with patch.object(browser, "DZIENNIK", plik):
        sprawdz("zepsute linie pomijane",
                browser.kogo_juz_restackowalismy() == set())

print()
print("=== 4. PETLA NAPRAWDE GO PYTA ===")
ZRODLO = io.open("agent-v2/browser.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "restackuj_w_kanale":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""
sprawdz("blok pyta o odpoczywajacych",
        "kogo_juz_restackowalismy()" in CIALO)
sprawdz("i odsiewa po autorze", "in odpoczywaja" in CIALO)
sprawdz("oraz po odcisku cudzej notki", "odcisk_zrodla" in CIALO)
sprawdz("mowi o tym glosno", "juz byl podany dalej w tym tygodniu" in CIALO)
sprawdz("i liczy takie pominiecia", '"odpoczywa"' in CIALO)
sprawdz("rachunek podaje te liczbe", "%d odpoczywa" in CIALO)

print()
print("=== 5. DZIENNIK ZAPAMIETUJE ZRODLO ===")
# Bez tego pola odcisk nie mialby skad sie wziac przy nastepnym przebiegu.
sprawdz("zapis restacka niesie odcisk cudzej notki",
        'zrodlo=plaski(str(notka.get("tekst") or ""))[:120]' in CIALO)
sprawdz("i nadal zapisuje autora", 'komu=notka.get("autor", "")' in CIALO)

print()
print("=== 6. RESZTA ODSIEWOW NIE ZOSTALA RUSZONA ===")
for fraza in ("to nasza wlasna notka", "poza rewirem",
              "nie odczytalem tresci notki", "zrobione_odciski.add("):
    sprawdz("nadal jest: %s" % fraza[:34], fraza in CIALO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
