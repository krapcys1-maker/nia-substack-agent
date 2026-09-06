# Audyt dystrybucji: czyste repo, presety i instalacje użytkowników

**Data:** 6 września 2026. **Punkt wyjścia:** gałąź `presety`,
commit `320f790`; publiczne `main` było 23 commity wcześniej.
Przedmiot audytu: pobranie projektu, wybór presetu, własne konto i klucze,
logowanie, praca na komputerze lub serwerze oraz pozostawienie czystego
repozytorium źródłowego.

## Werdykt

**Tak, proponowany model dystrybucji jest możliwy i jego podstawowy mechanizm
już działa.** Użytkownik pobiera silnik i publiczne presety, wpisuje konto oraz
klucze w swojej instalacji, wybiera paczkę i tworzy własną instancję. Te
czynności nie wymagają edycji wspólnego presetu ani dostępu do zapisu na GitHubie.

**Nie jest to jeszcze produkt „wybierz preset i automatycznie uruchom wszędzie”.**
Największe pozostałe braki dotyczą wiarygodnego sprawdzenia konta przeglądarki,
izolacji Chrome, pełnego cyklu przełączania instancji i przygotowania
harmonogramu/środowiska serwerowego. Samo odłączenie nie przywraca całego
używanego katalogu do stanu świeżego pobrania.

Rekomendowana dystrybucja: **jedna publiczna gałąź `main` z silnikiem i
katalogiem presetów; jedna świeża instalacja na publikację.** Krótkie gałęzie
robocze mogą istnieć podczas rozwoju i znikać po scaleniu. Użytkownik nie powinien
musieć wybierać gałęzi, żeby otrzymać aktualny produkt.

## Co zostało sprawdzone

Odczyt GitHuba, pobranie aktualnych referencji oraz analiza kodu loadera,
konfiguracji, CLI, przeglądarki, wywołań modeli, generatora systemd, ignorowania
plików i CI. Następnie osobny klon bez prywatnych plików właściciela:
walidacja obu publicznych presetów, renderowanie promptów, aktywacja z fikcyjnym
kontem w lokalnym `.env`, przełączenie tematu, rozdzielenie danych i
kontrpróby ujawniające luki.

Testy uruchomiono na dostępnym interpreterze Python 3.12 z zainstalowanymi
bibliotekami; świeży był checkout i stan konta, nie cały system operacyjny.
Po utworzeniu klonu połączenia sieciowe procesów kontrolnych były blokowane.
Nie używano rzeczywistych kluczy, logowania do konta ani płatnych modeli.
Wynik nie jest testem publikacji z serwera ani pomiarem jakości nowej redakcji.

## Przepływ użytkownika

| Krok | Stan obecny | Co użytkownik musi wiedzieć |
|---|---|---|
| Pobiera GitHub/ZIP | Działa | Pobierać aktualne `main`; nie kopiować katalogu używanej produkcji |
| Wybiera `ai` lub `hidden-bill` | Działa przez CLI | Nie ma jeszcze graficznego selektora/kreatora |
| Wpisuje konto i API w `.env` | Działa | Eksportowane zmienne mają pierwszeństwo przed plikami |
| Podłącza preset | Działa | Walidacja klucza nie oznacza sprawdzenia dostępu do modelu |
| Loguje się | Ręcznie | Najpierw aktywacja, potem zapis sesji do właściwej instancji |
| Uruchamia na komputerze | Działa przez CLI | Harmonogram Windows i dostępność Chrome wymagają konfiguracji |
| Uruchamia na serwerze | Częściowo przygotowane | Są jednostki bota; brakuje kompletnego przygotowania przeglądarki i ekranu |
| Odłącza preset | Działa jako dezaktywacja | Nie usuwa danych, konta, kluczy, sesji i harmonogramów |
| Podłącza nowy temat | Działa z nowym ID | Zatrzymać procesy; stare ID wznawia stare dane |
| Repo i publiczne presety zostają nietknięte | Potwierdzone dla sprawdzonego przepływu | Zwykły runtime nie robi `git push`; Git nie jest magazynem danych użytkownika |

## Ustalenia i poprawki

### 1. GitHub pokazywał poprzednią generację projektu — poprawione w przygotowanym wydaniu

Domyślną gałęzią było `main`, podczas gdy aktualny system presetów był na
`presety`. Użytkownik pobierający projekt zwykłym klonowaniem dostawał więc
inną wersję niż opisywana w tej rozmowie. Opis About nadal obiecywał stały
koszt, liczbę ról i bramek dla dawnego ustawienia.

Przygotowane uporządkowanie przenosi aktualną wersję na `main` z zachowaniem
historii i usuwa potrzebę utrzymywania osobnej gałęzi produktowej `presety`.
README przedstawia obecny model dystrybucji, katalog i instrukcję uruchomienia.
Opis projektu nie powinien obiecywać kosztów ani wyników niezależnych od presetu.

### 2. Sprzeczne instrukcje instalacji — poprawione

Stara dokumentacja kazała konfigurować pojedynczy `konfiguracja.toml`,
odsyłała do dawnych ścieżek sesji i opisywała stały harmonogram oraz wydatki.
Nowy loader obsługuje pełne katalogi presetów, konto z `.env` i katalogi instancji.

Ujednolicono [README](../../README.md), [instalację](../../docs/INSTALL.md),
[konto i personalizację](../../docs/PLUGGING_IN_AN_ACCOUNT.md),
[opis presetów](../../docs/PRESETY.md), katalog,
[zasady współpracy](../../CONTRIBUTING.md), [dane prywatne](../../SECURITY.md)
i `.env.example`. Nowy preset został dostosowany do tego samego przepływu.
Odnośniki w jego dokumentacji są względne, więc działają poza komputerem autora.

### 3. Zbyt niska deklarowana wersja Pythona — poprawione w instrukcji i macierzy CI

Preset używa bezpośredniego `import tomllib`; produkt oparty na presetach
wymaga Python 3.11+. Dawne „Python 3.10+” dotyczyło wcześniejszej ścieżki silnika.
CI przestawiono na 3.11/3.12 i dodano osobną walidację obu publicznych paczek.

Na Windows dochodzi baza stref IANA. Kod używa `ZoneInfo`, a instalacja może
nie mieć `tzdata`. Instrukcja zawiera teraz jej instalację. Docelowo zależności
danych i platform powinny wejść do jednego manifestu instalacyjnego; obecny
audyt zależności patrzy przede wszystkim na importy Pythona.

Źródła: [loader](../../agent-v2/preset.py),
[walidator stref](../../agent-v2/konfiguracja.py),
[workflow](../../.github/workflows/testy.yml).

### 4. Wspólny preset i prywatne konto są już rozdzielone — potwierdzone

`SUBSTACK_HANDLE` i `NAZWA_MARKI` nadpisują wartości `[konto]`.
Aktywacja zapisuje lokalny wskaźnik i katalog instancji. Suma kontrolna
wszystkich plików publicznych paczek pozostała taka sama przed i po aktywacjach,
odłączeniach i zmianie tematu.

Klucze, wskaźnik i instancje są ignorowane. Nowe prywatne katalogi presetów
również. Publiczny `hidden-bill` został jawnie dopuszczony w `.gitignore`
i audycie, bez wyłączania kontroli sekretów.

Wniosek: **nie potrzebujecie osobnego repozytorium ani gałęzi na każdego
użytkownika.** Użytkownik nie musi również forkować projektu, żeby go uruchomić.
Fork służy do własnego rozwoju kodu, nie do samej konfiguracji konta.

Źródła: [końcowe składanie konfiguracji](../../agent-v2/config.py),
[CLI](../../narzedzia/presety.py), [reguły Git](../../.gitignore).

### 5. Kontrola konta przeglądarki nie potwierdza zalogowanej tożsamości — priorytet wysoki

`wymagaj_wlasciwego_konta` pyta o publiczny profil **skonfigurowanego**
uchwytu. Taki wynik może potwierdzić, że profil istnieje, ale nie dowodzi,
że aktualna sesja jest zalogowana właśnie jako on. Brak odpowiedzi lub wyjątek
powoduje ostrzeżenie i kontynuację. Wynik dodatni jest zapamiętywany w procesie.

Podobnie `sprawdz_sesje` ocenia tekst strony, a `sprawdz_serwer` łączy
ciastko, publiczny profil i widoczność kompozytora. To przydatne sygnały
diagnostyczne, ale nie pełny dowód właściwego konta.

**Do zmiany:** potwierdzać rzeczywiście uwierzytelnionego użytkownika i jego
dostęp do właściwej publikacji. Odpowiedź niepewna powinna blokować zapis,
z czytelnym komunikatem naprawczym. Zapisaną sesję powiązać z właścicielem
instancji i sprawdzać po podłączeniu/przelogowaniu.

**Odbiór:** skonfigurowane konto A, zalogowane B → zero zapisów; brak odpowiedzi
identyfikacyjnej → zero zapisów; sesja A z uprawnieniem do właściwej publikacji
→ przejście. Nie zgadywać endpointu bez sprawdzenia jego semantyki.

Źródło: [browser.py — kontrola konta i sesji](../../agent-v2/browser.py).

### 6. Zmiana konta w środowisku omija właściciela podczas startu — priorytet wysoki

Potwierdzona kontrpróba: aktywować instancję dla A, zmienić `.env` na B
i uruchomić nowy proces. Konfiguracja przyjmuje B, podczas gdy
`wlasciciel.json` nadal wskazuje A. Powtórne `podlacz` prawidłowo odrzuca
taki konflikt, ale sam start nie wymusza tego sprawdzenia.

**Skutek:** instrukcja „wpisz inne konto i uruchom” może skierować nowe konto
do banku, historii i sesji starej instancji.

**Do zmiany:** przy starcie, po rozwiązaniu środowiska, porównać skuteczne konto,
preset i właściciela katalogu. Przy różnicy odmówić oraz wskazać nową instancję
lub świadomą procedurę migracji. Przeniesienie klucza tego samego konta nie
powinno wymagać nowego banku.

**Odbiór:** A → zmiana środowiska na B → start odmawia przed użyciem sesji,
banku lub modelu. Właściciel nie może być sprawdzany tylko przy komendzie CLI.

Źródła: [aktywacja i właściciel](../../agent-v2/preset.py),
[środowisko po aktywacji](../../agent-v2/config.py).

### 7. Numer aktywacji nie jest egzekwowany — priorytet wysoki

Kod zapisuje numer aktywacji, ale `aktywacja_nadal_wazna` porównuje odcisk
presetu i ID instancji. Kontrpróba potwierdziła, że po odłączeniu i ponownym
podłączeniu identycznej paczki do tego samego ID stary proces znów przechodzi
kontrolę, mimo zmienionego numeru.

**Do zmiany:** unikalna generacja aktywacji, porównywana przed płatnymi
wywołaniami i zapisami na koncie. Uwzględnić tożsamość instalacji/konta
w niezmiennym kontekście procesu. Zatrzymanie procesów nadal pozostaje
potrzebne przy wdrożeniu; żądania wysłanego wcześniej nie da się odwołać
samą zmianą pliku.

**Odbiór:** A → odłącz → to samo A/ID → nowy proces działa, stary bezwarunkowo
odmawia. Tak samo dla podmiany konta i dla równoległych przełączeń.

Źródło: [preset.py — aktywacja_nadal_wazna](../../agent-v2/preset.py).

### 8. Kilka klonów może współdzielić Chrome — priorytet wysoki dla wielu kont

`CDP_PORT = 9222`, a `CHROME_PROFILE` wskazuje katalog
`substack-agent-chrome` pod użytkownikiem systemowym. Ścieżka zapisu sesji
jest per instancja, ale połączenie CDP wybiera działający kontekst przeglądarki.
Nowy klon może więc ominąć własny plik sesji i trafić do poprzednio
zalogowanego Chrome.

**Do zmiany:** konfiguracja przeglądarki należy do instalacji, nie publicznego
presetu: unikalny profil, port/endpoint i jednoznaczny właściciel połączenia.
Kontrola zajętego portu powinna sprawdzać zgodność, a nie tylko istnienie serwera.

**Obecnie:** jedna publikacja na maszynę/izolowane środowisko jest prostsza.
Sam oddzielny katalog klonu ani odrębne konto systemowe bez izolacji portów
nie wystarczają jako gwarancja.

**Odbiór:** dwa konta w dwóch klonach na tym samym hoście nie mogą korzystać
z tego samego uwierzytelnionego kontekstu omyłkowo.

Źródło: [browser.py — CDP_PORT, CHROME_PROFILE, podlacz_sie](../../agent-v2/browser.py).

### 9. Harmonogram i serwer nie są jeszcze kompletnym instalatorem — priorytet wysoki dla wygody

Generator tworzy usługę agenta, artykułu i alarmu oraz timery z aktywnego
presetu. Nie przygotowuje jednak Chrome, ekranu, zdalnego logowania i całego
cyklu utrzymania sesji. `AGENT_V2_SERVER=1` nie instaluje tych składników.

Nazwy usług są stałe, więc dwie instalacje mogą się nadpisać. Przy zmianie
presetu na zero artykułów nowe jednostki artykułu są pomijane, ale stare
pliki i zainstalowany timer nie są automatycznie usuwane. Generator nie czyści
również wcześniej wygenerowanych plików z tego samego katalogu wyniku.

Na Windows brakuje eksportu zadań harmonogramu. Operator ręcznie przepisuje
godziny UTC, wybiera użytkownika i ustawia katalog roboczy.

**Do zmiany:** `install/start/stop/status/uninstall` dla jednej nazwanej
instalacji; osobne nazwy usług, sprzątanie nieaktualnych zadań, generator
Windows, kontrola Chrome i stref czasowych. Dla serwera wybrać i przetestować
jeden konkretny sposób utrzymywania przeglądarki z ręcznym logowaniem.

**Odbiór:** nowy użytkownik na czystym Windows oraz Linux przechodzi jedną
instrukcję; po zmianie 1 artykuł → 0 nie zostaje żaden dawny wyzwalacz;
dwie instalacje nie zmieniają sobie zadań.

Źródła: [generator](../../narzedzia/jednostki.py),
[szablony usług](../../agent-v2/systemd/nia-agent.service),
[instrukcja z obecnymi ograniczeniami](../../docs/INSTALL.md).

### 10. „Czysty” ma trzy różne znaczenia — trzeba je rozdzielić w produkcie

1. **Czyste repo dystrybucyjne:** silnik i publiczne paczki, bez danych użytkownika.
2. **Nieaktywny silnik:** wskaźnik odłączony; prywatne dane pozostają na dysku.
3. **Nowa redakcja:** nowa instancja, właściwe konto/sesja i brak dawnych kolejek.

Odłączenie daje punkt 2, nie punkt 1. Nowe ID daje nowe lokalne dane, ale
nie usuwa starych treści z tego samego konta Substack. Bot może je ponownie
odczytać w ramach normalnej pracy z kontem.

**Do zmiany w interfejsie:** osobne operacje „wstrzymaj/odłącz”, „wznów”,
„nowa instancja” i „usuń prywatne dane”. Destrukcyjne kasowanie powinno
wymieniać konkretne ścieżki i zakres. Nie łączyć go automatycznie z odłączeniem.

### 11. Sufit kosztów nie jest limitem wszystkich instalacji — priorytet średni

Koszty są przypisane do bazy instancji, a nie do wspólnego rachunku dostawcy.
Dwa klony na tych samych kluczach mają oddzielne liczniki. Nowa instancja
również zaczyna nowy lokalny rejestr. Preflight sprawdza dotychczasowy koszt;
cena następnego żądania zależy od odpowiedzi, narzędzi i cennika.

**Do zmiany:** wspólny opcjonalny rejestr budżetu dla profilu rozliczeniowego,
rezerwacja kosztu przed żądaniem i rozliczenie rzeczywistego zużycia.
Oddzielić cele liczby publikacji od limitów pieniędzy; wyczerpanie budżetu
ma dawać czytelny status niewykonanych slotów.

**Obecnie:** limity są użyteczne operacyjnie, lecz nie należy reklamować
„25/40 USD gwarantuje cały miesiąc” ani mnożyć instancji bez zsumowania rachunku.

Źródło: [llm.py — preflight i zapis kosztów](../../agent-v2/llm.py).

### 12. Wybór modeli, stylu i startowych pomysłów ma granice — priorytet średni

Schemat pozwala przypisywać role, ale samo wpisanie innej nazwy dostawcy
nie dostarcza adaptera. Obecny transport tekstowy obsługuje Claude i DeepSeek;
ścieżka OpenAI dotyczy obrazów. Tokeny, część ustawień rozumowania,
reguły form i bramki nie są w pełni parametrami presetów.

Podobnie `START.md` nowej paczki nie jest automatycznie wczytywany do banku.
`eksportuj` daje TOML bez promptów i stylu. Puste pole korpusu nie sięga
do starego korpusu silnika, ale paczka może wciąż wczytać własny
`styl/korpus.txt`, jeśli ten istnieje.

**Do zmiany:** jawne możliwości presetu, kontrola zgodności z wersją silnika,
pełny eksport paczki, import pomysłów z deduplikacją oraz rozdzielenie
„bez korpusu” od domyślnej ścieżki korpusu. Nowe języki i gatunki wymagają
próbek i oceny, nie samego przełączenia etykiety.

Źródła: [schema i eksport](../../agent-v2/preset.py),
[transport modeli](../../agent-v2/llm.py),
[paczka Hidden Bill](../../presety/hidden-bill/README.md).

### 13. Aktualizacja publicznego presetu zmienia lokalny plik użytkownika — priorytet średni

Użycie publicznej paczki bez edycji jest wygodne. Przy późniejszym
`git pull` aktualizacja tej paczki zmienia jednak lokalny odcisk; start może
odmówić do czasu reaktywacji. Po reaktywacji użytkownik przyjmuje również
nowe ustawienia redakcyjne. To nie wyciek danych, lecz zagadnienie wersjonowania.

**Do zmiany:** wydania silnika, wersje paczek, changelog i możliwość przypięcia
wybranej wersji. Aktualizacja powinna pokazać różnicę stylu, źródeł, modeli,
kosztów i harmonogramu. Prywatna kopia daje dziś prostą kontrolę nad własnymi
ustawieniami, kosztem ręcznego przenoszenia poprawek.

## Zalecana kolejność rozwoju

| Etap | Rezultat | Warunek zakończenia |
|---|---|---|
| Teraz: porządek w dystrybucji | Aktualne `main`, opis, katalog, jedna instrukcja | Pobranie prowadzi do obecnego workflow i nie wymaga danych autora |
| 1. Tożsamość i granice procesu | Właściciel przy starcie, właściwa sesja, generacja aktywacji | Kontrpróby z punktów 5–8 blokują niewłaściwe operacje |
| 2. Uruchomienie jako produkt | Kreator, diagnostyka, Windows i Linux | Powtarzalny start dwóch izolowanych instalacji z czystego systemu |
| 3. Utrzymanie i koszty | Zatrzymywanie, kopie, aktualizacje, wspólny budżet | Bez dawnych timerów, mieszania danych i resetowania limitu przez nowe ID |
| 4. Bogatsze presety | Możliwości, wersje, eksport i import banku | Paczka przenosi wszystkie potrzebne zasoby, a jakość jest oceniona próbkami |

Nie potrzeba teraz przepisywać całego bota na nowy framework. Największą
różnicę dla użytkownika zrobi domknięcie powyższych granic i jedna sprawdzona
procedura instalacji.

## Weryfikacja przygotowanej wersji

Dziesięć istniejących zestawów zakończyło się wynikiem **436 asercji zdanych,
0 oblanych**: presety, konfiguracja, wartości pochodne, dwa zestawy systemd,
neutralność promptów, korpus, odłączenie, konto z `.env` i liczby w dokumentacji.
Obie paczki przeszły `sprawdz` oraz `podglad`. Mapa funkcji nie wymagała zmian;
w generowanym opisie silnika odświeżono licznik sprawdzeń po usunięciu
nieaktualnych wymagań liczbowych wobec przebudowanego README.

Dodatkowe próby integracyjne potwierdziły odmowę aktywacji placeholdera,
skuteczne konto z `.env`, ścieżkę sesji per instancja, odrzucenie zajętego ID,
zachowanie starego katalogu przy zmianie tematu i brak zmian w publicznych
paczkach. Odmowa przebiegu bez presetu ma kod wyjścia **3**; początkowe
oczekiwanie kodu 1 w pomocniczym skrypcie zostało skorygowane do rzeczywistego
kontraktu CLI. Dwie kontrpróby potwierdziły opisane luki generacji i właściciela;
nie są dowodem ich naprawienia.

Końcowy audyt repozytorium z historią: **59 sprawdzeń zdanych, 0 oblanych,
3 uwagi**. Uwagi dotyczą istniejącej kontroli wyliczania terminu i ostrzeżeń
walidacji obu paczek w środowisku kontrolnym. Test linków dokumentacji również
przeszedł. Kontrola historii dotyczy reguł tego audytora; nie stanowi gwarancji
wykrycia każdego możliwego sekretu.

To zakres wybranych kontroli, nie deklaracja przejścia każdego historycznego
testu ani gotowości produkcyjnej nowego serwera. Repozytorium ma dodatkowy
workflow CI, pominięcia środowiskowe i testy zależne od dawnych commitów.
