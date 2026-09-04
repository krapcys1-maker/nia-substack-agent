# Rozwiązywanie problemów — dziennik z czasu pracy

> **To jest ZAPIS Z CHWILI NAPOTKANIA, nie instrukcja obsługi.** Część pozycji
> opisuje problemy, które są już naprawione — zostają, bo naprawa ma sens
> dopiero wtedy, gdy wiadomo, czego dotyczyła. Wersja aktualna i uporządkowana
> na „co cię jeszcze ugryzie" / „co już ugryzło nas" stoi w
> [TROUBLESHOOTING.md](TROUBLESHOOTING.md), po angielsku, bo repozytorium jest
> publiczne.
>
> Ten plik zostaje, bo pomiary stojące za każdą pozycją są tu opisane
> dokładniej, a właściciel czyta po polsku.

Dziennik problemów napotkanych przy mapowaniu bota, czyszczeniu go
i budowie konfiguratora. Każda
pozycja ma **objaw** (co dokładnie zobaczyłem), **znaczenie** (co to naprawdę
było) i **obejście** (co zrobić). Pisane na bieżąco, w chwili napotkania —
objaw zapisany po fakcie zamienia się we wniosek, a wniosek bywa fałszywy.

Kolejność chronologiczna, nie ważnościowa.

---

## 1. Skan sekretów przed pushem zwraca fałszywe trafienia

**Objaw.** Polecenie ze zlecenia:

```
git ls-files | grep -iE "\.env$|storage-state|subskrybenci|haslo|token"
```

zwróciło dwa pliki zamiast zera:

```
archiwum/tests/test_la01_max_tokens.py
archiwum/tests/test_timeout_token_agreement.py
```

**Znaczenie.** To nie są sekrety. Wzorzec `token` trafił w słowo „tokens"
w NAZWACH plików testowych poprzedniego agenta. Skan po nazwie pliku nie
odróżnia „token dostępu" od „token modelu językowego".

**Obejście.** Skan po nazwie jest sitem wstępnym, nie dowodem. Dowód to skan
po TREŚCI:

```bash
git ls-files -z | xargs -0 grep -ilE "sk-ant-[A-Za-z0-9_-]{8,}|sk-proj-[A-Za-z0-9_-]{8,}|BEGIN (RSA|OPENSSH) PRIVATE"
```

Trafienia sprawdzone po jednym: wszystkie to atrapy w testach
(`sk-ant-test-secret`, `sk-ant-REPLACE_ME`) oraz asercje sprawdzające, że
sekret NIE wycieka do logu. Realnych kluczy w klonie nie ma.

Potwierdzone też, czego w klonie nie ma wcale: `agent-v2/data/` (baza, dziennik,
`storage-state.json`), `agent-v2/.env`, `kopie/*.csv`. `git clone` kopiuje
wyłącznie pliki śledzone, a te są w `.gitignore` oryginału.

---

## 2. `.env.example` opisuje POPRZEDNIEGO agenta, nie tego

**Objaw.** `.env.example` w korzeniu repozytorium wymienia:

```
ANTHROPIC_API_KEY, ANTHROPIC_MODEL_FAST, ANTHROPIC_MODEL_QUALITY,
PRICE_INPUT_USD_PER_MTOK, PRICE_OUTPUT_USD_PER_MTOK,
PRICE_CACHE_READ_USD_PER_MTOK, PRICE_CACHE_WRITE_USD_PER_MTOK,
PRICE_WEB_SEARCH_USD_PER_1K, DRY_RUN, KILL_SWITCH,
ALARM_EMAIL_TO, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
```

Prawdziwa lista, wyciągnięta z kodu (`grep` po `_env(` / `os.environ.get(`
w `agent-v2/*.py`, z pominięciem testów i archiwum), to:

```
ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY,
DRY_RUN, KILL_SWITCH, AGENT_V2_TRYB,
AGENT_V2_SERVER, AGENT_V2_CHEAP, AGENT_V2_NO_LIMIT, AGENT_V2_WRITER,
ALARM_EMAIL_TO, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
```

**Znaczenie.** Dwa różne błędy naraz, oba kosztowne dla kogoś, kto to odpala
u siebie po raz pierwszy:

1. **Brakuje `DEEPSEEK_API_KEY` i `OPENAI_API_KEY`.** DeepSeek obsługuje
   **21 z 26 etapów** — czyli ktoś, kto wypełni `.env.example` co do litery,
   dostanie bota, który nie zrobi prawie niczego.
2. **Pięć zmiennych `PRICE_*` i dwie `ANTHROPIC_MODEL_*` nie są czytane przez
   żadną linię `agent-v2/`.** To spadek po agencie z `archiwum/`; w v2 cennik
   stoi w `config.PRICING`, a modele w `config.MODEL_FOR`.

**Obejście.** Nie ufać temu plikowi. Lista zmiennych w
[MAPA_KONFIGURACJI.md](MAPA_KONFIGURACJI.md), część 3, jest wyprowadzona
z kodu. `.env.example` trzeba przepisać — to pozycja w części 5.

---

## 3. Kontrola kluczy przed wywołaniem modelu pokrywa 3 modele z 5

**Objaw.** `agent-v2/llm.py:74-79`:

```python
if model == config.CLAUDE and not config.ANTHROPIC_API_KEY: ...
if model == config.DEEPSEEK and not config.DEEPSEEK_API_KEY: ...
if model == config.IMAGE_MODEL and not config.OPENAI_API_KEY: ...
```

`config.CLAUDE` to `claude-opus-5`, `config.DEEPSEEK` to `deepseek-v4-flash`.

**Znaczenie.** Porównanie jest po WARTOŚCI modelu, nie po dostawcy. W systemie
są jeszcze dwa identyfikatory:

* `FABLE = "claude-fable-5-1"` — etap `write`, czyli artykuł;
* `DEEPSEEK_PRO = "deepseek-v4-pro"` — **jedenaście etapów**, w tym `comment`,
  `reply`, `restack`, `discovery`, `synthesis`.

Przy braku klucza te etapy **nie zatrzymują się na kontroli wstępnej**. Idą do
sieci i wywracają się dopiero na odpowiedzi HTTP — czyli komunikat mówi
o transporcie, a nie o brakującym kluczu.

**Obejście.** Diagnoza po objawie: błąd sieci/autoryzacji na `discovery`,
`comment` albo `write` przy działającym `curiosity` to prawie na pewno brak
klucza, nie awaria dostawcy. Naprawa jest jednolinijkowa i opisana w części 5
mapy (kontrola po dostawcy zamiast po identyfikatorze modelu).

---

## 4. Sześć testów oblewa się na świeżym klonie — cztery z nich nie z winy kodu

**Objaw.** Pełny zestaw w klonie: **116 zdanych, 6 oblanych**.

```bash
for t in agent-v2/tests/test_*.py; do python "$t"; done
```

**Znaczenie.** Zlecenie zapowiadało dwa znane windowsowe oblania. Są cztery
dalsze i żadne nie jest wadą kodu — wszystkie to **brak danych produkcyjnych
albo brak klucza**:

| test | co dokładnie mówi | przyczyna |
|---|---|---|
| `test_artykul` | `ModuleNotFoundError: playwright` | brak pakietu (znane) |
| `test_czas` | brak `SIGTERM` | Windows nie ma sygnałów POSIX (znane) |
| `test_komplet_sciezek` | `BLAD policzone na 0 plikach` | `agent-v2/data/` jest pusty |
| `test_podlogi_playbook` | `brak agent-v2/data/articles/NNNN-*.md` | katalog w `.gitignore` |
| `test_ratunek_tekstu` | `(5) KONTRDOWOD: wiersz zajmowal jedno z pieciu miejsc (5, 5)` | brak `data/promocja.json` |
| `test_zapora_platnych_wywolan` | `DRY_RUN nie jest blokowany: brak ANTHROPIC_API_KEY` | brak `.env` |

**Obejście — sprawdzone, nie zgadnięte.** Każdą z tych trzech przyczyn
potwierdziłem, usuwając ją i uruchamiając test ponownie:

* `test_komplet_sciezek` — test sprawdza, że nie ruszył produkcyjnych plików,
  i asercją „policzone na N plikach" pilnuje, żeby ten pomiar w ogóle coś
  mierzył. Przy pustym `data/` N wynosi 0. Po włożeniu jednego dowolnego pliku
  do `agent-v2/data/` test przechodzi (kod wyjścia 0).
* `test_ratunek_tekstu` — kontrdowód zakłada, że dopisanie wiersza do `articles`
  powiększy listę kątów o jeden. `stages.recent_angles` ma sufit
  `DIVERSITY_LOOKBACK = 5` i dobija do niego z `prompts/historia_startowa.json`,
  więc bez `data/promocja.json` obie strony porównania wychodzą po 5.
  Po utworzeniu `agent-v2/data/promocja.json` z trzema pozycjami:
  **87 zdanych, 0 oblanych**.
* `test_zapora_platnych_wywolan` — po założeniu `agent-v2/.env` z atrapami
  kluczy test przechodzi.

**Dlaczego to jest problem produktu, a nie ciekawostka.** Ktoś, kto sklonuje to
repozytorium i uruchomi testy, zobaczy sześć czerwonych i nie ma jak odróżnić
„brak playwrighta" od „kod jest zepsuty". Zestaw nie ma trybu „świeża
instalacja". To pozycja w części 5 mapy.

---

## 5. Test-strażnik płatnych wywołań NIE WIDZI martwego etapu, jeśli ma dekorator

**Objaw.** `tests/test_kanal_platnego_wywolania.py` przechodzi na zielono
i wypisuje:

```
stages.kandydaci_z_fedreg      KANAL:bank      fedreg
stages.sprawdz_fakty           MARTWE          factcheck
```

Tymczasem `kandydaci_z_fedreg` **nie ma ani jednego wołającego w kodzie
produkcyjnym**:

```bash
grep -rn "kandydaci_z_fedreg\|korpus_fedreg" --include=*.py . | grep -v archiwum
# stages.py:7129  def korpus_fedreg(...)
# stages.py:7205  def kandydaci_z_fedreg(...)
# tests/platne/test_fedreg_pelna_sciezka.py:34, 47
# tests/test_kanal_platnego_wywolania.py:510
```

Jedyne wywołania są w **teście płatnym** i w liście oczekiwań samego strażnika.

**Znaczenie.** Kolejność warunków w `werdykt()` (linie 279–285):

```python
if f.get("kanal"):      stan = "KANAL:%s" % f["kanal"]
elif q in pokryte:      stan = "dziedziczy"
elif not zywe:          stan = "MARTWE"
```

Sprawdzenie dekoratora stoi **przed** sprawdzeniem, czy ktokolwiek tę funkcję
woła. Funkcja z `@_na_kanal("bank")` i zerem wołających raportuje się jako
zdrowa. To znaczy, że w systemie są **dwa** martwe etapy płatne, nie jeden:
udokumentowany `factcheck` przez `sprawdz_fakty` oraz **nieudokumentowany
`fedreg`** przez `kandydaci_z_fedreg`.

To dokładnie ta klasa błędu, którą projekt sam nazywa: test świeci na zielono
nad kodem martwym.

**Obejście.** Nie da się tego naprawić przez zmianę konfiguracji — trzeba
przestawić kolejność warunków tak, żeby brak wołających wygrywał z dekoratorem:

```python
if not zywe and q not in pokryte:   stan = "MARTWE"
elif f.get("kanal"):                stan = "KANAL:%s" % f["kanal"]
```

i dopisać `fedreg` do listy `BEZ_WOLAJACYCH` albo wpiąć go w produkcję.
Do czasu naprawy: **`config.MODEL_FOR["fedreg"]` jest ustawieniem bez skutku**.

---

## 6. Sześć funkcji nie ma ani jednego użycia w całym repozytorium

**Objaw.** `docs/FUNCTION_MAP.md` (generowana z drzewa składni) oznacza
19 funkcji jako `MARTWA?`. Po sprawdzeniu każdej po kolei — grepem po całym
repozytorium, łącznie z testami i dokumentacją — sześć nie ma **żadnego**
użycia:

| funkcja | plik |
|---|---|
| `wlasciwe_konto(page)` | `browser.py:44` |
| `polec_publikacje(fraza, powod, wyslij)` | `browser.py:3312` |
| `ustaw_oswiadczenie_ai(wyslij)` | `browser.py:3610` |
| `w_szczycie(kiedy)` | `config.py:428` |
| `sesje_dnia()` | `stages.py:1001` |
| `corpus_words()` | `style.py:120` |

**Znaczenie — jedna z nich ma ciężar doktrynalny.** `ustaw_oswiadczenie_ai` to
jedyny kod, który czyta `prompts/OSWIADCZENIE_AUTORSTWA.md` i ustawia oświadczenie
„Jak to robię" na profilu. DOKTRYNA §9 mówi, że konto „nigdy nie kłamie
zapytane wprost", a komentarz w `config.py:88-91` opiera się na tym, że
oświadczenie „pokazuje się tak samo". Automat tego nie ustawia **nigdy** —
to musiał być jednorazowy ruch ręką.

Dla produktu to nie jest wada do naprawienia, tylko **krok instalacyjny do
opisania**: ktoś, kto postawi to u siebie, dostanie konto bez oświadczenia
i nie dowie się o tym z żadnego logu.

Pozostałe pięć to narzędzia jednorazowe albo pozostałości. `corpus_words()`
jest szczególnie mylące: docstring mówi „podłoga porównuje tekst z korpusem",
sugerując istniejącą bramkę, a bramki nie ma.

**Obejście.** Lista jest w `docs/FUNCTION_MAP.md` i przebudowuje się poleceniem
`python narzedzia/mapa_funkcji.py`, więc następna martwa funkcja pokaże się
sama.

---

## 7. Pisarz artykułu czyta pliki spoza `agent-v2/`

**Objaw.** `agent-v2/config.py:47`:

```python
STYLE_PROFILES_DIR = REPO_ROOT / "style-profiles"
```

`stages.py:514-515` (etap `write`) woła `style.load_examples()` i
`style.load_profiles()`, a to drugie czyta:

```
<korzeń repo>/style-profiles/ARTICLE_STYLE_PROFILE_V1.md
<korzeń repo>/style-profiles/ARTICLE_NEGATIVE_STYLE_PROFILE_V1.md
```

**Znaczenie.** Zlecenie opisywało `style-profiles/` jako
„materiały, nie kod". To jest **żywa ścieżka**: bez tych dwóch plików etap
`write` rzuca `StyleError` i artykuł nie powstaje — po opłaconym researchu.
`agent-v2/` nie jest samowystarczalny.

Katalog ma pięć plików, ale kod czyta tylko dwa. `CLAUDE_INSTRUKCJA_NATURALNEGO
_PISANIA.md` (45 KB), `NOTES_STYLE_PROFILE_V1.md` i `STYLE_SOURCES_MANIFEST.md`
nie są czytane przez żadną linię.

**Obejście.** Przy przenoszeniu bota trzeba wziąć cały korzeń repozytorium, nie
sam `agent-v2/`. W konfiguratorze ta ścieżka ma być polem, nie stałą.

---

## 8. Każda liczba w oryginalnym README była nieaktualna

**Objaw.** README repozytorium źródłowego opisywał system, którego już nie ma:

(kolumna druga to **repozytorium źródłowe zmierzone 31 sierpnia 2026**, nie
to repozytorium dzisiaj — bez daty przy liczbie ta tabela za miesiąc byłaby
kolejnym przykładem błędu, który opisuje)

| README mówił | jest naprawdę | ile razy więcej |
|---|---|---|
| 11 plików `.py` | **23** | 2,1× |
| 11 231 wierszy | **27 998** | 2,5× |
| 43 zestawy testów | **122** (+ 10 płatnych) | 2,8× |
| 25 promptów | **27** | — |
| dokumentacja: 10 535 wierszy | **12 946** | — |

Do tego sekcja „Stan na dziś" podawała 37 przebiegów, 718 wywołań i 12,50 USD,
a `JAK_DZIALA_V2.md` z tego samego repozytorium liczy 507 wywołań i 8,73 USD —
bo są to pomiary z różnych dni, oba nieopatrzone datą przy liczbie.

**Znaczenie.** Nie chodzi o niechlujstwo. To jest **dokładnie ta klasa błędu,
przed którą projekt sam ostrzega**: liczba wpisana ręcznie, żeby było widać
skalę, przestaje być prawdziwa przy pierwszej zmianie i nikt tego nie zauważa,
bo nic jej nie pilnuje.

Ten sam projekt rozwiązał ten problem gdzie indziej i dobrze:
`JAK_ZBUDOWANY_JEST_BOT.md` jest **generowany** przez `dokumentacja-zrodla/sklej.py`
i pilnowany przez `test_dokumentacja_zywa`, który oblewa się, gdy przebudowa
cokolwiek zmienia. README stało poza tym mechanizmem.

**Ciąg dalszy, 4 września 2026 — ta sekcja miała chorobę, którą opisuje.**
Policzono liczby w TYM repozytorium. Sama liczba funkcji stała w **sześciu
dokumentach w pięciu wersjach** (548, 548, 535, 529, 519, 519), a w drzewie
było 549. Liczba modułów: 23 / 24 / 25 / 27. Liczba testów: 122 / 123 / 129 /
140. Recepta zapisana wyżej — „liczby w dokumentach pisanych ręcznie sprawdza
się przed wydaniem" — jest obietnicą człowieka na jeden dzień i tyle wytrzymała.

Dwie z tych rozbieżności **nie były błędem**: „27 modułów" liczyło też
`dokumentacja-zrodla/`, a „140 plików testowych" liczyło `platne/` i pomocników.
Obie definicje są sensowne — tyle że żaden dokument nie mówił, której używa,
więc pomiar nieaktualny wyglądał identycznie jak pomiar innej rzeczy.

Naprawa: `agent-v2/tests/test_liczby_w_dokumentach.py` wyprowadza każdą liczbę
z drzewa (funkcje z tego samego przejścia po AST, z którego powstaje
`FUNCTION_MAP.md`) i porównuje z dokumentami, a **regułę pomiaru trzyma obok
wartości**. Wzorzec, który przestał trafiać, oblewa tak samo jak zła liczba —
przepisane zdanie nie zabierze wpisu spod kontroli po cichu.

**Obejście.** Nowy README ma liczby przeliczone na dzień 3 września 2026.
Trwałe rozwiązanie: albo wciągnąć nagłówkową tabelę README do generatora, albo
dopisać do `test_dokumentacja_zywa` sprawdzenie liczb z README wobec stanu
faktycznego. `docs/FUNCTION_MAP.md` jest odporna z definicji — przebudowuje się
poleceniem `python narzedzia/mapa_funkcji.py`.

---

## 9. W historii repozytorium leżą zacommitowane bazy danych — sprawdzone, są puste

**Objaw.** Skan historii przed pushem (nie sam `git ls-files`, tylko wszystkie
commity, jakie klon zna):

```bash
git log --all --diff-filter=A --name-only --format="" | sort -u \
  | grep -iE "\.db$|dziennik\.jsonl"
```

zwrócił dwanaście plików, których nie ma w żadnej gałęzi:

```
agent-prototyp/data/agent-prototyp.db
agent-prototyp/data/dziennik.jsonl
agent-prototyp/.live-experiments/E-012…E-024/…/experiment.db   (dziesięć sztuk)
```

Razem ~2,5 MB binariów.

**Znaczenie.** Zlecenie mówiło, że `git clone` kopiuje wyłącznie pliki śledzone
i że baza, dziennik i sesja są w `.gitignore`. To prawda **dla dzisiejszego
drzewa**. Nie jest prawdą dla historii: `agent-prototyp/` to porzucony prototyp
napisany przez inny model, zarchiwizowany 23 sierpnia 2026 commitem
`00e9653` i osiągalny wyłącznie z tagu `prototyp-gpt-2026-08`.

Nie ma go w `main` ani w `proba-innego-tematu`, więc `git ls-files` go nie
pokazuje — a mimo to obiekty leżą w klonie i poszłyby na zdalne repozytorium
razem z tagiem.

**Sprawdziłem zawartość, zamiast zgadywać.** Wyciągnąłem bazę do katalogu
tymczasowego poza repozytorium i otworzyłem:

* 25 tabel, z czego **24 puste**. Jedyna z danymi to `runs` — trzy wiersze,
  wszystkie z 21 sierpnia 2026, `cost_usd = 0.0`, etapy `test-bibliotekarz`,
  `test-notki-z-banku`, `test-styl-grafik`. To przebiegi testowe.
* `dziennik.jsonl` — wpisy typu
  `{"gdzie": "https://ktos.substack.com/p/cos", "tekst": "Nasze zdanie o mechanizmie."}`,
  czyli atrapy.
* Skan po adresach e-mail i kluczach API: **zero trafień**.

Plik tymczasowy skasowałem po sprawdzeniu.

**Wniosek: nie ma tu sekretów.** Ale to jest przypadek, nie zasługa — te bazy
zostały zacommitowane, zanim `.gitignore` zamknął `data/`, i gdyby prototyp
zdążył popracować na żywym koncie, leżałyby tam prawdziwe adresy.

**Obejście, zastosowane.** Wypchnięte zostały **tylko gałęzie, bez tagów**.
Tagi zostają w klonie lokalnym i można je dosłać świadomą decyzją:

```bash
git push origin --tags
```

Zanim to zrobisz, warto wiedzieć, że wraz z `prototyp-gpt-2026-08` idzie
2,5 MB pustych baz i 31 000 wierszy porzuconego prototypu.

**Zasada na przyszłość.** Skan `git ls-files` odpowiada na pytanie „co jest
w drzewie". Pytanie przed pushem brzmi „co jest w historii" i wymaga innego
polecenia. Te dwa skany dają różne wyniki i mylenie ich jest tym rodzajem
błędu, który wychodzi raz i nie da się go cofnąć.

---

## 10. Nazwa konta przeżyła całe czyszczenie, bo była rozbita między dwa literały

**Objaw.** Po pełnym przebiegu usuwania tożsamości i po **wydaniu publicznym**
skan dawał zero trafień:

```bash
grep -ril "Stara Marka Konta" .    # 0 plików
```

A w `agent-v2/stages.py` stało (nazwa poniżej zastąpiona atrapą — lekcja nie
zależy od tego, jak brzmiała naprawdę, a prawdziwa nie ma czego szukać
w publicznym repozytorium):

```python
SCOUT_SYSTEM = (
    "You are a topic scout for the English-language Substack 'Stara Marka "
    "Konta', a publication about ..."
)
```

**Znaczenie.** Python skleja sąsiadujące literały. W **źródle** nie ma nigdzie
pełnej nazwy — jest „Stara Marka " i osobno „Konta'". Grep działa na źródle,
więc nie miał czego znaleźć. Wartość powstaje dopiero przy parsowaniu.

To ta sama klasa błędu, co fraza przecięta końcem linii w promptach
(`artificial\nintelligence`), która przeżyła **trzy** przebiegi czyszczące
z tego samego powodu.

**Skutek był realny:** stara nazwa konta stała w publicznym repozytorium od
pierwszego wydania.

**Obejście — dwutorowe, bo jednotorowe zawiodło.**

1. Skan po **wartości**, nie po źródle:

   ```bash
   python narzedzia/audyt.py     # sekcja 2: TOZSAMOSC W SKLEJONYCH LITERALACH
   ```

   Używa `ast.literal_eval` na każdym przypisaniu, więc widzi sklejoną wartość.
   To samo robi krok CI „czy w drzewie nie ma tożsamości konta".

2. **Usunięcie powodu, nie objawu.** Marka jest teraz `config.NAZWA_MARKI`,
   a `SCOUT_SYSTEM` i `WRITER_SYSTEM` składają się z niej f-stringiem. Nazwa ma
   jedno miejsce, więc nie ma czego przeoczyć przy następnej zmianie.

**Zasada.** Skan po napisie w źródle nie widzi wartości, która powstaje przy
parsowaniu: sklejonych literałów, f-stringów, konkatenacji przez `+`, fraz
zawiniętych końcem linii. Przy czymkolwiek, co MUSI zniknąć, potrzebne są dwa
skany — po źródle i po wartości.

---

## 11. Testy czytają historię gita, więc świeży klon je wywraca

**Objaw.** W kopii repozytorium z historią założoną od nowa siedemnaście testów
padało w połowie pliku:

```
AttributeError: module 'alarm_6ed4e7d' has no attribute 'przeglad'
CalledProcessError: Command '['git','show','6ed4e7d:agent-v2/alarm.py']'
                    returned non-zero exit status 128
```

**Znaczenie.** To nie jest wada. `DOKTRYNA.md` §12 wymaga, żeby kontrdowód był
**odtworzony, a nie opisany**, a wersja odniesienia przypięta do konkretnego
SHA — nigdy do `HEAD`, bo test mierzący się względem `HEAD` gaśnie w chwili
commita, którego strzeże.

Skutek uboczny: **te testy zależą od historii tego repozytorium.** W kopii bez
niej `git show` trafia w commit, którego nie ma.

Awaria wyglądała przy tym jak **wada kodu** i nie mówiła czytającemu nic
o przyczynie — czyli odwrotność klasycznej pułapki tego projektu: nie test
zielony nad martwym kodem, ale test czerwony nad kodem zdrowym.

**To ma też konsekwencję strategiczną.** Czysta historia i kontrdowody przypięte
do SHA **wykluczają się nawzajem**. Nie ma wariantu, w którym publikuje się
repozytorium z wyczyszczoną historią i te testy działają.

**Obejście.** `agent-v2/tests/historia.py`:

```python
import historia
historia.wymaga_historii("6ed4e7d")
```

Sprawdza `git cat-file -e <sha>^{commit}` i przy braku wypisuje, których
commitów brakuje i dlaczego kontrdowodu nie da się odtworzyć, po czym kończy
kodem 0. Pominięcie jest **jawne i policzalne**, a nie udawanym przejściem.

**Uwaga przy wpinaniu strażnika.** Musi stać **przed pierwszym użyciem** gita,
nie przed pierwszą asercją. Dwa testy wołają `git show` na poziomie modułu,
w linii 116 i 125, a ostatni import stoi niżej — strażnik wstawiony „po
importach" stał za rzeczą, której miał pilnować, i nie zmieniał nic.

---

## 12. Poprawka, która wyglądała na zrobioną i nie robiła nic

**Objaw.** Test-strażnik płatnych wywołań nie widział martwego etapu
z dekoratorem kanału (pozycja 5). Poprawka wyglądała oczywiście:

```python
if not zywe and q not in pokryte:
    stan = "MARTWE"
```

Po niej `stages.kandydaci_z_fedreg` **nadal** raportował się jako `KANAL:bank`.

**Znaczenie.** Pięć linii wyżej stoi:

```python
pokryte = {q for q, f in dane["funkcje"].items() if f["kanal"]}
```

`pokryte` jest **zasiewane dekoratorami**. Funkcja z dekoratorem była w nim od
początku, więc `q not in pokryte` zawsze było fałszem i cały warunek
sprowadzał się do starego zachowania.

Poprawka przechodziła code review we własnej głowie, kompilowała się, nie
psuła żadnego testu — i nie robiła nic. **To jest dokładnie ta klasa błędu,
którą ten test ma łapać.**

**Obejście.** Właściwe pytanie nie dotyczy `pokryte` w ogóle:

```python
if not zywe and not z_main:
    stan = "MARTWE"
```

Czy cokolwiek ją woła, i czy nie jest ręcznym wejściem z `__main__`. Nic więcej.

**Zasada.** Po każdej poprawce sprawdź, że **objaw zniknął**, a nie tylko że
kod się zmienił. Tu wystarczyło jedno uruchomienie i spojrzenie, czy nazwa
funkcji pojawiła się na liście `MARTWE`. Bez tego poprawka zostałaby
zacommitowana jako zamknięta.
