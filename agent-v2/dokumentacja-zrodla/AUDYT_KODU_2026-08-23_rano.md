> **Zrzut z 23 sierpnia 2026, rano.** Liczby w tym raporcie pochodzą sprzed
> zmian z tego samego dnia — mówi o 10 419 wierszach dokumentacji i 17 246
> wierszach kodu; po południu było 10 535 i 11 231. Zostaje jako **zapis
> stanu z tamtej godziny**, nie jako opis dzisiaj.
>
> Część jego ustaleń zamknęłem tego dnia: kotwica długości pracująca przeciw
> skalowaniu, martwy `min_words`, sprzeczne polecenia o granicach w prompcie
> pisarza, ranking skauta liczony dwa razy źle. Stan bieżący:
> [`../../README.md`](../../README.md) i [`AUDYT_2026-08-23.md`](AUDYT_2026-08-23.md).

# Raport z audytu — `JAK_ZBUDOWANY_JEST_BOT.md` i kod `agent-v2`

**Data:** 2026-08-23 · **Przedmiot:** dokument odtworzeniowy (10 419 wierszy) + 11 modułów `.py` (17 246 wierszy)
**Zamówienie właściciela:** ocena architektury i strategii; mandat konstrukcyjny miękki; wolno podważać wszystko.
**Zgłoszony ból:** *„tematy są miałkie na artykuły"* oraz jakość tekstów.

---

## 0. Metoda i granice tego raportu

Przeczytałem dokument w całości (części 0–VIII, załączniki A/B/C wyrywkowo) i przeszedłem
kod. Osiem agentów zrobiło niezależny przegląd modułów i oddało **94 surowe znaleziska**;
warstwa adwersaryjnej weryfikacji padła na limicie sesji, więc **zweryfikowałem sam
najważniejsze ~30** — otwierając pliki i uruchamiając kod. Reszta jest w §7 jako materiał
**niezweryfikowany**, wyraźnie oznaczony. Nie podaję ich jako ustaleń.

Dwie uwagi o danych, żeby nie mylić poziomów:

- Lokalna baza `data/agent-v2.db` to **stan roboczy z 15–16 sierpnia** (99 przebiegów,
  15 artykułów, $14,67), a nie produkcja opisana w rozdziale VI (28 przebiegów,
  6 artykułów, $11,00). Gdzie powołuję się na dane, piszę na które.
- Bramki, które wtedy nie istniały, nie mogły się zapalić — nie wyciągam z tego wniosków
  o dzisiejszych bramkach.

**Ocena ogólna, żeby nie chować jej na końcu.** To jest bardzo dobrze zbudowany system.
Zasada „model obserwuje, kod rozstrzyga", wymóg kontrdowodu w testach, dziennik działań
osobno od dziennika wywołań, jawne katalogowanie własnych wad — to są rzeczy, których
w projektach tej wielkości zwykle nie ma. Wady, które opisuję niżej, są w większości
**wadami tej samej metody zastosowanej niekonsekwentnie**: reguła została odkryta, zapisana,
a potem wpięta w jedno miejsce zamiast we wszystkie.

---

# CZĘŚĆ I. Dlaczego tematy są miałkie

To jest oś raportu. Dokument **zna objaw** (VIII.1 poz. 9: *„skaut nie trafia w kryteria
artykułowe — ostatni przebieg dał 0 z 10. Mamy miernik, nie mamy generatora"*), ale nie ma
diagnozy. Poniżej siedem mechanizmów. Każdy działa osobno; razem tworzą pętlę, z której
system nie ma wyjścia.

## 1.1. Obserwacja, od której zacząłem

Wszystkie tematy, jakie ten system kiedykolwiek wybrał — z bazy lokalnej i z listy
produkcyjnej w rozdziale VI:

> torebka sałaty · metka w piżamie · szpara pod drzwiami kabiny · pistolet dystrybutora ·
> cztery cyfry na oponie · kropkowana ramka na szybie · wypustki na chodniku · kwadrat na
> tubce pasty · metka materaca · zakrętka przy butelce · naklejka na bananie · alejka
> z jajkami · strzałka przy wskaźniku paliwa · dziura w oknie samolotu · zegar, który sam
> uruchamiasz · blokada na stacji paliw · żółte światło · numer na dnie butelki

Osiemnaście tematów. **Jeden kształt: zwykły przedmiot z oznaczeniem, za którym stoi norma.**
Wyjątek jest dokładnie jeden — *„The Fossil of a Vote"* (zakleszczone głosowanie), i to jest
ten, który sam nazwałeś najlepszym z serii.

Trzy tytuły to ten sam szablon: *„The Number on the Bottom of the Bottle **Was Never Talking
to You**"*, *„The Square on the Toothpaste Tube **Was Never Talking to You**"*, *„The Tag **Is
Not Talking to You**"*. Cztery kolejne to jego wariant: *„is doing a job"*, *„are doing thermal
work"*, *„is not the one deciding"*, *„is doing exactly what it was told"*.

A ostatni zrzut skauta (`data/cache/scout.json`) to sześć propozycji, sześć na sześć
przedmiotów, w tym **dwie powtórki już opublikowanych artykułów**: *„The Dotted Border On The
Windshield"* (= artykuł 0036) i *„The Triangle On The Plastic"* (= artykuł 0025).

To nie jest problem „model jest mało kreatywny". To jest **maszyna, która ma jeden tryb pracy
i wszystkie jej zabezpieczenia pilnują, żeby w nim pozostała**.

## 1.2. Mechanizm 1 — zasada „nic nie blokuje" jest zastosowana dokładnie tam, gdzie jej własne uzasadnienie działa na odwrót

Zasada nadrzędna I.2 brzmi: *„Zablokowany artykuł to czysta strata 1,30 USD researchu i zero
informacji w zamian."* To jest dobry argument — **po** opłaceniu researchu.

Skaut kosztuje **$0,0183** średnio (rozdział VI, tabela etapów: 7 wywołań, $0,1277). Pełny
artykuł kosztuje **$0,7318**. Czyli:

| decyzja | koszt odrzucenia | koszt przepuszczenia złego |
|---|---|---|
| odrzucić kartę dowodową po dyskoverii | $1,30 straty | jeden słaby tekst |
| **odrzucić listę sześciu tematów** | **$0,02** | **$0,71 + jeden słaby tekst** |

Odrzucenie na etapie skauta jest **trzydzieści sześć razy tańsze** niż tekst, który z niego
powstanie. A mimo to `scout()` **nie ma ścieżki odrzucenia w ogóle**: liczy `nosny`,
`na_artykul`, `precedensy`, `zasieg`, sortuje — i oddaje listę. `pick_topic` bierze
`ranked[0]`. Nie ma miejsca, w którym system może powiedzieć „ta szóstka jest do niczego,
zamów następną".

**Zasada uzasadniona ekonomią została przeniesiona tam, gdzie ekonomia mówi coś odwrotnego.**
To jest najważniejsze zdanie w tym raporcie.

> **Naprawa.** Jeden warunek w `run.py`, przed dyskoverią:
> ```python
> for proba in range(config.PRZEBIEGOW_SKAUTA):        # np. 3
>     topics = stages.scout(conn, run_id, args.topics)
>     if sum(1 for t in topics if t["na_artykul"]) >= config.MIN_ARTYKULOWYCH:
>         break
>     print("  [skaut] %d/%d tematow artykulowych — zamawiam nowa liste"
>           % (sum(1 for t in topics if t["na_artykul"]), config.MIN_ARTYKULOWYCH))
> ```
> Trzy próby to $0,055 — **7,5% kosztu artykułu**. Ostatnia próba idzie dalej niezależnie od
> wyniku, więc zasada „artykuł powstaje zawsze" zostaje nienaruszona: nie blokujemy, tylko
> **kupujemy sobie trzy losowania zamiast jednego**.
>
> **Test z kontrdowodem:** podaj listę sześciu tematów z `na_artykul=False` i sprawdź, że
> funkcja woła skauta drugi raz; potem tę samą listę z dwoma `True` i sprawdź, że **nie
> woła**. Bez drugiej połowy test nie odróżnia wersji.

## 1.3. Mechanizm 2 — miernik artykułowości jest zawsze fałszywy, więc de facto nie istnieje

```python
t["na_artykul"] = (t["ile_precedensow"] >= config.PRECEDENSOW_NA_ARTYKUL   # 2
                   and t["duzy_zasieg"])                                    # AN_INDUSTRY|A_COUNTRY
```

Dokument sam podaje wynik: **0 z 10**. Kryterium spełnione przez zero procent kandydatów nie
różnicuje niczego — w kluczu sortowania `pick_topic` jest to stała.

Klucz wygląda tak:

```python
return (nosny(a),            # True dla wszystkich (broken_belief >= 5 slow wystarcza)
        artykulowy(a),       # False dla wszystkich
        wlasny_ranking(a),   # <- to jedyne, co realnie decyduje
        swiezy(a), watki(a), waga[depth], confidence, expected_primary_sources)
```

Czyli o wyborze tematu decyduje **ranking modelu wśród sześciu równie płytkich propozycji**.
System ma dwa kryteria jakości artykułowej i oba są w praktyce wyłączone.

Dodatkowo — **docstring `swiezy` kłamie o własnej pozycji**:

> *„TO JEST NAJWAŻNIEJSZY KLUCZ PO NOŚNOŚCI i powód, dla którego ranking w ogóle
> przepisano."*

W kodzie `swiezy` jest **czwarty**, za `artykulowy` i za `wlasny_ranking`. Dwa docstringi
w tej samej funkcji roszczą sobie prawo do pozycji drugiej. To jest ta sama klasa błędu,
którą dokument tropi u innych (`gates.py` „cztery bramki, które blokują") — tylko nikt jej
nie zauważył tutaj.

> **Naprawa.** Kryterium, które nigdy nie jest spełnione, jest **informacją, nie sortowaniem**.
> Wypisz je głośno i zamień w warunek ponowienia z §1.2. Docstring `swiezy` — poprawić albo
> przesunąć klucz; jedno z dwóch, świadomie.

## 1.4. Mechanizm 3 — twardy wymóg promptu nie jest sprawdzany przez ani jedną linię kodu

`prompts/skaut.md` mówi wprost:

> **At least half your list must be `SYSTEM_UNDER_TEST`, and at least three of them must
> carry two or more precedents each. Keep at least two `BROKEN_BELIEF` as well.**
> *This is a hard requirement, not a preference.*

`grep` po całym repozytorium: **zero linii, które to liczą.** `scout()` wylicza `ma_stawke`
dla pojedynczego tematu, ale nigdy nie pyta, ilu tematów w liście to `SYSTEM_UNDER_TEST`.
Model może oddać sześć przedmiotów — i oddaje — a system tego nie odnotowuje nawet w logu.

To jest tym bardziej bolesne, że projekt **sam odkrył tę regułę i zapisał ją w kodzie**, przy
restacku:

> *„Prompt tego zakazuje, ale zakaz w prompcie już raz przegrał z modelem przy szkielecie
> artykułu — więc tu sprawdza to także kod."*

Reguła została wyciągnięta z bolesnego doświadczenia i wpięta w **jedno zdanie dopisku do
cudzej notki**, a nie w najważniejszy wymóg w całym systemie.

> **Naprawa.** Sześć wierszy w `scout()`, po pętli obliczeniowej:
> ```python
> pod_probe = sum(1 for t in topics if t.get("ma_stawke"))
> z_historia = sum(1 for t in topics if t["ile_precedensow"] >= 2)
> if pod_probe < len(topics) // 2 or z_historia < 3:
>     print("  [skaut] LISTA NIE SPELNIA KONTRAKTU: %d/%d pod probe, %d z historia"
>           % (pod_probe, len(topics), z_historia), flush=True)
>     raise KontraktSkauta(...)      # lapane przez petle ponowien z 1.2
> ```

## 1.5. Mechanizm 4 — `depth` to ostatnia nieweryfikowana samoocena modelu, i to ona ustawia długość artykułu

Cały projekt stoi na zasadzie: *„Oceny liczbowe modelu degenerują się do jednej wartości —
sprawdzone trzy razy na trzy różne sposoby."* Siedem ocen skauta zostało z tego powodu
usuniętych. Ale **jedna została** — `depth` z odsiewu, w trzech kubełkach zamiast we floacie.

`wykonalnosc.md` definiuje przy niej **sprawdzalny warunek**:

> *Judging RICH is a claim you should be able to back. **Either name the parallels in
> `parallels` — two of them, or it is not RICH by that route** — or point at the three-plus
> threads the topic already carries.*

Kod **nie sprawdza żadnego z dwóch**. `parallels` figuruje w `test_martwe_sygnaly.py:89` na
liście dozwolonego rusztowania z uzasadnieniem *„zmusza do UZASADNIENIA oceny RICH; sama
ocena jest czytana"*. To uzasadnienie jest błędne: prompt nie prosi o uzasadnienie dla
higieny myślenia — prompt **stawia warunek** i sam mówi, kiedy jest niespełniony.

Skutek jest mechaniczny i prowadzi prosto do „miałkości":

```
depth = RICH  →  dlugosc_dla("RICH") = 1075 slow  →  pisarz dostaje polecenie napisania 1075 slow
```

Przy braku `depth` (`run.py:908`: `str(verdict.get("depth") or "RICH").upper()`) też wychodzi
RICH. W `data/cache/feasibility.json` **wszystkie sześć ocen ma `depth: null`** — czyli
w zapisanym przebiegu ten sygnał w ogóle nie dotarł, a artykuł i tak dostał 1075 słów.

I to jest dokładnie wada, którą `wykonalnosc.md` opisuje jako powód swojego istnienia:

> *„It was stretched to eleven hundred words by restating the mechanism three times, spending
> three paragraphs on what the evidence did not say, and narrating its own research."*

Prompt zna chorobę, opisuje ją, prosi model o diagnozę — i wyrzuca odpowiedź.

> **Naprawa — trzy wiersze, wzór już istnieje w kodzie.** `bibliotekarz` robi dokładnie to,
> czego tu brakuje: *„Model proponuje, KOD weryfikuje"* — `if len(czlonkowie) >= 2 and
> len(dziedziny) >= 2`. Ta sama forma:
> ```python
> for a in assessments:
>     if str(a.get("depth", "")).upper() != "RICH":
>         continue
>     parallels = a.get("parallels") if isinstance(a.get("parallels"), list) else []
>     watki = temat(a).get("ile_watkow", 0)
>     if len(parallels) < 2 and watki < 3:
>         a["depth"] = "SINGLE"
>         a.setdefault("uwagi_kodu", []).append(
>             "RICH bez pokrycia: %d paraleli, %d watkow — schodze na SINGLE"
>             % (len(parallels), watki))
> ```
> Skutek: temat bez drugiego aktu dostaje **650 słów zamiast 1075**. To sama w sobie jest
> naprawa „miałkości" — tekst przestaje mieć 400 słów do wypełnienia niczym.
>
> Osobno: **`DLUGOSC_WG_GLEBOKOSCI` nie ma klucza `THIN`** (dokument to zna), więc temat
> uznany za najsłabszy dostaje najdłuższą formę. Dopisanie `"THIN": {"cel": 420, "min": 300,
> "max": 560}` to jedna linia.

## 1.6. Mechanizm 5 — pamięć broni formy prozy i pojedynczego faktu, ale nie broni kształtu tematu

Zestawienie tego, czego system pilnuje, jest samo w sobie diagnozą:

| co się nie może powtórzyć | mechanizm | siła |
|---|---|---|
| szkielet prozy | `gates.odcisk_formy` — 6 cech, próg 5/6, 4 ostatnie teksty | mocna |
| pojedynczy fakt w notce | `zuzyte_fakty.json` — 180 wpisów | mocna |
| pierwsze słowo notki | `ostatnie_otwarcia` + sortowanie kandydatów | mocna |
| publikacja, u której komentujemy | `gdzie_komentowalismy.json`, 4 dni | mocna |
| formułka otwierająca restack | `_FORMULKI_RESTACKA`, 6 wzorców | mocna |
| **kształt tematu artykułu** | **brak** | — |

Jedyna obrona to `recent_angles` → `{history_json}`: **pięć tytułów tematów** plus tytuły
z `promocja.json`. Prompt mówi *„do not repeat or paraphrase any of them, and do not stay in
the same subject area"* — i model wykonuje to **dosłownie**: proponuje inny przedmiot.
„Subject area" czyta jako dziedzinę (samochody vs jedzenie), nie jako kształt.

**Dowód rozstrzygający:** skaut zaproponował *„The Dotted Border On The Windshield"*, mając
w dorobku artykuł *„The Dotted Border On A Car Windscreen"*. To nie jest ten sam kształt —
to jest **ten sam przedmiot**, a pamięć go nie zauważyła, bo miała okno pięciu pozycji
i porównywała napisy.

Projekt **odkrył tę regułę na poziomie prozy** i zapisał ją tak, że nie da się jej nie
zauważyć:

> *„Powtarzalna FORMA zdradza maszynę tak samo jak powtarzana TREŚĆ."*

Zdanie jest prawdziwe o jeden poziom wyżej, niż zostało zastosowane. Czytelnik, który
przeczyta trzy teksty pod tytułem „X Was Never Talking to You", widzi maszynę — niezależnie
od tego, jak różne są ich akapity.

> **Naprawa — `gates.odcisk_tematu()`, analogia 1:1 do `odcisk_formy`.** Zgrubne cechy, nie
> ocena:
> ```python
> def odcisk_tematu(t: dict) -> dict:
>     tytul = (t.get("title") or "").lower()
>     return {
>         "rodzaj": str(t.get("kind") or "").upper(),          # BROKEN_BELIEF / SYSTEM_UNDER_TEST
>         "zasieg": str(t.get("scale") or "").upper(),
>         "nosnik": ("oznaczenie" if re.search(
>                        r"\b(mark|symbol|number|code|label|tag|sticker|stamp|dot|arrow"
>                        r"|square|triangle|digit)\b", tytul) else
>                    "procedura" if re.search(
>                        r"\b(what happens|when|fails?|cannot|deadlock|refuses?)\b", tytul)
>                    else "inne"),
>         "ma_historie": t.get("ile_precedensow", 0) >= 2,
>     }
> ```
> Cztery cechy, próg 3/4 wobec **dwunastu** ostatnich tematów (nie pięciu — bo tu okno musi
> obejmować cały dorobek, inaczej powtórka wraca po sześciu tekstach). Trafienie **nie
> blokuje** — dopisuje do `{history_json}` zdanie, którego dziś nigdzie nie ma:
>
> > *You have published eleven articles. Ten of them were an ordinary object with a marking
> > on it, and the last four had the same title shape. Propose nothing of that shape.*
>
> **Test z kontrdowodem:** dwa tematy o tym samym kształcie → zgłoszone; temat
> `SYSTEM_UNDER_TEST` po serii przedmiotów → **milczy**. Bez drugiej połowy bramka krzyczałaby
> zawsze.

## 1.7. Mechanizm 6 — treść samego promptu uczy przedmiotów

Prompt skauta ma 436 wierszy i mówi rzecz właściwą: *„The object is the easiest and it is also
the most exhausted. Prefer the other two."* Ale **jego przykłady mówią coś innego**:

| sekcja | przykłady |
|---|---|
| „Strong, because the belief is real and wrong" | żółte światło · stacja paliw · żółty autobus szkolny — **3/3 przedmioty** |
| „Dead, because there is no belief to break" | symbol na kosmetykach · aneks do rozporządzenia · latarnie morskie — **3/3 przedmioty** |
| `SYSTEM_UNDER_TEST` — „Examples of the shape" | *„What happens to trading when a market falls far enough"* itd. — **5 zdań abstrakcyjnych, ani jednego wypełnionego kompletu pól** |

Jedyny konkretny, „dotykalny" przykład drugiego rodzaju to konklawe — i pojawia się on jako
**anegdota w prozie**, nie jako wypełniony obiekt JSON. Tymczasem `precedents` dostaje pełny
worked example z wcięciami i etykietami pól.

`wykonalnosc.md` powtarza ten sam wzorzec o poziom niżej: wzorzec sukcesu = **okno samolotu**,
wzorzec porażki = **symbol na kosmetykach**. Oba są przedmiotami. Model uczący się z tego
promptu dowiaduje się, że różnica przebiega **wewnątrz kategorii „przedmiot"**.

Do tego dochodzi efekt świeżości: **ostatnie 40 wierszy** promptu to instrukcja rankingu
(`most_written_about` / `least_written_about` / `richest` / `thinnest`) — czyli rzecz, którą
model przeczyta ostatnią, jest o **porządkowaniu listy, którą już wymyślił**, a nie o tym,
z czego ma ją zrobić.

> **Naprawa — nic w kodzie, sama redakcja promptu:**
> 1. Wstaw **dwa pełne, wypełnione obiekty JSON** typu `SYSTEM_UNDER_TEST` — z `the_moment`,
>    `open_outcome`, `governing_record` i dwoma `precedents` — dokładnie w tym samym formacie,
>    w jakim dziś stoi worked example dla `precedents`. Model imituje konkret, nie abstrakcję.
> 2. Zamień jeden z trzech przykładów „Strong" na **procedurę, przez którą czytelnik został
>    przeprowadzony** (reklamacja, odwołanie, kontrola na lotnisku) — bo sam prompt mówi
>    „Prefer the other two", a nie pokazuje ani jednego.
> 3. Przenieś twardy wymóg mieszanki (`at least half`) **na koniec promptu**, tuż przed
>    kontraktem JSON. Dziś stoi w środku, w wierszu ~400 z 436.

## 1.8. Mechanizm 7 — trzy z czterech kanałów podaży materiału są odłączone

`grep` po wywołaniach w kodzie produkcyjnym (bez `tests/`):

| podsystem | funkcje | wywołań |
|---|---|---|
| Federal Register | `korpus_fedreg`, `kandydaci_z_fedreg` | **0** |
| indeks kandydatów | `wez_kandydatow`, `stan_indeksu` | **0** (zapis `dopisz_kandydatow` — 1) |
| bank notek | `wez_z_banku_notek`, `dopisz_do_banku_notek`, `stan_banku_notek` | **0** |
| plan tygodnia | `plan_tygodnia` | **0** |
| bank fragmentów | `bank_fragmentow` | 1 (żyje) |

Indeks kandydatów jest **tylko do zapisu**: kod płaci za wyszukiwanie, zapisuje wynik do
`indeks_kandydatow.json` i nigdy stamtąd nie czyta — mimo komentarza obiecującego, że
„zasila indeks na tygodnie". Bank notek jest martwy w **obie** strony. Federal Register —
jedyny kanał, który dostarcza materiał **spoza pamięci modelu** — nie jest wołany przez
żadną ścieżkę przebiegu.

Czyli: jedynym realnym źródłem tematów artykułowych jest **pamięć modelu, odpytywana od zera
w każdym przebiegu**. A pamięć modelu, jak trafnie pisze sam prompt, *„is the most
written-about and therefore the most available"* — czyli z definicji zwraca to, czego jest
najwięcej. Przedmioty z oznaczeniami.

Dokument prezentuje wszystkie te podsystemy w rozdziale II jako części systemu, bez
adnotacji, że nic ich nie woła. To jest **dokładnie ta klasa błędu, którą `test_martwe_sygnaly`
miał wyłapywać** — tyle że ten test szuka martwych *pól JSON* i martwych *stałych w config.py*,
a nie martwych *funkcji*.

> **Naprawa.** Rozstrzygnąć każdy z osobna, jawnie: albo wpiąć, albo usunąć, albo oznaczyć
> `# NIEUZYWANE:` z powodem — tak jak potraktowano `BEST_NOTE_HOURS`. Trzecia opcja jest
> w porządku, cicha martwota nie. Do `test_martwe_sygnaly.py` dołożyć czwartą sieć: **funkcja
> publiczna bez wywołania poza testami**, z tą samą listą uzasadnionych wyjątków.
>
> Osobno, i to jest najważniejsze dla tematów: **Federal Register to jedyny mechanizm w tym
> systemie, który mógłby przełamać pętlę pamięci modelu.** Preambuły przepisów, w których
> regulator odpowiada na zastrzeżenia, to jest dokładnie „blizna" z promptu skauta — tylko
> udokumentowana, a nie przypomniana. Wpięcie go jako **drugiego, równoległego źródła
> tematów** (nie zamiast skauta, obok) jest w moim przekonaniu największą pojedynczą dźwignią
> w całym projekcie.

## 1.9. Pętla, którą te siedem mechanizmów tworzy

```
pamiec modelu -> przedmioty  (bo brak podazy z zewnatrz, §1.8)
   -> brak wymuszenia mieszanki  (§1.4)
   -> miernik artykulowosci zawsze False  (§1.3)
   -> decyduje ranking modelu wsrod szesciu przedmiotow
   -> brak sciezki odrzucenia  (§1.2)
   -> depth=RICH bez pokrycia -> 1075 slow z cienkiego materialu  (§1.5)
   -> artykul o przedmiocie z oznaczeniem
   -> trafia do recent_angles jako TYTUL  (§1.6)
   -> skaut widzi 5 tytulow, proponuje INNY przedmiot
   -> [powrot na gore]
```

Żaden pojedynczy element nie jest zepsuty. Zepsuty jest **brak sprzężenia zwrotnego na
poziomie kształtu** — dokładnie ten sam brak, który przy prozie już raz naprawiono
(`odcisk_formy`), i który przy tematach nie został zauważony.

---

# CZĘŚĆ II. Jakość tekstów — pisarz dostaje sprzeczne rozkazy

Drugi zgłoszony ból. Znalazłem trzy rzeczy w `prompts/pisarz.md`, które działają przeciwko
sobie.

## 2.1. Prompt każe zebrać niewiadome w jeden akapit i zaraz zakazuje ich zbierania

**Wiersz 118:**
> **One paragraph. Not two, not three.** *(o akapicie granic)*

**Wiersz 200:**
> **Put each unknown where it arises, alone.** *A collected list of everything the record does
> not settle, arriving near the end, drops the temperature at exactly the point where it should
> be rising.*

To są przeciwstawne polecenia dotyczące tej samej rzeczy: pierwsze mówi „zbierz w jeden
akapit", drugie „nie zbieraj, rozłóż w miejscach powstania". Do tego:

- kontrakt JSON prosi o `limits_paragraph_present: true|false` — czyli **zakłada, że ten
  akapit istnieje** (wersja z wiersza 118);
- bramka `NIEWIADOME_NA_KONCU` **karze** zebrany akapit w ostatniej trzeciej — czyli karze
  dokładnie to, o co prosi wiersz 118;
- bramka `ZAPOWIEDZ_GRANIC` **pilnuje pierwszego zdania** tego akapitu — czyli zakłada, że
  akapit ma istnieć.

Model postawiony przed sprzecznością robi to, co robi zawsze: **spełnia oba polecenia
połowicznie**. Stąd teksty, które mają i zbiorczy akapit, i rozsiane zastrzeżenia — czyli
podwójną dawkę hedgingu. To jest dokładnie objaw, dla którego powstało `BUDZET_ZASTRZEZEN = 1`.

> **Naprawa.** Wybrać jedno i usunąć drugie. Rekomenduję wersję z wiersza 200 (każda
> niewiadoma tam, gdzie powstaje) — bo to ona jest poparta obserwacją z produkcji („drops the
> temperature"), a wersja z wiersza 118 jest reakcją na inny problem (jedna trzecia tekstu na
> zastrzeżeniach), który ta sama zasada rozwiązuje lepiej. Wtedy: usunąć
> `limits_paragraph_present` z kontraktu, przemyśleć `ZAPOWIEDZ_GRANIC`, zostawić
> `NIEWIADOME_NA_KONCU`.

## 2.2. Kotwica długości jest wpisana na sztywno i unieważnia `{target_words}`

`prompts/pisarz.md`, wiersze 5–8 — **czwarte zdanie promptu**:

> **Length: {target_words} words.** *That is the target, not a floor — the two articles this
> publication has approved run **1048 and 1101** words, and neither felt short.*

Ta liczba jest **wpisana na stałe** i wysyłana także wtedy, gdy `{target_words}` wynosi 650.
Model dostaje wówczas: „cel 650 słów, ale nasze zatwierdzone teksty mają 1048 i 1101 i żaden
nie wydawał się krótki". Kotwica psychologiczna wygrywa z liczbą, bo jest **konkretna,
uzasadniona i podana jako precedens redakcyjny**.

Kontrargument leży 100 wierszy niżej („A tight six hundred words is a good article") — czyli
za daleko, żeby konkurować, i bez precedensu.

`config.py` sam opisuje objaw: *„przy »cel 1075, zakres 950-1250« model kotwiczył się przy
górnej granicy (średnia 1212). Sufit obniżony…"* — sufit obniżono, **kotwicę zostawiono**.

> **Naprawa — jedna linia.** Wymienić stałą na pole:
> ```
> **Length: {target_words} words.** That is the target, not a floor. {precedens_dlugosci}
> ```
> gdzie `precedens_dlugosci` dla RICH brzmi jak dziś, a dla SINGLE/THIN: *„A tight six hundred
> words is a complete article; padding to a thousand is the failure this publication watches
> for."*

## 2.3. `min_words` nie dociera do pisarza

`stages.write()` podaje `min_words=dl["min"]` do `_prompt("pisarz.md", ...)`.
Pola w `pisarz.md`: `{card_json} {ile_paraleli} {language} {max_words} {ruch_koncowy_nazwa}
{ruch_koncowy} {style_examples} {style_negative} {style_positive} {target_words}`.

**`{min_words}` nie ma.** `str.format` ignoruje nadmiarowe kwargi bez słowa — więc dolna
granica długości (480 dla SINGLE) **nie istnieje z punktu widzenia modelu**, mimo że kod ją
liczy i przekazuje. Do kompletu: `run.py` wypisuje w logu `config.MIN_WORDS` (globalne 950),
czyli trzecią liczbę, która nie jest ani tą podaną, ani tą użytą.

To razem z §2.2 znaczy, że **z trzech liczb opisujących długość do modelu dociera
jedna i pół**.

## 2.4. Dwa pola kontraktu pisarza są martwe

`numbers_used` i `limits_paragraph_present` nie są czytane przez żadną linię (dokument to
zna). `numbers_used` figuruje w `test_martwe_sygnaly` jako rusztowanie z uzasadnieniem
„bramka i tak liczy je sama" — ale to znaczy, że model **wypisuje listę wszystkich liczb
w tekście** i wynik idzie do kosza, przy każdym artykule. Przy 1075-słowowym tekście to
realne tokeny wyjścia u modelu po **$50/mln**.

---

# CZĘŚĆ III. Wady, których dokument nie zna — zweryfikowane

Wszystkie poniższe otworzyłem i sprawdziłem w źródle. Numery wierszy z 2026-08-23.

## 3.1. Krytyczne

**A. `--stop-after` nie zatrzymuje dwóch etapów, a z `--wyslij` artykuł idzie na żywo.**
`STAGES` ma dziesięć nazw; `run.py` ma **osiem** sprawdzeń `if args.stop_after == stage:`
(wiersze 777, 796, 823, 868, 886, 918, 970, 1004). Dwa etapy nie mają odpowiednika. Wywołanie
`run.py --stop-after review --wyslij`, czyli naturalny sposób powiedzenia „chcę zobaczyć
recenzję i nic więcej", **publikuje artykuł na Substacku**. `argparse` przyjmuje tę wartość
bez zastrzeżeń, bo `choices=STAGES`.
*Naprawa:* asercja przy starcie — `assert set(STAGES) <= zebrane_punkty_stopu`, albo
przynajmniej test porównujący liczbę wystąpień z `len(STAGES)`.

**B. Ucięta odpowiedź księguje najdroższe wywołanie w systemie jako $0,00.**
`llm.py`: `Truncated` jest podnoszone **po** `stream.get_final_message()`, czyli po zapłaceniu
i przy znanym `message.usage`. Ścieżka błędu w `call()` zapisuje:
```python
db.record_call(..., tokens_in=0, tokens_out=0, cost_usd=0.0, price_verified=0, ok=0, ...)
```
z komentarzem *„Koszt nieudanego wywołania bywa nieznany"*. Dla `Truncated` i `refusal` jest
**znany** i zostaje wyrzucony. Skutki są dwa i drugi jest gorszy:
1. `write` na Fable to do $0,65 — zapisane jako zero;
2. `_preflight` liczy sufit przebiegu przez `SUM(cost_usd) WHERE run_id = ?`, więc **nie widzi
   tych pieniędzy** — a `run.py` natychmiast po awarii pisarza powtarza go na Opusie.
   Przebieg może wydać ponad `RUN_LIMIT_USD` i nie zauważyć.
*Naprawa:* przekazać znane `usage` do wyjątku i zaksięgować je z `ok=0`.

## 3.2. Poważne

**C. `juz_sie_odezwalismy` jest fail-open dla cudzych artykułów — wbrew dokumentowi.**
Dokument §13.3 przedstawia tę funkcję jako fail-closed („nie wiem, czyli nie ryzykuję")
i cytuje tylko gałąź `if not moje_id: return True`. Ale niżej:
```python
post = api_json(page, f"/api/v1/posts/{slug}", baza=czyja)
if not isinstance(post, dict) or not post.get("id"):
    return False          # <- "nie wiem" znaczy tu "smialo, pisz"
```
Przy niedostępnym API cudzej publikacji agent **dopisuje drugi komentarz pod tekstem, pod
którym już pisał** — czyli robi dokładnie to, przed czym ta funkcja ma bronić i co dokument
nazywa „najostrzejszym sygnałem automatu, jaki można dać".

**D. `ile_dzis_wystawione` przy błędzie oddaje `notki: 0` — czyli pełną normę drugi raz.**
Docstring: *„po restarcie albo przerwanym przebiegu księgowość się rozjeżdża i agent wystawia
dzienną normę drugi raz"* — i dokładnie to robi jej własna obsługa błędu:
```python
except Exception as exc:
    print(f"  (nie policzylem dzisiejszych: {type(exc).__name__})", flush=True)
    return wynik            # wynik["notki"] == 0
```
Jedna nieudana odpowiedź API = pięć notek ponad normę.

**E. Naprawa obserwacji i subskrypcji z 20 sierpnia jest w połowie martwa.**
`run.py` odejmuje teraz `juz.get("follow", 0)` i `juz.get("subskrypcje", 0)`. Ale `juz`
pochodzi z `ile_dzis_wystawione` → `z_dziennika_dzis`, a tam:
```python
nazwa = {"komentarz": "komentarze", "polubienie": "lajki", "restack": "restacki"}
```
Rodzajów `"obserwacja"` i `"subskrypcja"` **nie ma**, więc oba `get` zwracają zawsze zero.
Dzielenie przez `zostalo_przebiegow` faktycznie usuwa trzykrotność — ale odejmowanie „ile już
dziś" jest atrapą. Przy przebiegu powtórzonym po awarii limit miesięczny znów przecieka,
a każda subskrypcja to poczta do skrzynki właściciela.

**F. `WORST_NOTE_HOURS` jest opisane jako martwe, a wycisza agenta dwie godziny dziennie.**
`config.py:1069` — komentarz: *„UWAGA: CZTERY PONIŻSZE STAŁE NIE SĄ UŻYWANE PRZEZ ŻADNĄ LINIĘ
KODU"*. `config.py:341`:
```python
if g in WORST_NOTE_HOURS:
    return False, f"{g:02d}:00 u czytelnikow — najgorsze okno wg researchu"
```
Stała blokuje publikację codziennie w 12:00–13:59 ET. `test_martwe_sygnaly.py:96` **utrwala
fałszywy opis**, a dokument powtarza go w VIII.1 poz. 5. To jest odwrotność błędu, który
projekt sam ściga („martwa stała czyta się jak gwarancja, której nie ma") — tutaj **żywa stała
jest udokumentowana jako martwa**, więc nikt nie wie, że okno publikacji ma dziurę.

**G. SIGTERM w ścieżce artykułu nie zostawia śladu.**
`_sygnal_ma_zostawic_slad` zamienia SIGTERM na `KeyboardInterrupt`, który dziedziczy po
`BaseException`, nie po `Exception`. Ścieżka dnia łapie `except BaseException` (`run.py:738`)
— poprawnie. Ścieżka artykułu łapie `except Exception`. Czyli przebieg artykułowy ubity przez
systemd zostaje w bazie jako `RUNNING` na zawsze, aż posprząta go `alarm.zawieszone()` po
trzech godzinach. Cały mechanizm „SIGTERM ma zostawić ślad" działa w jednej z dwóch ścieżek.

**H. `ile_przebiegow_zostalo` robi odwrotność tego, co obiecuje docstring.**
> *„Przebieg PRZERWANY też się nie liczy, i to jest cała pointa: gdy jeden padnie, kolejne
> widzą, że **zostało ich mniej**, i dobierają **więcej**."*

Kod: `max(1, PRZEBIEGOW_DZIENNIE - zamkniete)`, gdzie `zamkniete` liczy tylko `DONE`. Przebieg
`FAILED` **nie powiększa** `zamkniete`, więc `zostalo_przebiegow` jest **większe**, a
`na_teraz = round(v / zostalo_przebiegow)` — **mniejsze**. Po awarii pierwszego przebiegu
kolejne biorą po jednej trzeciej normy zamiast po połowie, i dzień kończy się z jedną trzecią
niewykorzystaną. Dokładnie ten skutek, przed którym docstring ostrzega.

**H2. `CHEAP_MODE` kieruje najdroższy etap na najdroższy model.**
```python
if CHEAP_MODE:
    MODEL_FOR = {k: (CLAUDE if k == "discovery" else DEEPSEEK) for k in MODEL_FOR}
```
`CLAUDE` to `claude-opus-5` ($5/$25 za mln + $10/1000 wyszukiwań). Dyskoveria to etap
o zmierzonych **219 151 tokenach wejścia** i 26 wyszukiwaniach w przebiegu 25. Na Opusie:
~$1,10 za samo wejście + $0,26 za wyszukiwania. Czyli „tryb tani", reklamowany w dokumencie
jako *„przebieg kosztuje wtedy grosze zamiast ~1 USD"*, ma jeden etap droższy niż cały normalny
przebieg ($0,73). Instrukcja odtworzeniowa (rozdział VI §10 krok 6) każe go użyć jako
weryfikacji przed pierwszym płatnym uruchomieniem.

## 3.3. Średnie i drobne — zweryfikowane

| # | rzecz | gdzie |
|---|---|---|
| I | `_precedens_ok` ma **dwa literalne znaki 0x08** zamiast `\b`: `r"...\|nic\x08\|brak\x08)"` — warianty polskie są martwe | `stages.py:2862` |
| J | Martwe funkcje bez żadnego wywołania poza testami: `sesje_dnia`, `plan_tygodnia`, `korpus_fedreg`, `kandydaci_z_fedreg`, `wez_kandydatow`, `stan_indeksu`, `wez_z_banku_notek`, `dopisz_do_banku_notek`, `stan_banku_notek` | `stages.py` |
| K | Docstring `swiezy` twierdzi, że jest kluczem drugim; jest czwarty | `stages.py` (`pick_topic`) |
| L | `recent_angles` ignoruje własny `limit` dla `promocja.json` — lista zakazanych kątów rośnie bez końca i pcha do promptu cały dorobek | `stages.py:53` |
| M | Kopia testowa broni **obecnością ręcznie tworzonego pliku** — `TO_JEST_KOPIA_TESTOWA` **nie istnieje w tej kopii roboczej**, więc `--wyslij` opublikuje stąd na żywo | `run.py:65` |

---

# CZĘŚĆ IV. Dokument jako artefakt — co z nim jest nie tak

Zamówiłeś ocenę architektury, a dokument jest dziś częścią architektury tego projektu: ma
544 KB, jest większy niż kod, który opisuje, i deklaruje, że **z niego da się odtworzyć bota
od zera**. To jest twierdzenie sprawdzalne i miejscami nieprawdziwe.

## 4.1. Główna obietnica metodologiczna jest naruszona, i to w miejscu, które ukrywa błąd

> *„Kod jest wklejany **dosłownie ze źródeł**, nie przepisywany."* (§0)

Rozdział III cytuje `_precedens_ok` jako:
```python
return not re.match(r"^\W*(nothing|none|no\s|nic|brak)", zmiana, re.I)
```
W źródle (`stages.py:2862`) stoi:
```python
return not re.match(r"^\W*(nothing|none|no\s|nic\x08|brak\x08)", zmiana, re.I)
```
Dokument pokazuje wersję **wyczyszczoną**. Nie jest to złośliwość — to skutek przejścia kodu
przez edytor przy pisaniu. Ale konsekwencja jest dokładnie taka, przed jaką dokument
ostrzega w innych miejscach: **czytelnik dostaje kod, który wygląda na poprawny, i nie ma jak
zobaczyć usterki.**

## 4.2. Załączniki rozjechały się z tekstem głównym

Trzy potwierdzone rozjazdy (znalezione przez agenta, sprawdzone przeze mnie na próbie):

- Załącznik VII wkleja `llm._cost` **sprzed naprawy** — bez `"cache": stawka["cache"]` —
  czyli dokładnie ten błąd, który rozdział VI dwa rozdziały wcześniej ogłasza jako
  **NAPRAWIONY 2026-08-20**. Ten sam dokument w dwóch miejscach mówi „naprawione" i pokazuje
  niepoprawione.
- Załącznik VII wkleja `pick_topic` w wersji z **podwojoną** funkcją `artykulowy`, którą
  rozdział III zgłasza jako bieżącą wadę — a w kodzie jest jedna definicja. Wada została
  naprawiona, dokument opisuje ją jako otwartą i dowodzi tego nieaktualnym kodem.
- Załącznik A podaje `prompts/skaut.md` jako „359 wierszy" i wkleja wersję krótszą od pliku
  (436 wierszy) — **brakuje m.in. twardego wymogu połowy listy `SYSTEM_UNDER_TEST`**, czyli
  wymogu, o którym mowa w §1.4 tego raportu.

## 4.3. Gwarancja „nie da się rozjechać z kodem" jest napisem

Rozdział II otwiera się zdaniem: *„Wygenerowany ze źródeł przez `ast`, więc nie da się go
rozjechać z kodem."* W `dokumentacja-zrodla/sklej.py` to zdanie jest **stałym stringiem
w nagłówku**; generatora `ast` w repozytorium nie ma, a „generowane" części leżą jako
statyczne `.md`. To jest ta sama choroba co martwa stała: **gwarancja, która czyta się jak
mechanizm, a jest tekstem.**

## 4.4. Rozmiar dokumentu jest sam w sobie ryzykiem

544 KB na 17 246 wierszy kodu to około **32 bajty dokumentacji na bajt kodu**. Skutki widać:

- każda naprawa wymaga aktualizacji w kilku miejscach (rozdział tematyczny + lista zbiorcza
  + załącznik + tabela wad), a zaktualizowane jest zwykle jedno;
- rozdziały IV i VI zaczynają się już od noty *„opisuje stan zastany… pięć wad naprawiono
  tego samego dnia"* — czyli dokument sam przyznaje, że jest historią, nie stanem;
- lista wad w VIII jest oznaczona jako „kompletna na dzień 2026-08-20", a §7 tego raportu
  zawiera 94 kandydatów spoza niej.

> **Co bym zrobił.** Rozdzielić na trzy artefakty o różnym tempie starzenia:
> 1. **`DLACZEGO.md`** (~40 KB, zmienia się rzadko) — mandat, trzy zasady, historia błędów
>    z uzasadnieniami. To jest najcenniejsza część i jedyna, której nie da się odtworzyć
>    z kodu. Zostaje ręczna.
> 2. **`STAN.md`** (generowany, nigdy ręcznie) — spis modułów, stałych, sufitów, wywołań,
>    martwych funkcji, liczby z produkcyjnej bazy. Skrypt istnieje w zalążku (`sklej.py`);
>    dokończyć go i **usunąć z repozytorium ręczne kopie tych sekcji**, żeby nie było czego
>    rozjeżdżać.
> 3. **`WADY.md`** — jedna lista, jedno miejsce, każda pozycja z datą i statusem. Dziś ta sama
>    wada występuje w rozdziale tematycznym, w liście zbiorczej rozdziału i w VIII, w trzech
>    różnych sformułowaniach i dwóch różnych stanach.
>
> Test na to jest prosty i w duchu projektu: **skrypt, który wyciąga z dokumentu każdy
> odnośnik `plik.py:N` i każdy blok kodu i porównuje ze źródłem.** Oblewa się, gdy dokument
> kłamie. Bez niego rozjazd jest kwestią czasu, nie staranności.

---

# CZĘŚĆ V. Trzy rzeczy, które zmieniłbym u fundamentu

## 5.1. Granica „nic nie blokuje" jest postawiona o jeden etap za wcześnie

Zasada jest słuszna **po wydaniu pieniędzy** i szkodliwa **przed**. Dziś obowiązuje w obu
miejscach, bo została sformułowana jako zasada o artykule, a nie jako zasada o pieniądzach.

> **Sformułowanie, które proponuję:**
> *„Bramka może odrzucić wszystko, za co jeszcze nie zapłacono. Od pierwszego wydanego dolara
> bramki tylko zgłaszają."*
>
> Granica pada między etapem 3 (dyskoveria) a 2 (odsiew). Skaut i odsiew **odzyskują prawo
> mówienia »nie«**, kosztem 2 centów za ponowienie. Wszystko od dyskoverii w górę zostaje jak
> jest. To jest zmiana jednego zdania w `config.py` i pętli w `run.py`, a rozwiązuje
> mechanizmy 1, 2 i 3 z Części I naraz.

## 5.2. System mierzy wolumen i koszt, a nie mierzy wyniku

Dokument ma 10 419 wierszy i **ani jednej liczby o czytelnikach**. Są koszty co do szóstego
miejsca po przecinku, tokeny per etap, trafienia w cache, rozkład wydatków po godzinach UTC —
i zero subskrybentów, zero otwarć, zero informacji o tym, czy którykolwiek z sześciu artykułów
kogokolwiek przyprowadził.

Najbliższe temu jest `alarm.przeglad` („ile odpowiedzi na jedno działanie") — i to jest dobra
miara, ale mierzy **rozmowę**, a nie **wynik**. Konsekwencja jest poważniejsza niż brak
dashboardu: **przy braku miary wyniku każde pytanie „czy to działa" musi zostać rozstrzygnięte
gustem właściciela.** Stąd bierze się to, że „tematy są miałkie" jest dziś odczuciem, a nie
liczbą — i stąd bierze się to, że system nie może sam tego wykryć.

Dokument sam wskazuje, gdzie leży aktywo: *„Lista subskrybentów… przy tempie 6-12 subskrypcji
miesięcznie sto osób to około jedenastu miesięcy pracy systemu."* Ta lista **nie jest nawet
kopiowana** (VI §9: katalog `kopie/` nie istnieje na serwerze).

> **Naprawa, tanio:** ten sam ręczny eksport CSV, który już jest opisany w
> `kopia_subskrybentow.py`, plus **jedna liczba dopisywana do `dziennik.jsonl` przy każdym
> uruchomieniu**: `{"rodzaj": "stan_konta", "subskrybentow": N}`. Po miesiącu masz szereg
> czasowy i możesz zapytać, czy artykuł z „drugim aktem" przyprowadza inaczej niż artykuł
> o oznaczeniu. Dziś nie da się tego zapytać w ogóle.

## 5.3. Reguły są odkrywane raz i wpinane w jedno miejsce

To jest wzorzec przewijający się przez cały ten raport i, moim zdaniem, **główna słabość
metody**, nie kodu:

| reguła odkryta | wpięta w | nie wpięta w |
|---|---|---|
| „zakaz w prompcie przegrywa z modelem — sprawdza też kod" | jedno zdanie restacka | twardy wymóg mieszanki tematów (§1.4) |
| „model proponuje, kod weryfikuje" | grupy bibliotekarza | ocenę `depth`/`parallels` (§1.5) |
| „powtarzalna forma zdradza maszynę" | szkielet prozy | kształt tematu (§1.6) |
| „martwa stała czyta się jak gwarancja" | stałe w `config.py` | martwe **funkcje** (§1.8) i żywe stałe opisane jako martwe (§3.2 F) |
| „kliknięcie to nie dowód" | notka, komentarz, odpowiedź, artykuł | restack, polubienie |
| „fail-closed tam, gdzie koszt błędu jest publiczny" | `juz_sie_odezwalismy` (gałąź tożsamości) | ta sama funkcja, gałąź artykułu (§3.2 C); `ile_dzis_wystawione` (§3.2 D) |

Sześć razy ta sama historia: **reguła jest prawdziwa, została zapisana pięknym komentarzem
i objęła jeden przypadek.**

> **Co bym z tym zrobił.** `test_martwe_sygnaly.py` jest dowodem, że wiesz, jak to
> rozwiązać — to nie jest test jednej usterki, tylko **sieć na klasę**. Ta sama forma dla
> pozostałych reguł:
> - **sieć na „kliknięcie to nie dowód"**: każda funkcja `browser.wystaw_*`/`_klik_*` musi
>   wołać jakieś `potwierdz_*` albo mieć wypisany powód, dlaczego nie może;
> - **sieć na „kod weryfikuje"**: każde pole kontraktu, które steruje liczbą albo długością,
>   musi mieć w kodzie warunek, który potrafi je odrzucić;
> - **sieć na martwe funkcje**: jak w §1.8;
> - **sieć na dokument**: jak w §4.4.
>
> Każda z nich to 40–80 wierszy skryptu z lokalnym `sprawdz()`. Razem mniej niż jeden istniejący
> test — i **to jest jedyna rzecz w tym raporcie, która działa na wady, których jeszcze nie ma.**

---

# CZĘŚĆ VI. Kolejność

Uszeregowane po stosunku „ile to zmienia" do „ile to kosztuje". Pierwsze cztery pozycje
adresują zgłoszony ból.

| # | co | gdzie | praca | co naprawia |
|---|---|---|---|---|
| 1 | weryfikacja `depth` przez `parallels`/`threads` + klucz `THIN` w `DLUGOSC_WG_GLEBOKOSCI` | `stages.pick_topic`, `config.py` | ~15 wierszy | cienki materiał przestaje być rozciągany do 1075 słów (§1.5) |
| 2 | wymuszenie kontraktu skauta + pętla ponowień | `stages.scout`, `run.py` | ~20 wierszy | lista przestaje być 6/6 przedmiotów (§1.2, §1.4) |
| 3 | `gates.odcisk_tematu` + zdanie o dorobku w `{history_json}` | `gates.py`, `stages.recent_angles` | ~40 wierszy | koniec powtarzania kształtu i tego samego przedmiotu (§1.6) |
| 4 | dwa wypełnione przykłady `SYSTEM_UNDER_TEST` + przeniesienie twardego wymogu na koniec | `prompts/skaut.md` | sama redakcja | model przestaje uczyć się przedmiotów z przykładów (§1.7) |
| 5 | usunięcie sprzeczności „jeden akapit / każda niewiadoma osobno" + kotwica długości + `{min_words}` | `prompts/pisarz.md` | sama redakcja | mniej hedgingu, długość zgodna z materiałem (§2.1–2.3) |
| 6 | `--stop-after` dla wszystkich etapów; asercja pokrycia | `run.py` | ~5 wierszy | publikacja przy zatrzymaniu na recenzji (§3.1 A) |
| 7 | księgowanie `Truncated`/`refusal` ze znanym `usage` | `llm.py` | ~10 wierszy | dziura w suficie przebiegu (§3.1 B) |
| 8 | `juz_sie_odezwalismy` → `return True` przy nieczytelnym API; `ile_dzis_wystawione` → nie zerować notek przy błędzie | `browser.py` | 2 wiersze | drugi komentarz pod tym samym tekstem; podwójna norma notek (§3.2 C, D) |
| 9 | `z_dziennika_dzis` uczy się `obserwacja`/`subskrypcja`; `except BaseException` w ścieżce artykułu | `browser.py`, `run.py` | 3 wiersze | (§3.2 E, G) |
| 10 | `WORST_NOTE_HOURS` — rozstrzygnąć: żywa czy martwa, i naprawić komentarz, test **i** dokument | `config.py`, testy, dokument | decyzja | dwie godziny ciszy dziennie, o których nikt nie wie (§3.2 F) |
| 11 | rozstrzygnięcie losu Federal Register i indeksu kandydatów | `stages.py` | dzień pracy | jedyne źródło tematów spoza pamięci modelu (§1.8) |
| 12 | pomiar wyniku: liczba subskrybentów do `dziennik.jsonl` | `kopia_subskrybentow.py` | ~10 wierszy | pierwsza miara, która mówi, czy to działa (§5.2) |
| 13 | rozbicie dokumentu na trzy + test odnośników | dokumentacja | 2–3 dni | koniec rozjazdu dokument↔kod (§4.4) |
| 14 | cztery „sieci na klasę" wzorem `test_martwe_sygnaly` | `tests/` | 2 dni | wady, których jeszcze nie ma (§5.3) |

**Czego bym nie robił:** nie ruszał zasady „artykuł powstaje zawsze" od dyskoverii w górę —
jest dobrze uzasadniona i działa. Nie ruszał anonimowości konta — cena jest opisana w VIII.2
i policzona uczciwie. Nie wracał do trzech wariantów notki — oszczędność $28/mies była dobrą
decyzją i nic w danych jej nie podważa.

---

# CZĘŚĆ VII. Materiał niezweryfikowany

Poniższe zgłosili agenci przeglądający kod; **warstwa weryfikacji nie zdążyła**, więc traktuj
je jako tropy, nie jako ustalenia. Kolejność mniej więcej wg deklarowanej wagi.

**`browser.py`** — potwierdzenie notki i odpowiedzi porównuje czysty tekst z zaszerowanym
zrzutem JSON (wypowiedzi z cudzysłowem raportowane jako niewysłane) · przycisk „Reply"
wybierany po odległości od nazwiska bez warunku kierunku, więc może trafić w przycisk
poprzedniego komentarza · odpowiedź pod artykułem trafia w pierwszą `textarea` w drzewie ·
między odczytaniem treści notki a kliknięciem restacka stoi przerwa 10–30 min, a lokator
`nth(i)` rozwiązuje się dopiero po niej · `uruchom_chrome()` nieosiągalne, brak Chrome cicho
przełącza w tryb bezgłowy · `sprawdz_sesje` nadpisuje plik sesji na podstawie tekstu strony ·
licznik notek pyta kanał profilu bez filtra `types[]=note` · `dopisz_skutki` zamraża liczbę
reakcji z chwili pierwszego zobaczenia · `wystaw_artykul` przy już opublikowanym tekście
wychodzi przed zapisem do promocji.

**`gates.py` / `kanal.py`** — `_akapity` odrzuca akapit zaczynający się od `*`, więc pogrubione
otwarcie omija bramkę `ZAKAZANE_OTWARCIE` · `GESTOSC_BEATOW` milczy przy zerze przekonań ·
`BRAK_ESKALACJI` sprawdza `is True`, więc `"true"` lub `1` wyłącza bramkę · `_META_GRANIC`
dopasowuje podciąg („Recorded", „Resources") · `szukaj_nowych` nie odsiewa naszych własnych
notek · `_wiek_minut` łapie tylko `ValueError`, data bez strefy rzuca `TypeError`.

**`stages.py` / `run.py`** — `unused_evidence` zawiera także fragmenty użyte w artykule, więc
bank może podać cytat już opublikowany · trzy z ośmiu form notek matematycznie nieosiągalne,
sekwencja `(typ, forma)` identyczna każdego dnia · powtórzony `index` w odpowiedzi modelu nie
jest odsiewany · uszkodzony `promocja.json` czytany jako pusta lista i natychmiast nadpisywany ·
`zmiesci_sie` rezerwuje ten sam czas przebiegu dwa razy · zwłoka 0–40 min przed pierwszą notką
nie pyta zegara · `fetch` z `follow_redirects=True` omija `BLOCKED_HOSTS` · ruch końcowy
losowany bez pamięci i nigdzie niezapisywany · `save` wypisuje uwagi jako `repr` słowników.

**`alarm.py` / operacje** — wyciszenie 24 h zderza się z zegarem chodzącym raz na dobę
(co drugi alarm przepada) · `nadaktywnosc` liczy wywołania modelu, nie działania na Substacku ·
restack doliczany do polubień w pomiarze skuteczności · kopia subskrybentów nadpisuje wcześniejszą
z tego samego dnia i zapisuje się z prawami 0644 mimo cudzych adresów e-mail · `test_artykul`
daje się oszukać komentarzem w `requirements.txt` · `test_martwe_sygnaly` uznaje pole za czytane,
gdy jego nazwa wystąpi gdziekolwiek jako napis, i przeszukuje tylko `config.py`.

**Dokument** — 16 z 52 sprawdzonych odnośników `plik.py:N` wskazuje zły wiersz (systematyczne
przesunięcia: −7 w `stages.py`, −9 w `browser.py`, −8 w `config.py`, −45 w `alarm.py`) ·
rozdział II pomija `config.py` i `kopia_subskrybentow.py` · „siedem plików w `tests/platne/`" —
jest ich dziesięć · załącznik B ma stałą zdublowaną, jedną brakującą i 28 wartości uciętych
w połowie literału · załącznik C pokazuje `storage-state-serwer.json` z prawami 0664, podczas
gdy rozdział VI ogłasza naprawę na 0600.
