
## VIII. Znane wady i decyzje otwarte

Lista jest kompletna na dzień 2026-08-20 i celowo stoi w głównym dokumencie,
a nie w przypisach. Każda pozycja ma podaną **przyczynę** i **koszt**, bo
w tym projekcie najdroższe okazały się nie błędy, tylko rzeczy wyglądające na
działające.

### VIII.1. Wady niedomknięte

| # | rzecz | dlaczego to wada | koszt |
|---|---|---|---|
| 1 | jedenaście plików `.py` zamiast dziesięciu | naruszenie mandatu | brak funkcjonalnego |
| 2 | `articles.status` zawsze `SAVED`, `blocked_by` zawsze `NULL` | kolumny sugerują decyzję, której nie ma | mylące przy czytaniu bazy |
| 3 | `feasible` prawdziwe w 6 ocenach na 6 | odsiew nie odrzuca niczego, więc nie jest odsiewem | płacimy za etap, który nie filtruje |
| 4 | `threads` i `already_written` wyrównane do stałej przez model | obchodzone wymuszonym wyborem, **nie naprawione u źródła** | dwa pola bez wartości informacyjnej |
| 5 | `BEST_NOTE_HOURS` i `BEST_NOTE_DAYS` nieużywane | **nasze własne źródła się nie zgadzają**: config mówi 6–8 ET, research z 18 sierpnia 19:00–22:00 UTC (15–18 ET) — dopóki to nie zostanie rozstrzygnięte, nic nie waży godzin | dwie stałe jako zapis ustaleń, wyraźnie oznaczone |
| 5b | ~~`WORST_NOTE_HOURS` nieużywane~~ **NIEPRAWDA — poprawione 23 sierpnia** | stała stała w bloku opisanym jako „nie są używane przez żadną linię kodu", a jest **egzekwowana** przez `config.pora_na_publikacje`: między 12:00 a 13:59 u czytelników agent nie wystawia ani notek, ani komentarzy | kto skasowałby ją jako martwą, dostałby `NameError` w funkcji wołanej na początku **każdego** przebiegu dnia |
| 6 | brak przeglądu materiału już zapisanego | klasyfikacja tylko na wejściu; po zmianie kryteriów w indeksie zostaje materiał ze starych reguł | 20 sierpnia kryteria zmieniły się dwa razy |
| 7 | ~~kolejność bloku komentarzy~~ **ZAMKNIĘTE** | `browser.mozna_komentowac` stoi **przed** pobraniem strony i przed wszystkimi płatnymi krokami | zostaje wąski przypadek: gdy API nie oddaje `write_comment_permissions`, funkcja zwraca `True` i płacimy mimo wszystko |
| 8 | dwie zerowe bazy w `data/` | `agent.db` i `zasiew-produkcji.db`, obie 0 B; żywa baza to `agent-v2.db` — zerowe pliki są pułapką przy diagnostyce i raz już wysłały mnie do pustej bazy | brak funkcjonalnego |
| 9 | ~~skaut nie trafia w kryteria artykułowe~~ **ZAMKNIĘTE 23 sierpnia** | prompt przepisany pod ten próg: zaczyna od tego, **gdzie** szukać (procedura jako blizna po katastrofie, dziewięć gęstych dziedzin), nazywa dwa tryby porażki i pokazuje wzorcowy precedens | pomiar po zmianie: **6 z 10** artykułowych, każdy z dwiema udokumentowanymi awariami |
| 10 | cztery pliki w `prompts/` nie są czytane przez żaden kod | `ROZWOJ_KONTA.md`, `SKAD_BRAC.md`, `ZASADY_NOTEK_I_KOMENTARZY.md`, `po_ludzku.md` — nazwy nie padają w źródłach | to notatki właściciela; generator wypisuje je osobno w ZAŁĄCZNIKU A.2, żeby nie udawały promptów |
| 11 | `EFFORT` dociera do API tylko dla jednego etapu z sześciu | reszta chodzi na DeepSeeku, który tego pokrętła nie czyta; przepięcie go tam odtworzyłoby awarię „rozumowanie zjada budżet odpowiedzi" | `llm.call` mówi o tym raz na proces, więc wpis przestał być cichą ozdobą |
| 12 | żaden przebieg nie chodził jeszcze z naprawą rytmu | `run.rytm` wdrożony 23 sierpnia o 02:41, po ostatnim przebiegu | pierwszy sprawdzian przy najbliższym odpaleniu zegara |

### VIII.2. Decyzje należące do właściciela, nie do kodu

**Godziny wystawiania notek (wada 5).** Zanim cokolwiek zacznie ważyć godziny,
trzeba rozstrzygnąć, którym z dwóch własnych źródeł wierzymy. Nie jest to
usterka do cichego naprawienia.

**Więź parasocjalna a anonimowość.** Literatura o powrotach mówi konsekwentnie,
że czytelnicy wracają **do osoby**: autorzy wpuszczający własną perspektywę
budują więź z człowiekiem, a ci, którzy dają samą treść, budują więź
z informacją — a informacja jest wymienna. To konto świadomie nie jest osobą
(ADR-018). Decyzja jest dobra i nie podważamy jej przy okazji, ale **ma cenę
i tą ceną jest mechanizm powrotu**. Proponowany substytut: rozpoznawalna
**metoda** zamiast osobowości — zawsze mówimy, czego zapis nie rozstrzyga,
i zawsze nazywamy, kto na tym stoi.

**Zaległa kolejka promocji.** Dwa starsze artykuły czekają na swoje trzy notki;
po zmianie na „najświeższy pierwszy" dostaną je z zimnym linkiem. Do decyzji:
zostawić czy wyczyścić.

### VIII.3. Wady naprawione — zapisane, bo klasa błędu wraca

Ta sekcja istnieje, bo każda z tych rzeczy **wyglądała na działającą** i żadna
nie rzucała wyjątku.

| co | jak się objawiało | przyczyna | dowód, że było źle |
|---|---|---|---|
| `cache_hit` wysadzał zapis | grafika „nie powstała (IntegrityError)" | `DEFAULT 0` nie działa przy jawnym `NULL` — wchodzi tylko wtedy, gdy kolumny w `INSERT` nie ma wcale | `ok=1` w **591 wywołaniach na 591**; ścieżka błędu nigdy nie zapisała nic |
| odstęp restacków po ostatnim | agent spał 10–30 min z otwartą przeglądarką po wykonaniu normy | warunek wyjścia sprawdzany na górze pętli, odstęp na dole | po naprawie: **79 ms** między „podane dalej 1/1" a „dzień zamknięty" |
| brak pola komentarza | `TimeoutError` po 15 s, dwa razy jednego dnia | `locator("textarea").first` bierze pierwszą w **drzewie**, nie pierwszą widoczną; API tych postów nie oddaje `write_comment_permissions` wcale | sprawdzone u źródła na obu adresach |
| ranking wybierał cliché | siedem z dwunastu tematów to kanon mythbustingu | `ma_przekonanie` jako **pierwszy klucz**; temat oklepany ma z definicji najostrzejsze „everyone assumes" | po naprawie kanon zniknął w całości |
| `ma_stawke` niewidoczne dla `pick_topic` | tematy drugiego rodzaju wracały na dół | skaut sortował po nośności, `pick_topic` po samym przekonaniu | pięć dobrych tematów nie zostałoby wybranych nigdy |
| blok obserwacji nie chodził | **zero obserwacji przez pięć dni** przy budżecie 30–44/mies | zegar sprawdzają bloki 1–6, lajki i restacki nie; obserwowanie stało za komentarzami | zmierzone na dzienniku |
| prompt formy chodził po zdaniach | **47 „beatów" na 1097 słów** | „przejdź artykuł zdanie po zdaniu" zamiast „w co czytelnik teraz wierzy" | testy tego nie złapały, bo podawałem obserwację ręcznie |
| recenzent gubił własne ustalenia | zdanie oznaczone jako nieoparte, ale niepowtórzone w liście zbiorczej, przepadało | czytaliśmy tylko `unsupported_facts`, ufając, że model przepisze wynik w drugie miejsce | teraz kod składa z **obu** źródeł |
| `pick_topic` zabijał przebieg | wyjątek, gdy nic nie przeszło odsiewu | sprzeczne z zasadą „bramki zgłaszają" | prawdopodobnie dlatego `feasible` nigdy nie było fałszem |
| martwe sygnały | siedem ocen skauta liczonych i **czytanych przez zero linii kodu** | brak jakiegokolwiek nadzoru nad tym | wykrywacz znalazł 19 pól i 8 stałych |
| stałe udające zabezpieczenia | `MAX_KOMENTARZY_NA_PUBLIKACJE = 2` nieegzekwowane nigdzie | martwa stała czyta się jak gwarancja | powołałem się na nią jako na istniejący limit tego samego dnia |

**Wspólny mianownik połowy tej tabeli:** szkodę zrobiła rzecz **dołożona**, żeby
było bezpieczniej albo lepiej widać. Licznik trafień w cache zdusił grafikę.
Odstęp chroniący przed tempem farmy uwięził agenta. Zapora przed pisaniem
u płacących przepuściła to, czego API nie opisało. Wcześniej zapora przed
wstrzyknięciem zabiła promocję własnego artykułu. Dodatek przychodzi poprawić
system i psuje go po cichu, bo **nikt nie pisze testu na to, czy licznik nie
zabija tego, co liczy**.

Dlatego istnieje `test_martwe_sygnaly.py`: oblewa się przy **każdym nowym**
martwym polu i **każdej nowej** martwej stałej, z listą wyjątków, gdzie każde
rusztowanie musi mieć wypisany powód.
