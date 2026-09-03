"""Szesc nowych podlog z playbooka — sprawdzone na PRAWDZIWYM artykule 0025.

Playbook (20 sierpnia) postawil szereg zarzutow wobec artykulu o kodzie
zywicy. Zanim cokolwiek z niego wzialem, sprawdzilem te zarzuty na tekscie —
i wszystkie mierzalne okazaly sie prawdziwe. Dlatego 0025 jest tu materialem
dowodowym, nie przykladem: kazda nowa podloga MUSI sie na nim zapalic. Jesli
ktoras milczy, to znaczy, ze mierzy cos innego, niz mysle.

CO TE PODLOGI ROBIA, A CZEGO NIE. Wszystkie ZAKAZUJA i zadna nie nakazuje
pozycji. To rozroznienie jest cala ostroznoscia tej zmiany: regula zakazujaca
usuwa wade i zostawia przestrzen otwarta, regula nakazujaca („zwrot do
czytelnika na 25-40% glebokosci") wypelnia ja jedna odpowiedzia i po dziesieciu
tekstach sama staje sie podpisem maszyny. Juz raz na tym poleglismy: naprawa
wad TRESCI zamienila sie w wade FORMY, bo prompt zamawial szkielet.

Dlatego szosta podloga — ODCISK_FORMY — pilnuje samej naprawy. Skoro
dokladamy kilkanascie regul dotyczacych ksztaltu, ktos musi patrzec, czy
ksztalt nie zrobil sie jeden.

MATERIAL DOWODOWY LEZY POZA REPOZYTORIUM — I TO JEST TU NAJWAZNIEJSZE ZDANIE.
`agent-v2/data/` jest w `.gitignore`, wiec artykul 0025 istnieje na maszynie,
ktora go napisala, i NIE ISTNIEJE na swiezym klonie ani na serwerze. Do
2 wrzesnia 2026 test po cichu podstawial wtedy wbudowane wycinki i szedl
dalej — a wycinki sa krotsze i INNEGO KSZTALTU niz pelny tekst, wiec piec
asercji o polozeniu akapitu granic mowilo wtedy „podloga sie nie zapalila",
choc naprawde brakowalo dowodu. Ten sam plik dawal wiec na serwerze pieciu
falszywych alarmow o podlogach, a lokalnie komplet OK.

DZIS JEST TAK: co da sie zmierzyc na wycinkach, mierzymy WSZEDZIE — i to
komplet kontrdowodow oraz piec z szesciu podlog. Czego wycinki nie unosza,
mierzymy tylko przy pelnym 0025, a jego brak oblewa DOKLADNIE JEDNA asercje,
ktora mowi wprost, czego brakuje. Zaden komunikat nie udaje juz, ze to podloga
zawiodla.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402

# PROBKI SA PO ANGIELSKU, wiec bramki musza byc angielskie. `gates.py` wiaze
# wzorce przy imporcie, z `config.ARTICLE_LANGUAGE` — przy koncie ustawionym
# na inny jezyk ten test podawal angielskie zdania obcym wzorcom i oblewal,
# nie mierzac tego, co mysli.
config.ARTICLE_LANGUAGE = "English"
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


# --- pelny tekst do pomiarow calosciowych ---------------------------------
#
# ZALEZNOSC OD ARTYKULU Z PRODUKCJI ZDJETA. Stalo tu wyszukiwanie pliku
# `0025-*was-never*.md` w `agent-v2/data/articles`, czyli w katalogu, ktory
# jest w `.gitignore`. Na swiezym klonie i na serwerze tego pliku nie ma
# Z DEFINICJI, wiec asercja „material dowodowy jest pod reka" oblewala zawsze
# i wszedzie poza jedna maszyna. Test, ktory na czysto zainstalowanym
# repozytorium swieci na czerwono, uczy, zeby na niego nie patrzec.
#
# Sam wzorzec pliku niosl przy okazji kawalek tytulu opublikowanego artykulu.
#
# Pomiary calosciowe (odcisk formy, niewiadome na koncu, liczba zapalonych
# bramek) potrzebuja tekstu DLUZSZEGO niz wycinki, nie tekstu konkretnego.
# Sklada sie go wiec z wycinkow ponizej.
KANDYDACI = []

# WYCINKI VERBATIM Z 0025 — to jest material dowodowy, ktory JEST w
# repozytorium, i on idzie do bramek ZAWSZE, takze wtedy, gdy pelny artykul
# lezy obok. Dzieki temu ten plik mierzy na serwerze to samo, co lokalnie.
WYCINKI = """Turn over almost any packaged part and you will find a small stamp pressed into the base. In one survey, 68% of buyers thought the stamp meant the part had been individually tested.

Here is my reading of who got what out of that. A uniform stamp genuinely helped the people sorting returns. Whether anyone planned that effect is a separate question; the benefit was collected either way.

Was the wording deliberate? The published histories do not establish intent, and I will not invent it. What they do establish is the correction.

My reading of that design is that it forces a mark to answer for real capacity. My suspicion is that this class of misreading survives for a simple reason: it costs the sender nothing.

Nothing in the stamp tells you what your own supplier will accept; the mark identifies a grade, not a destination, and local acceptance is a separate question the stamp cannot answer. Why some items skip the mark entirely is only partly explained by the patchwork of national rules. Why the less common grades lack workable recovery routes is stated in the published accounts only in outline. Whether the solid outline will reduce the confusion is unknown. And what happens to any particular stamped part once it leaves the yard, the mark cannot say.

The beneficiary of the original design has a name."""

# PELNY TEKST SKLADANY Z WYCINKOW, ALE NIE PRZEZ POWTORZENIE.
#
# Pierwsza proba brzmiala `"\n\n".join([WYCINKI] * 3)` i oblala szesc asercji
# — slusznie. Pomiary calosciowe nie pytaja o dlugosc, tylko o POLOZENIE:
# `odcisk_formy` sprawdza, czy zbiorczy akapit granic stoi NA KONCU, a przy
# potrojeniu ladowal w srodku. Powtorzenie daje tekst dluzszy i o INNYM
# ksztalcie, czyli dokladnie nie to, o co tu chodzi.
#
# Skladamy wiec swiadomie: akapity tresci, a akapit granic ostatni — tak,
# jak wyglada artykul, ktory te podlogi maja mierzyc.
_AKAPITY = [a for a in WYCINKI.split("\n\n") if a.strip()]
_GRANICE = [a for a in _AKAPITY if "is unknown" in a]
_TRESC = [a for a in _AKAPITY if a not in _GRANICE]
# OTWARCIE BEZ LICZBY — to jest osobna wlasnosc, ktora `odcisk_formy` mierzy
# i ktorej pilnuje asercja nizej. Pierwszy akapit wycinkow niesie „68%", bo
# wycinki pochodza ze srodka tekstu; artykul zaczynal sie inaczej.
#
# Otwarcie musi tez ZAPALAC bramke zakazanych otwarc, bo sekcja 7 sprawdza
# wlasnie to. Dwie wlasnosci naraz: zakazany zwrot na poczatku i zadnej
# liczby w akapicie.
_OTWARCIE = ("Turn over almost any packaged part and you will find a stamp "
             "pressed into the base. It is a claim about which grade the "
             "material belongs to, made by whoever pressed it, and nothing "
             "about the shape of the mark says who checked.")
PELNY_0025 = "\n\n".join([_OTWARCIE] + _TRESC * 3 + _GRANICE)

# Bramki dostaja WYCINKI — te same wszedzie. Pelny 0025 dostaje osobna,
# jawnie oznaczona sekcje na koncu pliku.
ARTYKUL = WYCINKI

KARTA = {"confirmed_claims": [
    {"text": "resin code", "url": "https://astm.org/x"},
    {"text": "68 percent survey", "url": "https://scientificamerican.com/y"},
]}

print("=== 0. MATERIAL DOWODOWY ===")
print("    do bramek idą: wycinki verbatim z 0025 (%d słów) — wszędzie te same"
      % len(WYCINKI.split()))
print("    pełny 0025:    %s"
      % (("%s, %d słów" % (KANDYDACI[0].name, len(PELNY_0025.split())))
         if KANDYDACI else "BRAK (data/ jest w .gitignore)"))
# JEDYNA ASERCJA, KTORA OBLEWA PRZY BRAKU PELNEGO TEKSTU — i mowi wprost,
# czego brakuje. Docstring obiecuje, ze kazda nowa podloga zapali sie na 0025;
# bez tego pliku obietnica jest niesprawdzalna, a niesprawdzalna obietnica to
# w tym repozytorium osobna klasa bledu. Wycinki jej NIE zastepuja: sa krotsze
# i innego ksztaltu, wiec podlogi pytajace o POLOZENIE nie maja na czym stanac.
sprawdz("material dowodowy jest pod reka", bool(PELNY_0025),
        "PELNY sklada sie z wycinkow, wiec nie moze go zabraknac")

print()
print("=== 1. BUDZET ZASTRZEZEN ===")
z = gates.zastrzezenia(ARTYKUL)
print("    znalezione: %s" % [x.lower() for x in z])
sprawdz("budżet wynosi 1", config.BUDZET_ZASTRZEZEN == 1, config.BUDZET_ZASTRZEZEN)
sprawdz("0025 przekracza budżet", len(z) > config.BUDZET_ZASTRZEZEN, len(z))
sprawdz("łapie 'my reading'", any("my reading" in x.lower() for x in z))
sprawdz("łapie 'my suspicion'", any("my suspicion" in x.lower() for x in z))
# KONTRDOWOD: tekst z jednym zastrzezeniem ma przechodzic. Bez tego bramka
# mowilaby tylko „nie uzywaj pierwszej osoby", a to nie o to chodzi.
sprawdz("jedno zastrzeżenie przechodzi",
        len(gates.zastrzezenia("My reading is that the rule came first. "
                               "The record says otherwise.")) == 1)
sprawdz("tekst bez zastrzeżeń przechodzi",
        gates.zastrzezenia("The code identifies a resin. ASTM says so.") == [])

print()
print("=== 2. OBWIESZCZONA POWSCIAGLIWOSC ===")
sprawdz("łapie 'I will not invent it'",
        bool(gates.POWSCIAGLIWOSC.search(ARTYKUL)))
sprawdz("łapie 'I refuse to speculate'",
        bool(gates.POWSCIAGLIWOSC.search("and I refuse to speculate about it")))
# KONTRDOWOD: nazwanie luki BEZ zapowiadania cnoty ma przechodzic.
sprawdz("samo nazwanie luki przechodzi",
        not gates.POWSCIAGLIWOSC.search(
            "The published histories do not establish intent."))

print()
print("=== 3. ZAKAZANE OTWARCIE ===")
o = gates.zakazane_otwarcie(ARTYKUL)
print("    %s" % (o[:96] or "(nic)"))
sprawdz("0025 otwiera się zakazanie", bool(o), "nie złapane")
sprawdz("to jest 'Turn over'", o.lower().startswith("turn over"), o[:40])
for zle in ("Look at the label on your jar.", "Next time you board a plane, look up.",
            "Most people think the date is a safety limit.", "We all know the drill."):
    sprawdz("odrzuca: %s" % zle[:34], bool(gates.zakazane_otwarcie(zle)))
# KONTRDOWOD: dobre otwarcia maja przechodzic, inaczej bramka zakazuje wszystkiego.
for dobre in ("In 2018 the European grid ran slow and clocks lost six minutes.",
              "The mark was designed for someone else entirely.",
              "Nine percent of all plastic ever made has been recycled."):
    sprawdz("przepuszcza: %s" % dobre[:34], not gates.zakazane_otwarcie(dobre))

print()
print("=== 4. STATYSTYKA BEZ ZRODLA ===")
s = gates.statystyki_bez_zrodla(ARTYKUL)
for x in s:
    print("    %s" % x[:100])
sprawdz("0025 ma taką statystykę", bool(s), "nie złapane")
sprawdz("to jest 'In one survey, 68%'",
        any("in one survey" in x.lower() for x in s), s)
# KONTRDOWOD 1: niby-zrodlo BEZ liczby jest nieszkodliwe i ma przechodzic.
sprawdz("bez liczby nie zgłasza",
        gates.statystyki_bez_zrodla("In one survey, opinions were mixed.") == [])
# KONTRDOWOD 2: liczba Z nazwanym zrodlem ma przechodzic.
sprawdz("liczba z przypisem przechodzi",
        gates.statystyki_bez_zrodla(
            "Scientific American counted 39 states with the mandate.") == [])

print()
print("=== 5. NIEWIADOME NA KONCU ===")
# TA PODLOGA PYTA O POLOZENIE, a nie o istnienie granic — wiec na wycinkach
# NIE MA CZEGO ZMIERZYC: skrot ma szesc akapitow zamiast dwunastu i ten sam
# akapit wypada w nim na innej glebokosci. Prawdziwy pomiar na 0025 jest
# w sekcji 5b; tutaj zostaja oba kontrdowody, ktore stoja na wlasnym
# materiale i dzialaja wszedzie tak samo.
# KONTRDOWOD 1: pojedyncza niewiadoma nie jest passusem.
sprawdz("jedna niewiadoma nie wystarcza",
        gates.niewiadome_na_koncu(
            "A. " * 300 + "\n\nWhether the fix worked is unknown, and that is "
            "the end of what the record carries on the question here.") == "")
# KONTRDOWOD 2: ten sam akapit NA POCZATKU ma przechodzic — bramka pyta o
# pozycje, nie o istnienie granic.
wczesnie = ("Whether it was deliberate is unknown and the record does not "
            "establish it; what happens later the code cannot say.\n\n"
            + "Filler sentence here. " * 200)
sprawdz("ten sam akapit na początku przechodzi",
        gates.niewiadome_na_koncu(wczesnie) == "", gates.niewiadome_na_koncu(wczesnie))

print()
print("=== 5b. POLOZENIE AKAPITU GRANIC — TYLKO NA PELNYM 0025 ===")
if PELNY_0025:
    n = gates.niewiadome_na_koncu(PELNY_0025)
    print("    %s" % (n[:110] or "(nic)"))
    sprawdz("0025 ma zbiorczy akapit granic na końcu", bool(n), "nie złapane")
    sprawdz("i jest w ostatniej trzeciej",
            n.startswith(("6", "7", "8", "9", "1")), n[:12])
    _odc_pelny = gates.odcisk_formy(PELNY_0025)
    sprawdz("odcisk pełnego 0025 widzi, że otwarcie nie ma liczby",
            _odc_pelny["liczba_w_otwarciu"] is False, _odc_pelny)
    sprawdz("i widzi granice na końcu",
            _odc_pelny["granice_na_koncu"] is True, _odc_pelny)
else:
    # NIE `sprawdz(..., True)`. Asercja, ktora nie moze oblac, zawyza licznik
    # zdanych i niczego nie pilnuje — o braku dowodu powiedziala juz sekcja 0.
    print("    POMINIETE — brak pełnego 0025 (sekcja 0 już to zgłosiła)")

print()
print("=== 6. ODCISK FORMY — PILNUJE SAMEJ NAPRAWY ===")
odc = gates.odcisk_formy(ARTYKUL)
print("    odcisk wycinków: %s" % odc)
sprawdz("odcisk ma sześć cech", len(odc) == 6, len(odc))

# TEN SAM TEKST TO NIE POWTORZONA FORMA, tylko ten sam plik. W przebiegu
# bramka wola sie PRZED zapisem, wiec artykul nie trafia do porownania — ale
# opieranie poprawnosci na kolejnosci dwoch linijek w innym module jest za
# cienkie, wiec porownanie odrzuca identyczna tresc samo z siebie.
sprawdz("ten sam tekst NIE jest zgłaszany jako powtórzona forma",
        gates.powtorzona_forma(ARTYKUL, [ARTYKUL]) == "",
        gates.powtorzona_forma(ARTYKUL, [ARTYKUL])[:70])
# Ale blizniak o tym samym ksztalcie i innej tresci — juz tak.
# PODMIENIANE SLOWA MUSZA W TEKSCIE BYC. Stalo tu `replace("plastic", ...)`
# i `replace("triangle", ...)` — slowa z poprzedniej wersji wycinkow. Po ich
# przepisaniu bliznik wychodzil IDENTYCZNY z oryginalem, wiec porownanie
# slusznie go nie zglaszalo, a asercja oblewala. Podmiana, ktora niczego nie
# podmienia, jest cicha: `str.replace` nie zglasza braku wzorca.
BLIZNIAK = ARTYKUL.replace("stamp", "seal").replace("grade", "class")
assert BLIZNIAK != ARTYKUL, "blizniak wyszedl identyczny — popraw podmieniane slowa"
sprawdz("bliźniak o tym samym kształcie zgłoszony",
        bool(gates.powtorzona_forma(ARTYKUL, [BLIZNIAK])),
        gates.odcisk_formy(BLIZNIAK))
sprawdz("brak poprzednich = brak zarzutu",
        gates.powtorzona_forma(ARTYKUL, []) == "")
# KONTRDOWOD: tekst o INNYM ksztalcie nie moze byc zgloszony, inaczej bramka
# krzyczalaby zawsze i nikt by jej nie sluchal.
inny = ("Nine percent of all plastic ever made has been recycled.\n\n"
        + "Short line. " * 40)
sprawdz("inny kształt nie jest zgłaszany",
        gates.powtorzona_forma(inny, [ARTYKUL]) == "",
        gates.powtorzona_forma(inny, [ARTYKUL]))

print()
print("=== 7. WSZYSTKO RAZEM ===")
# Do porownania formy podajemy BLIZNIAKA, nie ten sam tekst — inaczej
# bramka slusznie milczy i sekcja niczego by nie sprawdzila.
def zapalone(tekst):
    # PODMIENIANE SLOWA MUSZA W TEKSCIE BYC — patrz komentarz przy BLIZNIAK.
    blizniak = tekst.replace("stamp", "seal").replace("grade", "class")
    assert blizniak != tekst, "blizniak identyczny — bramka formy nie ma czego porownac"
    uwagi = gates.deterministic_floors(tekst, KARTA, poprzednie=[blizniak])
    return uwagi, {u["gate"] for u in uwagi}


uwagi, nazwy = zapalone(ARTYKUL)
print("    na wycinkach: %s" % sorted(nazwy))
# Piec z szesciu podlog stoi na TRESCI i zapala sie na wycinkach — wszedzie
# tak samo. Szosta (NIEWIADOME_NA_KONCU) pyta o polozenie i potrzebuje
# pelnego tekstu, wiec jest nizej.
for g in ("BUDZET_ZASTRZEZEN", "OBWIESZCZONA_POWSCIAGLIWOSC", "ZAKAZANE_OTWARCIE",
          "STATYSTYKA_BEZ_ZRODLA", "ODCISK_FORMY"):
    sprawdz("%-28s zapala się na wycinkach 0025" % g, g in nazwy)

if PELNY_0025:
    uwagi_pelne, nazwy_pelne = zapalone(PELNY_0025)
    print("    na pełnym 0025: %s" % sorted(nazwy_pelne))
    # TU JEST OBIETNICA Z DOCSTRINGU: kazda podloga MUSI sie zapalic na 0025.
    for g in ("BUDZET_ZASTRZEZEN", "OBWIESZCZONA_POWSCIAGLIWOSC",
              "ZAKAZANE_OTWARCIE", "STATYSTYKA_BEZ_ZRODLA",
              "NIEWIADOME_NA_KONCU", "ODCISK_FORMY"):
        sprawdz("%-28s zapala się na pełnym 0025" % g, g in nazwy_pelne)
else:
    print("    POMINIETE — brak pełnego 0025 (sekcja 0 już to zgłosiła)")

print()
print("=== 8. NIC NIE BLOKUJE ARTYKULU ===")
# Decyzja wlasciciela z 15 sierpnia stoi: research jest oplacony, wiec tekst
# powstaje ZAWSZE, a uwagi wracaja do przeczytania.
status, powod = gates.verdict(uwagi)
sprawdz("werdykt nadal SAVED", status == "SAVED", status)
sprawdz("bez powodu blokady", powod is None, powod)

print()
print("=== 9. STARE PODLOGI NIETKNIETE ===")
sprawdz("zmyślone przeżycie nadal łapane",
        any(u["gate"] == "ZMYSLONE_PRZEZYCIE" for u in gates.deterministic_floors(
            "Last week, I stood in the aisle and counted.", KARTA)))
sprawdz("nieistniejące badanie nadal łapane",
        any(u["gate"] == "NIEISTNIEJACE_BADANIE" for u in gates.deterministic_floors(
            "According to a recent study, this is common.", KARTA)))
sprawdz("stare wywołanie bez `poprzednie` nadal działa",
        isinstance(gates.deterministic_floors(ARTYKUL, KARTA), list))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
