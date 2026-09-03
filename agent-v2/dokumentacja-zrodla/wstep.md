# Your Publication — dokumentacja odtworzeniowa agenta

**Wersja:** 2026-08-20 · **Stan opisywany:** `main`, wdrożony na produkcji
**Cel:** z tego dokumentu ma dać się odtworzyć całego bota od zera, razem
z promptami, progami, selektorami i zawartością dysku.

---

## 0. Jak czytać ten dokument

Dokument opisuje **stan faktyczny**, nie zamierzony. Wszędzie, gdzie kod robi
coś innego, niż mówi jego nazwa albo komentarz, jest to oznaczone **WADA** albo
**DECYZJA OTWARTA** — i takich miejsc jest kilkanaście. Nie są ukryte
w przypisach, bo ich ukrywanie było przyczyną większości kosztownych pomyłek
w tym projekcie.

Kod jest wklejany **dosłownie ze źródeł**, nie przepisywany. Prompty są
w załączniku A **w całości**, nie w streszczeniu — bo to one, a nie kod,
decydują o tym, co bot napisze.

Liczby są **zmierzone na produkcji**, nie szacowane. Gdzie coś jest szacunkiem,
napisane jest, że to szacunek.

**Struktura:**

| część | zawartość |
|---|---|
| I | mandat, ograniczenia, architektura |
| II | spis wszystkich modułów i funkcji |
| III | ścieżka artykułu — dziesięć etapów |
| IV | ścieżka dnia i styk z Substackiem |
| V | bramki i kontrola jakości |
| VI | dane, dysk, koszty, operacje |
| VII | kluczowy kod dosłownie |
| VIII | znane wady i decyzje otwarte |
| A | **wszystkie 25 promptów w całości** |
| B | wszystkie 150 stałych konfiguracji |
| C | mapa dysku produkcyjnego |

---

## I. Mandat i architektura

### I.1. Czego wymagał właściciel

Agent prowadzi anglojęzycznego Substacka **„Your Publication"**, który
wyjaśnia ukryte systemy, bodźce i decyzje stojące za zwykłymi rzeczami.
Ograniczenia postawione przy starcie wersji drugiej:

| ograniczenie | stan faktyczny | ocena |
|---|---|---|
| maksimum 10 plików `.py` | **{{ile_plikow}} plików**, {{ile_wierszy}} wierszy | **PRZEKROCZONE** |
| 4 tabele w bazie | 4: `runs`, `calls`, `articles`, `sources` | dotrzymane |
| jedna warstwa abstrakcji | jedna: `llm.py` | dotrzymane |
| brak migracji, brak kolejek | `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE` | dotrzymane |
| jedno polecenie uruchamiające | `python agent-v2/run.py` | dotrzymane |
| pełna autonomia, zero pytań | brak interaktywnych promptów | dotrzymane |

**WADA — {{ile_plikow}} plików zamiast dziesięciu.** Najbliższe usunięciu:
`style.py` ({{wiersze_style}} wierszy, wołany tylko z `stages.py`) i
`kopia_subskrybentow.py` ({{wiersze_kopii}} wierszy, narzędzie ręczne poza
przebiegiem). Scalenie któregokolwiek przywraca zgodność z mandatem.

### I.2. Zasady o mocy nadrzędnej nad kodem

1. **Nic nie blokuje artykułu.** Gdy temat przeszedł odsiew, a research jest
   opłacony, artykuł MA powstać. Bramki oddają uwagi do przeczytania, nie
   werdykty. `gates.verdict()` zwraca zawsze `SAVED`. Zablokowany artykuł to
   czysta strata researchu i zero informacji w zamian.
2. **Konto nie ujawnia, że jest AI** (anonimowa marka redakcyjna), ale **nigdy
   nie kłamie zapytane wprost** i nie stosuje technicznego omijania wykrywania.
3. **Serwisy odmawiające automatom są respektowane.** Żadnych proxy
   rezydencjalnych, żadnego obchodzenia blokad. 403 i frazy odmowy trafiają do
   `sources.fail_reason`.
4. **Żadnych sekretów w repozytorium.** Repo jest publiczne; `.env` i `data/`
   są w `.gitignore`. Sesja Substacka (`storage-state.json`) nigdy nie opuszcza
   serwera.

### I.3. Rozkład odpowiedzialności

```
run.py ──┬─> stages.py ──┬─> llm.py ──> DeepSeek | Anthropic | OpenAI
         │               ├─> style.py
         │               └─> browser.py   (wyjatek 2 — dobor zrodel)
         ├─> gates.py        (bramki orkiestruje ROZDZIELNIK, nie etapy)
         ├─> db.py
         ├─> browser.py ──> Playwright ──> Chrome ──> Substack
         ├─> kanal.py
         └─> alarm.py

wszystkie moduly ──> config.py   (stale i losowania — ZALACZNIK B)

poza przebiegiem:  kopia_subskrybentow.py   (narzedzie reczne)
```

> Diagram pokazywal wczesniej osiem modulow z jedenastu i wieszal `gates.py`
> pod `stages.py`. Obie rzeczy myla przy odtwarzaniu: brakowalo `config.py`,
> od ktorego zalezy kazdy modul, a bramki wolane z wnetrza etapow odbieraja
> systemowi wlasnosc, na ktorej stoi — **etap nie ocenia sam siebie**.

**Reguła rozdziału i jej DWA wyjątki:** `stages.py` nigdy nie dotyka
przeglądarki, `browser.py` nigdy nie woła modelu.

1. `browser.restackuj_w_kanale(ile, decyzja, wyslij)` przyjmuje funkcję
   decyzyjną jako argument, więc sama decyzja zostaje w `stages` —
   przeglądarka tylko klika.
2. `stages.py:1672` **importuje `browser`** i woła `browser.read_pages`,
   żeby dobrać brakujące źródła w trakcie researchu. To jest prawdziwe
   złamanie reguły, nie odwrócenie zależności jak w punkcie 1.

> Dokument mówił wcześniej „bez wyjątku poza jednym udokumentowanym", czyli
> wprost zachęcał, żeby przestać szukać dalszych. Drugi wyjątek siedzi
> w głównej ścieżce artykułu.

Powód tego rozdziału jest praktyczny: dzięki niemu **cała warstwa myślowa da
się testować bez przeglądarki i bez pieniędzy**. {{ile_zestawow}} zestawów
testów, {{ile_sprawdzen}} sprawdzeń, żaden nie otwiera Chrome i żaden nie
woła płatnego modelu.

### I.4. Trzy zasady, z których wynika reszta

**Model obserwuje, kod rozstrzyga.** Oceny liczbowe modelu degenerują się do
jednej wartości — sprawdzone trzy razy na trzy różne sposoby: samooceny
wracały zawsze 1.0, liczba wątków zawsze sześć, liczba znanych tekstów zawsze
trzy. Dlatego pytamy o rzeczy **sprawdzalne**: cytat do znalezienia w tekście,
listę do policzenia, wymuszone porównanie, którego nie da się wyrównać.
Arytmetykę, pozycje i progi liczy kod.

**Kontrdowód w każdym teście.** Test musi umieć wykryć także zachowanie
**sprzed** poprawki. Test, który tego nie umie, nie jest dowodem, że poprawka
była potrzebna — jest lustrem.

**Powtarzalna forma zdradza maszynę tak samo jak powtarzana treść.** Dlatego
reguły stylu są **zakazujące**, a nie nakazujące pozycję, a ruch końcowy
i liczba paraleli są losowane na artykuł.
