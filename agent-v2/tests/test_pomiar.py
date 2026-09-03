"""Test pomiaru i doboru celow. Kazda zmiana z kontrdowodem.

Nic nie publikuje; produkcja pilnowana odciskami.
"""
import hashlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402
import config   # noqa: E402
import kanal    # noqa: E402
import run      # noqa: E402

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
             config.DATA_DIR / "promocja.json", config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "gdzie_komentowalismy.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

print("=== 1. WCZESNIE PRZED GLOSNO ===")

CELE = [
    {"pub": "gigant", "komentarze": 126, "reakcje": 3966},
    {"pub": "gigant2", "komentarze": 94, "reakcje": 3285},
    {"pub": "kameralny-zywy", "komentarze": 8, "reakcje": 276},
    {"pub": "kameralny-cichy", "komentarze": 3, "reakcje": 12},
    {"pub": "sredni", "komentarze": 22, "reakcje": 800},
    {"pub": "martwy", "komentarze": 0, "reakcje": 0},
]

nowa = [c["pub"] for c in sorted(CELE, key=kanal.wartosc_celu)]
stara = [c["pub"] for c in sorted(
    CELE, key=lambda n: n["reakcje"] * 2 + n["komentarze"] * 3, reverse=True)]
print("    STARA kolejnosc: %s" % " > ".join(stara))
print("    NOWA  kolejnosc: %s" % " > ".join(nowa))

sprawdz("STARY sposob stawial giganta na pierwszym miejscu", stara[0] == "gigant")
sprawdz("NOWY nie stawia giganta pierwszy", nowa[0] != "gigant", nowa[0])
sprawdz("na czele jest tekst z zywa publicznoscia i miejscem",
        nowa[0] == "sredni", nowa[0])
sprawdz("zatloczone laduja na koncu",
        nowa.index("gigant") > nowa.index("kameralny-zywy"), nowa)
sprawdz("wsrod zatloczonych wyzej ten z mniejszym tlokiem",
        nowa.index("gigant2") < nowa.index("gigant"), nowa)
sprawdz("zywy kameralny przed cichym kameralnym",
        nowa.index("kameralny-zywy") < nowa.index("kameralny-cichy"), nowa)
sprawdz("kolejnosc naprawde sie zmienila (test rozroznia)", nowa != stara)

print()
print("=== 2. NOTKA MA WLASNY PROG SWIEZOSCI ===")

print("    artykul: %s min    notka: %s min"
      % (config.MIN_WIEK_POSTA_MIN, config.MIN_WIEK_NOTKI_MIN))
sprawdz("prog dla notki jest KROTSZY niz dla artykulu",
        config.MIN_WIEK_NOTKI_MIN[1] < config.MIN_WIEK_POSTA_MIN[1])
sprawdz("ale nie zerowy — odpowiedz w 5 sekund zdradza automat",
        config.MIN_WIEK_NOTKI_MIN[0] >= 10, config.MIN_WIEK_NOTKI_MIN)

from datetime import datetime, timedelta, timezone  # noqa: E402

teraz = datetime.now(timezone.utc)


def post_sprzed(minut):
    return {"data": (teraz - timedelta(minutes=minut)).isoformat()}


odrzucone_art = sum(kanal._za_swiezy(post_sprzed(120)) for _ in range(40))
odrzucone_not = sum(kanal._za_swiezy(post_sprzed(120), config.MIN_WIEK_NOTKI_MIN)
                    for _ in range(40))
print("    tresc sprzed 2h: jako artykul odrzucona %s/40, jako notka %s/40"
      % (odrzucone_art, odrzucone_not))
sprawdz("2-godzinna notka PRZECHODZI (wczesniej odpadala)", odrzucone_not == 0)
sprawdz("2-godzinny artykul bywa odrzucany (stara reguła dziala)",
        odrzucone_art > 0, odrzucone_art)
sprawdz("5-minutowa notka nadal odpada",
        kanal._za_swiezy(post_sprzed(5), config.MIN_WIEK_NOTKI_MIN) is True)

print()
print("=== 3. KONTEKST CELU DO DZIENNIKA ===")

cel = {"pub": "Construction Physics", "skad": "szukanie: zoning",
       "komentarze": 81, "reakcje": 678,
       "data": (teraz - timedelta(minutes=200)).isoformat(), "url": "https://x/p/y"}
op = run.opis_celu(cel)
print("    %s" % op)
sprawdz("niesie publikacje", op["publikacja"] == "Construction Physics")
sprawdz("niesie skad przyszedl cel", "zoning" in op["skad"])
sprawdz("niesie ILU BYLO PRZED NAMI", op["komentarzy_przed"] == 81)
sprawdz("niesie wielkosc publicznosci", op["reakcje_celu"] == 678)
sprawdz("niesie wiek celu w minutach", 195 < op["wiek_celu_min"] < 210,
        op["wiek_celu_min"])
puste = run.opis_celu({})
sprawdz("pusty cel nie wywala", puste["komentarzy_przed"] == 0)

print()
print("=== 4. DOPISYWANIE SKUTKOW ===")

KANAL = {
    "activityItems": [
        {"id": "comment_like:900", "type": "comment_like", "target_comment_id": 100,
         "sender_count": 2, "recent_sender_ids": [1, 2],
         "created_at": "2026-08-16T17:31:02.000Z"},
        {"id": "note_reply:901", "type": "note_reply", "target_comment_id": 101,
         "sender_count": 1, "recent_sender_ids": [1],
         "created_at": "2026-08-16T12:09:28.000Z"},
        {"id": "follow:2026-08-16", "type": "follow", "sender_count": 3,
         "recent_sender_ids": [1, 2, 3], "created_at": "2026-08-16T21:27:27.000Z"},
        # Rodzaj, ktorego jeszcze nie widzielismy. MA byc zapisany: kanal dotyczy
        # wylacznie naszych tresci, wiec nieznany rodzaj to nowa wiadomosc.
        # Filtr z lista znanych przepuscilby restack, bo mial doslowne
        # „restack", a Substack nazwie go zapewne `note_restack`.
        {"id": "note_restack:950", "type": "note_restack", "target_comment_id": 100,
         "sender_count": 4, "recent_sender_ids": [1],
         "created_at": "2026-08-16T18:00:00.000Z"},
    ],
    "users": [{"id": 1, "name": "Designer"}, {"id": 2, "name": "Ktos"},
              {"id": 3, "name": "Trzeci"}],
}


class Nic:
    def new_page(self):
        return self

    def close(self):
        pass

    def stop(self):
        pass


oryg_api, oryg_podlacz, oryg_sesja = (browser.api_json, browser.podlacz_sie,
                                      browser.wymagaj_sesji)
oryg_dziennik = browser.DZIENNIK
try:
    browser.wymagaj_sesji = lambda: None
    browser.podlacz_sie = lambda: (Nic(), Nic(), Nic())
    browser.api_json = lambda page, sciezka, baza=None: (
        KANAL if "activity-feed-web" in sciezka else None)
    browser.DZIENNIK = pathlib.Path(tempfile.mkdtemp()) / "d.jsonl"

    ile = browser.dopisz_skutki()
    sprawdz("dopisal wszystkie cztery zdarzenia", ile == 4, ile)

    wpisy = [json.loads(l) for l in
             browser.DZIENNIK.read_text(encoding="utf-8").splitlines() if l.strip()]
    typy = sorted(w["typ"] for w in wpisy)
    sprawdz("zapisal wlasciwe typy",
            typy == ["comment_like", "follow", "note_reply", "note_restack"], typy)
    # KONTRDOWOD: stara lista znanych rodzajow przepuscilaby restack.
    stara_lista = ("comment_like", "comment_reply", "note_like", "note_reply",
                   "follow", "restack")
    sprawdz("STARA lista NIE zlapalaby 'note_restack' (test rozroznia)",
            "note_restack" not in stara_lista)
    restack = [w for w in wpisy if w["typ"] == "note_restack"][0]
    sprawdz("restack zapisany z liczba osob", restack["ilu"] == 4, restack)
    lajk = [w for w in wpisy if w["typ"] == "comment_like"][0]
    sprawdz("wie, CZEGO dotyczy reakcja", lajk["czego"] == 100, lajk)
    sprawdz("wie, ILU ludzi", lajk["ilu"] == 2, lajk)
    sprawdz("wie, KTO", "Designer" in lajk["kto"], lajk["kto"])

    ile2 = browser.dopisz_skutki()
    sprawdz("drugi przebieg NIE dopisuje tych samych reakcji", ile2 == 0, ile2)
    wpisy2 = [l for l in browser.DZIENNIK.read_text(encoding="utf-8").splitlines() if l.strip()]
    sprawdz("liczba wpisow sie nie zmienila", len(wpisy2) == 4, len(wpisy2))

    KANAL["activityItems"].append(
        {"id": "comment_reply:999", "type": "comment_reply", "target_comment_id": 100,
         "sender_count": 1, "recent_sender_ids": [1], "created_at": "2026-08-17T05:00:00Z"})
    sprawdz("NOWA reakcja zostaje dopisana", browser.dopisz_skutki() == 1)

    browser.api_json = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("padlo"))
    sprawdz("awaria kanalu nie wywala przebiegu", browser.dopisz_skutki() == 0)
finally:
    (browser.api_json, browser.podlacz_sie,
     browser.wymagaj_sesji) = oryg_api, oryg_podlacz, oryg_sesja
    browser.DZIENNIK = oryg_dziennik

print()
print("=== 5. PRZEGLAD UMIE TO POKAZAC ===")

import alarm  # noqa: E402

DZIEN = [
    {"kiedy": "2026-08-17T10:00:00+00:00", "rodzaj": "komentarz", "udane": True,
     "nasz_id": 1, "komentarzy_przed": 3, "skad": "szukanie: zoning", "slow": 40},
    {"kiedy": "2026-08-17T10:05:00+00:00", "rodzaj": "komentarz", "udane": True,
     "nasz_id": 2, "komentarzy_przed": 5, "skad": "szukanie: zoning", "slow": 55},
    {"kiedy": "2026-08-17T10:10:00+00:00", "rodzaj": "komentarz", "udane": True,
     "nasz_id": 3, "komentarzy_przed": 90, "skad": "szukanie: hidden fees", "slow": 30},
    {"kiedy": "2026-08-17T10:15:00+00:00", "rodzaj": "komentarz", "udane": True,
     "nasz_id": 4, "komentarzy_przed": 120, "skad": "szukanie: hidden fees", "slow": 44},
    {"kiedy": "2026-08-17T10:20:00+00:00", "rodzaj": "notka", "udane": True, "slow": 41},
    {"kiedy": "2026-08-17T11:00:00+00:00", "rodzaj": "skutek", "udane": True,
     "zdarzenie": "a", "typ": "comment_reply", "czego": 1, "ilu": 1, "kto": ["A"]},
    {"kiedy": "2026-08-17T11:01:00+00:00", "rodzaj": "skutek", "udane": True,
     "zdarzenie": "b", "typ": "comment_like", "czego": 2, "ilu": 2, "kto": ["B"]},
    {"kiedy": "2026-08-17T11:02:00+00:00", "rodzaj": "skutek", "udane": True,
     "zdarzenie": "c", "typ": "note_like", "czego": 9, "ilu": 6, "kto": ["C"]},
]

import io                       # noqa: E402
import contextlib               # noqa: E402

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    alarm._co_z_tego_wyszlo(DZIEN)
raport = buf.getvalue()
print(raport)

sprawdz("pokazuje zwrot z komentarza", "komentarz u obcych" in raport)
sprawdz("pokazuje zwrot z notki", "notka na profilu" in raport)
# TA PROBKA JEST DOWODEM, PO CO ROZDZIELILISMY ODPOWIEDZI OD POLUBIEN.
# Notka: 6 polubien, ZERO odpowiedzi. Komentarze: 1 odpowiedz na cztery sztuki.
# Na starej, lacznej mierze notka wychodzila osmiokrotnie lepiej (6,00 wobec
# 0,75) — mimo ze nie wywolala ani jednej rozmowy. Gdyby agent uczyl sie na
# tamtej liczbie, w kilka miesiecy przesunalby sie od wyjasniania do szoku,
# bo tam jest gradient polubien.
sprawdz("odpowiedzi sa naglowkiem, nie suma reakcji",
        "ODPOWIEDZI na jedno dzialanie" in raport, raport[:200])
sprawdz("komentarz ma 0,25 odpowiedzi na sztuke (1 na 4)",
        "0.25" in raport, raport[:400])
sprawdz("notka ma 0,00 odpowiedzi mimo szesciu polubien",
        "0.00" in raport, raport[:400])
sprawdz("polubienia pokazane OSOBNO", "polubienia (osobno" in raport, raport[:400])
sprawdz("raport nazywa proporcje polubien do rozmowy",
        "polubien" in raport and "odpowiedz" in raport)
sprawdz("pokazuje podzial wczesnie/w tloku", "czy oplaca sie byc wczesnie" in raport)
sprawdz("wczesne komentarze wracaja w 100%", "2 komentarzy, wrocilo 2" in raport, raport)
sprawdz("te w tloku nie wracaja wcale", "2 komentarzy, wrocilo 0" in raport, raport)
sprawdz("pokazuje, ktore haslo przynioslo rozmowe", "zoning" in raport)

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    alarm._co_z_tego_wyszlo([])
sprawdz("pusty dziennik nie wywala przegladu", buf.getvalue() == "")

print()
print("=== 6. NOTKI NIE IDA JUZ SCIEZKA ARTYKULOW ===")

zrodlo = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("blok komentarzy odsiewa notki", 'if x.get("rodzaj") != "notka"' in zrodlo)
sprawdz("blok dyskusji dobiera notki ze szukania",
        'if x.get("rodzaj") == "notka"' in zrodlo)
sprawdz("kanal oznacza rodzaj celu",
        '"rodzaj": "post"' in pathlib.Path("agent-v2/kanal.py").read_text(encoding="utf-8"))
sprawdz("dzien dopisuje skutki", "browser.dopisz_skutki()" in zrodlo)

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    teraz_o = odcisk(p)
    ok = teraz_o == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-28s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %s zdanych, %s oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
