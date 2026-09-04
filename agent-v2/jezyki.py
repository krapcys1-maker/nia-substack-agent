# -*- coding: utf-8 -*-
"""Wzorce bramek ZALEZNE OD JEZYKA — i glosny sprzeciw, gdy jezyka nie ma.

## Po co to istnieje

`config.ARTICLE_LANGUAGE` byl polem konfiguracji, ale wybor innego jezyka niz
angielski dawal bota, ktory pisze po nowemu, a **bramki cicho przestaja
cokolwiek lapac**. Siedem wzorcow w `gates.py` to angielskie wyrazenia
regularne: `ZAKAZANE_OTWARCIA` szuka „turn over", `ZASTRZEZENIE` szuka
„I think", `NIBY_ZRODLO` szuka „in one survey". Po polsku zwracaja pustke.

To jest najgrozniejsza awaria w calym systemie, bo **nie wyglada na awarie**.
Wszystko swieci na zielono: bramka nie zglasza naruszen, bo nie ma czym ich
znalezc. Kazdy inny blad w tym projekcie krzyczy; ten milczy.

## Co ten modul robi

Trzyma wzorce **osobno dla kazdego jezyka** i przy jezyku, ktorego nie zna,
**MOWI O TYM GLOSNO** zamiast oddac puste dopasowanie. Bramka bez wzorcow jest
wtedy jawnie wylaczona i widac to w logu przy kazdym przebiegu — a nie odkrywa
sie po miesiacu, ze nic nigdy nie zostalo zgloszone.

## Jak dolozyc jezyk

Dopisz wpis do `WZORCE` z tymi samymi kluczami co `"English"`. Kazdy wzorzec
ma opis, CO lapie — bo tlumaczenie wyrazenia regularnego bez wiedzy, po co ono
jest, daje wzorzec skladniowo poprawny i merytorycznie pusty.

Wzorce sa **zakazujace, nie nakazujace**: mowia, czego w tekscie ma nie byc.
Regula nakazujaca pozycje po dziesieciu tekstach sama staje sie podpisem
maszyny — to ustalenie z `DOKTRYNA.md` i obowiazuje w kazdym jezyku.
"""
from __future__ import annotations

import re

# Kazdy klucz to jedna bramka. Wartosc: (wzorzec, co lapie).
WZORCE: dict[str, dict[str, tuple[str, str]]] = {
    "English": {
        # WZORZEC PRZENIESIONY CO DO ZNAKU ze starego `gates.py`, wyciety
        # z gita, a NIE przepisany. Pierwsza proba byla moja wlasna,
        # "rownowazna" wersja i oblala `test_podlogi_z_pamieci`: nie lapala
        # ani "my wife", ani "last week, I". Kazda alternatywa w tym
        # wzorcu jest odpowiedzia na konkretny tekst, ktory kiedys przeszedl.
        "ZMYSLONE_PRZEZYCIE": (
            r"\bI\s+(stood|visited|watched|saw|went|drove|walked|bought|ate|drank|held|"
            r"spoke\s+to|asked|met|noticed|remember|counted|tried|tasted)\b"
            r"|\blast\s+(week|month|year|night),?\s+I\b"
            r"|\bwhen\s+I\s+was\b"
            r"|\bmy\s+(wife|husband|son|daughter|father|mother|friend|neighbou?r|colleague)\b",
            "czasowniki doswiadczenia w pierwszej osobie — konto nie ma przezyc",
        ),
        # TAKZE WYCIETY Z GITA. "In a shelf-life study at 8 stopni" jest
        # w porzadku — niesie szczegol z karty dowodowej. "According to a
        # recent study" nie jest. Moja przepisana wersja lapala oba.
        "NIEISTNIEJACE_BADANIE": (
            r"\baccording\s+to\s+(a|one)\s+(recent|new|major|landmark)?\s*(study|report|survey|paper)\b"
            r"|\bstudies\s+have\s+shown\b"
            r"|\bresearch\s+has\s+shown\b"
            r"|\bscientists\s+(have\s+)?(found|discovered)\b"
            r"|\bexperts\s+(say|agree|believe)\b",
            "powolanie na badanie bez nazwania go",
        ),
        "ZASTRZEZENIE": (
            r"\bmy\s+(reading|suspicion|guess|sense|hunch)\b"
            r"|\bI\s+(think|suspect|would\s+guess|imagine)\b"
            r"|\bin\s+my\s+view\b"
            r"|\bit\s+seems\s+to\s+me\b"
            r"|\bis\s+a\s+separate\s+question\b",
            "zastrzezenia w pierwszej osobie; szesc w jednym tekscie to tik",
        ),
        "POWSCIAGLIWOSC": (
            r"\bI\s+(will\s+not|won'?t|refuse\s+to|am\s+not\s+going\s+to)\s+"
            r"(invent|speculate|guess|make\s+up|assume)\b"
            r"|\bI\s+will\s+not\s+invent\s+it\b",
            "obwieszczona powsciagliwosc — luke nazywa sie wprost, bez zapowiedzi cnoty",
        ),
        "ZAKAZANE_OTWARCIA": (
            r"^\s*(turn\s+over|look\s+at|take\s+a\s+look|next\s+time\s+you|"
            r"ask\s+most\s+people|most\s+people\s+(think|believe|assume)|"
            r"we\s+all\s+know|pick\s+up|imagine\s+you|consider\s+the|"
            r"have\s+you\s+ever|if\s+you\s+(look|turn|check))\b",
            "otwarcia kazace czytelnikowi isc cos obejrzec zamiast go zatrzymac",
        ),
        "NIBY_ZRODLO": (
            r"\bin\s+one\s+(survey|study|poll|report)\b"
            r"|\bsome\s+estimates?\b"
            r"|\breportedly\b"
            r"|\bby\s+some\s+(counts?|estimates?)\b"
            r"|\bit\s+is\s+(said|estimated|reported)\b"
            r"|\bsurveys?\s+(suggest|show|find)\b",
            "zrodlo, ktore nie jest zrodlem — lapane TYLKO w zdaniu z liczba",
        ),
        # NIE JEST BRAMKA — jest CECHA KSZTALTU. `gates.odcisk_formy` pyta,
        # w ktorej cwiartce tekstu pada pierwszy zwrot do czytelnika, i porownuje
        # to miedzy artykulami. Wzorzec stal wpisany po angielsku w `gates.py`,
        # wiec przy innym jezyku cecha przyjmowala „brak" ZAWSZE — a cecha stala
        # zgadza sie zawsze i obniza faktyczny prog `powtorzona_forma`
        # z pieciu cech na cztery, czyli do poziomu, ktory ta funkcja sama
        # nazywa przypadkiem.
        "ZWROT_DO_CZYTELNIKA": (
            r"\byou(r|rs|rself)?\b",
            "zwrot do czytelnika w drugiej osobie — do POZYCJI w tekscie, "
            "nie do oceny",
        ),
    },

    # ------------------------------------------------------------------
    # POLSKI. Dopisany, bo `temat.jezyk = "Polish"` dawal bota, ktory pisze
    # po polsku przy OSMIU wylaczonych bramkach — czyli dokladnie te awarie,
    # ktora ten modul mial uczynic glosna. Glosna byla; naprawiona nie.
    #
    # NIE SA TO TLUMACZENIA WZORCOW ANGIELSKICH. Polski opuszcza zaimek, wiec
    # pierwsza osoba siedzi w koncowce czasownika, a nie w slowie „I". Kuszace
    # `\w+lem` jest PULAPKA: tak konczy sie narzednik rzeczownikow („stolem",
    # „cialem", „dzialem", „zespolem", „kolem"), wiec zlapaloby zdania bez
    # zadnej pierwszej osoby. Dlatego czasowniki sa WYLICZONE, w obu rodzajach.
    # ------------------------------------------------------------------
    "Polish": {
        "ZMYSLONE_PRZEZYCIE": (
            r"\b(sta[lł]|widzia[lł]|ogl[aą]da[lł]|posz[lł]|pojecha[lł]|"
            r"jecha[lł]|chodzi[lł]|kupi[lł]|zjad[lł]|jad[lł]|pi[lł]|"
            r"trzyma[lł]|rozmawia[lł]|zapyta[lł]|spotka[lł]|zauwa[zż]y[lł]|"
            r"policzy[lł]|spr[oó]bowa[lł]|pr[oó]bowa[lł]|odwiedzi[lł]|"
            r"dotkn[aą][lł]|us[lł]ysza[lł]|poczu[lł])(em|am)\b"
            r"|\bposzed[lł]em\b"
            r"|\bpami[eę]tam,?\s+(jak|gdy|kiedy)\b"
            r"|\bkiedy\s+by[lł](em|am)\b"
            r"|\b(w\s+)?(zesz[lł]ym|ubieg[lł]ym)\s+(tygodniu|miesi[aą]cu|roku)"
            r"[^.!?]{0,40}\b\w+[lł](em|am)\b"
            r"|\b(m[oó]j|moja)\s+"
            r"(żona|zona|m[aą][zż]|syn|c[oó]rka|ojciec|matka|mama|tata|"
            r"przyjaci[oó][lł]|przyjaci[oó][lł]ka|s[aą]siad|s[aą]siadka|"
            r"kolega|kole[zż]anka)\b",
            "czasowniki doswiadczenia w pierwszej osobie — konto nie ma przezyc",
        ),
        "NIEISTNIEJACE_BADANIE": (
            r"\bwed[lł]ug\s+(bada[nń]|jednego\s+z\s+bada[nń]|raportu|sonda[zż]u)\b"
            r"|\bbadania\s+(pokazuj[aą]|dowodz[aą]|wykaza[lł]y|sugeruj[aą])\b"
            r"|\bjak\s+wykaza[lł]y\s+badania\b"
            r"|\bz\s+bada[nń]\s+wynika\b"
            r"|\bnaukowcy\s+(odkryli|ustalili|wykazali|dowiedli)\b"
            r"|\beksperci\s+(twierdz[aą]|uwa[zż]aj[aą]|zgadzaj[aą]\s+si[eę])\b",
            "powolanie na badanie bez nazwania go",
        ),
        "ZASTRZEZENIE": (
            r"\bmoim\s+zdaniem\b"
            r"|\bwydaje\s+mi\s+si[eę]\b"
            r"|\b(s[aą]dz[eę]|podejrzewam|przypuszczam|domy[sś]lam\s+si[eę])\b"
            r"|\bmam\s+wra[zż]enie\b"
            r"|\bmoje\s+(odczucie|przeczucie|wra[zż]enie)\b"
            r"|\bto\s+(ju[zż]\s+)?osobna\s+(kwestia|sprawa)\b",
            "zastrzezenia w pierwszej osobie; szesc w jednym tekscie to tik",
        ),
        "POWSCIAGLIWOSC": (
            r"\bnie\s+(b[eę]d[eę]|zamierzam|chc[eę])\s+"
            r"(zmy[sś]la[cć]|wymy[sś]la[cć]|spekulowa[cć]|zgadywa[cć]|"
            r"zak[lł]ada[cć]|domy[sś]la[cć]\s+si[eę])\b"
            r"|\bnie\s+wymy[sś]l[eę]\s+tego\b",
            "obwieszczona powsciagliwosc — luke nazywa sie wprost, bez zapowiedzi cnoty",
        ),
        "ZAKAZANE_OTWARCIA": (
            r"^\s*(odwr[oó][cć]|sp[oó]jrz|przyjrzyj\s+si[eę]|"
            r"we[zź]\s+do\s+r[eę]ki|nast[eę]pnym\s+razem|"
            r"zapytaj\s+(wi[eę]kszo[sś][cć]|kogokolwiek)|"
            r"wi[eę]kszo[sś][cć]\s+(ludzi|z\s+nas)\s+"
            r"(my[sś]li|s[aą]dzi|zak[lł]ada|uwa[zż]a)|"
            r"wszyscy\s+wiemy|wyobra[zź]\s+sobie|"
            r"czy\s+kiedykolwiek|je[sś]li\s+(spojrzysz|odwr[oó]cisz|sprawdzisz))\b",
            "otwarcia kazace czytelnikowi isc cos obejrzec zamiast go zatrzymac",
        ),
        "NIBY_ZRODLO": (
            r"\bw\s+jednym\s+z\s+(bada[nń]|sonda[zż]y|raport[oó]w)\b"
            r"|\bwed[lł]ug\s+(niekt[oó]rych\s+)?szacunk[oó]w\b"
            r"|\b(podobno|rzekomo)\b"
            r"|\b(szacuje|m[oó]wi|uwa[zż]a)\s+si[eę]\b"
            r"|\bsonda[zż]e\s+(pokazuj[aą]|sugeruj[aą]|wskazuj[aą])\b",
            "zrodlo, ktore nie jest zrodlem — lapane TYLKO w zdaniu z liczba",
        ),
        # Polszczyzna nie ma jednego slowa „you". Zwrot do czytelnika idzie
        # przez zaimki i przez CZASOWNIK w drugiej osobie, wiec wzorzec jest
        # szerszy — a to nie szkodzi, bo cecha mierzy POZYCJE pierwszego
        # trafienia, a nie ich liczbe.
        "ZWROT_DO_CZYTELNIKA": (
            r"\b(ty|ciebie|tobie|cie|twoj\w*|wasz\w*|wy|was|wam)\b"
            r"|\b\w+(asz|esz|isz|ysz)\b",
            "zwrot do czytelnika w drugiej osobie — do POZYCJI w tekscie, "
            "nie do oceny",
        ),
    },
}

# Listy fraz, nie wyrazenia regularne. Ta sama zasada.
FRAZY: dict[str, dict[str, tuple[str, ...]]] = {
    "English": {
        "SYGNAL_NIEWIADOMEJ": (
            "is unknown", "cannot say", "does not establish", "do not establish",
            "only partly", "in outline", "is not clear", "leaves open",
            "leave open", "not settled", "cannot answer", "is a separate question",
        ),
        "META_GRANIC": (
            "record", "evidence", "documents", "sources", "the text",
            "worth stating", "leaves open", "leave open", "does not settle",
            "do not settle", "say once", "saying once", "hedge throughout",
            "plainly", "deserves saying",
        ),
    },
    "Polish": {
        "SYGNAL_NIEWIADOMEJ": (
            "nie wiadomo", "nie sposób powiedzieć", "nie sposob powiedziec",
            "nie ustala", "nie ustalają", "nie ustalaja", "tylko częściowo",
            "tylko czesciowo", "w zarysie", "nie jest jasne",
            "pozostawia otwarte", "pozostawiają otwarte", "nie rozstrzyga",
            "nie odpowiada na", "to osobna kwestia", "to osobna sprawa",
        ),
        # PIERWSZE SLOWO AKAPITU O OGRANICZENIACH. Regula jest strukturalna:
        # akapit ma zaczynac sie od SAMEGO ograniczenia, a nie od zdania
        # o tym, ze zaraz bedzie akapit o ograniczeniach.
        "META_GRANIC": (
            "zapis", "dowody", "dokumenty", "źródła", "zrodla", "tekst",
            "materiał", "material", "warto zaznaczyć", "warto zaznaczyc",
            "warto powiedzieć", "warto powiedziec", "pozostawia otwarte",
            "nie rozstrzyga", "nie rozstrzygają", "nie rozstrzygaja",
            "powiedzieć raz", "powiedziec raz", "zasługuje na",
            "zasluguje na", "trzeba zaznaczyć", "trzeba zaznaczyc",
        ),
    },
}

# Wzorzec, ktory nie dopasuje sie NIGDY. Uzywany, gdy jezyka nie znamy —
# zamiast wzorca angielskiego, ktory w innym jezyku dopasuje sie przypadkiem
# albo wcale, i w obu razach klamie.
NIGDY = r"(?!x)x"

_ostrzezono: set[str] = set()


def _ostrzez(jezyk: str, czego_brak: str) -> None:
    """Raz na proces, ale GLOSNO. Cicha bramka jest gorsza od jej braku."""
    klucz = "%s/%s" % (jezyk, czego_brak)
    if klucz in _ostrzezono:
        return
    _ostrzezono.add(klucz)
    print("  [bramki] JEZYK %r NIE MA WZORCOW dla %s — TA BRAMKA JEST WYLACZONA."
          "\n           Nie zglosi niczego, i to nie znaczy, ze tekst jest czysty."
          "\n           Dopisz wzorce w agent-v2/jezyki.py albo wroc na English."
          % (jezyk, czego_brak), flush=True)


def wzorzec(nazwa: str, jezyk: str) -> re.Pattern[str]:
    """Skompilowany wzorzec bramki dla tego jezyka. Brak = jawnie wylaczona."""
    dla_jezyka = WZORCE.get(jezyk)
    if dla_jezyka is None or nazwa not in dla_jezyka:
        _ostrzez(jezyk, nazwa)
        return re.compile(NIGDY)
    return re.compile(dla_jezyka[nazwa][0], re.IGNORECASE | re.MULTILINE)


def frazy(nazwa: str, jezyk: str) -> tuple[str, ...]:
    """Lista fraz dla tego jezyka. Brak = pusta lista i glosne ostrzezenie."""
    dla_jezyka = FRAZY.get(jezyk)
    if dla_jezyka is None or nazwa not in dla_jezyka:
        _ostrzez(jezyk, nazwa)
        return ()
    return dla_jezyka[nazwa]


def znane_jezyki() -> tuple[str, ...]:
    return tuple(sorted(set(WZORCE) | set(FRAZY)))


def brakujace(jezyk: str) -> list[str]:
    """Czego brakuje temu jezykowi wobec angielskiego. Pusta lista = komplet."""
    brak = []
    for zbior, dla in (("wzorzec", WZORCE), ("frazy", FRAZY)):
        wzorcowe = set(dla.get("English", {}))
        mamy = set(dla.get(jezyk, {}))
        brak += ["%s:%s" % (zbior, n) for n in sorted(wzorcowe - mamy)]
    return brak
