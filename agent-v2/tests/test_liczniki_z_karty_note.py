# -*- coding: utf-8 -*-
"""Liczniki z karty `note` — jedyne, ktore Substack oddaje ZAWSZE.

CO POKAZAL POMIAR 31 sierpnia 2026 na zywym koncie. Komentarz pod cudzym
ARTYKULEM dostaje z `/api/v1/note_stats/c-<id>` JEDNA karte, a nie piec, gdy
nie zebral ani jednego wejscia:

    bez kart:  ['note']
    z kartami: ['note', 'impressionValues', 'surfaces', 'audience',
                'interactions']

Z 52 naszych komentarzy 37 mialo sama karte podgladu. Zapisywalismy dla nich
same zera — i nie dalo sie odroznic „nikt nie zobaczyl" od „nie wiemy".

ROZSTRZYGNIETE SONDA: cztery komentarze bez kart mialy w karcie `note`
`like_count: 0, restack_count: 0, reply_count: 0`. Substack NIE LICZY zasiegu
wpisow, ktore nic nie zebraly — wiec brak kart znaczy brak zasiegu, nie brak
danych. (Sprostowanie do mojej wczesniejszej hipotezy, ze „nie wiemy".)

ALE PRZY OKAZJI WYSZLO, ZE DANE WYRZUCALISMY. Karta `note` niesie
`like_count`, `restack_count` i `reply_count` ZAWSZE — takze wtedy, gdy kart
statystyk brak. Czytalismy ja wylacznie po date wystawienia. Dziesiaty raz ten
sam ksztalt w jednej sesji: sygnal jest w odpowiedzi, ktora juz pobieramy,
i konczy w koszu.

Dowod, ze to nie teoria — komentarz c-316706799 mial `like 1, restack 1,
reply 1` w karcie `note`.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
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


def karta_note(**liczniki):
    """Karta `note` w ksztalcie, w jakim oddaje ja Substack."""
    return {"cardId": "note", "note": {"note": dict(
        {"id": "c-1", "timestamp": "2026-08-25T10:00:00.000Z"}, **liczniki)}}


print("=== 1. BEZ KART STATYSTYK LICZNIKI NADAL PRZYCHODZA ===")
# To jest ten przypadek, ktory dotad dawal same zera: 37 z 52 komentarzy.
r = statystyki.z_kart({"lastUpdatedAt": "2026-08-31T14:00:00Z",
                       "cards": [karta_note(like_count=3, restack_count=1,
                                            reply_count=2)]})
sprawdz("polubienia odzyskane", r["polubienia"] == 3, r["polubienia"])
sprawdz("restacki odzyskane", r["restacki"] == 1, r["restacki"])
sprawdz("odpowiedzi odzyskane", r["odpowiedzi"] == 2, r["odpowiedzi"])
sprawdz("wyswietlen nadal nie znamy — i tak ma byc",
        r["wyswietlenia"] == 0, r["wyswietlenia"])
sprawdz("i wprost widac, ze zasiegu nie policzono",
        r["ma_karty_zasiegu"] is False, r["ma_karty_zasiegu"])

print()
print("=== 2. KARTA INTERAKCJI MA PIERWSZENSTWO ===")
# Gdy panel statystyk cos podaje, to on jest zrodlem — liczniki z `note` sa
# DROGA ZAPASOWA, nie nadpisaniem. Inaczej pelny pomiar psulby sie od
# niepelnego.
pelne = statystyki.z_kart({
    "lastUpdatedAt": "2026-08-31T14:00:00Z",
    "cards": [karta_note(like_count=99, restack_count=99, reply_count=99),
              {"cardId": "impressions", "items": [{"title": "Views", "value": 40}]},
              {"cardId": "interactions", "items": [{"title": "Like", "value": 5},
                                                   {"title": "Reply", "value": 1}]}]})
sprawdz("polubienia z karty interakcji, nie z `note`",
        pelne["polubienia"] == 5, pelne["polubienia"])
sprawdz("odpowiedzi tez", pelne["odpowiedzi"] == 1, pelne["odpowiedzi"])
sprawdz("wyswietlenia policzone", pelne["wyswietlenia"] == 40)
sprawdz("i zasieg oznaczony jako policzony",
        pelne["ma_karty_zasiegu"] is True)

print()
print("=== 3. ZERO Z `note` TO POMIAR, NIE BRAK ===")
# Wszystkie cztery sondowane komentarze bez kart mialy prawdziwe zera.
# Rekord ma je zapisac jako zera, ale z `ma_karty_zasiegu=False` obok — zeby
# raport wiedzial, ze wyswietlen nie zmierzono, a polubienia owszem.
z = statystyki.z_kart({"cards": [karta_note(like_count=0, restack_count=0,
                                            reply_count=0)]})
sprawdz("zera zapisane", z["polubienia"] == 0 and z["odpowiedzi"] == 0)
sprawdz("i oznaczone jako pomiar bez zasiegu",
        z["ma_karty_zasiegu"] is False)

print()
print("=== 4. SMIECI NIE PSUJA POMIARU ===")
# Statystyki sa dodatkiem; wyjatek tutaj zabralby caly przebieg pomiarowy.
for opis, dane in (
        ("brak karty `note`", {"cards": [{"cardId": "impressions", "items": []}]}),
        ("`note` nie jest slownikiem", {"cards": [{"cardId": "note", "note": "x"}]}),
        ("zagniezdzenie urwane", {"cards": [{"cardId": "note", "note": {}}]}),
        ("liczniki sa napisami", {"cards": [karta_note(like_count="dwa")]}),
        ("cards = None", {"cards": None}),
        ("cale dane None", None)):
    try:
        wy = statystyki.z_kart(dane)
        ok = wy["polubienia"] == 0 and "ma_karty_zasiegu" in wy
    except Exception as exc:
        ok = False
        opis += "  (WYJATEK %s)" % type(exc).__name__
    sprawdz("  %s" % opis, ok)

print()
print("=== 5. KONTRDOWOD: BEZ POPRAWKI TE LICZBY GINELY ===")
# Gdyby stary parser je oddawal, ta poprawka byla by zbedna. Stary czytal
# karte `note` WYLACZNIE po `timestamp`.
sprawdz("liczniki nie pochodza z karty interakcji, bo jej nie ma",
        r["interakcje"] == {}, r["interakcje"])
sprawdz("a mimo to polubienia sa niezerowe", r["polubienia"] == 3)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
