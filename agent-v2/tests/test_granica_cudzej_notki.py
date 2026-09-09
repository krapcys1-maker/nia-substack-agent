# -*- coding: utf-8 -*-
"""Do modelu idzie JEDNA notka, nie zrzut calej strony kanalu.

## Co poszlo na konto 9 wrzesnia 2026

NIA podala dalej post Roberta Evansa:

    Would you trust an AI to have full control of your computer?

a podpisala go tekstem o tym, ze „one in five companies" ma dojrzaly model
zarzadzania agentami, a cztery na piec zarzadow prowadzi komitety etyczne
zbudowane dla modeli, ktore tylko przewidywaly i siedzialy cicho.

Statystyka nie byla zmyslona. Byla z CUDZEGO POSTA — Maxime'a Moutona — ktory
w kanale stoi zaraz pod Evansem. Odczytane z zapisanego zadania
(`persona-drafts/a242645eab624c…`): pole `tekst` nioslo zrzut calej strony:
post Evansa, post Moutona, dwa nastepne i pasek „People to follow"
z kilkunastoma nazwiskami.

Czytelnik widzial wiec pytanie i odpowiedz na inne pytanie. Wlasciciel
przeczytal to jako tekst bez ladu i skladu i mial racje.

## Przyczyna

`_notka_przy_przycisku` wspinala sie po drzewie DOM „dopoki kontener nie ma
wiecej niz 120 znakow". Prog mial znaczyc „mamy juz cala notke". Przy notce
KROTKIEJ znaczyl cos odwrotnego: post Evansa ma szescdziesiat znakow, wiec
petla nie zatrzymywala sie na jego granicy i wspinala sie dalej.

Krotka notka GWARANTOWALA przechwycenie cudzych. Ta sama funkcja karmi
`w_rewirze` przy polubieniach, wiec o polubieniu decydowal tekst obcych
wpisow obok.

## Regula

Granica jest strukturalna, nie dlugosciowa: nie wchodzimy do kontenera, ktory
niesie wiecej autorow niz nasza notka. Po stronie Pythona stoi druga zapora na
wypadek, gdyby Substack zmienil uklad — drugie „Subscribe" otwiera kolejny
wpis, a pasek boczny nie nalezy do zadnego.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_granica_cudzej_notki.py
"""
import io
import sys

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# PRZEPISANE Z PRODUKCJI, nie wymyslone. To jest dokladnie to, co dostal model.
ZRZUT = (
    "Robert Evans\n2d\nSubscribe\n\n"
    "Would you trust an AI to have full control of your computer?\n\n"
    "11\n20\n"
    "Maxime Mouton\n2d\nSubscribe\n\n"
    "Agentic AI has landed. Governance for it has not.\n\n"
    "One in five companies currently has a mature governance model for "
    "autonomous AI agents, even as agent deployment has accelerated across "
    "every sector in 2026. The frameworks already in place (ethics boards, "
    "responsible AI committees, CAIO roles) were built for static predictive "
    "models, not for agents that make multi-step decisions and act across "
    "systems without human sign-off at each step.\n\n"
    "6\n3\n"
    "Sakshi Jha\n1d\nSubscribe\n\nI joined Substack a few months ago. Am I late or what?\n\n"
    "17\n7\n"
    "People to follow\nSee all\nLenny Rachitsky\nFollow\nGergely Orosz\nFollow\n"
)

print("=== 1. Z CUDZYCH WPISOW ZOSTAJE PIERWSZY ===")
tekst, przyciete = browser._tylko_jeden_wpis(ZRZUT)
sprawdz("zauwazylismy, ze bylo ich kilka", przyciete is True)
sprawdz("pytanie Evansa zostalo",
        "full control of your computer" in tekst, tekst[:120])
sprawdz("statystyka Moutona ZNIKLA",
        "One in five companies" not in tekst, tekst[:200])
sprawdz("jego teza tez zniknela",
        "Governance for it has not" not in tekst, tekst[:200])
sprawdz("post Sakshi zniknal", "Am I late" not in tekst, tekst[:200])
sprawdz("pasek boczny zniknal",
        "People to follow" not in tekst and "Lenny Rachitsky" not in tekst,
        tekst[-140:])
sprawdz("i nazwisko nastepnego autora tez",
        "Maxime Mouton" not in tekst, tekst[-140:])

print()
print("=== 2. POJEDYNCZA NOTKA ZOSTAJE NIETKNIETA ===")
# KONTRDOWOD. Poprawka, ktora tnie takze poprawny material, jest gorsza od
# wady: obcielibysmy tresc, na ktora NIA ma odpowiadac.
JEDNA = ("Robert Evans\n2d\nSubscribe\n\n"
         "Would you trust an AI to have full control of your computer?\n\n11\n20")
t2, p2 = browser._tylko_jeden_wpis(JEDNA)
sprawdz("nic nie przyciete", p2 is False, t2[:80])
sprawdz("tresc bez zmian", t2 == JEDNA.strip(), t2[:80])

DLUGA = ("Maxime Mouton\n2d\nSubscribe\n\n"
         "Agentic AI has landed. Governance for it has not.\n\n"
         "One in five companies currently has a mature governance model for "
         "autonomous AI agents, even as agent deployment has accelerated.\n\n6\n3")
t3, p3 = browser._tylko_jeden_wpis(DLUGA)
sprawdz("dluga pojedyncza notka tez nietknieta", p3 is False, t3[:80])
sprawdz("i niesie swoja statystyke", "One in five companies" in t3)

print()
print("=== 3. PUSTE I DZIWNE WEJSCIA NIE WYWALAJA ===")
for wejscie in ("", "   ", "Bez zadnego Subscribe w ogole.",
                "Subscribe", "\nSubscribe\n\nSubscribe\n"):
    try:
        t, _ = browser._tylko_jeden_wpis(wejscie)
        sprawdz("przezylo: %r" % wejscie[:24], isinstance(t, str))
    except Exception as exc:                       # noqa: BLE001
        sprawdz("przezylo: %r" % wejscie[:24], False,
                "%s: %s" % (type(exc).__name__, exc))

print()
print("=== 4. GRANICA W DOM LICZY AUTOROW, NIE ZNAKI ===")
zrodlo = io.open("agent-v2/browser.py", encoding="utf-8").read()
i = zrodlo.index("def _notka_przy_przycisku")
j = zrodlo.index("def _tylko_jeden_wpis")
cialo = zrodlo[i:j]
sprawdz("liczymy odrebnych autorow w kontenerze",
        "const autorzy = (n) => new Set(" in cialo)
sprawdz("i przerywamy PRZED wejsciem do niego",
        "if (autorzy(rodzic) > 2) break;" in cialo)
# KONTRDOWOD: sam prog dlugosci zostaje jako dodatkowe zabezpieczenie, ale
# nie moze byc juz JEDYNYM warunkiem.
sprawdz("prog dlugosci zostal jako wtorny",
        "n.innerText.length > 120" in cialo)
i_aut = cialo.index("if (autorzy(rodzic) > 2) break;")
i_dl = cialo.index("n.innerText.length > 120")
sprawdz("i stoi PO sprawdzeniu autorow", i_aut < i_dl, (i_aut, i_dl))

print()
print("=== 5. PRZYCIECIE JEST WIDOCZNE, NIE CICHE ===")
# Ciche przyciecie zamienia jedna wade w druga: nie wiedzielibysmy, ze uklad
# strony sie zmienil i ze pierwsza zapora przestala dzialac.
sprawdz("przebieg mowi, gdy kontener niosl kilka wpisow",
        "kontener niosl kilka wpisow" in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
