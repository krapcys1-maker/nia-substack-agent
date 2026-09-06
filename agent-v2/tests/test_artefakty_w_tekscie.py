# -*- coding: utf-8 -*-
"""Ostatnia bramka przed publikacja: resztki szablonu i zdania o warsztacie nie wychodza na konto.

## Po co ten plik istnieje

2026-09-06, artykul 0006 kartridza `ai`, JUZ OPUBLIKOWANY na koncie testowym:
pod podtytulem stalo „Figures checked against sources to unknown." — kod
wstawil stopke ze slowem zamiast daty — a w srodku „The excerpts I worked
from carry no publication dates" i „in the pages I have", czyli pierwsza
osoba o wlasnym warsztacie, wprost zakazana w briefie pisarza. Recenzja nie
zablokowala, bramka `zapowiedziany_akapit_granic` patrzy tylko na poczatek
akapitu. Naprawa u zrodla (stopka tylko z data) nie wystarcza: nastepny
artefakt bedzie mial inny ksztalt.

Stad jedna deterministyczna bramka na samym koncu — po stopce z data, po
recenzji, PRZED okladka i przegladarka — i to samo pytanie przed weryfikacja
notki i komentarza. Tekst z artefaktem zostaje na dysku z powodem.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_artefakty_w_tekscie.py
"""
import ast
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config  # noqa: E402
import gates   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def lapie(tekst: str) -> list[str]:
    return [a["gate"] for a in gates.artefakty_w_tekscie(tekst)]


print("=== 1. TO, CO POSZLO NA KONTO 2026-09-06, DZIS BY NIE POSZLO ===")
sprawdz("stopka ze slowem zamiast daty", "ARTEFAKT_SZABLONU" in lapie(
    "# Title\n\nFigures checked against sources to unknown.\n\nAnthropic's help page says."))
sprawdz("the excerpts I worked from to zdanie o warsztacie", "WARSZTAT" in lapie(
    "The excerpts I worked from carry no publication dates, so the timing rests on July."))
sprawdz("in the pages I have tez", "WARSZTAT" in lapie(
    "The company has not explained, in the pages I have, why regional scoping cannot be made durable."))

print()
print("=== 2. INNE KSZTALTY TEGO SAMEGO BLEDU ===")
sprawdz("niewypelnione pole klamrowe", "ARTEFAKT_SZABLONU" in lapie("Read more in {title} tomorrow."))
sprawdz("niewypelnione pole katowe", "ARTEFAKT_SZABLONU" in lapie("The scene: <the scene, in one line>."))
sprawdz("znacznik TODO", "ARTEFAKT_SZABLONU" in lapie("The price is TODO per million tokens."))
sprawdz("as of n/a", "ARTEFAKT_SZABLONU" in lapie("The list is current as of n/a."))
sprawdz("dated none", "ARTEFAKT_SZABLONU" in lapie("A filing dated none was cited."))
sprawdz("the evidence card w tekscie", "WARSZTAT" in lapie("The evidence card lists three sources."))
sprawdz("wielkosc liter nie ratuje", "WARSZTAT" in lapie("THE SOURCES I CAN CITE are two."))

print()
print("=== 3. ZWYKLE ZDANIA PRZECHODZA (bramka nie moze byc nadgorliwa) ===")
for zdanie in (
    "The cause of the outage is unknown, and the company has not said when it will report.",
    "Prices rose from $10 to $20 per million tokens as of 2 August 2026.",
    "The filing dated 2026-07-01 lists 190 signatories.",
    "Anthropic's help page says: 'Marking will apply wherever Claude is offered.'",
    "Sources: the regulation, the help centre article, and the Nature study.",
    "A number below 272,000 tokens is billed at the base rate; above it, the whole request costs double.",
    "The record does not establish who signed the exemption.",
    "Here the documents leave one thing open: the date of the next review.",
    "Figures checked against sources to 2026-09-01.",
    "<b>bold</b> stays: html tags are not template fields",
):
    sprawdz("przechodzi: %s" % zdanie[:58], lapie(zdanie) == [], lapie(zdanie))
sprawdz("pusty tekst = pusta lista", gates.artefakty_w_tekscie("") == [])

print()
print("=== 4. WPIETA WE WSZYSTKIE TRZY SCIEZKI, PRZED KOSZTEM ===")
art = pathlib.Path("agent-v2/artykul_z_puli.py").read_text(encoding="utf-8")
i_wstaw = art.index("stages.wstaw_date_zrodel(draft[\"body\"], card)")
i_bramka = art.index("gates.artefakty_w_tekscie(", i_wstaw)
i_grafika = art.index("stages.grafika(conn, run_id, draft", i_wstaw)
i_publ = art.index("_opublikuj(sciezka)", i_wstaw)
sprawdz("artykul: bramka PO stopce z data", i_bramka > i_wstaw)
sprawdz("artykul: bramka PRZED okladka (zeby nie placic za obraz do tekstu, ktory nie wyjdzie)",
        i_bramka < i_grafika)
sprawdz("artykul: bramka PRZED publikacja", i_bramka < i_publ)
sprawdz("artykul: zatrzymany tekst ma wlasny kod i status w bazie",
        "KOD_ZATRZYMANY" in art and '"ZATRZYMANY", "artykul"' in art)
sprawdz("artykul: zatrzymany NIE trafia do ponowienia przez rutyne dnia",
        "zapamietaj_niewystawiony" not in art[i_bramka:art.index("return KOD_ZATRZYMANY", i_bramka)])
st = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
drzewo = ast.parse(st)
for nazwa in ("note", "comment_on"):
    fn = next((w for w in ast.walk(drzewo) if isinstance(w, ast.FunctionDef) and w.name == nazwa), None)
    if fn is None:
        continue
    zr = ast.unparse(fn)
    if "zweryfikuj(" in zr:
        sprawdz("%s: bramka artefaktow PRZED weryfikacja (platna)" % nazwa,
                "artefakty_w_tekscie(" in zr and zr.index("artefakty_w_tekscie(") < zr.index("zweryfikuj("))
    else:
        sprawdz("%s: bramka artefaktow obecna" % nazwa, "artefakty_w_tekscie(" in zr)

print()
print("=== 5. FRAZY WARSZTATU SA W TABELI JEZYKOW, NIE W KODZIE ===")
import jezyki  # noqa: E402
sprawdz("angielskie frazy warsztatu", len(jezyki.frazy("WARSZTAT", "English")) >= 10)
sprawdz("polskie frazy warsztatu", len(jezyki.frazy("WARSZTAT", "Polish")) >= 10)
sprawdz("bramka czyta je przez jezyki.frazy", "jezyki.frazy(\"WARSZTAT\"" in pathlib.Path("agent-v2/gates.py").read_text(encoding="utf-8"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
