# Test na żywo kartridża `ai` na koncie testowym — audyt warstwa po warstwie

Noc z 5 na 6 września 2026, gałąź `presety`. Silnik: czysty bot z gałęzi po
commitach z 5 września. Kartridż: `presety/nia/` = kopia `presety/ai/` z
uchwytem konta testowego, wszystkimi modelami tekstowymi na DeepSeeku
(`write`/`note`/`naprawa` = `deepseek-v4-pro`, `note_tani` i etapy
mechaniczne = `deepseek-v4-flash`), okładką na `gpt-image-1.5`, sufitami
podniesionymi na test (8 USD/dzień, 3 USD/przebieg). Sesja Substacka zdjęta
z zalogowanego Chrome'a właściciela po porcie 9222; publikacja idzie przez tę
samą przeglądarkę.

Wszystko poniżej jest zmierzone, nie założone: liczby pochodzą z logów
`agent-v2/instancje/nia/logi/*.log`, z tabeli `calls` w bazie instancji
i z `dziennik.jsonl`. Nazwiska cudzych autorów, pod którymi bot komentował
albo których polubił, celowo pominięte.

## 1. Co poszło na konto

| Kiedy (UTC) | Co | Wynik |
|---|---|---|
| 21:43 | komentarz pod cudzą notką o chatbotach w obsłudze klienta (znaleziona po haśle) | 20 słów, po jednej naprawie po factchecku, potwierdzony w wątku |
| 21:44, 21:45 | dwa polubienia | dwóch autorów finansowych z kanału konta (bez filtra tematu; naprawione) |
| 00:43 | notka (CIEKAWOSTKA / KONTRAST) o ocenie „Critical" GPT-6 Astra | 60 słów, po jednej naprawie, przyjęta (200), widoczna na profilu |
| 00:49 | komentarz pod cudzą notką o odpowiedzialności za błędne odpowiedzi | 16 słów, factcheck 1 wyszukiwanie, potwierdzony |
| po 01:00 | artykuł z okładką | sekcja 9 |

Zero restacków (cztery odmowy sędziego w przebiegu 2, budżet 0 w przebiegu 5),
zero obserwacji i subskrypcji (wyłączone w kartridżu).

## 2. Przejścia między warstwami — udany dzień (przebieg 5)

| Warstwa | Co weszło | Co wyszło | Koszt |
|---|---|---|---|
| sygnały (RSS/YouTube) | 21 kanałów kartridża | 1 571 wpisów → 1 555 tematów, 30 do promptu (przeplot po równo) | 0, 6,6 s |
| wydarzenia | tytuły z kanałów | 1 wielkie (GPT-6 Astra), furtka otwarta | 0 |
| stan dziedziny (`aktualne_modele`) | web search | 14 aktualnych modeli, 12 wycofanych, z cenami i datami; raz na dobę | 0,019 (przebieg 2) |
| ciekawostki (`curiosity`, /responses + web search) | 5 dziedzin × 4 wzorce, 30 tematów, stan dziedziny | 8 faktów z pokryciem, 7 z kanałów, 8 do indeksu, 3 o premierze | 0,067 (232 687 tokenów wejścia, 16 wyszukiwań) |
| bank (ranking) | 8 faktów | 8 ocenionych, 0 wyrzuconych | 0,011 (15 681 tokenów wyjścia — myślenie na głos, patrz §5) |
| notka (`note_tani`, flash) | 1 fakt + brief | 44 słowa | 0,006 |
| factcheck | notka | 1 twierdzenie OBALONE (rating dotyczy wersji, której nikt nie może wywołać) | 0,057 (17 wyszukiwań) |
| naprawa (pro) | zarzut | 60 słów, zdanie o ratingu poprawione | 0,007 |
| factcheck 2 | notka po naprawie | PRZYJĘTA, 0 nowych zarzutów | 0,024 (11 wyszukiwań) |
| publikacja | tekst | wpisany w kompozytor Chrome'a, Substack 200, id 330649917 | 0 |
| cele (szukanie po hasłach) | 5 haseł × 20 trafień | 74 odrzucone jako za stare (nowy filtr), 20 kandydatów, 4/9 warte | 0,013 (19 211 tokenów wyjścia — myślenie) |
| cele (dyskusje z kanału) | 16 cudzych notek | 3/16 warte | 0,002 |
| komentarz (pro) | cel + brief | 16 słów, postawa MECHANIZM | 0,008 |
| factcheck komentarza | 1 twierdzenie | 1 wyszukiwanie, PRZECHODZI | 0,003 (budżet wyszukiwań już działał) |
| polubienia | 6 przycisków w kanale | 2 pierwsze poza rewirem → 0 polubień (pętla ucinała do `ile`; naprawione) | 0 |
| kopia listy subskrybentów | panel | 0 adresów (konto ma 1 subskrybenta darmowego), bez zawieszenia | 0 |
| **razem** | | 1 notka, 1 komentarz | **0,130 USD, 9 wywołań, 0 nieudanych** |

Notka kosztuje około 0,10 USD (z czego 0,08 to dwa factchecki), komentarz
około 0,02 USD, dzień z jedną notką i jednym komentarzem 0,13 USD. Miesiąc
przy 2 notkach i 3–5 komentarzach dziennie mieści się w kilku dolarach,
o ile szukanie ciekawostek (0,067 na 8 faktów, raz na dobę) nie rośnie.

## 3. Gdzie pieniądze przepadały

1. **`DRY_RUN=true` w lokalnym `agent-v2/.env`** — przebieg 1 pominął każde
   płatne wywołanie i przez to dostawał puste odpowiedzi, a licznik prób
   wydarzeń i limit „bank raz na dobę" zapisały jałowe przejścia jako odbyte.
   Koszt: zero pieniędzy, godzina czasu. Przełączone na `false`.
2. **Serwer DeepSeeka ucinał niestrumieniowe odpowiedzi po ~200 s** —
   `RemoteProtocolError: peer closed connection without sending complete
   message body`. Padły: `curiosity` ×4 (przebiegi 2 i 3), `cele` ×4,
   `note_tani` ×1. Każda z tych prób zużyła tokeny po stronie dostawcy o
   nieznanej wysokości (tabela `calls` zapisuje je jako nieudane bez kosztu).
   To był największy pożeracz czasu i jedyny „przepał" o nieznanej kwocie.
   Naprawione strumieniowaniem na obu ścieżkach (`/responses` i
   `/chat/completions`); po poprawce ten sam prompt `curiosity` przeszedł za
   pierwszym razem.
3. **Nieudane szukanie zamykało dzień** — limit „bank raz na dobę" liczył
   także wywołania bez odpowiedzi, a zerwane połączenie zaliczało próbę
   wydarzenia. Skutek: przebieg 2 skończył się bez notki, choć miał budżet.
   Naprawione: limit liczy tylko `ok = 1`, awaria transportu nie jest próbą.
4. **Myślenie na głos w etapach mechanicznych** — DeepSeek V4 rozumuje
   domyślnie na `/chat/completions` i liczy to jako wyjście: 15 681 tokenów
   za ranking ośmiu faktów, 19 211 za ocenę dziewięciu celów, 6 395 za jedną
   odmowę restacku. Zmierzone na małym zadaniu sędziego: flash 707 → 138
   tokenów i 6,1 → 1,9 s po wyłączeniu myślenia; pro 2 785 tokenów i 52 s
   z myśleniem. Naprawione: `config.DEEPSEEK_BEZ_MYSLENIA` wyłącza je dla
   odsiewu, klasyfikacji, banku, celów, restacku, briefu grafiki; pisarz,
   notka, komentarz, synteza i recenzja myślą dalej.
5. **Factcheck bez budżetu wyszukiwań** — 17 wyszukiwań i 206 tys. tokenów
   wejścia na trzy twierdzenia jednej notki (0,057 USD), bo parametr
   ograniczający po stronie DeepSeeka nie działa (sprawdzone wcześniej).
   Naprawione w briefie: jedno wyszukiwanie na twierdzenie plus jedno po
   dokument pierwotny; następny factcheck zrobił 1 wyszukiwanie za 0,003.
6. **Cztery wywołania modelu przy restackach** (0,019 USD) tylko po to, żeby
   odrzucić cztery notki o walutach z kanału konta. Naprawione tanim filtrem
   po znakach niszy kartridża przed modelem (i przed polubieniem).

## 4. Co się psuło poza pieniędzmi

- **Zawieszenie na „kopii listy subskrybentów"** — przebieg 1 wisiał ponad
  8 minut na kroku, którego pętla jest ograniczona do ~2 minut; osobno ten
  sam krok trwa 10 s. Nie powtórzyło się w przebiegach 2 i 5 (watchdog z
  `py-spy` był uzbrojony, nie zadziałał). Przyczyna nieustalona; zostaje na
  liście otwartych spraw z gotowym watchdogiem.
- **Bot nawiguje kartą właściciela** — przy czytaniu statystyk użył
  istniejącej karty Chrome'a (zamiast otworzyć własną), co widać jako
  „przeskok" strony u właściciela. Kosmetyczne, ale warto wiedzieć: w czasie
  publikacji nie należy klikać w tej przeglądarce.
- **Komentarz pod notką sprzed 30 dni** — filtry wieku celu znały tylko
  dolną granicę. Dodana górna: 21 dni (`config.MAKS_WIEK_CELU_DNI`); w
  przebiegu 5 odrzuciła 74 i 78 starych trafień z wyszukiwarki.
- **Polubienia poza tematem** — kolejność w kanale, zero filtra; kanał konta
  testowego jest pełen finansów (subskrypcje z wcześniejszych prób). Po
  filtrze rewiru pętla oglądała tylko pierwsze `ile` przycisków i kończyła z
  zerem; teraz przegląda cały kanał aż do przydziału.
- **Wpis z kanału złożony z samego ogona nazwy** („| AI at Meta") przechodził
  jako temat z czterech „słów". Odsiany.
- **Blokady hostów**: `openai.com` odpowiada czytnikowi bota 403 z
  `cf-mitigated: challenge` (Cloudflare klasyfikuje UA `NIA/1.0` jako
  automat od pierwszego zapytania — to nie jest limit zapytań), `reuters.com`
  401 z DataDome. Awaryjne czytanie szło przez bezgłowe Chromium bez sesji i
  dostawało 0 znaków; prawdziwy Chrome właściciela po CDP czyta te same
  strony (4 602 i 6 136 znaków). Fallback przełączony na `podlacz_sie()`.
  Pozostałe 21 domen dokumentów pierwotnych z kartridża odpowiada 200.
  Wniosek: nie wykluczać, nie udawać przeglądarki — czytać tą, którą się
  publikuje. Reuters jako źródło wtórne i tak przegrywa z dokumentem
  pierwotnym.

## 5. Jakość

**Notka** (60 słów, KONTRAST): liczby z warunkiem („100% on ExploitBench",
„91,5% odbitych jailbreaków"), kontrast „safeguards off / on", poprawione
zdanie o ratingu. Braki: nie nazywa, kto zmierzył (system card OpenAI), a po
naprawie weszło nieobjaśnione słowo z wewnętrznego programu. Źródłem faktu
był blog dostawcy narzędzia, nie strona wytwórcy — trzy z ośmiu faktów miały
takie źródło. Poprawki: blok `glos_notki` kartridża każe nazwać mierzącego
i tłumaczyć kodename; brief ciekawostek silnika każe wpisywać w `url` stronę
wytwórcy z listy domen kartridża.

**Komentarze**: pierwszy (o wskaźniku „containment rate") był trafną uwagą
mechanizmową i przeszedł factcheck po jednej naprawie; drugi (limit
odpowiedzialności w umowach dostawców) jest poprawny, ale krótki i ogólny,
a cel — notka z 22 reakcjami sprzed 14 dni — słaby. Sędzia celów trafnie
odrzucał wpisy o rynkach, polityce i pseudonauce.

**Factcheck jako bramka**: dwa razy z dwóch obalił nieprawdziwe zdanie przed
publikacją (rating „Critical", definicja containment rate). To najdroższa
warstwa i najbardziej wartościowa; budżet wyszukiwań zbija koszt, nie
rezygnując z niej.

**Bank i powtórzenia**: indeks trzyma 8 faktów, jeden zużyty, 7 oddanych do
puli; pamięć notek pilnuje otwarć i rdzeni; wydarzenie GPT-6 Astra zapisane
jako obsłużone z trzema faktami; `wystawione_notki.json` przelicza się
z dziennika. Nic nie powtórzyło się w obrębie testu — próbka za mała, żeby
mówić o dłuższym horyzoncie.

**Statystyki**: `statystyki.jsonl`, `wzrost.jsonl`, `zrodla.jsonl`,
`czytelnicy.jsonl`, `dziennik.jsonl` zapisują się co przebieg (wyświetlenia
notek, subskrybenci, źródła ruchu, czytelnicy). Działa.

## 6. Poprawki, osobno silnik i osobno kartridż

Silnik (gałąź `presety`, commity w kolejności): fallback przez prawdziwego
Chrome'a i odsiew pustych tytułów (0a9fbdf); limit dobowy tylko z udanych
szukań, awaria transportu to nie próba, filtr rewiru dla polubień i
restacków, ponowienia 4×15 s (d88c39e); górna granica wieku celu (479d32a);
strumień na `/responses` (95d3166) i na `/chat/completions` (c7f1313);
brief ciekawostek z domenami kartridża (a618c33); budżet wyszukiwań
w weryfikacji (36e16a4); pętla polubień do przydziału (20ae891); wyłącznik
myślenia dla etapów mechanicznych (8e7e29e).

Kartridż `ai`: notka nazywa mierzącego i tłumaczy kodename (0d5075e).
Kartridż `nia` (lokalny, nieśledzony) dostał tę samą zmianę i został
podłączony na nowo (aktywacja nr 2).

Poza repo: `agent-v2/.env` `DRY_RUN=false`; sesja w
`agent-v2/instancje/nia/storage-state.json` (89 dni).

## 7. Optimum na teraz: jak najtaniej, jak najlepiej

Co już jest po poprawkach: dzień z notką i komentarzem ≈ 0,10 USD (bez
myślenia w sędziach i z budżetem wyszukiwań spodziewane 0,06–0,08).

Co jeszcze warto:

1. **`curiosity` ma 232 tys. tokenów wejścia** — to kontekst 16 wyszukiwań
   wliczany do wejścia. Trzy ruchy: mniej faktów na zamówienie (8 → 5–6 przy
   2 notkach/dobę), krótszy zaczyn z kanałów (30 → 20 tematów) i cache
   promptu (na `/responses` `cache_hit` wraca jako 0 — sprawdzić, czy
   DeepSeek go tam w ogóle liczy).
2. **Factcheck**: po budżecie 1 wyszukiwanie na twierdzenie; następny krok
   to podawać mu `control_url` z indeksu jako pierwszy adres do sprawdzenia.
3. **Sędziowie bez myślenia** — zmierzyć na 20 decyzjach, czy jakość ocen
   celów nie spadła; jeśli spadnie, włączyć myślenie tylko dla `cele`.
4. **Kanał konta**: polubienia i restacki są tak dobre jak kanał. Konto
   testowe subskrybuje finanse; dla kartridża AI trzeba zasubskrybować
   kilkanaście publikacji z rewiru (to praca ręczna właściciela albo
   włączenie `subskrypcje_miesiecznie` w kartridżu).
5. **Ostrzeżenie `[effort] … NIE MA SKUTKU`** przy każdym wywołaniu
   DeepSeeka to szum w logu; do wyciszenia.

## 8. Sprawy otwarte

- przyczyna jednorazowego zawieszenia na kopii listy (watchdog gotowy);
- prawdziwy koszt nieudanych wywołań u DeepSeeka (panel dostawcy);
- test polubień po naprawie pętli (w tym przebiegu było już 0 do zrobienia);
- kartridż nie ma jeszcze pola na górną granicę wieku celu ani na listę
  etapów bez myślenia — dziś to stałe silnika z rozsądnymi domyślnymi.

## 9. Artykuł: „The EU Watermark That Applies Everywhere"

Ścieżka `artykul_z_puli.py --wymus --wyslij`, fakt z indeksu (Anthropic
znakuje każdą odpowiedź Claude'a na świecie, bo nie umie zawęzić znakowania
do UE), bez ponownego szukania.

| Warstwa | Wynik | Koszt |
|---|---|---|
| wybór tematu (`wybor`, pro) | tytuł, pytanie, złamane przekonanie | 0,007 |
| dyskoveria (`/responses`, 14 wyszukiwań) | 6 wyników → 5 źródeł | 0,081 |
| pobieranie | 5/5 OK: eur-lex (587 tys. znaków), anthropic.com, support.claude.com, Komisja, nature.com; zero odbić | 0 |
| klasyfikacja (5 wywołań flash) | materiał dowodowy | 0,023 |
| synteza (pro) | karta | 0,025 |
| „czy jest tu luka" | 3 z 3 filarów, PISZ | 0,018 |
| pisanie (pro, RICH) | 1 058 słów, cel 1 075 | 0,066 |
| recenzja (pro) | uwagi, nic nie blokuje | 0,089 (20 308 tokenów myślenia) |
| forma (pro) | jedna uwaga o fakcie bez pokrycia | 0,095 (23 032 tokeny myślenia) |
| brief okładki (flash) + obraz (gpt-image-1.5) | korytarz serwerowni, bursztynowa lampka, kapiąca rura; zgodny z blokiem `okladka` | 0,004 + 0,040 |
| sprawdzenie faktów po napisaniu (log, nie bramka) | 19 wyszukiwań, odpowiedź narracyjna zamiast JSON → werdykt przepadł | 0,123 |
| publikacja | treść wklejona (1 090 słów, 3 linki), okładka wgrana, przycisk subskrypcji, „Send to everyone now", potwierdzony u Substacka, dodany do promocji | 0 |
| **razem** | | **0,570 USD, 15 wywołań** |

**Jakość.** Otwarcie od konkretnego zapisu (zdanie ze strony pomocy),
mechanizm nazwany raz (podpis pod kodeksem → znak wodny na poziomie modelu),
osobno „co dokumenty ustalają" i „czego nie ustalają", liczba z warunkiem
(20 mln odpowiedzi Gemini, różnice 0,01 i 0,02 punktu procentowego, z
zastrzeżeniem, że to nie Claude), drugi obszar (banery zgody na ciasteczka),
zamknięcie „inna wersja była do zbudowania". Trzy źródła pierwotne. Jak na
0,57 USD i DeepSeeka — dobry tekst w głosie kartridża.

**Wady.**
1. Pod podtytułem stoi zdanie „Figures checked against sources to unknown."
   Synteza wpisała „unknown" w datę najnowszego źródła (strony bez dat), a
   kod wstawiający stopkę sprawdzał tylko, czy pole jest niepuste.
   Naprawione w silniku (stopka tylko dla prawdziwej daty; test). **Zdanie
   w opublikowanym poście trzeba usunąć ręcznie w edytorze Substacka** —
   bot nie ma funkcji edycji posta.
2. „The excerpts I worked from carry no publication dates", „in the pages I
   have" — pierwsza osoba o własnym warsztacie, wprost zakazana w briefie
   pisarza (`pisarz.md`: nigdy „the excerpts", „the sources I can cite").
   Model zignorował zakaz, a recenzja nie zablokowała. Bramka
   `zapowiedziany_akapit_granic` patrzy tylko na początek akapitu, więc
   zdanie w środku przeszło. Do zrobienia: bramka zdaniowa na frazy
   warsztatowe (lista w `jezyki.py`).
3. Sprawdzenie faktów po napisaniu: 0,12 USD za narrację bez JSON-a.
   Naprawione: ratunek JSON-u drugim tanim wywołaniem, jak w ciekawostkach
   (test). Budżet wyszukiwań z briefu nie zmieścił artykułu o kilkunastu
   twierdzeniach — do rozważenia: sprawdzać po napisaniu tylko twierdzenia
   z liczbą lub datą.
4. Recenzja i forma razem 0,18 USD — więcej niż pisanie. `forma` dołączona
   do etapów bez myślenia; recenzja zostaje z myśleniem, bo wnosi uwagi.

## 10. Bilans całego testu

39 wywołań, 0,82 USD, 3 nieudane o nieznanym koszcie (wszystkie przed
strumieniowaniem). Na koncie: 1 notka, 2 komentarze, 2 polubienia, 1 artykuł
z okładką. Po poprawkach spodziewany koszt dnia z 2 notkami i 3–5
komentarzami: około 0,25 USD; artykułu: około 0,40 USD (bez jałowego
factchecku i bez myślenia w formie).
