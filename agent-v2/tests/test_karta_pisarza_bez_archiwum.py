# -*- coding: utf-8 -*-
"""Pisarz dostaje ZLECENIE, nie magazyn z werdyktem.

## Wada, ktora ten plik pilnuje

`karta_dla_pisarza()` zdejmowala z karty dokladnie jedno zdanie — note o wieku
zrodel — a `pisarz.md` wstawia do promptu `json.dumps(CALEJ karty)`. Do pisarza
szly wiec takze dwa pola, ktore dowodem nie sa:

  * `unused_evidence` — fragmenty i liczby, ktorych artykul nie zuzyl. Czyta je
    `bank_fragmentow()`, z karty ZAPISANEJ w bazie, zeby odzyskac oplacony
    research. W prompcie robily trzy zle rzeczy naraz: powtarzaly fragmenty
    obecne juz w syntezie, pokazywaly liczby, ktorych uzyc NIE WOLNO
    (`pisarz.md`: "Every number you write must appear literally in
    `citable_numbers`"), i nie mialy w prompcie ZADNEJ reguly — `pisarz.md` nie
    wspomina o tym polu ani slowem.
  * `ocena_ciekawosci` — werdykt o tej karcie z uzasadnieniem. Przy werdykcie
    ODLOZ model, ktorego zadaniem jest NAPISAC, dostawal w materiale wyjasnienie,
    dlaczego ten material nie da czytelnikowi powodu do zainteresowania.

`gates.py` juz to drugie pole zdejmowalo (`pobrane.pop("ocena_ciekawosci")`).
Pisarz byl jedynym miejscem, gdzie zostawalo.

Zmierzone na karcie o produkcyjnym ksztalcie: 8996 -> 3950 znakow, czyli 56%
mniej wejscia dla etapu, ktory jest najdrozszy w calym agencie.

## Czego ten plik pilnuje w DRUGA strone

Zeby przyciecie NIE dotknelo karty zapisanej ani recenzenta. Gdyby `bank_
fragmentow` przestal widziec `unused_evidence`, oplacony research przepadlby
bezpowrotnie — a to jest gorsza wada niz ta, ktora tu naprawiamy. Sekcje 2 i 3.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_karta_pisarza_bez_archiwum.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
import stages  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


FRAG = "The rule caps a single holder's tenure at ten units."


def karta():
    return {
        "working_thesis": "The rule trades continuity for independence.",
        "main_mechanism": "A new holder has no memory of prior judgements.",
        "confirmed_claims": [{"claim": FRAG, "evidence": FRAG, "url": "https://x"}],
        "citable_numbers": [{"value": "ten years", "means": "cap", "url": "https://x"}],
        "source_dates": {"newest": "2026-09-01", "oldest": "2026-08-20",
                         "note": "only one source carries a date"},
        "unused_evidence": [{"url": "https://y", "excerpts": [FRAG],
                             "numbers": ["10", "20"]}],
        "ocena_ciekawosci": {"werdykt": "ODLOZ", "powody": [FRAG], "ratunek": FRAG},
    }


print("=== 1. ARCHIWUM I WERDYKT NIE DOCIERAJA DO PISARZA ===")
chuda = stages.karta_dla_pisarza(karta())
tekst = json.dumps(chuda, ensure_ascii=False)
sprawdz("bez unused_evidence", "unused_evidence" not in chuda, sorted(chuda))
sprawdz("bez ocena_ciekawosci", "ocena_ciekawosci" not in chuda, sorted(chuda))
sprawdz("werdykt ODLOZ nie dociera w zadnej postaci", "ODLOZ" not in tekst)
sprawdz("a dowody zostaja", "confirmed_claims" in chuda and "citable_numbers" in chuda)

print()
print("=== 2. KONTRDOWOD: KARTA ZRODLOWA NIETKNIETA ===")
# `bank_fragmentow()` czyta `unused_evidence` z karty ZAPISANEJ. Gdyby ta
# funkcja mutowala wejscie, oplacony research przepadlby bez sladu — czyli
# lekarstwo byloby gorsze od choroby.
zrodlo = karta()
stages.karta_dla_pisarza(zrodlo)
sprawdz("wejscie ma nadal unused_evidence", "unused_evidence" in zrodlo)
sprawdz("wejscie ma nadal ocena_ciekawosci", "ocena_ciekawosci" in zrodlo)

print()
print("=== 3. PRZYCIETA IDZIE TYLKO DO PISARZA ===")
KOD = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("prompt pisarza dostaje karte przycieta",
        "json.dumps(karta_dla_pisarza(card)" in KOD)
sprawdz("zapis do bazy bierze karte PELNA",
        "json.dumps(card, ensure_ascii=False), status, blocked_by" in KOD)
sprawdz("recenzent tez dostaje PELNA",
        "card_json=json.dumps(card, ensure_ascii=False, indent=2)" in KOD)

print()
print("=== 4. NOTA O WIEKU DZIALA JAK DOTAD ===")
# Dwa wczesne `return card` istnialy PRZED ta zmiana i cicho omijalyby
# czyszczenie, gdyby zostaly nietkniete.
from datetime import datetime, timezone
swieza = stages.karta_dla_pisarza(
    karta(), teraz=datetime(2026, 9, 2, tzinfo=timezone.utc))
sprawdz("swiezy material: nota o wieku zdjeta",
        swieza["source_dates"]["note"] == "", swieza["source_dates"])
stara = stages.karta_dla_pisarza(
    karta(), teraz=datetime(2027, 6, 1, tzinfo=timezone.utc))
sprawdz("stary material: nota zostaje",
        stara["source_dates"]["note"] != "", stara["source_dates"])
sprawdz("ale archiwum zdjete W OBU wypadkach",
        "unused_evidence" not in swieza and "unused_evidence" not in stara)
bez_daty = karta()
bez_daty["source_dates"] = {}
sprawdz("i takze wtedy, gdy karta nie ma dat wcale",
        "unused_evidence" not in stages.karta_dla_pisarza(bez_daty))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
