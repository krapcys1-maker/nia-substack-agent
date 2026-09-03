"""Jakie modele istnieja DZISIAJ — pytane na zywo, nie brane z pamieci.

DLACZEGO TO ISTNIEJE. Bot napisal notke o ukrytych tokenach rozumowania w
modelach o1 i wystawil ja 25 sierpnia 2026 jako rzecz biezaca. Zrodlem byl
artykul o ich premierze z konca 2024. Fakt byl prawdziwy, wiec sprawdzanie
faktow go przepuscilo — ono pyta „czy to prawda", nie „czy to jeszcze aktualne".
Wlasciciel zlapal to jednym zdaniem: „a czy modele o1 jeszcze w ogole sa?".

Nie sa. OpenAI wylacza o1 z API 23 pazdziernika 2026.

Glebszy problem jest taki, ze MODEL NIE MA JAK TEGO ZAUWAZYC. Jego wiedza
konczy sie kilka miesiecy temu, a przeterminowany fakt czyta sie od srodka
dokladnie tak samo jak biezacy. Zadna instrukcja w prompcie tego nie naprawi,
bo instrukcja trafia do tej samej pamieci, ktora jest nieaktualna.

Jedyne wyjscie: PYTAC SWIATA, nie siebie. Ten modul raz na dobe pyta modelu z
wlaczonym wyszukiwaniem, jakie modele sa teraz, i trzyma odpowiedz w pliku.
Wynik idzie do promptow jako kontekst — wiec pisarz nie musi pamietac, tylko
czyta.

Odswiezamy raz na dobe, bo tempo wydan jest liczone w tygodniach, nie godzinach:
zmierzone na sierpniu 2026, Anthropic wydal cztery modele w niecale dwa
miesiace. Doba jest dosc gesta, zeby nie przegapic wydania, i dosc rzadka, zeby
nie placic za to samo pytanie przy kazdej notce.
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

SYSTEM = (
    "You report the current state of the AI model landscape. You search before "
    "answering and you never rely on memory: your training data is months old "
    "and the field moves in weeks. Return only valid JSON."
)

PYTANIE = """Today is {dzis}.

Search and report which large language models are CURRENT right now, from the
major labs: Anthropic, OpenAI, Google, Meta, Mistral, DeepSeek, xAI, Alibaba.

For each lab give the models a developer would actually reach for today, with
the release date of each. Then list, separately, the models that have been
retired, deprecated, or scheduled for removal — with the date they go.

Be exact about version numbers. "The newest" is useless six weeks from now;
"released 2026-07-24" is not.

If you cannot confirm something by search, leave it out rather than guessing.
An incomplete list is fine. An invented one is not.

Return only valid JSON:

{{"sprawdzone": "<today's date, YYYY-MM-DD>",
  "aktualne": [{{"lab": "<lab>", "model": "<exact name and version>", "wydany": "<YYYY-MM-DD or YYYY-MM>", "po_co": "<one short phrase: what it is for>"}}],
  "wycofane": [{{"model": "<exact name>", "kiedy_znika": "<YYYY-MM-DD or empty>", "uwaga": "<one short phrase>"}}],
  "uwagi": "<one or two sentences on anything a writer should know before naming a model today>"}}
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
            PYTANIE.format(dzis=teraz.strftime("%Y-%m-%d")),
            conn=conn, run_id=run_id,
            # WYSZUKIWANIE JEST TU CALA WARTOSCIA. Bez niego pytamy pamieci
            # modelu o to, czego pamiec z definicji nie wie — a wlasnie ta
            # pomylka kosztowala nas notke o modelach o1.
            web_search=True)
        dane = llm.parse_json(tekst)
        if not isinstance(dane, dict) or not dane.get("aktualne"):
            raise ValueError("odpowiedz bez listy aktualnych modeli")
    except Exception as exc:
        print("  [modele] nie odswiezylem (%s: %s) — biore ostatnie znane"
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
    print("  [modele] odswiezone: %d aktualnych, %d wycofanych"
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
    print(jako_tekst(d) or "(nic nie wiem o modelach)")
