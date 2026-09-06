# Audyt gałęzi `presety`: odłączanie presetu, czystość bota i osobne klony

Data: 6 września 2026. Repozytorium: `D:\Nia bot`. Zbadana wersja: `adcac837844b7b93e87b2dee5fc898e766389575`, gałąź `presety`, zgodna podczas audytu ze zdalną `publiczne/presety`.

**Raport bez wdrażania zmian.** Kod, presety, lokalna aktywacja, konfiguracja, klucze i dane robocze użytkownika pozostały bez zmian. Próby wymagające zapisu wykonano w jednorazowej kopii plików z badanego commita, poza repozytorium. Nie uruchamiano publikowania ani płatnych wywołań modeli.

**1. Odpowiedź na Twoje pytanie**

**Gałąź ma już sensowną podstawę wymiennych presetów, ale samo `odlacz` nie daje jeszcze gwarancji „mam całkowicie czystego bota”.** W szczególności nie zatrzymuje pracującego procesu, nie odcina aktywacji przez środowisko i nie chroni przed podpięciem innego tematu do katalogu danych poprzedniej instancji. Jest też rzeczywista droga powrotu starego korpusu stylu.

Jednocześnie **nie jest prawdą, że nowy preset zawsze dziedziczy poprzedni temat**. Prawidłowo uruchomiony nowy proces, z kompletnym presetem B i nowym, nieużywanym identyfikatorem instancji, dostaje osobny bank i osobne kolejki. Test składania konfiguracji B po A również przeszedł: ustawienia objęte mechanizmem resetowania są takie same jak dla B nakładanego na bazę silnika. To istotna poprawa względem wcześniejszego audytu.

**Na obecnym etapie rekomenduję zachować czystą, wersjonowaną bazę kodu i uruchamiać nową redakcję w świeżej kopii z Gita, z własną instancją i pełnym katalogiem presetu.** Nie kopiować całego używanego katalogu bota. Sam klon nie wystarczy jednak do rozdzielenia przeglądarki, nazw usług i wspólnego rachunku API. Te granice trzeba zapewnić osobno. Docelowo warto dopracować obecny mechanizm instancji, zamiast utrzymywać odrębne wersje kodu dla każdego tematu.

| Operacja | Co faktycznie otrzymujesz | Ocena |
|---|---|---|
| Świeża kopia śledzonych plików, bez aktywacji i starej konfiguracji | Pusta nisza; oba główne wejścia odmawiają pracy kodem 3 | Działa |
| Zatrzymanie A, kompletny B, nowy identyfikator instancji, nowy proces | Osobna pamięć redakcyjna i konfiguracja B | Podstawa izolacji działa; pozostają granice konta i kosztów |
| Samo `odlacz` podczas pracy A | Wskaźnik znika, proces nadal ma A w pamięci | Brak gwarancji zatrzymania |
| `odlacz`, ale proces startuje z `AGENT_V2_PRESET` | Preset może zostać aktywowany mimo braku wskaźnika | Brak gwarancji pustego stanu |
| B podłączony z tym samym `--instancja`, którego używał A | Ten sam katalog, bank i dostępny oczekujący artykuł A | Mieszanie stanu potwierdzone próbą |
| B z `styl.korpus = ""` i `wymagaj_korpusu = false` w używanym katalogu | Może pobrać stary domyślny korpus | Deklaracja nie oznacza „nie używaj korpusu” |
| Skopiowanie całego działającego folderu | Kopia także lokalnej konfiguracji, danych i potencjalnie sekretów | Nie jest czystym klonem |
| Świeży klon Gita na tym samym koncie systemowym | Oddzielne pliki, ale możliwy wspólny Chrome/CDP i kolizje usług | Częściowa izolacja |

Trzeba rozdzielić trzy znaczenia „czysty”: brak aktywnej redakcji, brak wpływu poprzedniej redakcji na nową oraz fizyczny brak archiwalnych plików. Pierwsze dwa są wymaganiami poprawnego działania. Trzecie nie musi być: archiwum A może zostać na dysku, pod warunkiem że B nie ma do niego automatycznej drogi. Usunięcie poprzednich artykułów z dysku nie jest potrzebne do prawidłowej izolacji.

**2. Co sprawdziłem i co jest obecnie lokalnie aktywne**

Potwierdziłem lokalną gałąź i jej zgodność ze zdalnym commitem po pobraniu informacji o `presety`. Różnica względem `main` obejmuje 103 pliki. Prześledziłem ładowanie konfiguracji, aktywację i odłączenie, źródła stylu, składanie promptów, pamięć researchu i banku, cache, kolejki artykułów, rozliczanie wywołań, sesję przeglądarki oraz generator harmonogramów.

Z dokładnie badanego commita powstała tymczasowa kopia przez `git archive`: 339 plików śledzonych w repozytorium, bez lokalnych `.env` i wskaźnika aktywacji. To badanie zawartości, którą daje świeży checkout, a nie uruchomienie produkcyjnej instalacji na serwerze. W tej kopii uruchomiłem istniejący `agent-v2/tests/test_presety.py`: **161 sprawdzeń zakończonych powodzeniem, 0 niepowodzeń**. Dołożyłem **19 prób diagnostycznych**, opisanych na końcu raportu. Korzystały z tymczasowych danych, fikcyjnych wpisów kosztów i blokady połączeń sieciowych.

Ważne ustalenie z odczytu rzeczywistego katalogu użytkownika:

| Element | Stan podczas audytu | Znaczenie |
|---|---|---|
| Lokalny wskaźnik aktywacji | Preset `nia`, instancja `nia`, aktywacja nr 2 | Lokalnie nie jest wskazany katalog `presety/ai` |
| `presety/nia` | Wariant presetu AI; względem `presety/ai` różni się plikiem TOML | Wszystkie porównane pliki promptów i stylu są identyczne |
| Odcisk lokalnej aktywacji | Zgodny z tym, co obecny loader sprawdza | Nie oznacza pełnej integralności korpusu i profili; problem opisany niżej |
| `agent-v2/konfiguracja.toml` | Nadal istnieje; stara nisza dotyczy raportowania, audytu i regulowania danych spółek | Po odłączeniu konfiguracja może zostać ponownie wczytana |
| `agent-v2/prompts/styl/` | Nadal zawiera `article_style_samples_v1.txt` i `przypiecia.json` | Jest dostępny dawny domyślny korpus; suma całego pliku zgadza się z przypięciem |
| `agent-v2/data` i `agent-v2/instancje/nia` | Istnieją dane lokalne; odpowiednio 14 plików i 28 plików w drzewie instancji | Używany folder zawiera więcej niż czysta gałąź |
| `.env` w katalogu głównym oraz `agent-v2/.env` | Oba pliki istnieją | Sprawdzono istnienie, bez wypisywania ich zawartości lub kluczy |

Śledzony preset `ai` zawiera przykładowe konto `your-handle`; lokalny `nia` ma inne ustawienie. **Świeży klon samej gałęzi nie odtworzy lokalnego `nia` ani jego konfiguracji konta.** Przeniesienie tej redakcji wymaga pełnego katalogu presetu i osobnego przygotowania środowiska. To prawidłowy rozdział materiałów, o ile operator o nim wie.

Nie stwierdzam, że obecny aktywny `nia` faktycznie korzysta ze starego korpusu. Ma jawnie wskazany korpus w swoim katalogu. Problem dotyczy następnego presetu z pustą lub niepełną konfiguracją stylu oraz odłączenia bez usunięcia ścieżki zgodności.

**3. Co na tej gałęzi zostało rzeczywiście poprawione**

Nie należy ponownie przypisywać projektowi wszystkich braków z [audytu z 5 września](</D:/Nia bot/analizy/2026-09-05-czystosc-presety/RAPORT.md>). Najważniejsze zmiany są funkcjonalne:

| Obszar | Obecne rozwiązanie | Ocena |
|---|---|---|
| Temat | Nisza, kąt redakcyjny, znaczniki, hasła, dziedziny i rytm roku mogą pochodzić z presetu; podstawowe pola tematu są puste w bazie | Dobry kierunek i działający reset |
| Głos redakcji | Siedem bloków promptów, opis stylu, pozytywny i negatywny profil oraz własny korpus | Preset AI przenosi faktyczny głos, a nie tylko nazwę tematu |
| Konfiguracja B po A | Przywrócenie bazy przed nałożeniem następnego presetu | Potwierdzone dla ustawień objętych mechanizmem |
| Pamięć | `DATA_DIR` przenoszony do katalogu instancji przed importem pozostałych modułów | Nowa instancja faktycznie oddziela bank, bazę i kolejki |
| Oczekujący artykuł | Znacznik `instancja` i odrzucanie znacznika innej instancji | Poprawione; nadal brakuje ochrony przed ponownym użyciem tej samej nazwy |
| Cache | Odcisk presetu w nazwie wyniku etapu | Odcina część wyników poprzedniej konfiguracji; nie identyfikuje konkretnego zadania |
| Stan dziedziny | Cache pamięta pytanie i sprawdza jego zgodność | Zmiana pytania unieważnia poprzednią odpowiedź |
| Źródła | RSS/Atom, kanały YouTube, preferowane i blokowane hosty | Źródła można dostarczyć wraz z tematem |
| Plan pracy | Liczby notek i artykułów, godziny, dni publikowania; obsługa wyłączenia wybranych treści przez zero | Dużo bliżej kompletnego presetu |
| Aktywacja | Walidacja przed zapisem i atomowa wymiana wskaźnika | Błędny preset odrzucony przez `podlacz` nie usuwa działającego wskaźnika A |
| Brak presetu | Główne wejścia `run.py` i `artykul_z_puli.py` odmawiają pracy | Potwierdzone w świeżym procesie |

Podstawa w kodzie: [ładowanie kontekstu](</D:/Nia bot/agent-v2/config.py:3394>), [przekierowanie danych](</D:/Nia bot/agent-v2/config.py:3003>), [pola konfiguracji](</D:/Nia bot/agent-v2/konfiguracja.py:418>), [bloki przekazywane do promptów](</D:/Nia bot/agent-v2/stages.py:298>), [stan dziedziny](</D:/Nia bot/agent-v2/aktualne_modele.py:107>).

To nie jest jeszcze w pełni niezależny moduł redakcji. Jednak przebudowa od zera nie jest potrzebna: obecne katalogi instancji, loader i mechanizm bloków są odpowiednią bazą do domknięcia granic.

**4. Problemy, które uniemożliwiają gwarancję czystości**

Priorytet **P1** oznacza problem do rozwiązania przed swobodnym przełączaniem redakcji lub równoległą pracą klonów. **P2** oznacza istotny brak przenośności, przewidywalności albo ochrony jakości. Nie każdy problem występuje w każdej instalacji; przy każdym podaję warunek.

**F01 — P1. Odłączenie zmienia plik, ale nie odbiera uprawnień działającemu procesowi.**

`odlacz()` dopisuje zdarzenie do dziennika i usuwa wskaźnik. Konfiguracja była już jednak wczytana przy imporcie. `wymagaj_aktywnego()` sprawdza obiekt `cfg.PRESET_AKTYWACJA` znajdujący się w pamięci, bez ponownego sprawdzenia wskaźnika. Nie ma mechanizmu, który przed kolejnym płatnym etapem lub publikacją potwierdza, że ta aktywacja nadal obowiązuje.

W próbie P17 użyłem rzeczywistego modułu `config`, bez obejścia bramy dla testów: aktywowałem preset w tymczasowej instalacji, wczytałem konfigurację, odłączyłem preset. Wskaźnik zniknął, lecz `config.PRESET` i nisza zostały, a brama nadal pozwalała przejść. P02 wykazała ten sam problem na minimalnym kontekście.

**Skutek:** A może skończyć tekst lub podejść do publikacji po komunikacie „odłączono”. Gdy operator od razu uruchomi B, blokada w katalogu danych A nie jest wspólną blokadą dla nowej instancji B. Możliwe są dwa różne konteksty pracujące nad tym samym kontem przeglądarki. Nie wykonałem rzeczywistej publikacji; potwierdziłem brak unieważnienia i ścieżkę w kodzie.

Dokumentacja uczciwie wymaga restartu, a `podlacz` wypisuje polecenie zatrzymania procesów. Nie jest to jednak gwarancja samej operacji. Komunikat `odlacz` przypomina tylko o wyłączeniu timerów. Zatrzymanie timera nie stanowi potwierdzenia zakończenia usługi, którą timer zdążył już uruchomić.

**Zmiana:** aktywacja powinna mieć identyfikator generacji oraz stan `active/draining/detached`. Odłączenie unieważnia generację, blokuje nowe zadania, czeka na bezpieczne zakończenie lub zatrzymuje pracowników i potwierdza brak trwających operacji. Każde płatne wywołanie i zewnętrzny zapis sprawdza tę generację. Potrzebna jest wspólna kontrola procesu wykonującego akcje na danym koncie. Operacji już wysłanej do serwisu zewnętrznego nie da się odwołać samym usunięciem pliku — wynik takiej operacji trzeba rozliczyć i zapisać.

Źródła: [odłączenie](</D:/Nia bot/agent-v2/preset.py:777>), [brama](</D:/Nia bot/agent-v2/preset.py:817>), [start procesu](</D:/Nia bot/agent-v2/run.py:2295>), [lokalna blokada](</D:/Nia bot/agent-v2/run.py:131>), [komunikat konsoli](</D:/Nia bot/narzedzia/presety.py:259>).

**F02 — P1. Aktywacja przez środowisko omija znaczenie „odłączono”.**

`AGENT_V2_PRESET` ma pierwszeństwo przed wskaźnikiem. Tworzy aktywację ze źródłem `srodowisko` i nazwą instancji `podglad-...`, ale sama ta nazwa nie wymusza trybu bez publikowania ani bez kosztów. Brama dopuszcza taki obiekt także w zwykłym procesie. P03 i P19 potwierdziły aktywację oraz zgodę bramy przy nieistniejącym wskaźniku.

`status` odczytuje przede wszystkim wskaźnik. Może więc powiedzieć „brak aktywnego presetu — silnik nie wystartuje”, podczas gdy uruchomiony ze zmienną proces ma aktywny kontekst. Nie sprawdzałem wartości lokalnych plików `.env`; nie twierdzę, że to obejście jest obecnie używane u Ciebie.

**Zmiana:** oddzielić podgląd od aktywacji produkcyjnej. Podgląd powinien otrzymać kontekst pozbawiony uprawnień do płatnych wywołań i zewnętrznych zapisów. Produkcja powinna wymagać ważnej, zarejestrowanej aktywacji. `status` ma pokazywać efektywne źródło konfiguracji, nadpisania środowiska i pracujące procesy, a nie sam plik.

Źródła: [pierwszeństwo środowiska](</D:/Nia bot/agent-v2/preset.py:704>), [status](</D:/Nia bot/narzedzia/presety.py:271>).

**F03 — P1. Instancja jest nazwą katalogu, a nie egzekwowanym właścicielem danych.**

`podlacz` pozwala wskazać istniejący identyfikator instancji. Nie wymaga zgodności właściciela katalogu z presetem, tematem ani kontem. Domyślnym identyfikatorem jest nazwa presetu. Zmienienie tematu i ponowne użycie tej nazwy również wznawia poprzednie dane.

W P04 aktywowałem A w instancji `shared`, zapisałem oznaczony fakt i oczekujący artykuł, a następnie podłączyłem B również jako `shared`. B czytał fakt A, a czytnik kolejki zwrócił artykuł A. Ochrona artykułu sprawdza tylko napis `instancja`; oba presety miały ten sam napis. P05 z nowym identyfikatorem B dała pusty bank i pustą kolejkę, zachowując archiwum A.

**Skutek:** instrukcja „daj nową nazwę” działa, ale system nie egzekwuje, że nazwa naprawdę jest nowa. Dotyczy to również zmiany ustawienia konta we wcześniej używanej instancji. Powrót do A powinien wznawiać A; rozpoczęcie nowej redakcji powinno wymagać świeżego stanu. Obecna komenda nie rozróżnia tych zamiarów wystarczająco mocno.

**Zmiana:** manifest instancji z niezmiennym identyfikatorem redakcji, identyfikatorem konta oraz historią wersji presetu. Tryb „nowa instancja” odmawia, jeśli katalog już istnieje. Tryb „wznów” wymaga zgodnego właściciela. Zmiana tematu lub konta prowadzi domyślnie do nowej instancji. Kolejka zapisuje ponadto wersję presetu i identyfikator aktywacji; tekst po zmianie stylu wymaga ponownej oceny, zamiast automatycznej wysyłki. Nie każda korekta godziny publikacji musi kasować cały bank — potrzebna jest jawna klasyfikacja zmian.

Źródła: [podłączanie](</D:/Nia bot/agent-v2/preset.py:739>), [znacznik artykułu](</D:/Nia bot/agent-v2/stages.py:3250>), [warunek odczytu](</D:/Nia bot/agent-v2/stages.py:3280>), [indeks banku](</D:/Nia bot/agent-v2/stages.py:7188>).

**F04 — P2. Po odłączeniu wraca ścieżka starej konfiguracji.**

Przy braku aktywacji `config.py` nadal czyta `agent-v2/konfiguracja.toml`. Lokalnie ten plik zawiera poprzedni temat związany z raportowaniem i audytem danych spółek. To nie jest wyłącznie historyczny komentarz w kodzie: zawartość ponownie trafia do konfiguracji procesu.

P18 potwierdziła zachowanie na sztucznym starym temacie: po odłączeniu nisza była niepusta. **Główne `run.main()` nadal odmówiło pracy kodem 3.** Nie jest więc poprawnym wnioskiem, że stary TOML sam uruchamia publikowanie. Prawidłowy wniosek brzmi: stan bez aktywacji nie jest neutralny dla wszystkich importerów konfiguracji, narzędzi i funkcji pomocniczych.

**Zmiana:** odczyt starego TOML-a wyłącznie w jawnej komendzie migracji. Zwykły start bez aktywacji powinien budować kontekst bez redakcji, a funkcje wymagające redakcji powinny dostawać błąd „brak kontekstu”. Zachowanie pliku jako archiwum jest dopuszczalne; automatyczny fallback nie powinien go wybierać.

Źródło: [gałąź bez aktywacji](</D:/Nia bot/agent-v2/config.py:3450>).

**F05 — P1. Pusty korpus nie znaczy „bez korpusu”; poprzedni styl może wrócić.**

Łańcuch jest konkretny:

1. Baza silnika wybiera pierwszy plik `.txt` z `agent-v2/prompts/styl/`.
2. `styl.korpus = ""` pozostawia tę domyślną ścieżkę.
3. `styl.wymagaj_korpusu = false` oznacza „brak pliku jest dopuszczalny”.
4. Gdy plik i przypięcia istnieją, `przyklady_albo_pusto()` nadal ładuje przykłady.

P10 użyła rozpoznawalnego, sztucznego korpusu A i poprawnych przypięć. Preset B deklarował pusty korpus i brak wymogu. Wynik: pięć przykładów A. To potwierdzony transfer materiału stylu, bez angażowania modelu.

W Twoim rzeczywistym katalogu domyślny korpus i przypięcia nadal istnieją. W świeżej kopii śledzonych plików ich nie ma. **Ten sam preset B może więc dostać inny materiał do pisania zależnie od tego, czy został uruchomiony w używanym folderze, czy w świeżym klonie.** Własny, poprawnie wskazany korpus `nia`/`ai` omija tę konkretną ścieżkę.

Dodatkowa niejednoznaczność: ścieżka względna jest interpretowana względem presetu, jeśli plik tam istnieje; w przeciwnym razie może zostać rozwiązana względem repozytorium. Brak zasobu w paczce powinien być brakiem zasobu, a nie okazją do znalezienia pliku o tej samej nazwie gdzie indziej.

**Zmiana:** osobne ustawienie użycia korpusu, np. `tryb = "brak" | "wskazany"`. `brak` zawsze daje zero przykładów, nawet gdy na dysku są stare pliki. `wskazany` wymaga jawnego pliku i poprawnych przypięć. Puste pole nie powinno oznaczać automatycznego wyszukiwania. Ścieżki materiałów przenośnego presetu rozwiązywać wyłącznie względem jego katalogu; zasoby wspólne dopuszczać tylko przez jawny, nazwany wybór.

Źródła: [wybór domyślnego pliku](</D:/Nia bot/agent-v2/config.py:55>), [znaczenie pustego pola](</D:/Nia bot/agent-v2/konfiguracja.py:805>), [rzeczywiste ładowanie przykładów](</D:/Nia bot/agent-v2/style.py:163>), [rozwiązywanie ścieżek](</D:/Nia bot/agent-v2/preset.py:271>).

**F06 — P1 dla spójności głosu. Odcisk i sprawdzenie presetu nie obejmują całej treści, którą dostaje pisarz.**

Odcisk obejmuje pola TOML-a i siedem bloków promptów. Pola stylu zawierają ścieżki. **Nie obejmuje zawartości profilu pozytywnego, profilu negatywnego, korpusu ani przypięć.** Zmiana pliku profilu może więc zmienić głos bez zmiany odcisku aktywacji.

P06 zmieniła tylko profil pozytywny: odcisk pozostał taki sam, a aktywacja została przyjęta. P07 zmieniła korpus bez aktualizacji przypięć: odcisk nadal był taki sam, `preset.sprawdz()` nie zgłosił błędów, a rzeczywisty loader stylu zakończył się `StyleError`.

Kontrola przypięć w `style.load_examples()` jest dobra i trzeba ją zachować. Problem polega na tym, że `sprawdz`/`podlacz` kontroluje głównie istnienie plików, więc obietnica kompletności jest szersza niż wykonana kontrola. Błąd może ujawnić się dopiero po wykonaniu innych etapów. W audycie nie płacono za te etapy; wskazuję ryzyko wynikające z kolejności sprawdzania.

Jest również odwrotna niespójność: w P09 skopiowanie identycznego katalogu presetu pod inną ścieżkę zmieniło odcisk, bo ścieżki stają się bezwzględne. Zmiana treści stylu bywa niewidoczna, a sama relokacja plików bywa traktowana jako zmiana presetu.

**Zmiana:** dwa identyfikatory. Pierwszy opisuje przenośną paczkę: znormalizowany manifest, względne ścieżki i hashe zawartości wszystkich używanych zasobów. Drugi opisuje rozwiązany kontekst wykonania: paczka, wersja silnika, efektywnie wybrane modele i parametry. Pełną walidację przypięć wykonać przed aktywacją i przed pierwszym kosztem. Uruchomiony proces powinien korzystać z niezmiennej wersji zasobów, aby podczas pracy nie mieszać starego briefu z nowym profilem.

Źródła: [obliczanie odcisku](</D:/Nia bot/agent-v2/preset.py:231>), [kontrola plików stylu](</D:/Nia bot/agent-v2/preset.py:511>), [pełna kontrola korpusu](</D:/Nia bot/agent-v2/style.py:116>).

**F07 — P2. Eksport TOML-a nie jest eksportem samodzielnego presetu.**

`eksportuj()` świadomie zapisuje wyłącznie pola. Komentarz informuje o pozostawieniu bloków w katalogu źródłowym, ale funkcja nie daje paczki nadającej się do niezależnego podłączenia do czystego bota.

P08: oryginalny preset miał siedem bloków, ponownie wczytany plik eksportu miał zero. Trzy ścieżki do materiałów stylu były bezwzględne. Odcisk oryginału i odtworzonego presetu nie był równy. Jeśli stara lokalizacja nadal istnieje, eksport może dalej korzystać z jej materiałów; jeśli nie istnieje, przeniesienie się nie powiedzie. P09 pokazuje dodatkowy problem ze stabilnością odcisku całego katalogu po przeniesieniu.

**Zmiana:** eksport kompletnego katalogu lub archiwum: manifest, bloki, profile, opcjonalny korpus, przypięcia i informacje o kompatybilnej wersji silnika. Bez danych instancji, cookies i kluczy. Import do katalogu tymczasowego, walidacja całej paczki, a dopiero potem udostępnienie do aktywacji. Eksport samych ustawień może zostać, ale powinien być nazwany „eksport konfiguracji”.

**Obejście dziś:** przenosić cały katalog presetu, a na docelowej instalacji sprawdzić i ponownie podłączyć go. Nie przenosić samego aktywnego wskaźnika i nie traktować `kopia.toml` jako pełnego backupu głosu redakcji.

Źródło: [eksport](</D:/Nia bot/agent-v2/preset.py:895>).

**F08 — P1 przy klonach i różnych kontach. Klon repozytorium nie izoluje całej przeglądarki.**

Trzeba skorygować uproszczenie w dokumentacji. `storage-state.json` jest liczony z `config.DATA_DIR`, więc **plik sesji jest per instancja**. Natomiast profil Chrome wskazuje `Path.home() / "substack-agent-chrome"`, a port CDP ma stałą wartość `9222`. Dwa klony uruchomione na tym samym koncie systemowym mogą połączyć się z tym samym Chrome. P13 potwierdza te trzy właściwości kodu.

Strażnik konta nie daje pełnej gwarancji tożsamości sesji: odpytuje publiczny profil wskazanego w konfiguracji uchwytu, a przy błędzie lub braku odpowiedzi wypisuje ostrzeżenie i idzie dalej. Kontrola jest zapamiętywana na proces. Z kodu nie wynika wiarygodny dowód, że sprawdzono tożsamość zalogowanego użytkownika. Nie testowałem odpowiedzi serwisu na żywym koncie, dlatego nie opisuję konkretnego przypadku publikacji z niewłaściwego konta jako zdarzenia, które już zaszło.

**Zmiana:** osobny profil i endpoint przeglądarki dla tożsamości konta, jawne przypisanie instancji do konta oraz potwierdzenie zalogowanej tożsamości przed zewnętrznymi zapisami. Brak potwierdzenia powinien zatrzymać zapis. Dla tego samego konta wiele redakcji może używać wspólnej usługi wykonującej akcje, ale musi ona serializować zapisy i sprawdzać aktywację. Klony na oddzielnych maszynach lub w rozdzielonych środowiskach sieciowych nie współdzielą lokalnego portu; samo rozdzielenie katalogów tego nie zapewnia.

Źródła: [plik sesji i port](</D:/Nia bot/agent-v2/browser.py:27>), [profil Chrome](</D:/Nia bot/agent-v2/browser.py:429>), [wybór połączenia](</D:/Nia bot/agent-v2/browser.py:588>), [kontrola konta](</D:/Nia bot/agent-v2/browser.py:69>).

**F09 — P1 dla wspólnego rachunku. Nowa instancja resetuje lokalne liczniki, choć konto i pieniądze mogą być te same.**

Koszty są sumowane z przekazanego połączenia SQLite. Po przełączeniu na nową instancję baza jest nowa. Klucze API mogą pozostać te same. Limit miesięczny w presecie jest więc limitem widocznym w tej bazie, a nie automatycznie limitem całego wspólnego rachunku.

W P12 do bazy A wstawiłem fikcyjne 30 USD kosztu przy limicie 25 USD. Kontrola A odmówiła. Dla pustej bazy B ta sama kontrola dopuściła etap. Limit dzienny w próbie był celowo ustawiony wyżej, aby sprawdzić właśnie limit miesiąca. **Nie wydano tych pieniędzy; to dane testowe.**

Analogiczna granica dotyczy działań społecznościowych: oddzielna instancja powinna zapomnieć niepasujące pomysły A, lecz na tym samym koncie nie powinna zapominać już zamieszczonych komentarzy, wykorzystanych limitów ani tego, że daną osobę już obserwuje. Dokumentacja wprost przyznaje, że nowa instancja może wrócić pod ten sam post.

**Zmiana:** osobno pamięć redakcji, historia realnego konta oraz księga kosztów właściciela kluczy. Limity instancji mogą dzielić budżet, ale nadrzędny limit rachunku powinien obowiązywać wszystkie instancje i tory testowe. Przy równoległych pracownikach potrzebna jest także rezerwacja kosztu przed wywołaniem, żeby dwa procesy nie wydały jednocześnie tego samego pozostałego budżetu. Zapis historii konta nie powinien być czyszczony przy zmianie tematu.

To istotny warunek Twojego „jak najtaniej”: świeży preset ma odzyskać neutralność tematyczną, a nie nowy przydział pieniędzy na tym samym rachunku.

Źródła: [kontrola budżetu](</D:/Nia bot/agent-v2/llm.py:129>), [sumowanie z jednej bazy](</D:/Nia bot/agent-v2/db.py:314>), [udokumentowane granice instancji](</D:/Nia bot/docs/PRESETY.md:108>).

**F10 — P1 dla równoległych klonów. Generator tworzy kolidujące nazwy usług.**

Zmiana katalogu i użytkownika w generatorze nie zmienia nazw jednostek `nia-agent`, `nia-artykul`, `nia-alarm`. P14 wygenerowała konfiguracje dla dwóch różnych katalogów: oba wyniki miały ten sam zestaw sześciu nazw plików. Zainstalowanie ich w tym samym zakresie systemd powoduje kolizję zamiast utworzenia dwóch niezależnych botów.

Drugie ograniczenie wynika z zapisu generatora: nadpisuje bieżące wyniki, ale nie usuwa poprzednich wygenerowanych plików, które przestały być potrzebne. Po ustawieniu zera artykułów nowy wynik nie zawiera timera artykułów, lecz stary plik w istniejącym katalogu wynikowym może pozostać. Warunek liczby artykułów w głównym wejściu ogranicza skutki, ale wdrożony harmonogram może nie odpowiadać temu, co operator widzi w presecie.

**Zmiana:** nazwy jednostek oparte na identyfikatorze instancji albo parametryzowane jednostki systemd. Generator powinien znać kompletny manifest wdrożenia, pokazać różnicę i zastępować zestaw jednostek, uwzględniając wycofane. Odłączenie musi obejmować także usługę już pracującą. Nie wykonywałem instalacji lub zatrzymywania usług.

Źródła: [zestaw jednostek](</D:/Nia bot/narzedzia/jednostki.py:171>), [zapis wyników](</D:/Nia bot/narzedzia/jednostki.py:252>).

**F11 — P2. Preset zmienia głos, ale nadal dziedziczy część formy i założeń redakcyjnych silnika.**

Nie znalazłem starej, wypełnionej historii tematów w śledzonym `historia_startowa.json`: plik zawiera pustą listę. Nie należy też nazywać każdego słowa „mechanizm” pozostałością po AI. Jest jednak istotna różnica między neutralnością wobec tematu a możliwością dowolnego stylu i gatunku.

Przykłady wykonywanych instrukcji wspólnych:

- Zastępcze przykłady dla `seam` kierują poszukiwania na pisemną regułę powstałą po tym, gdy coś poszło źle.
- Pisarz ma objaśniać mechanizm i wcześnie go nazwać; to konkretna forma publicystyki.
- Bank preferuje ciekawostkę sprawdzalną dokumentem lub pomiarem, wyjaśniającą mechanizm i wpływ na czytelnika.
- Domyślny profil w `style-profiles/` wprost nakazuje naturalny angielski i przyjmuje anonimową markę oraz określoną konstrukcję argumentu.
- Wspólne reguły krótkich treści zakazują średników i pauz, preferują bezpośredniość i ograniczają formuły grzecznościowe.
- Odpowiedzi i restacki dzielą blok głosu komentarza; nie można nadać im niezależnej polityki samym istniejącym zestawem siedmiu bloków.

To może dobrze pasować do analitycznej publikacji o AI, technice lub nauce. Dla podręcznika, poradnika krok po kroku, serdecznej społeczności czy innego gatunku sam wpis „nowy styl” może być sprzeczny z instrukcjami wspólnymi. Przy pominięciu profilu pozytywnego preset z językiem polskim może nadal dostać domyślną instrukcję pisania po angielsku.

**Zmiana:** rozdzielić niezależne od tematu zasady rzetelności i kontrakty danych od strategii redakcyjnej. Strategia powinna jawnie wybierać typy treści, sposób oceniania tematów, głosy poszczególnych formatów, dozwolone środki językowe i profil odbiorcy. Preset może wybrać gotową strategię analityczną, zamiast przepisywać wszystkie prompty. Reguły rzetelności pozostają wspólne. Dodać bezpłatne sprawdzenie konfliktów języka i brakujących zasobów oraz zestaw ocen jakości właściwych dla danego gatunku.

Źródła: [zastępczy kierunek researchu](</D:/Nia bot/agent-v2/stages.py:326>), [forma artykułu](</D:/Nia bot/agent-v2/prompts/pisarz.md:167>), [ranking banku](</D:/Nia bot/agent-v2/prompts/bank.md:32>), [wspólny profil](</D:/Nia bot/style-profiles/ARTICLE_STYLE_PROFILE_V1.md>), [reguły krótkich form](</D:/Nia bot/agent-v2/prompts/po_ludzku.md:11>).

**F12 — P2. Cache rozpoznaje preset, lecz nie rozpoznaje konkretnego zadania.**

Klucz `etap.odcisk_presetu` nie zawiera wejścia etapu. P11 wywołała cache tego samego etapu dla jednego presetu z dwoma różnymi funkcjami produkującymi wynik. Przy włączonym użyciu cache drugie wywołanie zwróciło pierwszy wynik. To może być celowe przy wznawianiu jednego przebiegu, ale nie wystarcza do ogólnego ponownego wykorzystania wyników dla nowego tematu.

Odcisk nie obejmuje również wersji wspólnego promptu, silnika ani kompletu efektywnych ustawień modeli. Zmiana domyślnej roli w kodzie nie musi zmienić odcisku TOML-a, który tej roli nie nadpisuje. Nie wykazuję tu automatycznego przecieku między poprawnie rozdzielonymi katalogami A i B; to problem aktualności i identyfikacji wyniku w obrębie instancji.

**Zmiana:** cache zadania wiązać z identyfikatorem zadania, hashem wejścia, wersją promptu, modelem i kontekstem wykonania. Wznawianie konkretnego przebiegu powinno wskazywać jego identyfikator. Wspólny cache surowych dokumentów może być osobny, indeksowany treścią i URL-em, bez prywatnych komentarzy redakcyjnych i wyników rankingu innej redakcji.

Źródło: [cache etapów](</D:/Nia bot/agent-v2/run.py:73>).

**F13 — P2 przy przyszłym przełączaniu w pamięci. Niskopoziomowe nałożenie błędnego presetu nie zachowuje A.**

`preset.zastosuj()` najpierw przywraca bazę, a potem próbuje zastosować ustawienia. P15 z niepoprawną rolą modelu zgłosiła `BladPresetu`, lecz wcześniejszy kontekst A był już zastąpiony bazą.

**Obecne `podlacz` waliduje kopię wcześniej i zachowuje stary wskaźnik przy błędzie.** Nie jest to wada tej poprawnie użytej komendy. To pułapka API, jeśli przyszła wersja zacznie przełączać presety w działającym procesie lub jeśli ktoś potraktuje `zastosuj` jako bezpieczną transakcję.

**Zmiana:** zbudować cały nowy kontekst poza żywym obiektem, zweryfikować go i dopiero atomowo udostępnić procesowi. Preferować kontekst przekazywany do etapów zamiast modyfikowania globalnego modułu. Na dziś wymiana przez nowy proces pozostaje prostsza.

Źródło: [kolejność modyfikacji](</D:/Nia bot/agent-v2/preset.py:633>).

**5. Gdzie powinny przebiegać granice: silnik, preset, instancja, konto i rachunek**

Najważniejsza zmiana architektury polega na zdefiniowaniu właściciela danych. Obecny podział na silnik i preset jest za krótki: część stanu powinna przeżyć zmianę tematu, a część musi być od niego odizolowana.

| Warstwa | Co do niej należy | Co dzieje się po odłączeniu A i podłączeniu B |
|---|---|---|
| Silnik | Kod etapów, kontrakty danych, kontrola źródeł, mechanizm publikacji, adaptery dostawców, zasady rzetelności | Pozostaje bez modyfikacji |
| Preset | Temat, odbiorca, język, źródła i zapytania, strategia treści, styl i przykłady, modele per rola, plan i przydzielony budżet | B dostarcza kompletny nowy opis; brak pola nie pobiera przypadkowych materiałów A |
| Instancja redakcji | Bank, research z oceną dla tej redakcji, odrzucone pomysły, zużyte fakty, szkice, kolejki, feedback i cache zadań | A staje się archiwum; B zaczyna od nowej przestrzeni albo jawnie wznawia własną |
| Konto publikacji | Potwierdzona tożsamość, sesja, opublikowane identyfikatory, komentarze, obserwacje, limity działań, blokada równoległych zapisów | Historia tego samego konta pozostaje; inne konto otrzymuje osobną przestrzeń |
| Właściciel rachunku API | Odwołania do sekretów, koszty wszystkich instancji, rezerwacje i limity nadrzędne | Wydatki nie zerują się przy zmianie presetu |
| Aktywacja | Powiązanie instancji, presetu, konta i generacji z procesem | Odłączenie unieważnia uprawnienia starej generacji |

W szczególności bank ma dwa różne rodzaje informacji. Surowy dokument źródłowy może być ponownie użyty przez kilka redakcji, jeśli ma poprawne pochodzenie i aktualność. Ocena „to dobry temat dla naszych czytelników”, proponowana teza, styl notki oraz historia wykorzystania należą do konkretnej redakcji. Mieszanie tych dwóch rodzajów pamięci może pozornie oszczędzać research, a faktycznie przenosić poprzedni profil pisania.

Wzorzec organizacji, **propozycja do wdrożenia, nie istniejąca struktura projektu**:

```text
silnik/<wersja>/                    kod oraz prompty mechanizmu
presety/<preset>/<wersja>/          manifest, bloki, style i materiały
runtime/instancje/<id>/             bank, szkice, cache, kolejki, manifest właściciela
runtime/konta/<id>/                 sesja, historia działań, blokada publikowania
runtime/rozliczenia/<id>/           księga kosztów i rezerwacje
runtime/aktywacje/<id>/             status, generacja, identyfikator procesu
```

Manifest instancji powinien zawierać co najmniej: trwały identyfikator redakcji, identyfikator konta, wybrany preset i jego wersję, hash paczki, wersję silnika, efektywny plan modeli, datę utworzenia oraz wersję schematu danych. Klucze API nie powinny znajdować się w przenośnej paczce; preset może wskazywać nazwę profilu poświadczeń. Nowa instalacja rozwiązuje tę nazwę lokalnie.

Warto oddzielić dwie operacje użytkownika: **„nowa redakcja”** zawsze tworzy świeżą instancję, a **„wznów redakcję”** zachowuje jej bank i historię. Osobno powinna istnieć **„zaktualizuj preset tej redakcji”**, która pokazuje zmianę kontekstu i rozstrzyga ważność kolejki. Obecna jedna komenda częściowo łączy te trzy znaczenia.

Aktualizacja wymaga różnej reakcji zależnie od zmiany:

| Zmieniono | Minimalna reakcja |
|---|---|
| Godzinę publikowania | Nowy plan harmonogramu; zachowanie banku |
| Model lub parametry pisarza | Nowy kontekst wykonania i cache generowania; zachowanie źródeł |
| Styl lub język | Ponowna ocena szkiców i kolejki; unieważnienie odpowiednich wyników generowania |
| Politykę źródeł | Ponowne sprawdzenie dopuszczalności dokumentów i ocen researchu |
| Główny temat lub tożsamość redakcji | Domyślnie nowa instancja |
| Konto publikacji | Jawne nowe przypisanie, weryfikacja tożsamości i brak automatycznego przejęcia kolejki |

**6. Czy preset zawiera już wszystko, o co chodziło: modele, źródła, styl i ilości?**

Schema ma 49 dozwolonych pól. W obecnym wariancie da się ustawić podstawowy temat, źródła, głos, liczbę notek i artykułów, działania społecznościowe, harmonogram, budżety, role modeli, model okładki i zapasowego pisarza. Preset AI ma pełny katalog bloków i materiałów stylu. To nie jest już jedynie paczka słów kluczowych.

Nadal brakuje pełnego, przenośnego planu wykonania. `EFFORT`, `DEEPSEEK_EFFORT` i `MAX_TOKENS` pozostają ustawieniami silnika, a nie polami tego schematu. Role nieopisane w presecie korzystają z domyślnej mapy silnika. Po aktualizacji kodu ten sam preset może więc działać inaczej. Nie chodzi o to, aby każdy operator ręcznie wypełniał kilkadziesiąt parametrów. Powinien móc wybrać wersjonowany profil wykonania, zobaczyć rozwiązany plan i nadpisać wybrane role.

Ponadto nazwa modelu w pliku nie tworzy obsługi jego API. Walidator badanej gałęzi dopuszcza do tekstowych ról obsługiwanych tu dostawców Anthropic i DeepSeek; inne tekstowe konfiguracje są blokowane. To stwierdzenie o kodzie gałęzi, nie o aktualnej ofercie dostawców. Gotowość na dowolny nowy model wymaga odpowiedniego adaptera, sposobu wywołania narzędzi, limitów i rozliczania. Nie weryfikowałem dostępności nazw modeli na kontach API ani ich aktualnych cen.

Źródła: [schemat](</D:/Nia bot/agent-v2/konfiguracja.py:418>), [parametry modeli](</D:/Nia bot/agent-v2/config.py:976>), [walidacja presetu](</D:/Nia bot/agent-v2/preset.py:447>).

Dla kosztu i jakości proponuję następujące zasady projektu:

- Kompletność paczki, zgodność języka, przypięcia stylu, obsługę ról i ważność aktywacji sprawdzać bez modeli, przed pierwszym kosztem. Błąd korpusu wykryty po researchu jest wydatkiem, który można było wyeliminować.
- Tanie, powtarzalne operacje wykonywać deterministycznie: walidacja, deduplikacja, limity, wybór plików i egzekwowanie właściciela danych. Model ma rozstrzygać treść wymagającą oceny.
- Surowy dokument pobierać raz, a ocenę dopasowania do tematu i odbiorcy przechowywać osobno dla każdej redakcji. Nie przenosić ocen banku A jako ocen B.
- Tańszy model kierować do wstępnej klasyfikacji i selekcji, a mocniejszy do trudnego researchu, syntezy lub tekstu, który przeszedł selekcję. Dobór potwierdzić na ocenionych próbkach danej redakcji; sama etykieta modelu nie mierzy jakości.
- Mierzyć koszt zaakceptowanego materiału: łączny koszt scoutingu, odrzuceń, researchu, prób pisania i napraw podzielony przez liczbę materiałów spełniających kryteria. Niska cena jednego wywołania może przegrać przez liczbę poprawek.
- Limitować naprawy i definiować zakończenie nieudanego zadania. Odrzucenie pomysłu powinno pozostawić przyczynę w banku tej redakcji, żeby nie płacić za ten sam ślepy zaułek.
- Preset powinien dostarczać ocenione przykłady: dobra notka, zła notka z powodem, poprawny komentarz, plan artykułu, granice źródeł. Korpus pomaga w głosie, ale nie zastępuje kryteriów akceptacji.

Nie podaję procentowej oszczędności: bez pomiaru pełnych przebiegów dla dwóch presetów byłaby zmyślona. W tym audycie ustalono błędy izolacji i kontroli kosztów, a nie wykonano płatnego porównania jakości modeli.

**7. Czysta baza i klony: co rekomenduję teraz**

**Tak: zachowuj czystą bazę i twórz świeżą instalację dla nowej redakcji.** Ma to obecnie praktyczną przewagę: nie przenosi przypadkiem starego TOML-a, domyślnego korpusu, banku, kolejki ani lokalnego wskaźnika. To obejście części braków cyklu życia. Nie daje automatycznie izolacji wszystkiego, co znajduje się poza repozytorium.

Nie trzeba utrzymywać innego kodu silnika dla każdego tematu. Każda instalacja może korzystać z tej samej przypiętej wersji i różnić się jedynie presetem oraz przypisaniem danych i konta. Poprawki silnika wtedy wdraża się przewidywalnie, z numerem wersji i migracją danych.

| Wariant | Zalety | Ograniczenia | Wybór |
|---|---|---|---|
| Ten sam używany katalog, przełączanie przez `odlacz/podlacz` | Najmniej pracy operacyjnej | Wszystkie opisane pułapki cyklu życia, stary TOML i korpus | Tylko z kontrolowanym zatrzymaniem i kompletnymi zasobami |
| Osobny świeży klon, własna instancja | Prosty rozdział plików i pamięci redakcyjnej, łatwa diagnostyka | Wspólny host nadal wymaga izolacji Chrome, usług i kontroli rachunku | Rekomendowany wariant przejściowy |
| Jedna wersja silnika i jawnie izolowane instancje po poprawkach | Wygodne zmiany tematów, jedna ścieżka aktualizacji, mniej ręcznej obsługi | Wymaga domknięcia aktywacji, właścicieli danych i paczek | Docelowy wariant |

Proponowana procedura nowej redakcji na obecnym kodzie — **instrukcja do późniejszego wykonania, nie działania wykonane w audycie**:

1. Wybrać konkretną wersję kodu, utworzyć świeży checkout z Gita. Nie używać kopiowania całego folderu `D:\Nia bot` jako sposobu tworzenia czystego bota.
2. Skopiować wyłącznie pełny katalog właściwego presetu albo utworzyć go z szablonu. Dla lokalnej redakcji `nia` trzeba świadomie przenieść `presety/nia`; nie znajduje się ona w śledzonych plikach gałęzi.
3. Nadać nową nazwę redakcji i nowy identyfikator instancji. Przed podłączeniem potwierdzić, że katalog instancji nie istnieje. Sam parametr `--instancja` dziś tego nie gwarantuje.
4. Dostarczyć własne profile stylu, wszystkie używane bloki i własny korpus. Jeśli korpusu ma nie być, na obecnym kodzie dodatkowo upewnić się, że nie ma domyślnego pliku w `agent-v2/prompts/styl/`. Docelowo powinien to gwarantować jawny tryb opisany w F05.
5. Przygotować właściwe poświadczenia i sesję dla docelowego konta. Jeśli klony mają działać równolegle, rozdzielić profil przeglądarki i lokalny endpoint przez odpowiednie środowiska uruchomieniowe. Nie uruchamiać dwóch klonów ze wspólnym Chrome na podstawie samego faktu, że mają różne foldery.
6. Jeżeli to zastąpienie poprzedniej redakcji na tym samym koncie, najpierw zatrzymać jej harmonogram i pracujące usługi oraz potwierdzić zakończenie procesów. Dopiero potem aktywować nową redakcję. Sam komunikat `odlacz` nie jest takim potwierdzeniem.
7. Sprawdzić preset i wykonać podgląd. Obejrzeć efektywny temat, źródła, pełne profile i próbki stylu, role modeli, ilości oraz harmonogram. Samo `sprawdz` jeszcze nie weryfikuje poprawności przypięć tak dokładnie jak loader używany w podglądzie/pisarzu.
8. Rozstrzygnąć nazwy i zakres usług przed instalacją harmonogramu. Dwie obecne konfiguracje `nia-agent.service` w tym samym systemd nie są dwoma niezależnymi agentami. Na osobnych hostach ten konkretny konflikt nazw nie zachodzi.
9. Zachować nadrzędną kontrolę wydatków obejmującą obie redakcje, jeśli korzystają ze wspólnego rachunku. Po zmianie instancji historia konta i kosztów wymaga świadomego zachowania; obecny loader nie przeniesie jej selektywnie za operatora.
10. Pierwsze materiały sprawdzić w trybie roboczym: czy nie zawierają starych tematów, głosu lub danych konta, czy źródła rzeczywiście pasują i czy działają właściwe limity. To oddzielny test jakości, którego nie zastępują testy loadera.

Przy zmianie tematu na tym samym koncie Substack jego opublikowane treści, obserwacje i relacje pozostaną w serwisie. Żaden klon ani odłączenie presetu nie uczyni z tego konta nowego konta. Czystość silnika i redakcyjnej pamięci lokalnej jest odrębną sprawą od historii publicznego profilu.

**8. Plan zmian w kolejności, która ma największy sens**

Proponuję pracę w sześciu pakietach. Pierwsze trzy domykają podstawową izolację. Pozostałe tworzą wygodny, przenośny produkt. Nie proponuję przy okazji przepisywania całego researchu, bo nie jest to konieczne do uzyskania poprawnej granicy presetów.

| Kolejność | Konkretny zakres | Główne miejsca w obecnym kodzie | Warunek zakończenia |
|---|---|---|---|
| 1. Prawdziwe odłączenie | Generacja aktywacji, blokada nowych zadań, zatrzymanie pracownika, kontrola przed kosztem i zapisem; podgląd bez uprawnień produkcyjnych | `preset.py`, `run.py`, `artykul_z_puli.py`, `llm.py`, `browser.py`, konsola presetów | Po odłączeniu stary proces nie zaczyna kolejnego kosztu ani publikacji; środowisko nie omija blokady |
| 2. Właściciel instancji | Manifest, osobne „nowa” i „wznów”, ochrona ponownego użycia katalogu; pochodzenie artykułów i cache | `preset.py`, `stages.py`, warstwa danych | B nie odczytuje banku ani kolejki A; błędna próba przejęcia katalogu kończy się odmową |
| 3. Jawne zasoby i pusty stan | Wycofanie automatycznego odczytu starego TOML-a, jednoznaczny brak korpusu, brak szukania zasobów w drugim katalogu, pełna walidacja stylu | `config.py`, `konfiguracja.py`, `style.py`, `preset.py` | B bez korpusu ma zawsze zero przykładów; start bez presetu nie odzyskuje starej niszy |
| 4. Konto i wspólny rachunek | Rozdzielenie historii konta od banku, potwierdzona sesja, wspólny limit i rezerwacje, izolacja Chrome oraz nazwy usług | `browser.py`, `db.py`, `llm.py`, `narzedzia/jednostki.py` | Zmiana redakcji nie resetuje realnych wydatków i nie powtarza działań tego samego konta |
| 5. Paczka i powtarzalność | Eksport całości, hashe treści, wersja silnika, rozwiązany plan modeli, transakcyjne składanie kontekstu | `preset.py`, `konfiguracja.py`, konsola | Import w niezależnym katalogu działa bez dostępu do pierwotnej lokalizacji |
| 6. Elastyczna redakcja i pomiar | Strategie formatów, rozdzielone głosy odpowiedzi/restacku, oceny jakości, cache wejść, pomiar kosztu zaakceptowanego tekstu | Prompty, `stages.py`, `run.py`, konfiguracja ról | Nowy gatunek i język przechodzą własne kryteria jakości bez konfliktu z domyślnym stylem |

Na początku wystarczy zachować architekturę nowego procesu dla nowego kontekstu. Wymiana w trakcie działania nie jest potrzebna do wygodnej obsługi presetów, a komplikuje spójność importowanych modułów. Najpierw należy mieć niezawodny cykl: zatrzymaj, unieważnij, zweryfikuj, aktywuj, uruchom.

**9. Testy, po których można powiedzieć „możemy bezpiecznie zmieniać preset”**

Obecne 161 sprawdzeń to wartościowa baza, lecz nie pokrywają wszystkich granic życia procesu i konta. Potrzebne są scenariusze odtwarzające zachowanie użytkownika:

| Scenariusz odbiorczy | Oczekiwany wynik |
|---|---|
| W A umieszczono znaczniki w banku, szkicu, profilu, korpusie, cache i kolejce; następnie uruchomiono nową B | Żaden prywatny materiał A nie trafia do kontekstu B |
| Odłączenie A między przygotowaniem tekstu a publikacją | Stara generacja nie zaczyna zapisu; zadanie otrzymuje rozstrzygnięty stan |
| Operacja zewnętrzna była już wysłana w chwili odłączenia | System ustala jej wynik i nie powtarza jej bez sprawdzenia |
| Brak wskaźnika, ale obecne `AGENT_V2_PRESET` | Dopuszczony tylko jawny podgląd; produkcja odmawia |
| Próba B na istniejącym katalogu A | Odmowa z wyjaśnieniem właściciela i propozycją nowej instancji |
| Ponowne uruchomienie A z tym samym właścicielem | Bank i niedokończone zadania A są dostępne zgodnie z wersją presetu |
| B deklaruje brak korpusu, w instalacji znajduje się stary korpus | Zero przykładów stylu, niezależnie od obecności dawnych plików |
| Zmiana profilu, korpusu albo przypięć po aktywacji | Zmiana hashy i wymóg ponownej walidacji; brak cichej podmiany |
| Eksport, usunięcie dostępu do oryginalnej lokalizacji, import pod inną ścieżką | Wszystkie bloki i materiały działają; hash paczki pozostaje zgodny |
| B ma nowy język i własne profile | Brak sprzecznej instrukcji językowej; ocenione próbki spełniają kryteria B |
| Dwa klony, to samo konto | Wspólna historia działań i blokada konkurencyjnych publikacji |
| Dwa klony, różne konta | Każdy potwierdza właściwą tożsamość; brak wspólnego przypadkowego profilu |
| Nowa instancja po wyczerpaniu wspólnego budżetu | Nadal odmowa, również przy równoległym starcie pracowników |
| Aktualizacja presetu z artykułów 1 do 0 | Wycofanie niepotrzebnego harmonogramu; brak osieroconej usługi publikującej |
| Dwa różne zadania w tej samej wersji presetu | Cache nie zwraca treści pierwszego jako wyniku drugiego |
| Niepoprawny B podczas przygotowania nowej aktywacji | A i jego dane pozostają spójne; B nie ma częściowej aktywacji |

Testy izolacji można przeprowadzać na sztucznych treściach i atrapach dostawców. Jakość faktycznie napisanych notek i artykułów trzeba potem ocenić osobno na reprezentatywnych próbkach. Te dwie oceny odpowiadają na różne pytania.

**10. Rejestr wykonanych prób i granice wniosków**

Istniejący zestaw: [test_presety.py](</D:/Nia bot/agent-v2/tests/test_presety.py>) uruchomiony w tymczasowej kopii badanego commita. Wynik: **161 udanych sprawdzeń, 0 nieudanych**. Nie nazywam tego pełnym testem całego bota. To jeden wyspecjalizowany zestaw.

Poniżej dodatkowe próby. A i B były kontrolowanymi wariantami presetu, z syntetycznymi znacznikami umożliwiającymi rozpoznanie pochodzenia danych. Nie były oceną jakości gotowego presetu o nowej dziedzinie. Część prób sprawdzała funkcje, część pełne ładowanie modułu w świeżym procesie; zakres jest wskazany w opisie.

| Próba | Wykonanie | Zaobserwowany wynik |
|---|---|---|
| P01 | Nałożenie B po A i porównanie stałych objętych resetowaniem z B na bazie silnika | Zgodność; nie wykazano dziedziczenia tych ustawień |
| P02 | Odłączenie z zachowanym obiektem aktywacji w kontekście | Wskaźnik nie istnieje, nowy odczyt zwraca brak aktywacji, lecz brama starego kontekstu dopuszcza pracę |
| P03 | Odczyt aktywacji przez zmienną środowiskową po odłączeniu | Aktywacja istnieje, brama ją dopuszcza |
| P04 | A i B podłączone kolejno do instancji `shared`, oznaczony bank i znacznik artykułu A | B odczytuje bank A i znacznik artykułu A |
| P05 | B podłączone do nowego identyfikatora zamiast `shared` | Bank B pusty, kolejka B pusta, pliki A zachowane |
| P06 | Zmiana samego pliku profilu pozytywnego po aktywacji | Odcisk bez zmiany, ponowny odczyt aktywacji zaakceptowany |
| P07 | Zmiana korpusu bez zmiany przypięć; porównanie walidatora presetu i loadera stylu | Odcisk bez zmiany, lista błędów walidatora pusta, loader zgłasza `StyleError` |
| P08 | Eksport do pojedynczego TOML-a i ponowne wczytanie | 7 bloków w oryginale, 0 w eksporcie; 3 bezwzględne ścieżki stylu; odcisk inny |
| P09 | Kopia identycznego katalogu presetu pod inną ścieżkę | Odcisk zmieniony mimo identycznej zawartości paczki |
| P10 | Syntetyczny stary korpus z poprawnymi przypięciami, B z pustym korpusem i wyłączonym wymogiem | Wybrana domyślna ścieżka; załadowano 5 przykładów zawierających znacznik starego głosu |
| P11 | Dwa różne wyniki producenta dla tego samego etapu/presetu, drugie wywołanie z cache | Drugie wywołanie zwraca pierwszy wynik |
| P12 | Dwie tymczasowe bazy: A ma fikcyjne 30 USD przy limicie 25 USD, B pusta | A blokowana, B dopuszczona; żadnego płatnego wywołania |
| P13 | Sprawdzenie wyliczanych lokalizacji i portu przeglądarki | Profil Chrome poza klonem, CDP 9222, plik sesji pod katalogiem instancji |
| P14 | Generator jednostek dla dwóch różnych katalogów instalacji | Te same 6 nazw plików jednostek; bez instalowania ich w systemie |
| P15 | Niepoprawna rola B przekazana do niskopoziomowego `preset.zastosuj` po A | Wyjątek, ale A nie zachowane; konfiguracja przywrócona do bazy |
| P16 | Świeży zwykły proces bez presetu, środowiskowego nadpisania i starego TOML-a | Pusta nisza; rzeczywiste `run.main()` i `artykul_z_puli.main()` zwracają 3 |
| P17 | Rzeczywisty moduł `config`: aktywacja w kopii, wczytanie, odłączenie, ponowne wywołanie bramy | Brak wskaźnika, zachowany preset i nisza w module, brama dopuszcza pracę |
| P18 | Świeży proces bez aktywacji, z syntetycznym dawnym TOML-em | Dawna nisza wczytana; `run.main()` nadal zwraca 3 |
| P19 | Świeży zwykły proces z `AGENT_V2_PRESET=presety/ai`, bez wskaźnika | Źródło aktywacji `srodowisko`, brama dopuszcza pracę |

Istotne warunki odtwarzania: dokładnie badany commit, dane testowe w nowym katalogu, brak prawdziwych kluczy w środowisku prób, tryb bez rzeczywistych publikacji, zablokowane połączenia sieciowe. Dla P16–P19 proces nie był uruchamiany jako darmowy test z katalogu `tests`; sprawdzał normalną ścieżkę aktywacji. Dla P17 i P19 nie wykonywano dalszych etapów po przejściu bramy. Potwierdzony wynik to dopuszczenie przez bramę, nie zrealizowana akcja na koncie.

Próby można odtworzyć według powyższych scenariuszy, bez używania danych produkcyjnych. W szczególności P04 wymaga tylko pliku indeksu z wyróżniającym wpisem i znacznika oczekującego artykułu; nie wymaga pisania ani publikowania artykułu. P12 wymaga tylko wpisu w tabeli kosztów i wywołania lokalnej kontroli limitu.

Nie wykonywałem kontroli działających procesów na serwerze, połączenia z Chrome, logowania na konto, wysyłki treści, odczytu rachunku dostawcy ani pomiaru jakości generowanych tekstów. Nie ustalałem, czy którakolwiek opisana luka została już wykorzystana w produkcji. Wnioski o współdzieleniu Chrome i wdrożeniu usług wynikają z kodu oraz lokalnych prób konfiguracji; nie są raportem incydentu.

**Decyzja wdrożeniowa wynikająca z audytu:** obecny mechanizm nadaje się do kontrolowanych, osobnych instalacji z kompletnymi presetami. Do obietnicy „wyjmuję preset i od razu mam czystego, bezpiecznie przełączalnego bota” trzeba domknąć F01–F06. Przy współdzieleniu kont, rachunku lub hosta równie konieczne są F08–F10. Eksport pełnej paczki i wersjonowanie kontekstu domkną przenośność; strategie redakcyjne i oceny jakości domkną swobodę nowego stylu.
