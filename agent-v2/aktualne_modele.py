"""Co w tej dziedzinie jest AKTUALNE dzisiaj — pytane na zywo, nie z pamieci.

DLACZEGO TO ISTNIEJE. Bot napisal notke o ukrytych tokenach rozumowania w
rodzinie modeli i wystawil ja jako rzecz biezaca. Zrodlem byl
artykul o ich premierze z konca 2024. Fakt byl prawdziwy, wiec sprawdzanie
faktow go przepuscilo — ono pyta „czy to prawda", nie „czy to jeszcze aktualne".
Wlasciciel zlapal to jednym zdaniem: „a czy te modele jeszcze w ogole sa?".

Nie byly. Dostawca wylaczal je z API osiem tygodni po tamtej notce.

Glebszy problem jest taki, ze MODEL NIE MA JAK TEGO ZAUWAZYC. Jego wiedza
konczy sie kilka miesiecy temu, a przeterminowany fakt czyta sie od srodka
dokladnie tak samo jak biezacy. Zadna instrukcja w prompcie tego nie naprawi,
bo instrukcja trafia do tej samej pamieci, ktora jest nieaktualna.

Jedyne wyjscie: PYTAC SWIATA, nie siebie. Ten modul raz na dobe pyta modelu
z wlaczonym wyszukiwaniem, co w TEJ dziedzinie jest teraz aktualne, i trzyma
odpowiedz w pliku. Wynik idzie do promptow jako kontekst — wiec pisarz nie musi
pamietac, tylko czyta.

DZIEDZINA IDZIE Z KONFIGURACJI. Pytanie bylo wpisane i dotyczylo wylacznie
modeli jezykowych, z nazwami osmiu laboratoriow w tresci — wiec konto o kazdej
innej dziedzinie placilo codziennie za liste modeli AI. Mechanizm jest ogolny
(przeterminowany fakt czyta sie tak samo w kazdej dziedzinie), pytanie nie bylo.
Patrz `config.pytanie_o_stan_dziedziny` i wylacznik `STAN_DZIEDZINY_PYTAJ`.

NAZWA PLIKU I POL ZOSTAJE. `aktualne_modele.json`, klucze `aktualne`
i `wycofane` — przemianowanie ich kosztowaloby migracje danych i cztery
miejsca w kodzie, a nie daje nic poza ladniejsza nazwa. Zapisane jest tu, zeby
nastepny czytelnik nie szukal wyjasnienia.

Odswiezamy raz na dobe, bo w dziedzinach, ktore sie w ogole zmieniaja, tempo
liczy sie w tygodniach, nie w godzinach. Doba jest dosc gesta, zeby nie
przegapic zmiany, i dosc rzadka, zeby nie placic za to samo pytanie przy kazdej
notce. Dziedzina, ktora nie zmienia sie i tak, moze to wylaczyc
(`stan_dziedziny.pytaj = false`).
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import config
import llm

PLIK = config.DATA_DIR / "aktualne_modele.json"

# Ile godzin odpowiedz jest wazna. Doba — patrz uzasadnienie w naglowku.
WAZNE_GODZIN = 24

# PYTANIE BYLO WPISANE I DOTYCZYLO WYLACZNIE MODELI JEZYKOWYCH — z nazwami
# osmiu laboratoriow w tresci. Uzasadnienie tego modulu (patrz naglowek) nie ma
# jednak z AI nic wspolnego: model nie ma jak zauwazyc, ze fakt sie
# przeterminowal, w KAZDEJ dziedzinie. Konto o dowolnej innej dziedzinie
# placilo wiec codziennie za liste modeli AI i dostawalo ja do promptu jako
# „stan swojej dziedziny".
#
# Dzis pytanie idzie z `config.pytanie_o_stan_dziedziny()`, a domyslne buduje
# sie z `NISZA`. Slownictwo odpowiedzi zostalo ogolne („pozycja", nie „model"),
# bo to samo pole ma pomiescic wersje oprogramowania, przepis, sklad i stawke.
SYSTEM = (
    "You report what is CURRENT in a field, right now. You search before "
    "answering and you never rely on memory: your training data is months old "
    "and things change. Return only valid JSON."
)

PYTANIE = """Today is {dzis}.

Search and report what is current in this field:

{o_co}

Give the things somebody working in that field would reach for or refer to
today, each with the date it appeared or was last changed. Then list,
separately, what has been withdrawn, replaced, discontinued or scheduled to
end — with the date it goes.

Be exact about names and versions. "The newest" is useless six weeks from now;
"changed 2026-07-24" is not.

If you cannot confirm something by search, leave it out rather than guessing.
An incomplete list is fine. An invented one is not.

Return only valid JSON:

{{"sprawdzone": "<today's date, YYYY-MM-DD>",
  "aktualne": [{{"lab": "<who is behind it, or empty>", "model": "<exact name and version>", "wydany": "<YYYY-MM-DD or YYYY-MM>", "po_co": "<one short phrase: what it is for>"}}],
  "wycofane": [{{"model": "<exact name>", "kiedy_znika": "<YYYY-MM-DD or empty>", "uwaga": "<one short phrase>"}}],
  "uwagi": "<one or two sentences a writer should know before naming any of these today>"}}
"""


def _swieze(dane: dict[str, Any]) -> bool:
    """Czy zapisana odpowiedz jest jeszcze wazna."""
    kiedy = str((dane or {}).get("_pobrane") or "")
    if not kiedy:
        return False
    try:
        pobrane = datetime.fromisoformat(kiedy)
    except ValueError:
        return False
    if pobrane.tzinfo is None:
        pobrane = pobrane.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - pobrane < timedelta(hours=WAZNE_GODZIN)


def wczytaj() -> dict[str, Any]:
    """Ostatnia zapisana odpowiedz. Pusty slownik, gdy nie ma albo jest zepsuta."""
    if not PLIK.exists():
        return {}
    try:
        dane = json.loads(PLIK.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dane if isinstance(dane, dict) else {}


def pobierz(conn=None, run_id: int | None = None,
            wymus: bool = False) -> dict[str, Any]:
    """Aktualny stan modeli. Z pliku, gdy swiezy; inaczej pyta na nowo.

    NIGDY NIE WYWALA PRZEBIEGU. Gdy pytanie sie nie uda, oddajemy ostatnia
    znana odpowiedz, a gdy i jej nie ma — pusty slownik. Notka bez tej wiedzy
    jest gorsza, ale notka, ktora sie nie ukazala, jest gorsza jeszcze bardziej.
    """
    zapisane = wczytaj()
    if not wymus and _swieze(zapisane):
        return zapisane

    # WYLACZNIK Z KONFIGURACJI. Dziedzina, ktora nie zmienia sie z tygodnia na
    # tydzien, nie ma po co placic za to wywolanie codziennie. Oddajemy to, co
    # juz wiemy — zapisana odpowiedz nie znika przez samo wylaczenie pytania.
    if not getattr(config, "STAN_DZIEDZINY_PYTAJ", True):
        return zapisane

    teraz = datetime.now(timezone.utc)
    # Wlasne polaczenie, gdy nikt nie podal — koszt wywolania ma trafic do
    # bazy tak samo jak kazdy inny. Etap, ktory nie zapisuje kosztu, jest
    # niewidzialny dla kontroli budzetu.
    wlasne = None
    if conn is None:
        import db as _db
        conn = wlasne = _db.connect()
    try:
        tekst = llm.call(
            "aktualne_modele", SYSTEM,
            PYTANIE.format(dzis=teraz.strftime("%Y-%m-%d"),
                           o_co=config.pytanie_o_stan_dziedziny()),
            conn=conn, run_id=run_id,
            # WYSZUKIWANIE JEST TU CALA WARTOSCIA. Bez niego pytamy pamieci
            # modelu o to, czego pamiec z definicji nie wie — a wlasnie ta
            # pomylka kosztowala nas notke o modelach, ktorych juz nie bylo.
            web_search=True)
        dane = llm.parse_json(tekst)
        if not isinstance(dane, dict) or not dane.get("aktualne"):
            raise ValueError("odpowiedz bez listy aktualnych modeli")
    except Exception as exc:
        print("  [stan dziedziny] nie odswiezylem (%s: %s) — biore ostatnie znane"
              % (type(exc).__name__, str(exc)[:120]), flush=True)
        return zapisane
    finally:
        if wlasne is not None:
            wlasne.close()

    dane["_pobrane"] = teraz.isoformat()
    try:
        PLIK.parent.mkdir(parents=True, exist_ok=True)
        PLIK.write_text(json.dumps(dane, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    except OSError:
        pass
    print("  [stan dziedziny] odswiezone: %d aktualnych, %d wycofanych"
          % (len(dane.get("aktualne") or []), len(dane.get("wycofane") or [])),
          flush=True)
    return dane


def jako_tekst(dane: dict[str, Any] | None = None) -> str:
    """Stan modeli w postaci, ktora wchodzi do promptu.

    Pusty napis, gdy nic nie wiemy — wtedy prompt po prostu nie dostaje tej
    sekcji i pisarz zostaje przy ogolnej zasadzie „nie nazywaj wersji, ktorej
    nie sprawdziles".
    """
    dane = dane if dane is not None else wczytaj()
    if not dane or not dane.get("aktualne"):
        return ""

    # KROTKO, I TO JEST POPRAWKA PO AWARII. Pierwsza wersja wypisywala wszystkie
    # znalezione modele z opisami plus cala liste wycofanych — przy 25 i 16
    # pozycjach to kilkadziesiat wierszy w prompcie, ktory i tak ma juz 255.
    #
    # Skutek zmierzony 25 sierpnia: szukanie ciekawostek zrobilo TRZYDZIESCI
    # wyszukiwan, zjadlo 388 tysiecy tokenow wejscia i nie oddalo zadnego JSON-a.
    # Model gonil za weryfikacja kazdej pozycji zamiast szukac faktow.
    #
    # Ta sekcja ma odpowiadac na jedno pytanie — "czy ta nazwa jeszcze istnieje"
    # — i do tego wystarczy sama nazwa z data. Opisy "po co to jest" nie sluza
    # niczemu w tym miejscu, a kusza do sprawdzania.
    linie = ["Checked %s. Names and dates only — this is a list to check a name"
             " against, not material." % (dane.get("sprawdzone") or "recently")]
    linie.append("CURRENT: " + ", ".join(
        "%s (%s)" % (m.get("model", "?"), str(m.get("wydany", "?"))[:7])
        for m in (dane.get("aktualne") or [])[:16]))
    wyc = dane.get("wycofane") or []
    if wyc:
        linie.append("GONE OR GOING, do not build on these: " + ", ".join(
            str(m.get("model", "?")) for m in wyc[:12]))
    return "\n".join(linie)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    d = pobierz(wymus="--wymus" in sys.argv)
    print()
    print(jako_tekst(d) or "(nic nie wiem o stanie dziedziny)")
