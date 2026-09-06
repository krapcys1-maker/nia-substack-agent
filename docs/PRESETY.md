# Presety — konsola i kartridż

Stan na 6 września 2026, gałąź `presety`. Angielskie streszczenie stoi
w `presety/README.md`.

## Podział

**Silnik** (`agent-v2/`) jest konsolą. Ma metodę: etapy, bramki, kontrakty
JSON, wzorce tematów, reguły rzetelności, zapory testowe. **Nie ma tematu.**
Od 6 września nisza, kąt redakcyjny, znaki rewiru, hasła, dziedziny,
kalendarz roku, kanały, tożsamość okładki i oświadczenie o autorstwie są
w silniku puste. Bez podłączonego kartridża `run.py` i `artykul_z_puli.py`
odmawiają startu.

**Kartridż** (`presety/<nazwa>/`) jest wszystkim, co odróżnia jedną
publikację od drugiej:

| Plik | Co niesie |
|---|---|
| `preset.toml` | pokrętła (notki/dobę, artykuły/tydzień, komentarze, polubienia, przebiegi, modele per rola, budżety, zegar), konto, temat, źródła, styl |
| `prompty/linia_redakcyjna.md` | co jest tematem, a co nie, i jakie pytania zadawać; czytają skaut, ciekawostki, bank, bramka „warto pisać” |
| `prompty/glos_artykulu.md` | jak ten tytuł pisze długi tekst; czyta pisarz |
| `prompty/glos_notki.md` | jak brzmi notka; czytają briefy notki i myśli |
| `prompty/glos_komentarza.md` | jak brzmi komentarz, odpowiedź, zdanie przy restacku |
| `prompty/okladka.md` | tożsamość wizualna: blok stylu kopiowany dosłownie do promptu obrazu |
| `prompty/kogo_szukamy.md` | pod czyimi postami komentujemy, a pod czyimi nie |
| `prompty/oswiadczenie.md` | publiczne oświadczenie o autorstwie (ustawienie konta) |
| `styl/profil_pozytywny.md`, `styl/profil_negatywny.md` | do czego dąży pisarz i czego mu nie wolno |
| `styl/korpus.txt` (opcjonalnie) | teksty do przypięcia: własne albo o wolnej licencji, z manifestem źródeł `styl/KORPUS_ZRODLA.md` i przypięciami `styl/przypiecia.json` obok (wzór: `presety/ai/styl/`) |

Każdy plik w `prompty/` jest opcjonalny: brak daje w briefie jawne zdanie
zastępcze („preset nie dostarczył...”), nigdy pustkę i nigdy cudzą treść.
Tekst przed pierwszym `---` w pliku bloku jest notatką dla człowieka i do
promptu nie idzie. Ścieżki stylu w `preset.toml` są względem katalogu
kartridża.

## Polecenia

```bash
python narzedzia/presety.py lista                 # kartridże i który podłączony
python narzedzia/presety.py nowy moj-temat        # kopia SZABLON/ do wypełnienia
python narzedzia/presety.py sprawdz ai            # błędy i uwagi, bez płatnych wywołań
python narzedzia/presety.py pokaz ai              # rozwiązane stałe, pochodzenie, bloki
python narzedzia/presety.py podglad ai            # briefy tak, jak zobaczy je model
python narzedzia/presety.py podlacz ai            # aktywacja
python narzedzia/presety.py status
python narzedzia/presety.py odlacz
python narzedzia/presety.py importuj-konfiguracje --nazwa moje   # stary konfiguracja.toml -> kartridż
python narzedzia/presety.py eksportuj ai > kopia.toml            # znormalizowany TOML, bez sekretów
```

Po `podlacz` i `odlacz` **procesy uruchamia się od nowa**. Kontekst jest
czytany raz, przy starcie. Zegary systemd buduje się z kartridża:
`python narzedzia/jednostki.py --katalog /srv/bot --uzytkownik bot`.

## Co się dzieje przy podłączeniu

1. Kartridż jest czytany i sprawdzany **w całości**: pola wymagane (bez nich
   silnik nie ma czym pracować), znaczniki `<<...>>` z szablonu, reguły
   strukturalne tematu (pula haseł szersza niż jeden przebieg, każde hasło ze
   znakiem rewiru, co najmniej 10 komórek siatki na notkę dziennie), pliki
   profili stylu, dostawcy modeli, spójność zegara. Każdy błąd zatrzymuje
   `podlacz` zanim cokolwiek zostanie zapisane. Poprzedni kartridż zostaje
   podłączony bez zmian.
2. Powstaje katalog instancji (`agent-v2/instancje/<nazwa>/`; inna nazwa przez
   `--instancja` daje świeży katalog danych z tym samym kartridżem).
3. Wskaźnik aktywacji jest zapisywany atomowo.
4. Przy każdym starcie `config.py` czyta wskaźnik, wczytuje kartridż z dysku,
   porównuje odcisk SHA-256 pól i bloków z odciskiem z aktywacji, **przywraca
   neutralną bazę silnika** i dopiero na nią nakłada kartridż. Kartridż
   zmieniony po aktywacji zatrzymuje start z komunikatem, co zrobić.

Stąd własność, o którą chodziło w audycie: kartridż B skompilowany po
używaniu A daje **ten sam kontekst** co B na czystym silniku. Pilnuje tego
`agent-v2/tests/test_presety.py`.

## Co się dzieje przy odłączeniu

`odlacz` usuwa wskaźnik i dopisuje wpis do dziennika instancji. Dane
instancji zostają; ponowne `podlacz` tego samego kartridża je wznawia. Bez
wskaźnika:

- `run.py` i `artykul_z_puli.py` odmawiają startu (kod wyjścia 3, komunikat
  z poleceniami). Silnik nie ma do czego wracać.
- `alarm.py` zgłasza kontrolę `preset` jako pierwszą.
- Zegary systemd trzeba wyłączyć ręcznie (`odlacz` wypisuje polecenie).

W **darmowym teście** (proces uruchomiony z `agent-v2/tests/`) brama milczy,
tak samo jak zapora płatnych wywołań. Testy pracują na silniku, nie na tym,
co operator akurat podłączył. Zmienna `AGENT_V2_PRESET=presety/ai` podłącza
kartridż jednemu procesowi bez wskaźnika (podgląd, testy).

## Skąd biorą się dane

- **Sygnały** (o czym mówi się w tym tygodniu): `zrodla.kanaly_youtube`
  (identyfikatory `UC...`, czytane po RSS) i `zrodla.kanaly_rss` (blogi
  laboratoriów, listy publikacji, RSS 2.0 lub Atom). Silnik przeplata źródła
  po równo, więc lista z pięćdziesięcioma wpisami dziennie nie zagłusza
  dziesięciu kanałów wideo. Sygnał nigdy nie jest źródłem: tytuł mówi, gdzie
  patrzeć, dokument trzeba znaleźć osobno.
- **Dowody** (czym potwierdzamy): research z wyszukiwaniem w sieci;
  `zrodla.domeny_preferowane` mówi mu, na których hostach leżą dokumenty
  pierwotne tej dziedziny; `zrodla.blokowane_hosty` mówi, których nie czytać.
- **Stan dziedziny**: raz na dobę jedno wywołanie z wyszukiwaniem o to, co
  jest aktualne (`stan_dziedziny.o_co_pytac`); odpowiedź pamięta pytanie,
  więc zmiana pytania ją unieważnia.

## Co jest izolowane, a co celowo wspólne

| Izolowane per instancja | Wspólne |
|---|---|
| baza, bank pomysłów, indeks kandydatów, zużyte fakty, przegrane tematy | klucze API (`agent-v2/.env`) |
| cache etapów (`cache/<etap>.<odcisk>.json`) | sesja przeglądarki i profil Chrome |
| stan dziedziny (pamięta pytanie) | kod, prompty silnika, wzorce tematów |
| oczekujący artykuł i kolejka promocji (znacznik `instancja`) | |
| dziennik działań, czytelnicy, obserwowani | |

Nowa instancja nie pamięta komentarzy poprzedniej i może wrócić pod ten sam
post. Wznowienie tej samej instancji pamięta.

## Kartridż `ai`

`presety/ai/` jest kompletny i sprawdzony bez płatnych wywołań: temat, 26
haseł, 32 dziedziny, przykłady, rytm roku, 11 kanałów YouTube sprawdzonych po
RSS, 6 kanałów RSS, 15 hostów preferowanych, własne profile stylu i siedem
bloków promptów. Dwie notki dziennie, jeden artykuł we wtorek, trzy przebiegi
dziennie, komentarze 3–5, polubienia 5–8, obserwacje i subskrypcje wyłączone,
pisarz `claude-fable-5-1`, notki `claude-opus-5`. Przed podłączeniem podmień
`[konto]`. Kolejny temat robi się z `nowy <nazwa>` i szablonu.

## Czego jeszcze nie ma

- Wymiany kontekstu w pracującym procesie: po przełączeniu nowy proces.
- Walidacji kluczy u dostawców: `sprawdz` mówi tylko, których brakuje.
- Osobnego bloku dla restacku i odpowiedzi: dzielą `glos_komentarza`.
- `konfiguracja.toml` jest nadal czytany, gdy kartridża nie ma, ale sam z
  siebie nie daje tematu: pola tematu i tak trzeba wypełnić.

## Odłączanie i świeży bot (po audycie z 6 września 2026)

Cztery gwarancje, każda z testem w `agent-v2/tests/test_swiezy_bot_po_odlaczeniu.py`:

1. **Odłączenie unieważnia pracujący proces.** `odlacz` usuwa wskaźnik, a każde
   płatne wywołanie (`llm._preflight`) i każdy zapis na koncie
   (`browser.naprawde_wyslac`) sprawdza przed wykonaniem, czy wskaźnik nadal
   wskazuje ten sam preset i tę samą instancję. Stary proces po `odlacz` albo
   po `podlacz` innego presetu dostaje odmowę przy następnym koszcie
   i następnej publikacji. Proces trzeba i tak uruchomić od nowa, ale nie
   zdąży już nic wydać ani wysłać.
2. **`AGENT_V2_PRESET` to podgląd.** Proces uruchomiony ze zmienną ma kontekst
   presetu (prompty, podgląd, testy), ale nie ma prawa do płatnych wywołań ani
   publikacji. Produkcja wymaga aktywacji wskaźnikiem. `status` ostrzega, gdy
   zmienna jest w środowisku.
3. **Instancja ma właściciela.** Pierwsze `podlacz` zapisuje w katalogu
   instancji `wlasciciel.json` (preset, uchwyt konta). Inny preset albo inne
   konto na tym samym `--instancja` dostaje odmowę i radę, żeby wziąć nową
   nazwę. `--przejmij` to jawna decyzja, zapisana w dzienniku instancji.
4. **Bez kartridża nie wraca stary temat.** Bez aktywacji silnik nie czyta
   `agent-v2/konfiguracja.toml` (poza darmowym testem i jawnym
   `AGENT_V2_KONFIGURACJA_TOML=1`). Droga na stałe: `importuj-konfiguracje`.

Dwie reguły o stylu:

- **Pusty `styl.korpus` znaczy brak korpusu.** Kartridż z pustym polem
  wskazuje własny `styl/korpus.txt`; jeśli go nie ma, pisarz dostaje zero
  przykładów. Domyślny katalog silnika (`agent-v2/prompts/styl/`) nie jest
  dla kartridża zapasem.
- **Ścieżki stylu w katalogu presetu rozwiązują się tylko w tym katalogu.**
  Brak pliku w paczce to błąd `sprawdz`, a nie plik o tej samej nazwie
  z repozytorium. Plik wspólny z repozytorium wybiera się jawnie:
  `profil_pozytywny = "repo:style-profiles/ARTICLE_STYLE_PROFILE_V1.md"`.

Odcisk presetu obejmuje pola (jak w TOML-u, ze ścieżkami względnymi), bloki
promptów i skróty plików stylu z katalogu presetu (profile, korpus,
przypięcia). Ten sam kartridż skopiowany gdzie indziej ma ten sam odcisk;
zmieniony profil to inny odcisk i odmowa startu do czasu `podlacz`.

Czego ta gałąź nadal nie daje (F07–F13 audytu): eksportu pełnej paczki,
osobnego profilu Chrome i nazw usług na klon, wspólnego limitu rachunku
między instancjami, cache zadań z hashem wejścia. To sprawy otwarte.

## Konto z instalacji, nie z kartridża

Kartridż ma być wspólny: ten sam `ai` może pracować u wielu osób. Konto jest
jedno, więc siedzi w `agent-v2/.env`:

```
SUBSTACK_HANDLE=prawdziwy-uchwyt
NAZWA_MARKI=Prawdziwa nazwa publikacji
```

Obie zmienne nadpisują `[konto]` z kartridża, przy starcie i w każdym
`sprawdz`/`podlacz`. Kartridże w repozytorium zostają z placeholderem
(audyt tego pilnuje), a `podlacz` odmawia, dopóki uchwyt albo marka jest
placeholderem. Samo `sprawdz` tylko ostrzega, żeby dało się ocenić kartridż
bez konta. Właściciel instancji zapisuje uchwyt faktycznie użyty.

Ścieżka dla kogoś z zewnątrz: sklonować repozytorium, `cp .env.example
agent-v2/.env` i wpisać klucze, uchwyt i nazwę, `podlacz ai`, `browser.py
sesja`, `alarm.py`. Repozytorium zostaje czyste; zmiany robi się u siebie.

