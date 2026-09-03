# Jak działa bot v2 — pełny obraz, koszty i gdzie da się jeszcze uciąć

Stan na 2026-08-19, spisany wtedy na gałęzi `v2-test`
(gałęzi już nie ma — wmergowana w `main` 23 sierpnia). Wszystkie liczby pochodzą z bazy
produkcyjnej i z faktury DeepSeeka, nie z szacunków.

---

## 1. Dwie ścieżki, które robi ten sam program

Agent budzi się z zegara **trzy razy dziennie** (11:20, 19:20, 23:40 UTC) i za
każdym razem robi jedną z dwóch rzeczy albo obie.

### Ścieżka artykułu — od pomysłu do publikacji

| # | etap | model | co robi | koszt/wywołanie |
|---|---|---|---|---|
| 1 | `scout` | deepseek-**pro** | 6 tematów, każdy z **nazwanym złamanym przekonaniem** | $0,018 |
| 2 | `feasibility` | deepseek-flash | tani odsiew: czy temat ma drugi akt (`RICH`/`SINGLE`/`THIN`) | $0,009 |
| 3 | `discovery` | deepseek-**pro** | szuka źródeł w sieci, pomija hosty, które nas nigdy nie wpuściły | **$0,234** |
| 4 | `fetch` | **bez modelu** | pobiera strony i **PDF-y**; poniżej 4 źródeł uruchamia drugą rundę | $0 |
| 5 | `classify` | deepseek-flash | wyciąga fragmenty i liczby z pobranych stron | $0,004 |
| 6 | `synthesis` | deepseek-**pro** | składa kartę dowodową + `parallel_mechanisms` | $0,025 |
| 7 | **`warto_pisac`** | deepseek-**pro** | **bramka ciekawości — czy jest tu luka** | $0,015 |
| 8 | `write` | **claude-fable-5** | **pisze artykuł. To jest produkt** | **$0,426** |
| 9 | `review` | deepseek-**pro** | rozlicza tekst zdanie po zdaniu wobec karty | $0,054 |
| 10 | bramki | **bez modelu** | sześć kontroli deterministycznych | $0 |
| 11 | `grafika` | deepseek-flash | pisze *opis* okładki | $0,002 |
| 12 | `obraz` | **gpt-image-1.5** | rysuje okładkę | $0,040 |

**Cały przebieg artykułu: $0,75–0,78.**

### Ścieżka dnia — to, co realnie napędza wzrost

| etap | model | budżet dzienny | koszt/wywołanie |
|---|---|---|---|
| `cele` | deepseek-flash | — | $0,006 |
| `curiosity` | deepseek-flash | — | **$0,056** |
| `wybor` | deepseek-pro | — | — |
| `note` | **claude-fable-5** | 5 notek | $0,086 × 3 warianty |
| `factcheck` | deepseek-flash | — | $0,007 |
| `comment` | deepseek-**pro** | 15–20 | $0,006 |
| `reply` | deepseek-**pro** | poza limitem | $0,005 |
| `restack` | deepseek-**pro** | 2–4 | $0,003 |
| polubienia | **bez modelu** | 12–20 | $0 |

Obserwacje: 30–44 miesięcznie. Subskrypcje: 6–12 miesięcznie.

---

## 2. Dlaczego akurat te modele

**Fable 5 (najdroższy) pisze artykuły i notki.** Wygrał A/B z Opusem na
identycznej karcie — wyłapał, że przepis o nakrętkach jest węższy niż jego
popularne streszczenie. Przy notkach różnica widać gołym okiem: DeepSeek dał
*„a structural panel in a pressurized cabin"*, Fable *„an aircraft cabin window
that seals itself"* i zamknął linią *„Failure is the mechanism, not the
emergency"*.

**DeepSeek pro tam, gdzie liczy się PAMIĘĆ FAKTÓW.** Benchmark SimpleQA: pro
57,9 wobec flash 34,1 — przewaga ~70%, jedyna, której przebudowa flasha nie
zetrze. Dlatego pro pisze komentarze, odpowiedzi i restacki: tam model musi
przypomnieć sobie, **gdzie indziej** ten sam mechanizm działa, a nie odczytać
to z podanego tekstu.

**DeepSeek flash tam, gdzie praca jest WYDOBYWCZA.** Klasyfikacja, factcheck,
ciekawostki, Federal Register — model czyta podany tekst albo szuka w sieci,
więc luka w pamięci nie ma znaczenia. Flash bije pro na wszystkich dziewięciu
benchmarkach agentowych i jest trzykrotnie tańszy.

**Dyskoveria została na pro mimo ceny.** Zmierzone: flash w **zero na sześć**
prób nie wystawił końcowego JSON-a — raz padł całkiem, resztę uratowała ścieżka
awaryjna. Podniesienie `effort` na `high` pogorszyło sprawę. To nie jest kwestia
jakości, tylko niezawodności etapu chodzącego codziennie bez nadzoru.

---

## 3. Bramki — co blokuje, a co tylko zgłasza

### Przed wydaniem pieniędzy

**Cztery bramki kandydata** (`stages.bramka_kandydata`) — zero kosztu, sam kod:

1. **Nazwany decydent Z DATĄ.** Zabija „dlaczego niebo jest niebieskie".
2. **Złamane przekonanie.** Najostrzejsza reguła w całym potoku: *„większość nie
   wie" to nie przekonanie, tylko niewiedza*, a niewiedza produkuje ciekawostki.
3. **Kontakt.** Skutek musi nazywać **rzecz czytelnika**, nie osobę — sprawdzane
   przez wymóg słowa „your".
4. **Sprawdzalność.** Bez adresu źródła kandydat nie wchodzi.

**Bramka ciekawości** (`warto_pisac`, $0,015) — przed pisarzem. Model obserwuje
i **cytuje dowód z karty**, werdykt składa **kod**:
`PISZ` / `DOLOZ` (idź po parę do banku) / `ODLOZ`.

**Dwie drogi do PISZ** (od 2026-08-20):

| droga | warunek |
|---|---|
| **A — złamane przekonanie** | przekonanie + 2 z 3 filarów (decydent, odczuwalna liczba, druga dziedzina) |
| **B — nierozstrzygnięty wynik** | otwarty wynik + **spisana reguła, która go rozstrzyga** + nazwany decydent |

Droga B istnieje, bo **luka informacyjna z definicji się nasyca**. Loewenstein
pisze wprost: konsumpcja informacji jest nagradzająca, ale po zdobyciu
wystarczającej ilości ciekawość spada. Pismo złożone z samych pytań zamkniętych
produkuje czytelników zaspokojonych i odchodzących — musi zdobywać każdego od
nowa co tydzień.

**Warunek oddzielający to od wróżenia jest jeden i twardy:** karta musi nieść
spisaną regułę rozstrzygającą wynik. Bez niej temat nie przechodzi, choćby
pytanie brzmiało najdramatyczniej. Kod odrzuca też odpowiedź, która **zaprzecza
sama sobie w pierwszych słowach** („nic tego nie rozstrzyga, po prostu nikt tego
nie zapisał") — to opis luki w naszej wiedzy, nie stawki. Siatka kotwiczy na
początku zdania, więc poprawna reguła ze słowem „nothing" w środku przechodzi.

Skaut proponuje oba rodzaje (`kind`), a kod sortujący stawia oba na czele
kolejki. Zmierzone na żywym przebiegu: **3 z 8 tematów** to systemy pod próbą.

### Po napisaniu — dwanaście bramek deterministycznych, żadna nie blokuje

| bramka | co łapie |
|---|---|
| `ZMYSLONE_PRZEZYCIE` | „widziałem", „stałem" — czasowniki doświadczenia |
| `NIEISTNIEJACE_BADANIE` | „according to a recent study" bez nazwania |
| `LICZBA_SPOZA_KORPUSU` | liczba, której nie ma w materiale |
| `FRAZA_Z_INSTRUKCJI` | pisarz zacytował własny prompt |
| `ZAPOWIEDZ_GRANIC` | akapit o granicach zapowiada sam siebie |
| `WASKA_PODSTAWA` | artykuł stoi na jednym źródle |
| `BUDZET_ZASTRZEZEN` | więcej niż jedno „moim zdaniem" |
| `OBWIESZCZONA_POWSCIAGLIWOSC` | „nie zmyślę tego" — luki nazywa się wprost |
| `ZAKAZANE_OTWARCIE` | „Turn over…", „Next time you…" — errand zamiast zaczepu |
| `STATYSTYKA_BEZ_ZRODLA` | liczba i niby-źródło w jednym zdaniu |
| `NIEWIADOME_NA_KONCU` | zbiorcza lista granic w ostatniej trzeciej |
| `ODCISK_FORMY` | ten sam szkielet co któryś z czterech poprzednich |

### Cztery bramki „model obserwuje" ($0,025–0,05, `prompts/forma.md`)

Osobne wywołanie od recenzji — **celowo**. Recenzent ma wprost chronić
wnioskowanie przed zgłoszeniem (śmiała interpretacja nie jest wadą), a te
bramki liczą m.in. zastrzeżenia. Złączone w jedno pytanie tępiłyby się nawzajem.

| bramka | co łapie |
|---|---|
| `GESTOSC_BEATOW` | mniej niż jedno nowe przekonanie na 150 słów |
| `BRAK_ESKALACJI` | najmocniejszy fakt w tonie przypisu |
| `CZYTELNIK_NIEPRZYLAPANY` | nigdzie zwrotu do TEGO czytelnika z konkretem |
| `OTWARCIE_ZNANE` | pierwszy akapit stoi na tym, co czytelnik już wie |

Model oddaje **wyłącznie cytaty i tak/nie**. Liczenie, dzielenie i szukanie
pozycji robi kod — arytmetyki modelu nie da się sprawdzić, cytat da się znaleźć
w tekście.

**Czego świadomie NIE wzięliśmy z playbooka.** Reguł nakazujących pozycję: lede
z liczbą, przyłapanie czytelnika na 25–40% głębokości, najmocniejszy fakt
w osobnym akapicie, „zawsze nazwij beneficjenta i koszt". Reguła zakazująca
usuwa wadę i zostawia przestrzeń otwartą; reguła nakazująca pozycję wypełnia ją
jedną odpowiedzią i po dziesięciu tekstach **sama staje się podpisem maszyny**.
Raz już na tym polegliśmy. „Zawsze beneficjent" ścinałby sześć losowanych ruchów
końcowych do jednego. Pozycje **liczymy** i pokazujemy w logu — jako informację,
nie jako wadę.

`gates.verdict` **zawsze** zwraca `SAVED`. Decyzja właściciela: po opłaconym
researchu artykuł musi powstać, bramki tylko zgłaszają uwagi.

---

## 4. Gdzie naprawdę idą pieniądze

Cała historia produkcji, **$8,73** w 507 wywołaniach:

| etap | udział | $/wywołanie | średnie wejście |
|---|---|---|---|
| **`discovery`** | **34,9%** | $0,234 | **166 901 tokenów** |
| **`write`** | **24,4%** | $0,426 | 8 306 |
| `comment` | 11,0% | $0,006 | 753 |
| `factcheck` | 7,8% | $0,007 | 23 227 |
| `curiosity` | 6,4% | $0,056 | **195 567** |
| reszta (9 etapów) | 15,5% | — | — |

**Dwa etapy to 59,3% wszystkiego.**

---

## 5. Gdzie da się jeszcze uciąć — i gdzie NIE

### Największa dźwignia: `discovery`, 166 901 tokenów wejścia

Trzecia część całego rachunku. Powód jest w kodzie: **każda runda wyszukiwania
przesyła całą rozmowę od nowa**, więc przy 20 zapytaniach wejście puchnie do
setek tysięcy tokenów. To nie jest cena wiedzy, tylko cena powtarzania.

Nie mam na to gotowej odpowiedzi i nie udaję, że mam — ale to jest jedyne
miejsce, gdzie stawką jest jedna trzecia budżetu.

### Druga: `curiosity`, 195 567 tokenów wejścia

Ten sam mechanizm. Częściowo już rozbrojony **indeksem kandydatów**: jedno
wyszukiwanie zasila teraz cztery przebiegi zamiast jednego, a odrzuceni zostają
odrzuceni na stałe. **Federal Register jest tańszą alternatywą** — $0,0048 za
użytecznego kandydata wobec $0,0514 za wywołanie `curiosity`.

### Trzecia: trzy warianty notki

Piszemy trzy pełne notki, publikujemy jedną. Odkąd indeks kandydatów robi
selekcję **wcześniej**, te trzy warianty służą już tylko doborowi otwarcia.
Zejście do dwóch to jedna trzecia mniej na najdroższym modelu.

### Czego NIE warto robić — i to przeczy popularnej radzie

**Cache promptu prawie nic nam nie da przy notkach.** Rada brzmi: „prompt
systemowy, formy i reguły stylu są identyczne, to jest prefiks do
zacache'owania z rabatem 90%". Nasze dane mówią co innego:

> `note`: **220 tokenów wejścia**, 1 667 wyjścia.

Przy stawkach Fable to $0,0022 wejścia i **$0,0834 wyjścia** — czyli
**97% kosztu notki to wyjście**. Cache oszczędziłby około dwóch procent.

Rada jest słuszna w ogólności i błędna u nas, bo nasz prompt notki jest krótki,
a myślenie modelu długie. **Realną dźwignią przy notkach jest budżet myślenia
i liczba wariantów, nie cache.**

### Czego też nie warto

**Pakowania kilku notek w jedno wywołanie.** Mamy własny dowód przeciw: podanie
modelowi całej puli naraz dało pięć wariantów tego samego faktu, cztery z pięciu
o windzie. Jednakowy kształt to podpis maszyny.

**Zejścia z Fable na notkach.** To jedyne miejsce, gdzie najdroższy model jest
oczywistą decyzją: notki dają ponad 60% przyrostu subskrybentów, cała ich siła
siedzi w jednym pierwszym zdaniu, a płacimy premię za siedemdziesiąt tokenów.

---

## 6. Rzeczy, o których łatwo zapomnieć

**Stawki DeepSeeka rozliczone z fakturą co do centa** (15–19 sierpnia, dziesięć
wierszy odtworzonych dokładnie). Baza po podwyżce z 16 sierpnia: pro
$0,66/$1,98, flash $0,22/$0,66; **szczyt to dokładnie dwukrotność** i obejmuje
też cache. Godziny szczytu: 1–3 i 6–9 UTC — wszystkie nasze przebiegi są poza.

**Kopia testowa nie może publikować.** Plik `TO_JEST_KOPIA_TESTOWA` obok
`config.py` odbiera prawo do `--wyslij`.

**Bazy rozdzielają się same** — `DATA_DIR` wywodzi się z położenia `config.py`,
więc osobny klon to osobna baza bez żadnej zmiennej do zapomnienia.

**Uczymy się na ODPOWIEDZIACH, nie na polubieniach.** Na jedną odpowiedź
przypada osiem polubień; gdyby miarą sukcesu była suma reakcji, gradient
przesunąłby pismo od wyjaśniania do prowokacji w kilka miesięcy, a każdy
pojedynczy krok wyglądałby na poprawę.

**657 asercji w 26 zestawach**, zmierzone na serwerze — 26/26 zdanych. Testy
darmowe w `tests/`, płatne w `tests/platne/`, pomiary bez asercji w `pomiary/`.
Na Windowsie dwa zestawy oblewają się na środowisku, nie na kodzie: brak
`trafilatura`/`playwright` i SIGTERM, którego Windows nie ma.

## 7. Czego nauczył pierwszy dzień na produkcji (19 sierpnia 2026)

Wdrożenie poszło, ale dwa błędy wyszły dopiero na żywo — oba w miejscach, w
które nie celował żaden test, bo oba były **niewidoczne offline**.

**Wartość domyślna, która nie wchodzi.** Kolumna `calls.cache_hit` ma w
schemacie `NOT NULL DEFAULT 0`, a mimo to wysadzała zapis. Funkcja zapisu
wymieniała zawsze komplet kolumn, więc brakujące szły jako **jawny NULL** — a
`DEFAULT` wchodzi wyłącznie wtedy, gdy kolumny w `INSERT` nie ma wcale.
Podawało ją jedno miejsce z czterech. Grafika nie mogła się przez to zapisać
nigdy (artykuł 0025 wyszedł bez okładki), a ścieżka zapisu **nieudanego**
wywołania wywracała się na tym samym — czyli awaria dostawcy modelu
przychodziła do logu jako awaria bazy. Naprawione w jednym miejscu: `INSERT`
bierze tylko podane kolumny, więc następna dopisana kolumna nie powtórzy tego.

**Odstęp, który ciągnął się po ostatnim.** Przerwa 10–30 minut między
restackami stała na końcu ciała pętli, a warunek wyjścia sprawdza się dopiero
na górze następnego obrotu. Przy budżecie 2–4 restacki rozłożonym na 3–4
przebiegi `ile` wynosi zwykle 1, więc agent po wykonaniu normy spał jeszcze
pół godziny z otwartą przeglądarką — w przebiegu, który wcześniej odpuścił
obserwowanie **z braku czasu**. Pierwsza poprawka („przerwij po wykonaniu
normy") nie wystarczała i złapał to dopiero test: gdy w kanale jest mniej
notek niż budżet, norma nie jest wykonana i pętla i tak zasypia. Odstęp stoi
teraz **przed** kolejnym restackiem, nie po poprzednim.

Wspólny mianownik obu: szkodę zrobiła rzecz **dołożona** — licznik kosztów i
odstęp chroniący przed tempem farmy. Obie przyszły poprawić system i obie go
po cichu popsuły, bo dodatki tego rodzaju nie mają własnego testu.

Co zadziałało bez poprawek: bramka ciekawości (PISZ, 3/3 filary), publikacja z
potwierdzeniem u źródła, factcheck **obalił dwa własne komentarze agenta** na
cudzych postach zanim wyszły, jeden wariant sam **zamilkł**, bo post prosił o
osobiste doświadczenie, którego to konto nie ma, a subskrypcja przy braku
przycisku „Subscribe" **nie kliknęła nic innego**.
