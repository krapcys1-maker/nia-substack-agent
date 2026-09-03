"""Dwie nowe bramki: echo instrukcji w tekscie i artykul na jednym zrodle.

Kontrdowod: kazdy test musi wykryc TAKZE stan sprzed naprawy. Frazy uzyte
ponizej to prawdziwe zdania z artykulow 0016, 0017, 0019 i 0020 — jesli
bramka ich nie widzi, nie dziala.
"""
import hashlib
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import gates    # noqa: E402

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
PISARZ = (config.PROMPTS_DIR / "pisarz.md").read_text(encoding="utf-8")

print("=== 1. ECHO INSTRUKCJI — PRAWDZIWE ZDANIA Z ARTYKULOW ===")

# Te trzy stoja w pisarz.md jako ZAKAZANE przyklady, a mimo to wyszly w tekscie.
prawdziwe_wpadki = [
    ("0016", "The honest answer is that this article began life as an answer to "
             "a question about expiry dates."),
    ("0017", "What the record here does not establish deserves saying once, "
             "plainly. It does not say what hold amount any station uses."),
    ("0019", "A few things this evidence does not settle, and I will say them "
             "once rather than hedge throughout."),
]
for skad, zdanie in prawdziwe_wpadki:
    trafienia = gates.frazy_z_instrukcji(zdanie)
    sprawdz("wykrywa echo z %s" % skad, bool(trafienia), zdanie[:60])

print()
print("=== 2. NIE ALARMUJE NA ZWYKLEJ PROZIE ===")

czyste = [
    "The yellow change interval is not a universal constant. It is an "
    "engineering output, computed intersection by intersection.",
    "The shipping container is the same bargain cast in steel. Standard box "
    "dimensions mean that a crane and a truck chassis can be built anywhere.",
    "Pay at the pump with a card and two separate charges touch your account, "
    "and only one of them is the price of gasoline.",
]
for i, tekst in enumerate(czyste):
    sprawdz("milczy na prozie %d" % (i + 1), not gates.frazy_z_instrukcji(tekst),
            gates.frazy_z_instrukcji(tekst))

print()
print("=== 3. ZACHODZACE CIAGI SKLEJAJA SIE W JEDNA UWAGE ===")

# JEDNA DLUGA WKLEJKA Z JEDNEGO MIEJSCA PROMPTU. Daje kilkanascie zachodzacych
# szesciogramow, ktore MUSZA sklecic sie w jedna uwage — inaczej jedno wklejone
# zdanie zglaszaloby sie piec razy i uwagi utonelyby w szumie.
podwojna = ("Some lead-in sentence. The restraint is real and it should be "
            "invisible: state what the record says, and then more text.")
t = gates.frazy_z_instrukcji(podwojna)
sprawdz("jedna wklejka to jedna uwaga, nie piec", len(t) == 1, t)
sprawdz("sklejona fraza jest dluzsza niz prog szesciu slow",
        t and len(t[0].split()) > 6, t)
# KONTRDOWOD, ktory sam sie dzis objawil: DWIE osobne wklejki z ROZNYCH miejsc
# promptu maja dac DWIE uwagi. Sklejanie ma laczyc ciagi zachodzace, a nie
# wszystko, co znalezione — inaczej pisarz wklejajacy dwa akapity dostawalby
# jedna uwage i drugi przechodzilby niezauwazony.
rozne = ("A few things this evidence does not settle, and I will say them once "
         "rather than hedge throughout, though the record is clear enough.")
sprawdz("dwie osobne wklejki to dwie uwagi",
        len(gates.frazy_z_instrukcji(rozne)) == 2,
        gates.frazy_z_instrukcji(rozne))

print()
print("=== 4. SZEROKOSC PODSTAWY ===")

sprawdz("jeden serwis to jeden, mimo www i dwoch adresow",
        gates.szerokosc_podstawy({"confirmed_claims": [
            {"url": "https://www.tc.columbia.edu/a"},
            {"url": "https://tc.columbia.edu/b"}]}) == (1, ["tc.columbia.edu"]))
sprawdz("trzy serwisy licza sie jako trzy",
        gates.szerokosc_podstawy({"confirmed_claims": [
            {"url": "https://ops.fhwa.dot.gov/x"},
            {"url": "https://law.cornell.edu/y"},
            {"url": "https://highways.fhwa.dot.gov/z"}]})[0] == 3)
sprawdz("pusta karta nie wywala", gates.szerokosc_podstawy({}) == (0, []))
sprawdz("twierdzenie bez adresu nie liczy sie jako zrodlo",
        gates.szerokosc_podstawy({"confirmed_claims": [{"text": "x"}]}) == (0, []))

print()
print("=== 5. BRAMKI TRAFIAJA DO UWAG, ALE NIC NIE BLOKUJA ===")

karta_waska = {"confirmed_claims": [{"url": "https://tc.columbia.edu/a"}],
               "citable_numbers": []}
f = gates.deterministic_floors("A plain sentence about buses.", karta_waska)
sprawdz("waska podstawa daje uwage",
        any(x["gate"] == "WASKA_PODSTAWA" for x in f), f)
status, blokada = gates.verdict(f)
sprawdz("mimo uwagi status to SAVED", status == "SAVED", status)
sprawdz("mimo uwagi nic nie blokuje", blokada is None, blokada)

karta_szeroka = {"confirmed_claims": [{"url": "https://a.gov/1"},
                                      {"url": "https://b.org/2"}],
                 "citable_numbers": []}
f2 = gates.deterministic_floors("A plain sentence about buses.", karta_szeroka)
sprawdz("dwa zrodla juz nie alarmuja",
        not any(x["gate"] == "WASKA_PODSTAWA" for x in f2), f2)

print()
print("=== 6. PROMPT ZAPOBIEGA, NIE TYLKO WYKRYWA ===")

sprawdz("prompt mowi, ze nie jest slownikiem",
        "This brief is scaffolding, not vocabulary." in PISARZ)
# PROG PODANY ZGODNIE Z KODEM. Prompt mowil „word for word", a bramka
# porownuje ciagi SZESCIOWYRAZOWE — czyli straszyla szerzej, niz
# egzekwuje, i zniechecala pisarza do fraz, ktorych sama nie lapie.
sprawdz("prompt uprzedza o kontroli i podaje jej prawdziwy prog",
        "six words in a row" in PISARZ)
sprawdz("znikla najbardziej cytowalna fraza z 0020",
        "the simplest sentence that is still" not in PISARZ)
sprawdz("ale polecenie o bodzcu nadal stoi",
        "State the incentive plainly" in PISARZ)

print()
print("=== 7. NIC NIE ZOSTALO DOTKNIETE ===")
for p in PILNOWANE:
    sprawdz("bez zmian: %s" % pathlib.Path(p).name, PRZED[str(p)] == odcisk(p))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
