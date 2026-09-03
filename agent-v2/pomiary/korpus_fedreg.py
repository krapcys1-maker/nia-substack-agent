"""Ile ze stu przepisow Federal Register w ogole niesie material dla nas.

Teza do sprawdzenia: preambuly, w ktorych regulator ODPOWIADA na zastrzezenia,
sa najgestszym zlozem „wiekszosc sadzi X, naprawde Y" w publicznym internecie,
bo agencja musi opisac rozumowanie i odniesc sie do zarzutow.

Ale nie kazdy przepis takie odpowiedzi ma — pierwszy sprawdzony byl o dodatku
paszowym i mial trzy slowa „comment" na trzynascie tysiecy znakow. Ten test
mierzy, ile procent dokumentow niesie cokolwiek, ZANIM wydamy grosz na model.

Nic nie kosztuje: samo API i pobranie tekstu, zero wywolan modelu.
"""
import re
import sys

sys.path.insert(0, "agent-v2")

ILE_DOKUMENTOW = 100
API = "https://www.federalregister.gov/api/v1/documents.json"
POLA = ["title", "abstract", "agencies", "publication_date", "html_url",
        "raw_text_url", "type", "action"]

# Slady tego, ze regulator odpowiada komuś, kto sie nie zgadzal. To jest
# dokladnie ksztalt „wiekszosc sadzi X, naprawde Y", tylko napisany przez
# strone, ktora ma obowiazek sie tlumaczyc.
SPOR = (r"commenters?\b", r"\bwe disagree\b", r"\bwe decline\b",
        r"\bwe do not agree\b", r"\bin response to (the |these )?comments?\b",
        r"\bone commenter\b", r"\bseveral commenters\b", r"\bwe considered\b")


def main() -> int:
    import httpx

    print("pobieram %d najnowszych przepisow (typ RULE)..." % ILE_DOKUMENTOW,
          flush=True)
    with httpx.Client(timeout=45, follow_redirects=True) as c:
        r = c.get(API, params={"per_page": ILE_DOKUMENTOW, "order": "newest",
                               "conditions[type][]": "RULE", "fields[]": POLA})
        if r.status_code != 200:
            print("API odmowilo: HTTP %s" % r.status_code)
            return 1
        dokumenty = r.json().get("results") or []
        print("dostalem %d" % len(dokumenty), flush=True)

        z_tekstem = brak_tekstu = 0
        wyniki = []
        for i, d in enumerate(dokumenty, 1):
            url = d.get("raw_text_url")
            if not url:
                brak_tekstu += 1
                continue
            try:
                t = c.get(url).text
            except Exception:
                brak_tekstu += 1
                continue
            z_tekstem += 1
            trafienia = sum(len(re.findall(w, t, re.I)) for w in SPOR)
            wyniki.append({
                "tytul": (d.get("title") or "")[:70],
                "urzad": ((d.get("agencies") or [{}])[0].get("name") or "")[:34],
                "znakow": len(t),
                "spor": trafienia,
                "url": d.get("html_url", ""),
            })
            if i % 20 == 0:
                print("  ... %d/%d" % (i, len(dokumenty)), flush=True)

    print()
    print("=" * 78)
    print("POBRANIE: %d z tekstem, %d bez" % (z_tekstem, brak_tekstu))
    if not wyniki:
        print("nic nie pobrano")
        return 1

    gest = [w for w in wyniki if w["spor"] >= 5]
    slabe = [w for w in wyniki if 1 <= w["spor"] < 5]
    puste = [w for w in wyniki if w["spor"] == 0]
    print()
    print("GESTOSC SPORU (ile razy regulator odnosi sie do zastrzezen):")
    print("  gestych (>=5 sladow):  %3d   %4.0f%%" % (len(gest), 100*len(gest)/len(wyniki)))
    print("  slabych (1-4):         %3d   %4.0f%%" % (len(slabe), 100*len(slabe)/len(wyniki)))
    print("  bez sporu (0):         %3d   %4.0f%%" % (len(puste), 100*len(puste)/len(wyniki)))
    print()
    sr = sum(w["znakow"] for w in wyniki) / len(wyniki)
    print("sredni dokument: %.0f znakow" % sr)
    print("gesty dokument:  %.0f znakow" % (
        sum(w["znakow"] for w in gest)/len(gest) if gest else 0))

    print()
    print("DZIESIEC NAJGESTSZYCH — to jest material, o ktory chodzi:")
    for w in sorted(wyniki, key=lambda x: -x["spor"])[:10]:
        print("  %3d sladow  %6d zn.  [%s]" % (w["spor"], w["znakow"], w["urzad"]))
        print("       %s" % w["tytul"])

    print()
    print("WNIOSEK DO DECYZJI:")
    if gest:
        print("  Na sto dokumentow %d niesie gesty spor. Zeby dostac dziesiec"
              % len(gest))
        print("  gestych preambul, trzeba przejrzec okolo %d przepisow."
              % (round(1000 / max(1, len(gest)))))
        print("  Filtr jest DARMOWY (regex na pobranym tekscie), wiec model")
        print("  dostaje wylacznie to, co ma szanse przejsc bramki.")
    else:
        print("  ZERO gestych w tej probce — teza sie NIE potwierdza na")
        print("  najnowszych przepisach; trzeba szukac po typie albo urzedzie.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
