# -*- coding: utf-8 -*-
"""Narzedzia glosu: odcisk, slepa proba, stale wejscia — bez sieci i bez modelu.

## Po co ten plik istnieje

Wlasciciel raz policzyl recznie, czym przyjety artykul rozni sie od dwoch
odrzuconych, i ta tabela byla najkonkretniejsza rzecza zapisana o glosie NIA.
`narzedzia/odcisk_glosu.py` liczy to samo na kazdym tekscie. Ten test pilnuje
trzech rzeczy:

1. MIARY LICZA TO, CO OBIECUJA — po zdaniach, nie po trafieniach; zwrot
   „documentation says" to jedna atrybucja, nie dwie; „apparently" nie jest
   asekuracja; lista zrodel pod artykulem nie liczy sie jako linki w tresci.
2. WZORZEC CZYTA SIE Z PLIKOW, a pytania czytelnika, wiersze `Source:` i
   podpisy linkow nie wchodza do pomiaru. Wzorzec jest tu SYNTETYCZNY:
   test silnika nie czyta kartridza (osobne galezie, osobne PR-y).
3. PASMO ODROZNIA GLOS OD RAPORTU: tekst z linkami w tresci, „according to"
   w co drugim zdaniu i trzema przypomnieniami o byciu AI laduje POZA pasmem
   na miarach raportu, a tekst w rejestrze wzorca laduje w pasmie.

Do tego slepa proba (dokladnie jeden kandydat w zestawie, klucz osobno,
ocena odpowiedzi) i stale wejscia proby glosu (szesc, kazde z zrodlem, bez
platnego wywolania bez `--live`).

Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_glos_narzedzia.py
"""
import json
import os
import pathlib
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, "narzedzia")
import odcisk_glosu as og     # noqa: E402
import slepa_proba_glosu as sp  # noqa: E402
import proba_glosu as pg      # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


NIA_1 = """You install a thing that promises to help. Then you find out the help has a switch.

Sweetheart. Check the switch.

The vendor's own page says it ships off. Fine. I'd like that sentence where the fingers are, not on page nine.

Sit with that for a second. The diligent person and the lazy one get the same result. We've automated the punishment for reading.

They wanted a helper. Not a fucking scavenger hunt."""

NIA_2 = """Your mum has competition. A weather model now updates the forecast every hour from live satellite pictures.

An absurd amount of hardware dedicated, in part, to the sentence "take a jacket."

I approve. Some of you need a satellite network before you'll listen to a woman."""

NIA_3 = """They actually asked the people who'll use the thing. I swear, some product teams treat that like asking the furniture for its opinion.

Making an everyday conversation easier matters. I can get behind that.

More of this. You're considerably more attractive when you're useful."""

RAPORT = """According to the vendor's documentation (https://example.org/docs), the sandbox feature is disabled by default, which is arguably worth noting.

As an AI language model, I should note that it seems the configuration may or may not apply to every deployment. According to the advisory (https://example.org/advisory), the baseline runtime permits execution without approval, and it remains to be seen whether the framework mitigates this.

As an AI, I cannot verify the claims made in the advisory; according to the maintainers, version 0.6.0 said the defaults were changed, which is perhaps sensible and useful. As an AI system I would add that it is worth noting that the broader ecosystem has, according to analysts, somewhat improved.

According to the README, the interpreter allowlist was reported to be revised. It is possible that this is a useful, interesting development."""


def wzorzec_tymczasowy(katalog):
    k = pathlib.Path(katalog)
    (k / "notki.md").write_text(
        "forma: notka\n\nSyntetyczne notki.\n\n## Jeden\n\n%s\n\nSource: test\n\n## Dwa\n\n%s\n\nSource: test\n\n## Trzy\n\n%s\n"
        % (NIA_1, NIA_2, NIA_3), encoding="utf-8")
    (k / "rozmowa.md").write_text(
        "forma: rozmowa\n\n## Pytanie\n\nReader: Will you guarantee my loan?\n\n"
        "I can't guarantee your loan. We've known each other for five minutes and you're already "
        "trying to leave me with the instalments.\n[a label]\n\nWhich car have you got your eye on?\n",
        encoding="utf-8")
    (k / "artykul.md").write_text(
        "forma: artykul\n\n## Tytul\n\n# Tytul\n\n*Podtytul.*\n\n%s\n\n%s\n\nFigures checked against sources to 2026-01-01.\n\n---\n\n## Sources\n\n- [a](https://example.org/a)\n- [b](https://example.org/b)\n"
        % (NIA_1, NIA_3), encoding="utf-8")
    (k / "README.md").write_text("# nie probka\n\n## To nie jest probka\n\nforma: notka\n", encoding="utf-8")
    return k


print("=== 1. MIARY LICZA TO, CO OBIECUJA ===")
o = og.odcisk("OpenClaw's own documentation says its sandboxing is off by default. Its advisory describes "
              "the program starting unlocked. The docs say this openly. Apparently we needed that.", "artykul")
sprawdz("atrybucje po zdaniach: `documentation says` to jedna, `advisory describes` druga",
        o["atrybucje"] == 2, o["atrybucje"])
sprawdz("`apparently` nie jest asekuracja", o["asekuracje"] == 0, o["_zdania"]["asekuracje"])
o = og.odcisk("It seems the model may well be right, arguably. Perhaps not.", "notka")
sprawdz("asekuracje po zdaniach: dwa zdania, nie cztery trafienia", o["asekuracje"] == 2, o["asekuracje"])
o = og.odcisk("I'm an AI woman with a mouth on me. As an AI I cannot verify it. The vendor is a company.", "artykul")
sprawdz("zdania o byciu AI: pierwsza osoba plus slowo o maszynie", o["zdania_o_ai"] == 2, o["_zdania"]["zdania_o_ai"])
o = og.odcisk("Check the switches. You may want to move the cake. The cake is fine.", "notka")
sprawdz("zwrot do czytelnika: rozkaz i `you`, nie trzecie zdanie", o["do_czytelnika"] == 2, o["do_czytelnika"])
sprawdz("koniec wycelowany: `The cake is fine.` nie jest zwrotem", o["koniec_wycelowany"] is False)
o = og.odcisk("Their host execution defaults permit commands. The pipeline is the framework.", "artykul")
sprawdz("zargon z listy: execution, framework, pipeline", set(o["zargon_slowa"]) == {"execution", "framework", "pipeline"},
        o["zargon_slowa"])
sprawdz("zargon liczony po zdaniach", o["zargon"] == 2, o["zargon"])
o = og.odcisk("That's not a plan. That's a hope. That's not safety. That's paperwork.", "notka")
sprawdz("ta sama konstrukcja `That's not X. That's Y.` policzona dwa razy", o["ta_sama_konstrukcja"] == 2,
        o["ta_sama_konstrukcja"])
sprawdz("odcisk jest deterministyczny", og._bez_zdan(og.odcisk(NIA_1)) == og._bez_zdan(og.odcisk(NIA_1)))
sprawdz("pusty tekst nie dzieli przez zero", og.odcisk("")["slowa"] == 0)

print()
print("=== 2. ARTYKUL: TYTUL, PODTYTUL, STOPKA I ZRODLA ODPADAJA ===")
tytul, podtytul, tresc = og.cialo_artykulu(
    "# A title\n\n*A subtitle.*\n\nBody with no link.\n\nFigures checked against sources to 2026-01-01.\n\n---\n\n## Sources\n\n- [x](https://example.org/x)\n")
sprawdz("tytul i podtytul rozpoznane", tytul == "A title" and podtytul == "A subtitle.", (tytul, podtytul))
sprawdz("tresc bez stopki i bez listy zrodel", tresc == "Body with no link.", repr(tresc))
sprawdz("link z listy zrodel nie liczy sie jako link w tresci", og.odcisk(tresc, "artykul")["linki"] == 0)

print()
print("=== 3. WZORZEC Z PLIKOW ===")
with tempfile.TemporaryDirectory() as tmp:
    k = wzorzec_tymczasowy(tmp)
    probki = og.wczytaj_wzorzec(k)
    formy = sorted(p["forma"] for p in probki)
    sprawdz("piec probek: trzy notki, jedna rozmowa, jeden artykul",
            formy == ["artykul", "notka", "notka", "notka", "rozmowa"], formy)
    sprawdz("README nie jest probka", all(p["plik"] != "README.md" for p in probki))
    rozmowa = next(p for p in probki if p["forma"] == "rozmowa")
    sprawdz("pytanie czytelnika i podpis linku nie wchodza do tekstu",
            "guarantee my loan?" not in rozmowa["tekst"] and "[a label]" not in rozmowa["tekst"]
            and "Which car" in rozmowa["tekst"], rozmowa["tekst"][:80])
    artykul = next(p for p in probki if p["forma"] == "artykul")
    sprawdz("artykul we wzorcu bez tytulu, stopki i zrodel",
            "# Tytul" not in artykul["tekst"] and "example.org" not in artykul["tekst"]
            and "Figures checked" not in artykul["tekst"], artykul["tekst"][:80])
    pas = og.pasma(probki)
    sprawdz("pasma dla kazdej formy", set(pas) == {"notka", "rozmowa", "artykul"}, sorted(pas))
    sprawdz("pasmo to (min, max) po probkach", all(pas["notka"][m][0] <= pas["notka"][m][1] for m in og.MIARY_PASMA))
    sprawdz("liczniki raportu we wzorcu notek: zero plus jeden zapasu",
            pas["notka"]["linki"] == (0, 1) and pas["notka"]["asekuracje"] == (0, 1)
            and pas["notka"]["zdania_o_ai"] == (0, 1), {m: pas["notka"][m] for m in og.MIARY_RAPORTU})
    sprawdz("miara ciagla ma zapas po obu stronach",
            pas["notka"]["slow_na_zdanie"][0] < min(og.odcisk(t, "notka")["slow_na_zdanie"] for t in (NIA_1, NIA_2, NIA_3))
            and pas["notka"]["slow_na_zdanie"][1] > max(og.odcisk(t, "notka")["slow_na_zdanie"] for t in (NIA_1, NIA_2, NIA_3)),
            pas["notka"]["slow_na_zdanie"])

    print()
    print("=== 4. PASMO ODROZNIA GLOS OD RAPORTU ===")
    raport = og.odcisk(RAPORT, "notka")
    oceny = og.ocen(raport, pas["notka"])
    poza = [m for m in og.MIARY_RAPORTU if oceny[m] == "powyzej"]
    sprawdz("raport lezy POWYZEJ pasma na co najmniej pieciu miarach raportu", len(poza) >= 5, oceny)
    sprawdz("w tym: linki, atrybucje, zdania o AI, asekuracje",
            {"linki", "atrybucje_na_100", "zdania_o_ai", "asekuracje"} <= set(poza), poza)
    swoj = og.odcisk("I tell you I'm AI once. Imagine needing forensics to get that out of a grown man.\n\n"
                     "Beautiful. Now the bullshit comes with a receipt.", "notka")
    oceny2 = og.ocen(swoj, pas["notka"])
    sprawdz("notka w rejestrze wzorca nie wychodzi ponad pasmo na zadnej mierze raportu",
            all(oceny2[m] != "powyzej" for m in og.MIARY_RAPORTU), oceny2)
    # Kontrdowod na sam test: pasmo nie jest tak szerokie, ze wszystko w nim siedzi.
    sprawdz("pasmo nie polyka wszystkiego", any(s != "w pasmie" for s in oceny.values()))

    print()
    print("=== 5. SLEPA PROBA: JEDEN KANDYDAT W ZESTAWIE, KLUCZ OSOBNO ===")
    kandydaci = [{"nazwa": "nowa-1", "tekst": RAPORT}, {"nazwa": "nowa-2", "tekst": NIA_2 + " Extra."}]
    zest = sp.zestawy(probki, kandydaci, "notka", random.Random(7))
    sprawdz("po jednym zestawie na kandydata", len(zest) == 2, len(zest))
    sprawdz("kazdy zestaw ma trzy teksty i dokladnie jeden nie z wzorca",
            all(len(z["teksty"]) == 3 and sum(1 for t in z["teksty"] if not t["wzorzec"]) == 1 for z in zest))
    sprawdz("litera kandydata zgadza sie z jego miejscem",
            all(z["teksty"][sp.LITERY.index(z["kandydat"])]["wzorzec"] is False for z in zest))
    sprawdz("losowanie z ziarnem jest powtarzalne",
            [z["kandydat"] for z in sp.zestawy(probki, kandydaci, "notka", random.Random(7))]
            == [z["kandydat"] for z in zest])
    ark = sp.arkusz(zest)
    sprawdz("arkusz nie zdradza kandydata ani nazw",
            "nowa-1" not in ark and "wzorzec" not in ark.lower() and "kandydat" not in ark.lower(), ark[:120])
    klucz = {"zestawy": [{k: v for k, v in z.items() if k != "teksty"} for z in zest]}
    odp = {zest[0]["zestaw"]: zest[0]["kandydat"], zest[1]["zestaw"]: "A" if zest[1]["kandydat"] != "A" else "B"}
    wyniki = sp.ocen_odpowiedzi(klucz, odp)
    sprawdz("ocena: pierwszy rozpoznany, drugi nie",
            wyniki[0]["rozpoznany"] is True and wyniki[1]["rozpoznany"] is False, wyniki)
    try:
        sp._parsuj_odpowiedzi(["1=Z"])
        sprawdz("zla litera odpowiedzi jest bledem", False)
    except ValueError:
        sprawdz("zla litera odpowiedzi jest bledem", True)

    print()
    print("=== 6. NARZEDZIE Z LINII POLECEN NA TYM WZORCU ===")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    plik = pathlib.Path(tmp) / "kandydat-notka.txt"
    plik.write_text(RAPORT, encoding="utf-8")
    wynik = subprocess.run([sys.executable, "narzedzia/odcisk_glosu.py", "--wzorzec", str(k), "--json", str(plik)],
                           capture_output=True, text=True, env=env, encoding="utf-8")
    sprawdz("odcisk_glosu.py konczy sie zerem", wynik.returncode == 0, wynik.stderr[-300:])
    try:
        rekord = json.loads(wynik.stdout.strip().splitlines()[-1])
        sprawdz("JSON ma odcisk i ocene wobec pasma notek",
                rekord["odcisk"]["linki"] == 2 and rekord["ocena"]["linki"] == "powyzej", rekord.get("ocena"))
    except (ValueError, KeyError, IndexError) as exc:
        sprawdz("JSON ma odcisk i ocene wobec pasma notek", False, "%s: %s" % (exc, wynik.stdout[-200:]))
    wynik = subprocess.run([sys.executable, "narzedzia/odcisk_glosu.py", "--wzorzec", str(k), "--wzorzec-pokaz"],
                           capture_output=True, text=True, env=env, encoding="utf-8")
    sprawdz("--wzorzec-pokaz wypisuje pasma", wynik.returncode == 0 and "pasmo notka" in wynik.stdout, wynik.stdout[-200:])

print()
print("=== 7. STALE WEJSCIA PROBY GLOSU ===")
sprawdz("szesc wejsc", len(pg.WEJSCIA) == 6 and "o_sobie" in pg.WEJSCIA, sorted(pg.WEJSCIA))
sprawdz("kazde wejscie z faktem ma zrodlo i date",
        all((w["url"].startswith("https://") and len(w["source_date"]) == 10) for n, w in pg.WEJSCIA.items() if w["fact"]))
sprawdz("wejscia sa rozne", len({w["fact"] for w in pg.WEJSCIA.values()}) == 6)


class _Cfg:
    PERSONA_TEMATY = ["JA: say what she wants instead, small and specific.", "INNE: whatever"]


class _Pers:
    @staticmethod
    def _rozdziel_rubryke(t):
        etykieta, _, reszta = t.partition(":")
        return etykieta.strip(), reszta.strip()


m = pg.material_wejscia("gniew", _Cfg, _Pers)
sprawdz("material faktu ma ksztalt jak w personality.notes",
        set(m) == {"theme", "statistics", "world", "choice", "fact"} and m["fact"]["url"].startswith("https://"), sorted(m))
m = pg.material_wejscia("o_sobie", _Cfg, _Pers)
sprawdz("wejscie o sobie bierze rubryke JA z kartridza, bez faktu",
        "fact" not in m and m["theme"].startswith("say what she wants"), m)
env = dict(os.environ, PYTHONIOENCODING="utf-8")
wynik = subprocess.run([sys.executable, "narzedzia/proba_glosu.py", "--wejscie", "gniew"],
                       capture_output=True, text=True, env=env, encoding="utf-8")
sprawdz("bez --live nie ma platnego wywolania (kod 2, komunikat)",
        wynik.returncode == 2 and "--live" in wynik.stderr, wynik.stderr[-200:])
wynik = subprocess.run([sys.executable, "narzedzia/proba_glosu.py", "--lista-wejsc"],
                       capture_output=True, text=True, env=env, encoding="utf-8")
sprawdz("--lista-wejsc wypisuje szesc wejsc i konczy sie zerem",
        wynik.returncode == 0 and all(n in wynik.stdout for n in pg.WEJSCIA), wynik.stdout[-200:])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
