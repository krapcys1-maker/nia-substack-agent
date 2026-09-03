# -*- coding: utf-8 -*-
"""Kazdy pomiar ma nosic date WYSTAWIENIA, nie tylko pomiaru.

PO CO TO POWSTALO. Wlasciciel poprosil o rozdzielenie statystyk epoki AI od
epoki o ukrytych systemach (granica 25 sierpnia 2026). Okazalo sie, ze rekord
statystyk niesie WYLACZNIE `zmierzone` — czyli kiedy PYTALISMY. A pytamy
zawsze niedawno, takze o notki sprzed miesiaca, wiec podzial po tym polu daje
dwie epoki, z ktorych jedna jest pusta.

Trzeba bylo wiec laczyc kazda pozycje z dziennikiem po numerze — i to zawiodlo:

    unikalnych pozycji w pliku statystyk:  98
    notek nieprzypisanych do zadnej epoki: 10 z 37

Dziennik nie ma numerow starszych notek (z 29 wystawionych mial SZESC — to
zmierzone, ta sama luka, przez ktora pomiar notek bral je z profilu).

POMIAR, KTOREGO NIE DA SIE ZADATOWAC, NIE DA SIE Z NICZYM POROWNAC. Substack
podaje te date w karcie `note`, obok tresci, a dla artykulu w polu `post_date`
panelu wydawcy. Bierzemy ja przy KAZDYM pomiarze — plik statystyk przestaje
zalezec od tego, czy nasza wlasna ksiegowosc zapamietala numer.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import statystyki  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# KSZTALT PRZEPISANY Z ZYWEJ ODPOWIEDZI dla notki c-325184756, nie wymyslony.
KARTA = {
    "lastUpdatedAt": "2026-08-31T03:00:00.000Z",
    "cards": [
        {"type": "note", "cardId": "note",
         "note": {"type": "note",
                  "note": {"id": "c-325184756",
                           "timestamp": "2026-08-29T13:13:58.963Z",
                           "author": {"name": "Your Publication"}}}},
        {"type": "graphCard", "cardId": "impressions",
         "items": [{"title": "Views", "value": 48}]},
        {"type": "listCard", "cardId": "interactions",
         "items": [{"title": "Like", "value": 6},
                   {"title": "Reply", "value": 6}]},
    ],
}

print("=== 1. DATA WYSTAWIENIA JEST W REKORDZIE ===")
r = statystyki.z_kart(KARTA)
sprawdz("pole `wystawione` istnieje",
        "wystawione" in r, sorted(r))
sprawdz("i niesie date z karty, nie date pomiaru",
        r["wystawione"] == "2026-08-29T13:13:58.963Z", r.get("wystawione"))
sprawdz("`zmierzone` nadal mowi, kiedy PYTALISMY",
        r["zmierzone"] == "2026-08-31T03:00:00.000Z", r.get("zmierzone"))
sprawdz("to sa dwie ROZNE daty i o to chodzi",
        r["wystawione"][:10] != r["zmierzone"][:10])

print()
print("=== 2. RESZTA REKORDU NIETKNIETA ===")
sprawdz("wyswietlenia dalej liczone", r["wyswietlenia"] == 48, r["wyswietlenia"])
sprawdz("polubienia dalej liczone", r["polubienia"] == 6, r["polubienia"])
sprawdz("odpowiedzi dalej liczone", r["odpowiedzi"] == 6, r["odpowiedzi"])

print()
print("=== 3. BRAK DATY NIE WYWALA POMIARU ===")
# Karta bez `note` zdarza sie przy swiezej pozycji. Statystyki sa dodatkiem —
# maja oddac pusty napis, a nie zabrac caly przebieg.
for opis, dane in (
        ("brak karty `note`", {"cards": [{"type": "graphCard",
                                          "cardId": "impressions",
                                          "items": []}]}),
        ("`cards` jest None", {"cards": None}),
        ("pusty slownik", {}),
        ("note bez timestampu", {"cards": [{"cardId": "note",
                                            "note": {"note": {"id": "c-1"}}}]}),
        ("note nie jest slownikiem", {"cards": [{"cardId": "note",
                                                 "note": "cos"}]})):
    try:
        wy = statystyki.z_kart(dane)
        ok = wy.get("wystawione") == ""
    except Exception as exc:
        ok = False
        opis += "  (WYJATEK %s)" % type(exc).__name__
    sprawdz("  %s -> pusta data, bez wyjatku" % opis, ok)

print()
print("=== 4. ARTYKUL TEZ SIE DATUJE ===")
# Artykul nie idzie przez `z_kart` — liczby bierze z panelu wydawcy, gdzie
# data stoi w `post_date`. Bez tego polowa pliku dalaby sie przypisac do
# epoki, a polowa nie.
zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
i = zrodlo.index("def _artykuly_z_panelu(")
blok = zrodlo[i:zrodlo.index("\ndef ", i + 10)]
sprawdz("panel oddaje `wystawione`", '"wystawione"' in blok)
sprawdz("z pola `post_date`", 'post.get("post_date")' in blok)

print()
print("=== 5. KONTRDOWOD: SAM `zmierzone` NIE ROZDZIELA EPOK ===")
# Gdyby wystarczyl, ta poprawka nie mialaby sensu. Dwie notki wystawione
# po dwoch stronach granicy, obie zmierzone tego samego dnia.
PIVOT = "2026-08-25"
stara = statystyki.z_kart({
    "lastUpdatedAt": "2026-08-31T03:00:00.000Z",
    "cards": [{"cardId": "note", "note": {"note": {
        "id": "c-1", "timestamp": "2026-08-19T10:00:00.000Z"}}}]})
nowa = statystyki.z_kart({
    "lastUpdatedAt": "2026-08-31T03:00:00.000Z",
    "cards": [{"cardId": "note", "note": {"note": {
        "id": "c-2", "timestamp": "2026-08-29T10:00:00.000Z"}}}]})
sprawdz("po `zmierzone` obie trafiaja do TEJ SAMEJ epoki",
        (stara["zmierzone"][:10] >= PIVOT) == (nowa["zmierzone"][:10] >= PIVOT))
sprawdz("po `wystawione` trafiaja do ROZNYCH",
        (stara["wystawione"][:10] >= PIVOT) != (nowa["wystawione"][:10] >= PIVOT),
        (stara["wystawione"], nowa["wystawione"]))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
