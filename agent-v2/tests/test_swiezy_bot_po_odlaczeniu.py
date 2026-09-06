# -*- coding: utf-8 -*-
"""Po odlaczeniu presetu bot jest swiezy: stary proces nie placi i nie publikuje, B nie widzi A.

## Po co ten plik istnieje

Zewnetrzny audyt z 6 wrzesnia 2026 („Odlaczanie presetu, czystosc bota i osobne
klony") wykonal 19 prob na commicie adcac83 i wskazal, ze samo `odlacz` nie
daje „calkowicie czystego bota". Kazda sekcja ponizej odtwarza jedna z tych
prob i ma przechodzic DOPIERO po naprawie:

  P02/P17  odlaczenie usuwalo wskaznik, ale brama pytala tylko obiekt w pamieci
  P03/P19  AGENT_V2_PRESET omijal znaczenie „odlaczono"
  P04      B na instancji A czytal bank A i oczekujacy artykul A
  P06/P07  zmiana profilu albo korpusu nie zmieniala odcisku
  P09      kopia identycznego katalogu zmieniala odcisk
  P10      pusty korpus B pobieral stary domyslny korpus silnika
  P18      bez aktywacji wracal temat ze starego konfiguracja.toml

Kazda sekcja ma KONTRDOWOD: pokazuje, ze asercja umie oblac.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_swiezy_bot_po_odlaczeniu.py
"""
import json
import pathlib
import shutil
import sys
import tempfile
import types

sys.path.insert(0, "agent-v2/tests")
import wlasna_konfiguracja  # noqa: E402

wlasna_konfiguracja.pomin_gdy_bez_tomllib("czy po odlaczeniu bot jest swiezy")

sys.path.insert(0, "agent-v2")
import config          # noqa: E402
import konfiguracja    # noqa: E402
import preset          # noqa: E402
import llm             # noqa: E402
import browser         # noqa: E402
import style           # noqa: E402

BAZA = config.DOMYSLNE_SILNIKA
zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def oblewa(fabryka):
    try:
        fabryka()
        return None
    except (preset.BladPresetu, preset.BrakPresetu, konfiguracja.BledKonfiguracji,
            llm.PreflightFailed) as exc:
        return str(exc)


TOML = '''
[preset]
nazwa = "%(nazwa)s"
schema = 1

[konto]
uchwyt = "%(uchwyt)s"
nazwa_marki = "Marka %(nazwa)s"

[temat]
nisza = "nisza %(nazwa)s"
kat_redakcyjny = "what the record says."
jezyk = "English"
znaki_niszy = ["probn", "test"]
hasla_szukania = ["probna a", "probna b", "probna c", "probna d", "probna e",
    "probna f", "probna g", "probna h", "probna i", "probna j", "probna k",
    "probna l", "probna m", "probna n", "probna o", "test p"]
dziedziny = ["d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8"]

[styl]
profil_pozytywny = "styl/profil_pozytywny.md"
profil_negatywny = "styl/profil_negatywny.md"
korpus = "%(korpus)s"
wymagaj_korpusu = false
'''


def kartridz(korzen: pathlib.Path, nazwa: str, uchwyt: str = "konto-x", korpus: str = "") -> pathlib.Path:
    kat = korzen / "presety" / nazwa
    (kat / "styl").mkdir(parents=True, exist_ok=True)
    (kat / "prompty").mkdir(exist_ok=True)
    (kat / "preset.toml").write_text(TOML % {"nazwa": nazwa, "uchwyt": uchwyt, "korpus": korpus},
                                     encoding="utf-8")
    (kat / "styl" / "profil_pozytywny.md").write_text("# Profil %s\n\nGlos %s.\n" % (nazwa, nazwa),
                                                       encoding="utf-8")
    (kat / "styl" / "profil_negatywny.md").write_text("# Zakazy %s\n" % nazwa, encoding="utf-8")
    (kat / "prompty" / "okladka.md").write_text("n.\n---\nBlok okladki %s.\n" % nazwa, encoding="utf-8")
    return kat


def cfg_procesu(akt, agent: pathlib.Path):
    """Kontekst, jaki ma pracujacy proces: preset w pamieci, brama produkcyjna."""
    return types.SimpleNamespace(W_TESCIE=False, PRESET_AKTYWACJA=akt, AGENT_DIR=agent)


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    korzen = pathlib.Path(tmp)
    agent = korzen / "agent-v2"
    agent.mkdir()
    A = kartridz(korzen, "a", uchwyt="konto-a")
    B = kartridz(korzen, "b", uchwyt="konto-b")

    # ================================================== 1. F01
    print("=== 1. ODLACZENIE UNIEWAZNIA PRACUJACY PROCES (P02, P17) ===")
    akt_a, _ = preset.podlacz(A, agent, config, BAZA, srodowisko={})
    proces = cfg_procesu(akt_a, agent)
    sprawdz("przed odlaczeniem brama przepuszcza", preset.wymagaj_aktywnego(proces, "run.py") is akt_a)
    sprawdz("i aktywacja jest wazna", preset.aktywacja_nadal_wazna(proces) == "")
    preset.odlacz(agent)
    powod = oblewa(lambda: preset.wymagaj_aktywnego(proces, "run.py"))
    sprawdz("po odlaczeniu TEN SAM obiekt w pamieci dostaje odmowe",
            powod is not None and "odlaczony" in powod, powod)
    sprawdz("z powodem, ktory mowi co zrobic", powod is not None and "od nowa" in powod)
    akt_a2, _ = preset.podlacz(A, agent, config, BAZA, srodowisko={})
    proces_stary = cfg_procesu(akt_a, agent)
    sprawdz("ponowne podlaczenie tego samego presetu: stary proces znow wazny (ten sam odcisk i instancja)",
            preset.aktywacja_nadal_wazna(proces_stary) == "")
    akt_b, _ = preset.podlacz(B, agent, config, BAZA, srodowisko={})
    powod2 = preset.aktywacja_nadal_wazna(proces_stary)
    sprawdz("podlaczenie INNEGO presetu uniewaznia proces A", "zmienila sie" in powod2, powod2)
    # KONTRDOWOD: brama w darmowym tescie milczy jak dotad
    sprawdz("kontrdowod: w darmowym tescie brama nie sprawdza wskaznika",
            preset.wymagaj_aktywnego(types.SimpleNamespace(W_TESCIE=True, PRESET_AKTYWACJA=None)) is None)

    # ================================================== 2. F02
    print()
    print("=== 2. AGENT_V2_PRESET TO PODGLAD: BEZ KOSZTU I BEZ PUBLIKACJI (P03, P19) ===")
    preset.odlacz(agent)
    ze_srod = preset.aktywacja(agent, srodowisko={preset.ZMIENNA: str(A)})
    sprawdz("aktywacja ze srodowiska nadal powstaje (podglad promptow ma dzialac)",
            ze_srod is not None and ze_srod.zrodlo == "srodowisko")
    sprawdz("brama startu ja przepuszcza (podglad)", oblewa(lambda: preset.wymagaj_aktywnego(
        cfg_procesu(ze_srod, agent), "podglad")) is None)
    sprawdz("ale jest oznaczona jako podglad", preset.tylko_podglad(cfg_procesu(ze_srod, agent)))
    _stan = (config.W_TESCIE, config.PRESET_AKTYWACJA, config.KILL_SWITCH, config.DRY_RUN, config.AGENT_DIR)
    try:
        config.W_TESCIE, config.PRESET_AKTYWACJA, config.KILL_SWITCH, config.DRY_RUN = False, ze_srod, False, False
        config.AGENT_DIR = agent
        b = oblewa(lambda: llm._preflight("note", None, None))
        sprawdz("platne wywolanie z podgladu jest odrzucone PRZED kosztem",
                b is not None and "podglad" in b, b)
        sprawdz("publikacja z podgladu nie idzie", browser.naprawde_wyslac(True, "notka") is False)
        # odlaczony wskaznik w PRODUKCJI: to samo dla obiektu ze wskaznika
        akt_c, _ = preset.podlacz(A, agent, config, BAZA, srodowisko={})
        config.PRESET_AKTYWACJA = akt_c
        preset.odlacz(agent)
        b2 = oblewa(lambda: llm._preflight("note", None, None))
        sprawdz("po odlaczeniu platne wywolanie odrzucone: %s" % (b2 or "")[:50],
                b2 is not None and "odlaczony" in b2)
        sprawdz("po odlaczeniu publikacja nie idzie", browser.naprawde_wyslac(True, "komentarz") is False)
        # KONTRDOWOD: wazna aktywacja wskaznikiem przechodzi te dwie kontrole
        akt_d, _ = preset.podlacz(A, agent, config, BAZA, srodowisko={})
        config.PRESET_AKTYWACJA = akt_d
        sprawdz("kontrdowod: wazna aktywacja wskaznikiem publikuje jak dotad",
                browser.naprawde_wyslac(True, "notka") is True)
        b3 = oblewa(lambda: llm._preflight("note", None, None))
        sprawdz("kontrdowod: i nie jest zatrzymana przez kontrole aktywacji",
                b3 is None or ("podglad" not in b3 and "niewazna" not in b3), b3)
    finally:
        (config.W_TESCIE, config.PRESET_AKTYWACJA, config.KILL_SWITCH, config.DRY_RUN, config.AGENT_DIR) = _stan

    # ================================================== 3. F03
    print()
    print("=== 3. INSTANCJA MA WLASCICIELA (P04) ===")
    preset.odlacz(agent)
    akt_w, _ = preset.podlacz(A, agent, config, BAZA, instancja="wspolna", srodowisko={})
    sprawdz("pierwsze podlaczenie zapisuje wlasciciela",
            (preset.wlasciciel(akt_w.katalog_danych) or {}).get("preset") == "a")
    odm = oblewa(lambda: preset.podlacz(B, agent, config, BAZA, instancja="wspolna", srodowisko={}))
    sprawdz("B na instancji A dostaje odmowe", odm is not None and "nalezy do presetu 'a'" in odm, odm)
    sprawdz("z rada o nowej instancji", odm is not None and "--instancja" in odm and "--przejmij" in odm)
    sprawdz("wskaznik A zostal nietkniety", preset.czytaj_wskaznik(agent)["preset"] == "a")
    akt_w2, _ = preset.podlacz(A, agent, config, BAZA, instancja="wspolna", srodowisko={})
    sprawdz("ten sam preset i konto: wznowienie bez odmowy", akt_w2.numer == 2)
    akt_p, _ = preset.podlacz(B, agent, config, BAZA, instancja="wspolna", srodowisko={}, przejmij=True)
    sprawdz("--przejmij: jawne przejecie przechodzi i przepisuje wlasciciela",
            (preset.wlasciciel(akt_p.katalog_danych) or {}).get("preset") == "b")
    dziennik = (akt_p.katalog_danych / preset.NAZWA_DZIENNIKA).read_text(encoding="utf-8")
    sprawdz("i jest zapisane w dzienniku instancji jako przejecie", '"przejecie"' in dziennik)
    # to samo preset, INNE konto = inny wlasciciel
    A2 = kartridz(korzen, "a", uchwyt="konto-inne")
    odm2 = oblewa(lambda: preset.podlacz(A2, agent, config, BAZA, instancja="wspolna", srodowisko={}))
    sprawdz("inne konto na tej samej instancji tez dostaje odmowe", odm2 is not None and "konto" in odm2)

    # ================================================== 4. F05
    print()
    print("=== 4. PUSTY KORPUS = BRAK KORPUSU, NIE KORPUS SILNIKA (P10) ===")
    stary_korpus = korzen / "silnik-styl"
    stary_korpus.mkdir()
    (stary_korpus / "dawny.txt").write_text(
        "\n\n".join("Dawny glos akapit %d: %s" % (i, "x" * 160) for i in range(6)) + "\n", encoding="utf-8")
    import hashlib
    _raw = (stary_korpus / "dawny.txt").read_bytes()
    _ak = style.split_paragraphs(_raw)
    (stary_korpus / "przypiecia.json").write_text(json.dumps({
        "plik": "dawny.txt", "korpus_sha256": hashlib.sha256(style.bajty_kanoniczne(_raw)).hexdigest(),
        "akapitow": len(_ak),
        "przyklady": [{"funkcja": f, "akapit": i, "skrot": hashlib.sha256(_ak[i].encode("utf-8")).hexdigest()[:10]}
                      for i, f in enumerate(style.FUNKCJE_STYLU)]}), encoding="utf-8")
    baza_ze_starym = dict(BAZA, STYLE_CORPUS=stary_korpus / "dawny.txt")
    pb = preset.wczytaj(B)
    proba_b, _ = preset.rozwiaz(pb, config, baza_ze_starym)
    sprawdz("kartridz z pustym korpusem wskazuje WLASNY katalog, nie silnika",
            pathlib.Path(proba_b.STYLE_CORPUS).parent == (B / "styl").resolve(), proba_b.STYLE_CORPUS)
    _st = (config.STYLE_CORPUS, config.STYL_WYMAGAJ_KORPUSU)
    try:
        config.STYLE_CORPUS, config.STYL_WYMAGAJ_KORPUSU = pathlib.Path(proba_b.STYLE_CORPUS), False
        sprawdz("i pisarz dostaje ZERO przykladow", style.przyklady_albo_pusto() == [])
        # KONTRDOWOD: stara sciezka (domyslny katalog silnika) ladowala dawny glos
        config.STYLE_CORPUS = stary_korpus / "dawny.txt"
        _dawne = style.przyklady_albo_pusto()
        sprawdz("kontrdowod: domyslny katalog silnika z korpusem oddawal 5 dawnych akapitow",
                len(_dawne) == 5 and all("Dawny glos" in e["text"] for e in _dawne))
    finally:
        config.STYLE_CORPUS, config.STYL_WYMAGAJ_KORPUSU = _st
    bledy_b, uwagi_b = preset.sprawdz(pb, config, baza_ze_starym, srodowisko={})
    sprawdz("sprawdz mowi o braku korpusu jako uwadze, nie bledzie",
            not [b for b in bledy_b if "korpus" in b] and any("korpus" in u for u in uwagi_b), (bledy_b, uwagi_b))
    # sciezka spoza katalogu presetu NIE jest szukana w repo
    C = kartridz(korzen, "c")
    (C / "preset.toml").write_text((C / "preset.toml").read_text(encoding="utf-8").replace(
        'profil_pozytywny = "styl/profil_pozytywny.md"',
        'profil_pozytywny = "style-profiles/ARTICLE_STYLE_PROFILE_V1.md"'), encoding="utf-8")
    pc = preset.wczytaj(C)
    sprawdz("sciezka wzgledna w katalogu presetu rozwiazuje sie TYLKO w tym katalogu",
            pathlib.Path(pc.pola["styl.profil_pozytywny"]).parent.parent == C.resolve(),
            pc.pola["styl.profil_pozytywny"])
    bledy_c, _ = preset.sprawdz(pc, config, BAZA, srodowisko={})
    sprawdz("brak pliku w paczce to blad sprawdzenia, nie plik z repozytorium",
            any("profil" in b or "styl" in b for b in bledy_c), bledy_c)
    E = kartridz(korzen, "e")
    (E / "preset.toml").write_text((E / "preset.toml").read_text(encoding="utf-8").replace(
        'profil_pozytywny = "styl/profil_pozytywny.md"',
        'profil_pozytywny = "repo:style-profiles/ARTICLE_STYLE_PROFILE_V1.md"'), encoding="utf-8")
    pe = preset.wczytaj(E)
    bledy_e, _ = preset.sprawdz(pe, config, BAZA, srodowisko={})
    sprawdz("plik wspolny z repozytorium wybiera sie JAWNIE przez repo: i wtedy przechodzi",
            not any("profil pozytywny" in b for b in bledy_e), bledy_e)
    sprawdz("plik spoza paczki nie wchodzi do jej zasobow (odcisk paczki = paczka)",
            "styl/profil_pozytywny.md" not in pe.zasoby and "styl/profil_negatywny.md" in pe.zasoby)

    # ================================================== 5. F06
    print()
    print("=== 5. ODCISK OBEJMUJE TRESC STYLU I NIE ZALEZY OD MIEJSCA (P06, P07, P09) ===")
    pa = preset.wczytaj(A)
    sprawdz("odcisk zna zasoby stylu z paczki",
            "styl/profil_pozytywny.md" in pa.zasoby and "styl/profil_negatywny.md" in pa.zasoby, sorted(pa.zasoby))
    kopia = korzen / "gdzie-indziej" / "a"
    shutil.copytree(A, kopia)
    sprawdz("kopia identycznego katalogu ma TEN SAM odcisk", preset.wczytaj(kopia).odcisk == pa.odcisk)
    (A / "styl" / "profil_pozytywny.md").write_text("# Profil a\n\nInny glos.\n", encoding="utf-8")
    sprawdz("zmiana profilu pozytywnego zmienia odcisk", preset.wczytaj(A).odcisk != pa.odcisk)
    akt_e, _ = preset.podlacz(A, agent, config, BAZA, srodowisko={}, przejmij=True)
    (A / "styl" / "profil_negatywny.md").write_text("# Zakazy a\n\nNowy zakaz.\n", encoding="utf-8")
    z = oblewa(lambda: preset.aktywacja(agent, srodowisko={}))
    sprawdz("zmiana profilu po aktywacji = odmowa startu, jak przy zmianie TOML-a",
            z is not None and "zmienil sie po aktywacji" in z, z)
    D = kartridz(korzen, "d", korpus="styl/korpus.txt")
    (D / "styl" / "korpus.txt").write_text("\n\n".join("Akapit %d %s" % (i, "y" * 170) for i in range(6)) + "\n",
                                           encoding="utf-8")
    pd1 = preset.wczytaj(D)
    (D / "styl" / "korpus.txt").write_text("\n\n".join("Akapit %d %s" % (i, "z" * 170) for i in range(6)) + "\n",
                                           encoding="utf-8")
    sprawdz("zmiana korpusu zmienia odcisk", preset.wczytaj(D).odcisk != pd1.odcisk)
    sprawdz("kontrdowod: bez zasobow (stary sposob) te dwa korpusy mialyby ten sam odcisk",
            preset.odcisk(pd1.pola, pd1.schema, pd1.bloki) == preset.odcisk(preset.wczytaj(D).pola, pd1.schema, pd1.bloki))

    # ================================================== 6. F04
    print()
    print("=== 6. BEZ KARTRIDZA STARY konfiguracja.toml NIE WRACA (P18) ===")
    zrodlo_cfg = pathlib.Path("agent-v2/config.py").read_text(encoding="utf-8")
    i_else = zrodlo_cfg.index("_CZYTAJ_STARY_TOML")
    sprawdz("gałąź bez aktywacji czyta stary TOML tylko w tescie albo na jawne zyczenie",
            "W_TESCIE" in zrodlo_cfg[i_else:i_else + 300] and "AGENT_V2_KONFIGURACJA_TOML" in zrodlo_cfg[i_else:i_else + 300])
    sprawdz("i mowi o tym na ekran z droga migracji",
            "importuj-konfiguracje" in zrodlo_cfg[i_else:i_else + 1200])
    sprawdz("kontrdowod: w tym tescie (W_TESCIE) konfiguracja nadal jest czytana — testy konfiguracji na tym stoja",
            config.W_TESCIE is True)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
