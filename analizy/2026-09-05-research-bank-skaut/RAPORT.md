# Research, bank pomysłów i skaut NIA — audyt architektury

Stan lokalnego projektu z 5 września 2026. Raport obejmuje pozyskiwanie sygnałów, wybór tematów, wyszukiwanie i czytanie źródeł, wydobywanie dowodów, bank kandydatów, bank fragmentów, aktualność, prompty tych etapów oraz koszt uzyskania materiału nadającego się do publikacji.

**Główna diagnoza: bot potrafi zgromadzić materiał, ale nie zarządza konsekwentnie tym, co już wie, czego jeszcze nie sprawdził i za co już zapłacił.** Ten sam tekst bywa hipotezą skauta, „zweryfikowanym faktem” banku i potwierdzonym twierdzeniem karty, mimo że przejście między tymi stanami nie wymaga udokumentowanego sprawdzenia. Z kolei wartościowe wyniki researchu są rozproszone między pamięcią procesu, plikami etapów, wpisami kandydatów i kartami zapisanych artykułów.

Największą korzyść da spięcie tych miejsc jednym obiegiem dowodów. Skrócenie promptów i dobór modeli będą wtedy optymalizacją rzeczywiście potrzebnej pracy.

## 1. Zakres, metoda i granice ustaleń

Przeczytałem funkcje odpowiedzialne za wskazane etapy, ich wywołania, aktywne szablony promptów, konfigurację po załadowaniu lokalnego TOML, schemat bazy oraz jednostki harmonogramu zapisane w repozytorium. Analizowałem przepływ pól między funkcjami, a nie tylko deklaracje w komentarzach.

Wykonałem **18 bezpłatnych scenariuszy odtworzenia** na rzeczywistych funkcjach, z zastąpionym transportem modelu i syntetycznymi danymi. Przy próbach zapisu banku użyłem automatycznie usuwanego katalogu tymczasowego. Produkcyjną bazę otworzyłem wyłącznie w trybie SQLite mode=ro. Nie uruchamiałem płatnego researchu, generowania tekstów ani publikacji.

W raporcie rozróżniam:

- **Odtworzone:** funkcja rzeczywiście zachowała się w opisany sposób na kontrolowanym wejściu. Nie oznacza to, że zmierzono częstość tego błędu na produkcji.
- **Wynik odczytu:** przepływ wynika bezpośrednio z kodu lub promptu.
- **Propozycja:** projekt usprawnienia, którego wpływ na jakość należy sprawdzić porównaniem wyników.

Punktem odniesienia repozytorium był commit 1a711e80b7f81b049e5bdf55ddbd8973c09a2d3f. Podczas audytu pojawiły się równoległe zmiany ścieżek pisania i ich dokumentacji, w tym ograniczenie liczby paraleli materiałem karty. Nie są moją implementacją; poniższa diagnoza nie opiera się na dawnym obowiązku dodawania paraleli do pustej karty. Nazwy funkcji przy odnośnikach ułatwiają odnalezienie miejsca także po przesunięciu numerów linii.

**Jedynym pozostawionym przeze mnie rezultatem tego audytu jest ten raport.**

### Co rzeczywiście jest dostępne lokalnie

| Element | Stan podczas odczytu | Co z tego wynika |
|---|---:|---|
| Przebiegi w bazie | 7 | Za mało do oceny niezawodności długookresowej |
| Zapisane wywołania | 18 | Można wskazać konkretne rachunki, nie wiarygodną średnią miesięczną |
| Artykuły w tabeli articles | 0 | Brak lokalnej próby oceny jakości artykułów i skuteczności banku fragmentów |
| Rekordy sources | 6, wszystkie fetched_ok=1 | To mała próbka dostępności, nie dowód jakości wyciągniętych twierdzeń |
| Bank kandydatów | 4: 2 użyte, 1 odrzucony, 1 nowy | Nie jest reprezentatywnym przekrojem produkcyjnej puli |
| Kanały YouTube w efektywnej konfiguracji | 0 | Lokalny skaut nie ma tego zewnętrznego zaczynu |
| Automatyczne pytanie o stan dziedziny | Wyłączone | Nie należy przypisywać tej instalacji codziennego kosztu tego etapu |
| Lokalna nisza | Raportowanie, audyt i regulowanie liczb firmowych | Przykłady AI w komentarzach opisują również inne konfiguracje i historię projektu |

Nie sprawdzałem działającego serwera. Jednostka systemd w repozytorium pokazuje zamierzony punkt wejścia; nie dowodzi, co jest obecnie zainstalowane na zdalnej maszynie.

### Najważniejsze ustawienia

Jedna partia ciekawostek: 8. Próg pełnego banku: 20 wolnych wpisów. Przechowywane wpisy: najwyżej 600. Termin kandydatury: 7 dni. Zwykłe dobieranie banku: limit 1 przebiegu dziennie, z wyjątkami dla artykułu i nowych wydarzeń.

Discovery prosi o maksymalnie 10 źródeł i 8 wyszukiwań. Research próbuje uzyskać minimum 4 pobrane źródła i 2 pierwotne; prompt dodatkowo wymaga 2 wyjaśniających „dlaczego”. Klasyfikator dostaje do 90 000 znaków dokumentu i ma zwrócić do 12 fragmentów po 700 znaków. Synteza ma pozostawić 5–8 potwierdzonych twierdzeń i maksymalnie 8 liczb.

To są różne rodzaje ograniczeń: część egzekwuje kod, część istnieje wyłącznie w instrukcji. Ich rozbieżność jest jednym z ustaleń audytu.

## 2. Jak materiał naprawdę przepływa

### 2.1. Codzienne notki

~~~text
notki_dnia
  → ranking istniejącego banku
  → pobranie kandydatów z banku i oznaczenie ich jako użytych
  → jeśli zapasu brak: znajdz_ciekawostki
       → kanały i wykrywanie wydarzeń
       → ograniczenia dobierania banku
       → opcjonalny kontekst aktualności dziedziny
       → płatne wyszukiwanie i wygenerowanie faktów
       → kontrola świeżości
       → zapis z bramką do banku
       → zwrot znalezionych faktów niezależnie od wyniku bramki zapisu
  → dobór jednego faktu na notkę, kontrola powtórek
  → pisanie i późniejsze sprawdzanie gotowego tekstu
  → oddanie niewykorzystanej części puli
~~~

Źródła: [notki_dnia](<D:/Nia bot/agent-v2/stages.py:3518>), [znajdz_ciekawostki](<D:/Nia bot/agent-v2/stages.py:1628>).

### 2.2. Artykuł tygodniowy wskazany przez harmonogram

~~~text
artykul_z_puli.py
  → maksymalnie 8 kandydatów z tego samego banku co notki
  → pierwszy niekolidujący z historią
  → model tworzy brief i pytania szczegółowe
  → sprawdzenie, czy opisano drugi akt lub zasięg poza jedno miejsce
  → discovery dla pytania głównego i pytań szczegółowych
  → fetch
  → ewentualna druga runda według liczby dokumentów
  → classify dla samego pytania głównego
  → synthesis dla samego pytania głównego
  → dołożenie faktu startowego, jeśli jego URL nie ma potwierdzonego twierdzenia
  → ocena „warto pisać”, opcjonalnie bibliotekarz
  → pisarz i dalsze kontrole
~~~

Źródła: [jednostka artykułu](<D:/Nia bot/agent-v2/systemd/nia-artykul.service>), [wybierz_fakt](<D:/Nia bot/agent-v2/artykul_z_puli.py:255>), [_przebieg](<D:/Nia bot/agent-v2/artykul_z_puli.py:460>).

### 2.3. Osobny skaut starszej ścieżki

W run.py nadal istnieje ścieżka scout → feasibility → pick_topic → research. Jej skaut proponuje tematy, precedensy i ocenę nasycenia z pamięci modelu oraz nagłówków kanałów. Samo wywołanie scout nie włącza wyszukiwania. Feasibility również nie wyszukuje dokumentów.

**Poprawienie samego skaut.md nie zmieni wyboru tematów tygodniowego artykułu z banku.** Są dwa różne mechanizmy wyboru, z różnymi kryteriami. To trzeba uwzględnić przed każdą zmianą promptu. [scout](<D:/Nia bot/agent-v2/stages.py:5848>), [feasibility](<D:/Nia bot/agent-v2/stages.py:5407>), [starsza ścieżka](<D:/Nia bot/agent-v2/run.py:2341>).

### Co warto zachować

Projekt ma użyteczne fundamenty: rozdzielenie wyszukiwania, pobierania, ekstrakcji i syntezy; preferowanie dokumentów pierwotnych; konkretne mechanizmy zamiast samych tematów; pobieranie z banku przed płatnym dobieraniem; pamięć powtórek; rejestrowanie kosztu; możliwość wznowienia z karty; rozdzielenie daty źródła od dokumentu kontrolnego; pomysł łączenia materiału według mechanizmu.

RSS ma już pamięć w procesie z terminem 30 minut. Pobieranie używa wspólnego klienta HTTP, ma obsługę PDF, odstęp między żądaniami do jednego hosta i drugie podejście przez przeglądarkę. Nie proponuję „dodać cache RSS” ani „dodać PDF” jako nowych funkcji. Trzeba rozwinąć istniejące rozwiązania tam, gdzie kończy się ich zasięg.

## 3. Skaut: gdzie powstają złe decyzje redakcyjne

### S1. Pełny bank może zasłonić nowe wydarzenie

**Odtworzone.** Gdy notki_dnia dostało użyteczny fakt z banku, powstała jedna notka, ale licznik wywołań wyszukiwania i detektora wydarzeń wyniósł zero.

Detektor znajduje się wewnątrz znajdz_ciekawostki. Pobranie zapasu omija tę funkcję. Komentarz, że „furtka wydarzeń nie ginie”, dotyczy dopiero sytuacji wyczerpania zapasu. W międzyczasie temat z banku może wygrać z premierą, której system nawet nie sprawdził. [notki_dnia](<D:/Nia bot/agent-v2/stages.py:3518>).

**Zmiana:** tani odczyt sygnałów powinien być osobnym początkiem przebiegu. Dopiero jego wynik i stan banku decydują o płatnym szukaniu. Pełny bank ma zatrzymywać kupowanie kolejnych podobnych faktów, a nie wyłączać obserwację świata.

### S2. Wydarzenie może być „obsłużone” przez fakt na zupełnie inny temat

**Odtworzone.** Detektor zgłosił premierę Orion 5.1. Model zwrócił fakt o czujniku ciśnienia, bez wzmianki o Orionie. Pamięć wydarzenia dostała ile=1, a następne sprawdzenie nie uznało go za nowe.

Na końcu znajdz_ciekawostki do pamięci wszystkich nowych wydarzeń trafia liczba wszystkich zwróconych faktów. Nie jest to liczba przyjętych do banku pomysłów dotyczących danego wydarzenia. Nawet odrzucony lub już znany materiał może więc zamknąć okazję. [_zapamietaj_wydarzenia](<D:/Nia bot/agent-v2/stages.py:1469>), [znajdz_ciekawostki](<D:/Nia bot/agent-v2/stages.py:1628>).

**Zmiana:** każdy fakt powinien wskazywać event_id. Zapisywać osobno „sprawdzono”, „brak materiału”, „mamy użyteczny kąt”, „opublikowano”. Nieudana próba potrzebuje terminu ponowienia i powodu, zamiast semantycznie udawać obsłużenie wydarzenia.

### S3. Wspólny numer wersji może skleić różne premiery

**Odtworzone.** Dwa różne kanały z tytułami dotyczącymi Orion 5.1 i Vega 5.1 utworzyły jedno wydarzenie premierowe o rdzeniu „5.1”.

Premiera jest początkowo grupowana po tokenie zawierającym cyfrę, nie po parze produkt–wersja. Próba dopisania wspólnego kontekstu nie pomaga, jeżeli jedyną częścią wspólną jest sam numer. Ten sam mechanizm może też nie zauważyć nowej premiery, jeżeli identyczny numer występował wcześniej przy innym produkcie. [wielkie_wydarzenia](<D:/Nia bot/agent-v2/korpus_kanalow.py:183>).

**Zmiana:** identyfikować encję, wersję i rodzaj zdarzenia. Niepewne przypisanie ma pozostać sygnałem do sprawdzenia. Zbieżność tytułów kilku kanałów mierzy zainteresowanie; nie jest potwierdzeniem wydarzenia przez niezależne dokumenty.

### S4. Czyści się tytuł, ale nie odzyskuje zdarzenia

Przetwarzanie RSS odrzuca całe pozycje za frazy takie jak „first look”, „I tested”, „hands-on” oraz tytuły mające po czyszczeniu mniej niż cztery słowa. To może usunąć właśnie relację z pomiaru albo krótką, konkretną premierę. Deduplikacja usuwa kolejne jednakowe tytuły niezależnie od kanału, zanim detektor policzy liczbę różnych kanałów.

Nie zmierzyłem udziału utraconych tematów na reprezentatywnym korpusie. Mechanizm utraty wynika jednak wprost z [przetworz](<D:/Nia bot/agent-v2/korpus_kanalow.py:111>).

**Zmiana:** przechowywać surowe sygnały z identyfikatorem filmu i kanału. Oddzielić odrzucenie materiału czysto organizacyjnego od obniżenia priorytetu clickbaitowi. Grupowanie zdarzeń powinno zachować wszystkich świadków, nawet gdy widok listy pokazuje jeden wspólny temat.

### S5. Nakaz 75% z kanałów nie jest dopasowany do dostępnego wejścia

Oba prompty silnie narzucają kanały jako początek tematów. W aktualnej konfiguracji lokalnej kanałów jest zero. curiosity nadal otrzymuje rozbudowane polecenia dotyczące „tego tygodnia” i wymaganej proporcji, mimo braku tej listy.

Ponadto oznaczenie z_kanalu ustala podobieństwo słów. Nie ustala, że pytanie redakcyjne rzeczywiście wynika z sygnału. Przy pobieraniu z banku sam ten znacznik wygrywa z każdą rangą jakości: w próbie kandydat z rangą 999 wygrał z kandydatem o randze 0.

**Zmiana:** składać prompt warunkowo z dostępnych źródeł; kotwicę identyfikować przez signal_id. Aktualność traktować jako osobny wymiar wyboru. Silny priorytet powinno dostawać potwierdzone, czasowo istotne wydarzenie, nie każda leksykalna zbieżność z jakimkolwiek tytułem.

### S6. Starszy skaut ma zbyt wąską teorię dobrego artykułu

skaut.md zaczyna od szerokiego zainteresowania tematem, ale potem wymusza dwa rodzaje: błędne przekonanie albo system pod próbą. Co najmniej połowa listy ma należeć do drugiego rodzaju; co najmniej trzy pozycje mają mieć po dwa precedensy. Artykułowość w kodzie zależy od precedensów i dużego zasięgu.

To selekcja pod określony gatunek opowieści. Utrudnia wybór mocnego wyjaśnienia, wyniku eksperymentu, historii odkrycia czy jednego mechanizmu o wielu konsekwencjach. Wymaganie precedensów z pamięci dodatkowo zachęca model do proponowania najbardziej dostępnych, wielokrotnie opisanych przypadków.

**Zmiana:** wspólny katalog sposobów rozwinięcia materiału: wyjaśnienie, pomiar, zmiana w czasie, spór dowodowy, korekta udokumentowanej obietnicy, historia decyzji. Dopuszczać brak mitu, precedensu i drugiej dziedziny. Rodzaj ma wynikać z dowodów. [skaut.md](<D:/Nia bot/agent-v2/prompts/skaut.md>).

### S7. Nasycenie i wykonalność są zgadywane przed obejrzeniem źródeł

„Nie przypominam sobie artykułu o tym” nie mierzy faktycznej oryginalności. Feasibility ocenia dostępność dokumentów bez próby pobrania, a dostaje tylko indeks, tytuł i główne pytanie. Prompt każe oceniać również threads, których w przekazanym obiekcie nie ma.

**Zmiana:** tanią ocenę modelu nazywać hipotezą wykonalności. Dla kilku finalistów sprawdzić jeden wskazany dokument i najbliższe wcześniejsze materiały. Oryginalność określać jako różnicę: jakie pytanie lub ustalenie wniesiemy względem znanego tekstu. Nie trzeba robić pełnego researchu całej puli. [feasibility](<D:/Nia bot/agent-v2/stages.py:5407>), [wykonalnosc.md](<D:/Nia bot/agent-v2/prompts/wykonalnosc.md>).

### S8. Pytania czytelników i dodatkowe źródła nie zasilają wspólnie wyboru

Pytania są zbierane, ale pytania_dla_skauta jest wywoływane przez starszy scout. Tygodniowy wybór faktu i curiosity nie otrzymują tej listy. Nie ma też stanu „odpowiedzieliśmy”, grupowania tej samej potrzeby ani powiązania pytania z gotowym tekstem.

Funkcje kandydaci_z_fedreg i osobnego banku notek istnieją, ale w przejrzanych głównych ścieżkach nie znalazłem ich włączenia do tego obiegu. Nie można zaliczać samej obecności modułu jako działającego kanału odkrywania.

**Zmiana:** jedno wejście dla sygnałów z kanałów, rejestrów, pytań czytelników i znalezionych luk. Każdy sygnał zachowuje pochodzenie oraz powód zainteresowania. Dobór źródeł powinien odpowiadać niszy; lokalne konto o raportowaniu liczb nie powinno zależeć od nieistniejących kanałów AI. [pytania_dla_skauta](<D:/Nia bot/agent-v2/stages.py:6590>).

## 4. Bank pomysłów: jakość wejścia, selekcja i życie materiału

### B1. Odrzucenie przez bank nie wyklucza użycia tego samego faktu

**Odtworzone.** curiosity zwróciło fakt z pustym wrong_belief. dopisz_kandydatow zapisało go jako odrzucony. Mimo tego znajdz_ciekawostki oddało na wyjściu jeden fakt — właśnie odrzucony.

Funkcja zapisująca zwraca liczniki, ale wywołujący nie używa wyniku do ograniczenia listy. Notki i artykuł mogą pobrać tę listę bezpośrednio. Materiał świeżo znaleziony ma zatem inną drogę do pisarza niż identyczny materiał odczytany jutro z banku.

To nie dowód, że ten konkretny przykład jest merytorycznie zły. To dowód, że **bramka nie jest wspólnym kontraktem dostępu do materiału**. [znajdz_ciekawostki](<D:/Nia bot/agent-v2/stages.py:1628>), [dopisz_kandydatow](<D:/Nia bot/agent-v2/stages.py:6958>).

**Zmiana:** po dopisaniu odbierać identyfikatory przyjętych lub już istniejących kandydatów. Wybór zawsze przeprowadzać na jednym, kanonicznym widoku banku. Najpierw poprawić sens kryteriów opisanych poniżej; samo uszczelnienie złej bramki mocniej odetnie dobre pomysły.

### B2. Bank wymusza mit nawet tam, gdzie prompt pozwala wyjaśniać

ciekawostki.md zabrania wymyślania przekonania czytelnika i dopuszcza fakt stojący samodzielnie. Jego końcówka stwierdza jednak, że bez wrong_belief i actually fakt jest bezwartościowy. Kod wymaga co najmniej czterech słów w obu polach.

**Odtworzone:** opis działania czujnika z pustym mitem został odrzucony jako „brak przekonania do złamania”. Model otrzymuje więc bodziec do dopisania przekonania, którego istnienia nie sprawdził.

**Zmiana:** wymagane pola zależne od rodzaju pomysłu. Dla wyjaśnienia: pytanie, ustalenie, mechanizm i znaczenie. Dla sprostowania dodatkowo rzeczywista obietnica lub twierdzenie z własnym źródłem. Pole opcjonalne nie może stawać się obowiązkowe w następnej funkcji. [bramka_kandydata](<D:/Nia bot/agent-v2/stages.py:6655>), [ciekawostki.md](<D:/Nia bot/agent-v2/prompts/ciekawostki.md>).

### B3. Dozwolony mechanizm fizyczny może przegrać z zakazem słowa

Prompt dopuszcza ograniczenia wynikające z konstrukcji i matematyki, nawet gdy nikt ich nie wybrał. Bramka odrzuca decision zawierające między innymi „nobody”, „no one”, „nothing”.

**Odtworzone:** „Nobody chose the response because the crystal structure physically forces it” zostało odrzucone jako brak mechanizmu.

Obowiązek drugiej osoby w consequence ma podobne ograniczenie: mierzy obecność angielskiego zaimka. Nie mierzy wartości dla odbiorcy i nie odpowiada konfiguracji innego języka. „Your industry has a complex ecosystem” przejdzie ten warunek bez konkretu.

**Zmiana:** mechanizm opisywać przez typ i relację przyczynową. Skutek ma nazwać obserwowalną zmianę lub wartość poznawczą. Zaimek i długość mogą pomagać formatowaniu, ale nie powinny udawać oceny sensu.

### B4. Identyfikator faktu usuwa właśnie to, co odróżnia aktualizację

**Odtworzone.** Zdania:

- Acme released Model 5.1 with a context window of 100000 tokens.
- Acme released Model 5.2 with a context window of 200000 tokens.

otrzymały identyczny klucz: „acme context model released tokens window with”.

_klucz_faktu bierze angielskie słowa długości co najmniej czterech znaków, usuwa liczby, sortuje zbiór i zachowuje do 12 słów. Nie jest identyfikatorem twierdzenia. Również _slowa usuwa liczby i skraca słowa do sześciu liter. [klucz faktu](<D:/Nia bot/agent-v2/stages.py:1287>), [_slowa](<D:/Nia bot/agent-v2/stages.py:3224>).

**Skutek:** nowa wersja, próg, data lub wynik mogą wyglądać jak zużyty fakt. Parafraza może natomiast przejść jako nowość, jeżeli dostatecznie zmieni słownictwo.

**Zmiana:** rozdzielić trwałe ID, identyfikację encji, podobieństwo tematu oraz porównanie twierdzeń. Zachowywać liczby z jednostką, wersję, datę obowiązywania i źródło. „Ten sam temat, nowe ustalenie” powinno być osobnym wynikiem deduplikacji.

### B5. Raz odrzucony pomysł utrudnia wejście poprawionej wersji

Deduplikacja przy dopisywaniu porównuje wszystkie rekordy, również odrzucone, użyte i przeterminowane. Nie ma operacji „uzupełnij brakujące źródło tego kandydata”. Poprawione zgłoszenie z tym samym kluczem odpada przed ponowną oceną.

Prompt idzie jeszcze dalej: nazywa powtórką tę samą regulację z innego kąta oraz ten sam mechanizm w sąsiedniej branży. To koliduje z bibliotekarzem, którego zadaniem jest odnajdywanie wartości właśnie w takich połączeniach.

**Zmiana:** przechowywać temat, kąt i dowód jako różne obiekty. Nowy kąt powinien wykazać nową odpowiedź dla czytelnika. Rewizja ma aktualizować kandydata z historią przyczyny, a nie próbować oszukać deduplikator innymi słowami. [dopisz_kandydatow](<D:/Nia bot/agent-v2/stages.py:6958>).

### B6. Pobranie z banku jest zapisywane jak zużycie

**Odtworzone:** wez_kandydatow ustawiło status uzyty przed pisaniem.

Są funkcje oddawania reszty i część obsługi niepowodzeń. Nie tworzą jednak transakcji obejmującej cały przebieg. Wyjątek po wyborze, zatrzymanie po samym temacie albo niewykonany zwrot może zostawić materiał jako zużyty. Z kolei świeżo wygenerowany fakt, przekazany bezpośrednio z curiosity, zaczyna od innego stanu.

**Zmiana:** oddzielić rezerwację od wykorzystania. Minimalne stany: do sprawdzenia, gotowy, zarezerwowany, szkic gotowy, opublikowany, do aktualizacji, odrzucony. Rezerwacja musi mieć identyfikator zadania, termin i możliwość wznowienia. Po potwierdzeniu publikacji zapisać relację do tekstu, nie tylko boolean. [wez_kandydatow](<D:/Nia bot/agent-v2/stages.py:7064>).

### B7. Ranking może nie działać właśnie wtedy, gdy pojawiają się wyniki czytelników

**Odtworzone w pełnej ścieżce rankingu.** Przy niepustych pomiarach co_zadzialalo prowadzi do _tabela_odbioru, które używa statystyki._liczba. Moduł statystyki importowany jest lokalnie wewnątrz co_zadzialalo, więc druga funkcja nie ma tej nazwy w swoim zakresie.

Wynik próby: NameError; posortuj_bank zwróciło ocenione=0 i wyrzucone=0; model rankingu nie został wywołany. Błąd jest łapany jako nieudany ranking, więc bot może dalej działać ze starą kolejnością.

**Zmiana:** naprawić przekazanie zależności do funkcji tworzącej tabelę. Ważniejszy warunek odbioru: pojawienie się pierwszego pomiaru nie może wyłączyć selekcji tematów. [co_zadzialalo](<D:/Nia bot/agent-v2/stages.py:7248>), [_tabela_odbioru](<D:/Nia bot/agent-v2/stages.py:7331>), [posortuj_bank](<D:/Nia bot/agent-v2/stages.py:7364>).

### B8. Przykłady „zadziałało” i „nie zadziałało” nakładają się

Po podstawieniu wyłącznie brakującej zależności w pamięci sprawdziłem logikę doboru przykładów. Przy czterech notkach i domyślnym ile=6 **wszystkie cztery znalazły się w obu grupach**.

To osobny problem od NameError. Ponadto kolejność opiera się na liczbie polubień + 3 × odpowiedzi. Wyświetlenia są pokazywane modelowi, ale nie normalizują doboru; wiek notki też nie jest podstawą porównania.

**Zmiana:** grupy rozłączne, minimalna dojrzałość pomiaru i porównywalne okno czasu. Oddzielić dystrybucję od reakcji po ekspozycji. Przy małej próbie nie orzekać „nie zadziałało”. Zostawić część miejsc na eksplorację, aby popularność dotychczasowych tematów nie zamknęła publikacji w jednej formule.

### B9. Nowy kandydat poza pierwszymi 40 może wywoływać ranking, do którego nie trafia

**Odtworzone:** 40 rekordów miało rangi, rekord 41. jej nie miał. Dwa uruchomienia posortuj_bank spowodowały dwa wywołania atrapy modelu. Nowego kandydata nie było w żadnym prompcie; nadal nie otrzymał rangi.

Warunek potrzeby rankingu bada całą listę, ale następnie funkcja bierze jej pierwsze ile elementów. Przy takim stanie płaci za ponowną ocenę starych. Domyślny próg 20 wolnych ogranicza częstość tego przypadku, ale nie jest twardym limitem wielkości banku: wydarzenia i ścieżka artykułu go omijają.

**Zmiana:** oceniać nowych lub zmienionych kandydatów razem z małą liczbą punktów odniesienia. Przechowywać wersję kryteriów, czas i identyfikator zestawu porównania. Ustalać końcową kolejność dla aktualnych finalistów; ranga 0 nadana w dwóch różnych partiach nie dowodzi równorzędnej jakości.

### B10. Płatna ocena artykułowości nie steruje wyborem artykułu

Bank zapisuje na_artykul i ogranicza udział takich rekordów do około jednej trzeciej. wybierz_fakt tego pola nie czyta. Wybiera pierwszy fakt bez kolizji z historią; jeśli wszystkie kolidują, bierze pierwszy mimo kolizji.

**Odtworzone:** kandydat oznaczony na_artykul=False wygrał przed kandydatem na_artykul=True. Potem osobny model jeszcze raz ocenia możliwość rozwinięcia, tworząc brief.

**Zmiana:** oddzielić gotowość do notki od potencjału artykułu i od udokumentowanej gotowości artykułu. Wybierać finalistów według zapotrzebowania konkretnej formy. Nie ustalać, że tylko jedna trzecia materiału może mieć potencjał: to limit miejsc redakcyjnych, nie własność faktów. [wybierz_fakt](<D:/Nia bot/agent-v2/artykul_z_puli.py:255>).

### B11. Sędzia banku nie dostaje dowodów potrzebnych do części własnych decyzji

Do rankingu trafia fakt, mechanizm, skutek i dziedzina. Nie trafiają źródłowy URL, data, dokument kontrolny ani cytat. Prompt pozwala jednak odrzucać materiał jako NOTHING_TO_CHECK, między innymi za brak źródła, i zaznaczać rozwinięcie na artykuł.

Kod chroni przed NO_MECHANISM, jeżeli decision ma sześć słów. To nie potwierdza mechanizmu; sześć słów może opisywać zdarzenie albo pustą deklarację. Ochrona przed wyrzuceniem ponad połowy partii ogranicza zniszczenie banku, ale nie naprawia oceny poszczególnych kandydatów.

**Zmiana:** wejście sędziego musi zawierać krótki stan dowodów. Oddzielić ocenę zainteresowania od stwierdzenia braku pokrycia. Brakujący dokument powinien tworzyć zadanie do sprawdzenia, a trwałe odrzucenie wymaga konkretnego powodu.

### B12. Pojemność banku nie oznacza ilości użytecznego zapasu

bank_pelny liczy nowość statusu, epokę konfiguracji i termin wpisu. Nie sprawdza świeżości samego twierdzenia, kolizji z opublikowanymi treściami ani zapotrzebowania na formę. Kontrola świeżości odbywa się dopiero przy wyjmowaniu; część niezgodności zostaje więc uprzątnięta z opóźnieniem.

Wspólne 7 dni oznacza, że trwałe wyjaśnienie i bieżąca cena tracą przydatność kandydatury według tego samego zegara. Obcinanie całego pliku do ostatnich 600 wpisów liczy również odrzucone i wykorzystane; kolejność dodania zastępuje politykę retencji.

**Zmiana:** mierzyć zapas w liczbie gotowych, różnych kątów na najbliższe publikacje. Osobno przechowywać termin okazji redakcyjnej, termin ponownej weryfikacji twierdzenia i termin rezerwacji. Archiwizować metadane, zachowywać wartościowe dokumenty i dowody. [bank_pelny](<D:/Nia bot/agent-v2/stages.py:7596>), [_zapisz_indeks](<D:/Nia bot/agent-v2/stages.py:6860>).

### B13. Atomowy zapis pliku nie chroni całej operacji na banku

os.replace zabezpiecza pojedynczą podmianę JSON. Nie obejmuje transakcją odczytu, wyboru i zapisu. Dwa procesy mogą odczytać ten sam stan, wybrać ten sam fakt, a później nadpisać wzajemne wyniki. Wspólny plik .json.nowy dodatkowo nie rozdziela zapisujących.

run.py ma własną blokadę procesu. W main artykul_z_puli.py nie znalazłem wejścia w tę blokadę. To **ryzyko wynikające z kodu**, nie odtworzona kolizja produkcyjna.

**Zmiana:** krótkie transakcje rezerwacji w istniejącym SQLite, z warunkowym przejściem ze stanu gotowy. Nie trzymać transakcji przez czas pracy modelu. SQLite zapewnia mechanizmy transakcyjne, ale aplikacja nadal musi zaprojektować rezerwację i obsłużyć zajętą bazę. [main artykułu](<D:/Nia bot/agent-v2/artykul_z_puli.py:323>), [dokumentacja transakcji SQLite](https://www.sqlite.org/lang_transaction.html).

## 5. Research: od hipotezy do dowodu

### R1. Brief podnosi status faktu bez nowego sprawdzenia

temat_z_faktu przedstawia wejście jako udokumentowany fakt, który publikacja zweryfikowała. Model otrzymuje streszczenie i URL, ale nie pobraną treść. Ma opisać drugi akt lub zasięg; uniesie_artykul przyjmuje pole, jeżeli ma co najmniej cztery słowa i nie jest jednym z rozpoznanych pustych określeń.

To przydatny filtr kompletności opisu, ale nie dowód istnienia rozwinięcia. Jednocześnie wybór rozpoczyna się od wrong_belief, actually i decision, więc pytanie może odziedziczyć niepotwierdzoną interpretację.

**Zmiana:** najpierw obejrzeć znane źródło. Brief powinien rozróżniać ustalenie startowe, hipotezę mechanizmu i pytania. Rozwinięcie artykułu uznać za wykonalne po znalezieniu dokumentu odpowiadającego na przynajmniej jedno istotne pytanie poza samym faktem. [brief](<D:/Nia bot/agent-v2/artykul_z_puli.py:109>), [uniesie_artykul](<D:/Nia bot/agent-v2/artykul_z_puli.py:208>).

### R2. Plan pytań znika po wyszukiwaniu

W tygodniowej ścieżce pytania szczegółowe są doklejane do question w discovery. classify i synthesis dostają już tylko brief["question"].

Źródło wyjaśniające jeden z dalszych wątków może wyglądać na mało trafne wobec pytania głównego. Ekstraktor nie wie, że właśnie tego dowodu potrzebuje konstrukcja artykułu. Synteza nie rozliczy brakujących odpowiedzi.

**Zmiana:** każde pytanie dostaje question_id, wagę i kryterium odpowiedzi. Dokumenty, fragmenty i twierdzenia wskazują te identyfikatory. Nie trzeba wszędzie wklejać całego briefu: wystarczy zwarta, wspólna lista zadań badawczych. [_przebieg](<D:/Nia bot/agent-v2/artykul_z_puli.py:460>).

### R3. Druga runda kupuje dokumenty, zanim wiadomo, jakiej wiedzy brakuje

Druga discovery następuje po fetch, przed classify. Decydują liczba pobranych stron i wstępne etykiety PRIMARY. Powtarzane jest całe pytanie, ewentualnie z nakazem samych dokumentów pierwotnych. Wyszukiwarka nie dostaje konkretnych luk ani treści już posiadanych dowodów.

Po klasyfikacji może zostać jeden istotny dokument i kilka braków, lecz na tym etapie nie ma już takiej pętli uzupełniania.

**Zmiana:** ekstrakcja → pokrycie pytań → wybór najważniejszej luki → celowane wyszukanie. Przerwać, gdy kolejne źródła powtarzają wiedzę, kiedy luka nie jest niezbędna albo koszt następnej próby przekracza jej wartość. Brak odpowiedzi też jest wynikiem researchu, który trzeba zapisać z zakresem wykonanej próby.

### R4. Liczba źródeł i status PRIMARY nie mierzą pokrycia twierdzeń

Discovery prosi o trzy organizacje, dwie pozycje „dlaczego” i liczby. Kod nie zamienia answers_why ani has_numbers w mapę wymagań. Synteza tych pól nie otrzymuje.

Oficjalny komunikat firmy jest pierwotnym źródłem tego, co firma ogłosiła. Nie staje się przez to niezależnym potwierdzeniem skuteczności jej produktu. Trzy serwisy powtarzające ten sam raport nie dostarczają trzech niezależnych pomiarów. Z kolei jeden prawidłowy dokument może wystarczyć do wąskiego twierdzenia.

**Zmiana:** oceniać rolę dokumentu względem konkretnego twierdzenia: oryginalny pomiar, deklaracja zainteresowanej strony, obowiązujący zapis, opis wtórny, krytyka, kontekst. Zachować pochodzenie wspólnego badania lub danych. Cel liczbowy źródeł traktować jako diagnostykę, nie substytut kompletności.

### R5. Limity źródeł i fragmentów nie są kontraktem wykonania

**Odtworzone:** discovery przy limicie 10 przyjęło 15 pozycji wskazujących ten sam URL. Nie ma deduplikacji całej zwracanej listy ani końcowego obcięcia do tego limitu. Kontrola pochodzenia adresu sprawdza hosty znalezione przez wyszukiwanie, nie zgodność konkretnej ścieżki URL; poza nimi dopuszcza do 3 adresów.

W drugiej próbie classify przyjęło 15 fragmentów po 1000 znaków, mimo konfiguracji 12 × 700. Filtruje niepuste napisy, ale nie egzekwuje obu tych ograniczeń.

**Zmiana:** walidować schemat, zakresy, unikalne identyfikatory i budżet po parsowaniu, zanim wynik uruchomi następny koszt. Zachować oryginalny URL oraz kanoniczną tożsamość dokumentu; przy canonicalizacji nie usuwać parametrów zmieniających wersję lub zakres danych. [discovery](<D:/Nia bot/agent-v2/stages.py:5251>), [classify](<D:/Nia bot/agent-v2/stages.py:4917>).

### R6. Pobranie strony nie tworzy trwałego, wersjonowanego źródła

Tabela sources zapisuje URL, tytuł, klasę i sukces pobrania. Nie zapisuje tekstu dokumentu, jego skrótu treści, daty publikacji, końcowego adresu po przekierowaniu ani powiązanych fragmentów. Tekst żyje w korpusie bieżącego przebiegu; starsza ścieżka może dodatkowo zapisać go przez cached.

To utrudnia odpowiedź: „który dokument dokładnie przeczytano, co się w nim zmieniło i czy trzeba ponownie zapłacić za ekstrakcję?”. Pobrane wcześniej źródło nie jest wspólnym zasobem następnych artykułów i notek.

**Zmiana:** rejestr wersji źródeł z tekstem, metadanymi, hashem i sposobem pobrania. Ekstrakcję cache'ować względem wersji dokumentu oraz wersji zadania, a nie samego URL. Trafilatura udostępnia również ścieżki zwracające strukturę dokumentu i metadane; wykorzystanie ich wymaga kontroli jakości dat, nie bezwarunkowego zaufania polu. [fetch](<D:/Nia bot/agent-v2/stages.py:5048>), [schemat sources](<D:/Nia bot/agent-v2/db.py:101>), [dokumentacja Trafilatura](https://trafilatura.readthedocs.io/en/latest/corefunctions.html).

### R7. Ucinanie początku dokumentu może usuwać najlepszy dowód

Klasyfikator dostaje pierwsze 90 000 znaków. PDF jest czytany do 40. strony, a tekst zostaje sklejony bez trwałych oznaczeń stron. Wynik, aneks, tabela lub zastrzeżenie poza tym zakresem nie docierają do ekstrakcji.

Pobieranie i klasyfikacja są sekwencyjne. Długie timeouty kolejnych hostów kumulują opóźnienie. Historyczna lista nieskutecznych hostów nie ma okna czasu ani terminu ponowienia: dwie rzeczywiste porażki i zero sukcesów mogą stale zniechęcać discovery do danego hosta.

**Zmiana:** rozpoznawać sekcje i strony, wybierać fragmenty według pytań, zachować sąsiedztwo tabeli i definicji. Najpierw używać istniejącego tekstu; OCR tylko dla potrzebnego dokumentu lub stron. Pobierać z małą kontrolowaną współbieżnością między hostami, nadal przestrzegając odstępów na jednym hoście. Błędy dostępności przechowywać per URL i przyczyna, z ponowieniem po czasie. [_tekst_z_pdf](<D:/Nia bot/agent-v2/stages.py:6614>), [historia hostów](<D:/Nia bot/agent-v2/stages.py:5209>).

### R8. Cytat istnieje dlatego, że model powiedział, że go skopiował

**Odtworzone:** wejście zawierało „The only documented number is 12.”. Atrapa modelu zwróciła „A study found 97 percent effectiveness.”. classify zachowało ten fragment jako dowód PRIMARY.

Prompt bardzo dobrze opisuje obowiązek dosłownego kopiowania. Kod nie sprawdza obecności fragmentu w tekście. Nie ma też pozycji cytatu, więc kolejny etap nie odtworzy go automatycznie.

**Zmiana:** numerować fragmenty wejściowe, a modelowi zlecać wybór ich identyfikatorów i zakresów. Kod ma odtwarzać cytat z przechowanego tekstu. Na początek można zastosować sprawdzenie dosłownego dopasowania z kontrolowaną normalizacją białych znaków; nie wolno normalizować liczb, negacji ani jednostek. Dopasowanie cytatu potwierdza jego istnienie, a nie jeszcze prawdziwość całego twierdzenia. [classify](<D:/Nia bot/agent-v2/stages.py:4917>).

### R9. Synteza nie zamyka dowodzenia relacji „cytat → całe twierdzenie”

synteza.md trafnie ostrzega przed dodawaniem do poprawnego cytatu nieudokumentowanej wyłączności, kolejności czy obowiązku. Funkcja synthesis jedynie parsuje odpowiedź i obcina listy twierdzeń oraz liczb. Nie sprawdza przypisania cytatu do źródła ani tego, czy źródło uzasadnia wszystkie części twierdzenia.

Późniejsze sprawdzanie gotowego tekstu może złapać błąd, lecz wtedy opłacono już syntezę i pisanie. Same cyfry obecne gdzieś w karcie nie dowodzą, że liczba ma właściwą jednostkę, próbę, okres i znaczenie.

**Zmiana:** osobne, krótkie sprawdzenie kluczowych twierdzeń na etapie karty. Wejście: twierdzenie, wskazane fragmenty oraz warunki jego prawdziwości. Wynik: wspierane, zbyt szerokie, sprzeczne lub nierozstrzygnięte. Mocniejszy model kierować do niejasności i sporów; dopasowanie cytatu i liczb wykonywać kodem. [synthesis](<D:/Nia bot/agent-v2/stages.py:4865>), [synteza.md](<D:/Nia bot/agent-v2/prompts/synteza.md>).

### R10. Daty są wymagane w syntezie, ale nie są systematycznie dostarczane

Obiekt po klasyfikacji nie niesie jawnej daty źródła. Synteza dostaje URL, tytuł, wydawcę, klasę, cytaty i liczby. Mimo tego ma zwrócić source_dates.newest i oldest, które później wpływają na oznaczenie aktualności tekstu.

Czasami datę da się ustalić z cytatu lub tytułu. Nie jest to jednak kontrakt zapewniający datę publikacji każdego użytego dokumentu. Data zdarzenia w treści może zostać pomylona z datą strony.

**Zmiana:** publikacja dokumentu, obowiązywanie opisywanego stanu, pobranie strony i ostatnia weryfikacja twierdzenia to cztery różne pola. Nieznane pozostaje nieznane. Najnowsza strona w bibliografii nie odmładza wszystkich twierdzeń artykułu.

### R11. Fakt wyjściowy wraca do potwierdzonych, nawet gdy nie został pobrany

Jeżeli URL faktu startowego nie występuje w confirmed_claims, kod dopisuje go z not_fetched=True. evidence pochodzi wtedy z control_fact, actually albo z powtórzonego faktu. Nie musi być cytatem z dokumentu.

To kryterium sprawdza obecność URL w twierdzeniach syntezy, nie samo pobranie źródła. Dokument mógł być nieobecny, odrzucony albo nie wnosić potwierdzonego twierdzenia. Wszystkie te sytuacje prowadzą do tego samego uzupełnienia.

Bramki liczące korpus rozpoznają not_fetched, więc nie twierdzę, że kod już wszędzie uważa ten rekord za pobrany. Problem polega na umieszczeniu go w sekcji potwierdzonych i przekazaniu takiej karty pisarzowi.

**Zmiana:** znany URL pobierać na początku. Do czasu potwierdzenia fakt zachować jako seed_claim ze statusem hipotezy. Gdy synteza go nie potwierdzi, poprosić o powód i celowane uzupełnienie lub zmienić temat, zamiast przywracać wyjściową wersję siłą. [_przebieg](<D:/Nia bot/agent-v2/artykul_z_puli.py:460>).

### R12. Aktualność jest w dużej części deklaracją modelu

**Odtworzone:** fakt ze źródłem z 2018 roku, control_verdict=MODIFIES i jedną klauzulą control_fact przeszedł kontrolę świeżości mimo pustych control_url i control_date. Ścieżka ENDS ma podobny skrót.

Nie oznacza to, że historyczny fakt jest nieprzydatny. Oznacza, że etykieta modyfikacji lub zakończenia nie wymaga w tej funkcji dowodu modyfikacji lub zakończenia. CONFIRMS z treścią o bezskutecznym szukaniu również nie jest logicznie równoważne potwierdzeniu, że nic się nie zmieniło.

**Zmiana:** stan twierdzenia oddzielić od wyniku wyszukiwania. „Nie znaleziono aktualizacji” to wynik ograniczonej próby; „nadal obowiązuje” wymaga właściwego dokumentu i zakresu. Kontrolę wieku dobierać do rodzaju twierdzenia. [swiezosc_faktu](<D:/Nia bot/agent-v2/stages.py:2174>).

### R13. Niepełna lista aktualności staje się fałszywym katalogiem całego świata

Prompt aktualne_modele wprost dopuszcza niepełną listę. jako_tekst dodatkowo ogranicza ją do 16 aktualnych i 12 wycofywanych pozycji. curiosity stwierdza jednak, że wszystko, czego na tej liście nie ma, jeszcze nie istnieje albo już zniknęło.

Ponadto brak aktualizacji może zwrócić stary zapis. Datę sprawdzenia widać w tekście, ale nie ma wiążącego statusu świeży/stary/niedostępny dla konsumenta.

**Zmiana:** rejestr jest pomocą do sprawdzania znanych nazw. Brak wpisu oznacza potrzebę sprawdzenia konkretnej encji. Aktualizować przede wszystkim encje użyte w gotowych materiałach i planie publikacji. W tej lokalnej konfiguracji pytanie jest wyłączone, więc korzyść dotyczy poprawności kontraktu oraz innych instalacji, a nie obniżenia obecnego codziennego rachunku. [aktualne_modele](<D:/Nia bot/agent-v2/aktualne_modele.py:118>), [jako_tekst](<D:/Nia bot/agent-v2/aktualne_modele.py:178>).

### R14. Ratowanie odpowiedzi z samych URL ma różny sens w różnych etapach

Gdy wyszukiwanie zwróci URL-e, ale nie tekst odpowiedzi, _call_deepseek_responses uruchamia _deepseek_pick_from_urls. Drugie wywołanie otrzymuje pierwotne zadanie i listę adresów, bez treści znalezionych dokumentów.

Dla wyboru źródeł jest to użyteczny sposób odzyskania już kupionej listy. Dla curiosity pierwotne zadanie wymaga faktów, dat, mechanizmu i dokumentu kontrolnego. Same adresy nie zapewniają danych do wypełnienia tych pól.

**Zmiana:** ratunek zależny od etapu. Discovery może odzyskać listę URL-i. Wyszukiwanie faktów powinno zapisać leady i pobrać ich dokumenty, a dopiero potem zlecić ekstrakcję. Nie zamieniać udanej rekonstrukcji JSON w dowód udanego researchu. [transport wyszukiwania](<D:/Nia bot/agent-v2/llm.py:313>), [ratunek z URL](<D:/Nia bot/agent-v2/llm.py:421>).

### R15. Kontrola gotowego tekstu powtarza research, ale nie zastępuje pamięci dowodów

zweryfikuj uruchamia osobne wyszukiwanie dla napisanego tekstu. Potrzeba tego etapu jest realna: pisarz może poszerzyć twierdzenie, dodać liczbę albo przykład. Problemem jest brak jawnego porównania finalnych twierdzeń z wersjonowanymi dowodami, które system już posiada.

Nie należy oszczędzać przez wyłączenie kontroli. Należy najpierw rozpoznać: zdanie wierne sprawdzonemu ustaleniu, nowe twierdzenie, rozszerzona interpretacja, stan wymagający odświeżenia. W sieci sprawdzać przede wszystkim nowe lub zmienne elementy.

W obecnym kodzie część awarii zwraca nie_sprawdzone=True równocześnie z safe_to_post=True; twierdzenia unverified bez cyfr mogą przechodzić. To istniejąca polityka publikacji, której audyt nie zmienia. Wniosek architektoniczny jest konkretny: **nie można zakładać, że późniejszy factcheck zawsze nadrobi brak dowodu we wcześniejszych etapach.** [zweryfikuj](<D:/Nia bot/agent-v2/stages.py:4111>).

### R16. Ocena materiału może dostać urwaną kartę i nie zamyka pętli uzupełnienia

warto_pisac próbuje skrócić zbyt dużą kartę przez ograniczenie wybranych list do sześciu elementów. Następnie i tak przekazuje pierwsze 14 000 znaków serializacji. Duże unused_evidence nie jest wśród skracanych pól. W efekcie model może dostać urwany JSON i niepełny obraz materiału.

Werdykt DOLOZ nie prowadzi do researchu wskazanej luki; uruchamia opisane dalej ogólne grupowanie banku. Po dołożeniu mechanizmów ocena nie jest ponawiana, więc dobór głębokości nadal może korzystać ze stanu sprzed uzupełnienia. ODLOZ jest doradczy i nie oznacza automatycznego odłożenia pisania.

**Zmiana:** oceniać zwartą mapę pytań i twierdzeń, z jawną informacją o pominiętych materiałach. Przy dołożeniu dowodu aktualizować pokrycie właściwego pytania, a następnie format i zakres tekstu. Polecenie „dołóż” powinno kończyć się informacją, czego faktycznie przybyło. [warto_pisac](<D:/Nia bot/agent-v2/stages.py:6390>), [_napisz_i_zapisz](<D:/Nia bot/agent-v2/artykul_z_puli.py:1181>).

## 6. Bank researchu i bibliotekarz: dlaczego zapłacona wiedza nie pracuje dalej

### K1. „Niewykorzystane dowody” nie są wyznaczane jako niewykorzystane

Tygodniowa ścieżka wpisuje do unused_evidence wszystkie zachowane fragmenty z klasyfikacji, bez porównania z twierdzeniami i gotowym tekstem. bank_fragmentow później czyta to pole z kart artykułów i traktuje je jako materiał do ponownego użycia.

To dobre zachowanie w jednym aspekcie: fragmenty nie giną tylko dlatego, że nie weszły do krótkiej listy twierdzeń. Błędna jest interpretacja, że są automatycznie niewykorzystane. Ten sam fragment może już stanowić główną myśl opublikowanego tekstu.

**Zmiana:** zachować wszystkie dowody w rejestrze, a wykorzystanie zapisywać przez relacje do twierdzeń i publikacji. Ten sam dowód wolno użyć ponownie, jeżeli nowy tekst wnosi inne ustalenie lub potrzebne przypomnienie. Bank ma umieć to pokazać, zamiast zgadywać po podobieństwie słów.

### K2. Research staje się bankiem dopiero po zapisaniu artykułu

bank_fragmentow czyta articles.evidence. Nie jest rejestrem wszystkich udanych ekstrakcji. Materiał z nieukończonego researchu, przerwanego przed pisarzem albo odłożonego tematu nie trafia tą drogą do bibliotekarza.

Data fragmentu pochodzi z created_at artykułu, a nie z publikacji źródła. Identyfikator jest wyliczany od nowa podczas odczytu. To słabe podstawy do trwałych odwołań, odświeżania i ustalania, co już sprawdzono.

**Zmiana:** zapisywać dokumenty i dowody po każdym udanym etapie, niezależnie od losu tekstu. Publikacja jest odbiorcą wiedzy, nie warunkiem jej istnienia w banku. [bank_fragmentow](<D:/Nia bot/agent-v2/stages.py:6206>).

### K3. Bibliotekarz nie zna artykułu, który ma ratować

Przy DOLOZ kod wysyła bibliotekarzowi cały bank, bez bieżącego pytania, mechanizmu ani brakującego filaru. Bierze pierwsze dwie zwrócone grupy i dokleja ich domeny oraz mechanizm do karty. Gubione są wskazania konkretnych źródeł, członkowie grupy i pole missing.

Grupa może być poprawna sama w sobie i nadal zupełnie nie pomagać temu artykułowi. „Znaleziono dwa mechanizmy” nie oznacza „uzupełniono brakujący dowód”.

**Zmiana:** wyszukać mały zestaw fragmentów pod konkretne pytanie i brak. Bibliotekarz powinien wskazać dopasowanie do bieżącego mechanizmu, granicę analogii oraz dowody obu stron. Przyjąć tylko propozycje, które rozwiązują określoną potrzebę. [_napisz_i_zapisz](<D:/Nia bot/agent-v2/artykul_z_puli.py:1181>), [bibliotekarz](<D:/Nia bot/agent-v2/stages.py:6247>).

### K4. Dwie domeny nie muszą oznaczać dwóch dowodów

**Odtworzone:** jedna grupa zawierała dwukrotnie ten sam fragment o id=0, raz opisany jako engineering, drugi raz jako insurance. Kod przyjął ją jako grupę spełniającą warunek dwóch członków i dwóch dziedzin.

Walidowane jest istnienie ID i różne napisy domain, ale nie unikalność fragmentów, faktyczna różnorodność źródeł ani trafność samej analogii.

**Zmiana:** wymagać różnych evidence_id, zachować ich źródła i kontrolować, czy porównanie zachowuje ten sam związek przyczynowy. Użyteczna analogia mówi także, gdzie przestaje działać. Etykieta branży nie jest dowodem odległości.

### K5. Przeglądanie całego banku będzie drożało wraz z publikacją

Domyślny bank_fragmentow nie ogranicza historii czasowo. Bibliotekarz otrzymuje wszystkie wyciągnięte fragmenty, bez wcześniejszego wyszukania i limitu dopasowanych pozycji.

Przy pustej lokalnej tabeli artykułów koszt ten dziś się tu nie ujawnia. Z kodu wynika jednak wzrost wejścia wraz z archiwum. Przy każdej potrzebie dołożenia materiału model ponownie czyta także rzeczy niezwiązane z bieżącym zadaniem.

**Zmiana:** pełnotekstowe wyszukiwanie lokalne, filtrowanie encji i mechanizmów, dopiero potem mały reranking. SQLite FTS5 ma wyszukiwanie pełnotekstowe i ranking BM25; lokalny Python przeszedł próbę utworzenia tabeli FTS5 w pamięci. To wystarczający punkt startu. Wyszukiwanie semantyczne warto dołączyć, gdy pomiar wykaże, że parafrazy i odległe analogie regularnie umykają. [dokumentacja FTS5](https://www.sqlite.org/fts5.html).

### K6. Są dwa sposoby wznowienia, ale brakuje wspólnej tożsamości zadania

Starsze cached zapisuje plik o nazwie etapu. Nie wiąże wyniku z hashem pytania, wejścia, promptu, modelu i datą ważności. Przy --use-cache łatwo odzyskać poprawny JSON z innego zlecenia.

Nowsza ścieżka ma --do-karty i --z-karty, lecz jeden wspólny plik karta_do_zatwierdzenia.json. Normalny przebieg nie zapisuje automatycznie trwałego punktu wznowienia na granicy każdego etapu.

**Zmiana:** każdy research ma research_id i historię etapów. Zakończone wywołanie zapisuje wynik natychmiast. Wznowienie sprawdza wejście oraz ważność dowodów; nie uruchamia ponownie całego skauta. Odłożony temat ma zachowane dokumenty, luki i koszt pozostały do ukończenia. [cached](<D:/Nia bot/agent-v2/run.py:72>), [_przebieg](<D:/Nia bot/agent-v2/artykul_z_puli.py:460>).

## 7. Jak zmienić prompty researchu, a nie tylko je skrócić

Objętość samych szablonów, przed podstawieniem danych: ciekawostki 2363 słowa, skaut 3500, bank 766, discovery 649, klasyfikacja 379, synteza 1001, bibliotekarz 430, wykonalność 744, warto_pisac 1016.

Największy problem nie polega na tym, że każdy długi prompt jest zły. Discovery ma wartościowe instrukcje o pierwotnych dokumentach, wersji zapisu i głosie autora cytatu. Klasyfikator ma potrzebne reguły dosłownej ekstrakcji. Do skrócenia lub rozdzielenia kwalifikują się przede wszystkim sprzeczne zadania, moralizujące uzasadnienia i wymagania dotyczące danych, których model nie dostał.

### 7.1. Oddzielić tani lead od zweryfikowanego faktu

Obecna curiosity ma jednocześnie znaleźć wiele ciekawych rzeczy, zapewnić źródła, ustalić aktualność, obalić przekonanie, rozpoznać mechanizm, opisać skutek i zachować różnorodność. Dużo płatnej pracy wykonuje dla kandydatów, którzy nigdy nie trafią do publikacji.

Proponowany kontrakt wstępnego skauta:

~~~text
Propose research leads from the supplied signals and reader questions.
A lead is a question worth checking, not a verified fact.
For each lead return:
- signal_ids;
- the concrete reader question;
- what would be new compared with our existing coverage;
- one plausible evidence route;
- the cheapest next check that could reject or advance the lead;
- an optional time-sensitive reason.
Do not invent an audience belief, a source passage, or a result.
Use only editorial modes that fit the lead. Leave unsupported fields empty.
Return fewer leads when the evidence routes are weak.
~~~

To propozycja treści do późniejszego wdrożenia, nie aktywny plik promptu. Przy szczególnie czytelnym, krótkim dokumencie ekstrakcja może nastąpić od razu; architektura nie powinna wymuszać dodatkowego modelu tylko po to, by zachować sztywną liczbę etapów.

### 7.2. Ranking ma porównać wartość i brakującą pracę

~~~text
Select the best candidates for the available publication slots.
Consider reader value, new information, evidence readiness and the
remaining research work. Treat unknown evidence as unknown.
Return an ordered shortlist and, for each selected item:
- why this belongs in this slot;
- the strongest verified finding;
- the single most important unresolved question;
- note_ready / article_candidate / needs_research.
A missing source creates a research task. It does not make a checked
candidate equivalent to an opinion.
Use measured reception only from the supplied comparable groups.
~~~

Nie wymagałbym od modelu dokładnej prognozy kosztu w dolarach. Kod zna dotychczasowe koszty klas zadań i dostępne dokumenty. Model ma wskazać rodzaj brakującej pracy, który da się wycenić na podstawie pomiarów.

### 7.3. Discovery ma rozwiązać zadaną lukę

~~~text
Find evidence for question_ids Q2 and Q4.
We already have the supplied source versions and established findings.
Return sources only when they add an answer, a material qualification,
or a contradiction. Identify which question each source may answer.
Prioritize the original record and preserve the origin of repeated data.
If nothing useful is found, return an empty list plus the attempted routes.
Do not fill source slots with duplicates or general commentary.
~~~

Limit wywołań narzędzi musi wynikać z kontrolera, jeśli dana integracja pozwala nim zarządzać. Zdanie w prompcie pozostaje pomocne, ale nie stanowi gwarancji kosztu.

### 7.4. Ekstraktor ma wybierać dowody, których położenie zna kod

~~~text
For each question_id, select the supplied paragraph or table-cell IDs
that directly support an answer or a limitation.
Preserve who is speaking, the date scope, units, denominator and conditions.
Separate the document author's finding from a quoted third-party claim.
If support is absent, mark the question unanswered.
Do not rewrite selected text and do not fill gaps from memory.
~~~

Dobór tekstu nie może być tak agresywny, że usuwa nagłówek tabeli lub zdanie określające zakres. Dowód powinien mieć krótki cytat i możliwość pobrania szerszego kontekstu.

### 7.5. Synteza ma zdać sprawę z pytań, nie stworzyć dowolne osiem zdań

~~~text
Build the answer from verified evidence IDs.
For each essential question return: answered / partial / unanswered /
contradicted, with supporting IDs.
Separate established findings, the proposed explanation and open questions.
Every factual clause must retain its conditions and attribution.
Do not promote the seed claim when its support is missing.
Suggest outside analogies separately as leads unless their evidence
has also been supplied.
~~~

Limit twierdzeń powinien wynikać z zakresu tekstu, a nie ucinać odpowiedzi na istotne pytanie. Pisarz nie potrzebuje całego dokumentu, ale potrzebuje dowodów wszystkich twierdzeń, które ma rozwinąć.

### 7.6. Bibliotekarz ma uzupełnić wskazany brak

~~~text
The current article asks the supplied question and lacks the named evidence.
From the retrieved bank excerpts, return only additions that address
that gap or demonstrate the same causal mechanism.
For each addition give distinct evidence IDs, its exact contribution,
the limit of the comparison, and what remains unverified.
Return no match if the bank cannot help this article.
~~~

Grupowanie całego archiwum według mechanizmów można wykonywać osobno i przyrostowo, po dopisaniu materiału. Nie powinno zastępować celowanego zapytania o pomoc dla konkretnej karty.

## 8. Docelowa architektura przy małej liczbie elementów

### 8.1. Jeden obieg materiału dla notek i artykułów

~~~text
Sygnały + pytania czytelników + nowe dokumenty
                    ↓
Identyfikacja wydarzeń i tematów, zachowanie wszystkich źródeł sygnału
                    ↓
Leady: pytanie, nowość względem archiwum, możliwa droga do dowodu
                    ↓
Dobór do zapotrzebowania i budżetu; krótka lista finalistów
                    ↓
Znane dokumenty → lokalny rejestr → pobranie brakujących wersji
                    ↓
Ekstrakcja z pozycjami cytatów → weryfikacja twierdzeń
                    ↓
Pokrycie pytań ── konkretna luka ──→ celowane wyszukiwanie
                    ↓
Gotowa notka / gotowy brief artykułu / temat odłożony z zachowaną wiedzą
                    ↓
Pisanie → sprawdzenie nowych i zmienionych twierdzeń → publikacja
                    ↓
Odbiór czytelników + relacje wykorzystania → następny dobór
~~~

Głębokość researchu zależy od potrzeby dowodowej. Krótka notka o jednym ustaleniu może potrzebować jednego dokumentu. Artykuł o spornym wniosku potrzebuje porównania niezależnych podstaw, nawet jeśli oba teksty mają podobną liczbę znaków.

### 8.2. Minimalny model danych

Nie są potrzebne od razu osobne serwisy. Istniejący SQLite może przechowywać metadane i relacje, a pliki dokumentów mogą być adresowane hashem.

| Obiekt | Minimalne znaczenie i pola |
|---|---|
| Sygnał | ID, pochodzenie, data, surowy tytuł/pytanie, encje, event_id |
| Temat i kąt | topic_id, angle_id, pytanie odbiorcy, rodzaj materiału, różnica wobec wcześniejszych tekstów |
| Wersja źródła | source_id, URL oryginalny i końcowy, hash treści, data publikacji i pobrania, rola dokumentu |
| Dowód | evidence_id, source_version_id, strona/akapit/tabela, dosłowny tekst i kontekst |
| Twierdzenie | claim_id, treść, zakres czasu, encje, liczby i jednostki, status, evidence_ids |
| Zadanie researchu | research_id, question_ids, pokrycie, luki, próby, wynik, wydany i pozostały budżet |
| Kandydatura | angle_id, gotowość do formy, priorytet, rezerwacja, termin aktualizacji, powód odłożenia |
| Wykorzystanie | publikacja lub szkic, angle_id, claim_ids, data, wynik i porównywalne pomiary odbioru |

Najpierw wdrożyłbym trwałe identyfikatory, zapis źródeł, statusy oraz powiązanie pytań z dowodami. Rozbudowany katalog mechanizmów i wyszukiwanie semantyczne mogą dojść później.

### 8.3. Przykład jednego researchu

Przykład całkowicie fikcyjny: kanał informuje, że firma obniżyła koszt obsługi o 40%.

Skaut nie zapisuje od razu „firma obniżyła wszystkie koszty o 40%”. Tworzy lead: „Co dokładnie zostało policzone i co zmieniło wynik?”. Rejestr sprawdza, czy mamy już raport i wcześniejszą wersję. Plan pyta: czego dotyczy koszt, jaki jest okres porównania, jakie składniki pominięto oraz co spowodowało różnicę.

Ekstrakcja znajduje przypis mówiący o jednym etapie obsługi. To staje się warunkiem twierdzenia. Brakuje metody porównania — następne wyszukiwanie dotyczy tylko metodologii, nie ogólnej „rewolucji w firmie”.

Jeżeli uda się wyjaśnić jedno ustalenie, powstaje notka. Jeżeli dodatkowo istnieje niezależnie udokumentowany mechanizm i istotne skutki, kandydat może zasilić artykuł. Za miesiąc nowy wynik aktualizuje wersję twierdzenia; nie znika jako duplikat tylko dlatego, że nazwa firmy i większość słów się powtarza.

Ta sama karta dowodowa służy notce, artykułowi i odpowiedzi na pytanie czytelnika. Każde wykorzystanie ma odrębny cel redakcyjny, więc ponowne użycie wiedzy nie oznacza publikowania tego samego tekstu.

## 9. Koszt: co rzeczywiście optymalizować

### 9.1. Co mówi lokalny zapis, a czego nie mówi

Jedyny lokalny zapis curiosity ma 328 096 tokenów wejścia, 31 352 wyjścia, 19 wyszukiwań i koszt zapisany jako 0,09287 USD. To jeden rekord księgi aplikacji, nie aktualny cennik dostawcy, pomiar średniej ani potwierdzony rachunek. Nie ma przy nim pełnej tożsamości wersji promptu i danych, więc nie należy na tej podstawie przypisywać wyniku wyłącznie obecnemu szablonowi.

Przy odczycie efektywnej konfiguracji curiosity i bank miały pułap 52 000 tokenów wyjścia, discovery 60 000, klasyfikacja 32 171, synteza 32 948, wybór briefu i warto_pisac po 34 000. Curiosity, bank i klasyfikacja były skierowane na skonfigurowany wariant Flash, a discovery i synteza na Pro.

Wysoki pułap nie znaczy, że tyle tokenów jest zawsze zużywane. Pokazuje jednak, jak dużo pracy może wykonać jedno wywołanie, zanim zakończy się nieudaną lub rozwlekłą odpowiedzią. Dla rankingu kilku rekordów należy osobno zmierzyć długość JSON i pozostały koszt generowania; podniesienie limitu nie powinno być domyślną odpowiedzią na każdy niedomknięty wynik.

### 9.2. Osiem wyszukiwań nie jest globalnym twardym limitem

W gałęzi Anthropic kod wysyła max_uses. Badana gałąź DeepSeek wysyła narzędzie web_search bez analogicznego egzekwowanego ograniczenia w kodzie aplikacji. Nie weryfikowałem aktualnego kontraktu dostawcy płatnym wywołaniem i nie proponuję dopisywać parametru, którego obsługi nie potwierdzono.

Limit w prompcie discovery jest instrukcją dla modelu. Curiosity ma ponadto własne polecenie zakończenia po uzyskaniu faktów, a nie identyczny kontrakt liczby wyszukiwań. Lokalnych 19 wyszukiwań nie należy przedstawiać jako dowodu złamania limitu 8 przez prompt curiosity; to dowód, że ta stała nie zapewnia uniwersalnego ograniczenia wszystkich etapów.

**Zmiana:** jeśli budżet musi być przewidywalny, kontroler powinien wydawać ograniczoną liczbę jawnych zadań wyszukiwawczych i oceniać wynik każdej rundy. Przy narzędziu wykonywanym wewnętrznie przez dostawcę potrzebne są zmierzone profile kosztu i rezerwa na trwające wywołanie. Sam timeout nie gwarantuje, że dostawca nie naliczył pracy. [llm.call](<D:/Nia bot/agent-v2/llm.py:546>).

### 9.3. Największe oszczędności wynikają z unikania powtórnej pracy

| Zmiana | Dlaczego obniża koszt | Warunek zachowania jakości |
|---|---|---|
| Znany dokument przed szerokim wyszukiwaniem | Wykorzystuje URL kupiony przy powstawaniu kandydata | Sprawdzenie właściwej wersji i zakresu dokumentu |
| Trwały rejestr tekstów i dowodów | Kolejna publikacja korzysta z opłaconego pobrania i ekstrakcji | Klucz cache uwzględnia treść oraz zadanie; aktualność osobno |
| Triage przed pełnym researchowaniem całej partii | Szczegółowo sprawdza kandydatów mających szansę na użycie | Lead nie jest przedstawiany jako fakt |
| Runda według brakującego pytania | Ogranicza kolejne ogólne listy źródeł | Pomiar pokrycia i sprzeczności |
| Mały zestaw fragmentów dla bibliotekarza | Wejście nie rośnie proporcjonalnie do całego archiwum | Sprawdzenie, czy lokalne wyszukiwanie nie pomija istotnych dowodów |
| Trwałe wznowienie etapu | Błąd późnej funkcji nie kupuje całego researchu ponownie | Weryfikacja zgodności wejścia i stanu źródeł |
| Poprawna rezerwacja kandydatów | Dobry fakt nie znika po awarii lub niewykorzystanym wyborze | Rozróżnienie szkicu i rzeczywistej publikacji |
| Sprawdzanie zmian w gotowym tekście | Ponowny research dotyczy nowych lub rozszerzonych twierdzeń | Zachowana kontrola pokrycia całego tekstu |

Przykład rachunkowy, **nie prognoza**: jeśli ta sama ekstrakcja kosztuje E i jest potrzebna w czterech tekstach, ponawianie daje 4E. Jednorazowa ekstrakcja z trzema odczytami lokalnymi daje E plus koszt utrzymania i ewentualnego odświeżenia. Różnica wynosi do 3E wyłącznie dla tego wspólnego etapu. Nie oznacza 75% oszczędności całego bota.

### 9.4. Model dobierać do rodzaju błędu i całej ścieżki

Tani model jest naturalnym kandydatem do ekstrakcji identyfikatorów, przypisania fragmentów, deduplikacji prostych przypadków i krótkiego rankingu. Trudniejsze rozstrzygnięcia — sprzeczne źródła, zakres twierdzenia, mechanizm przyczynowy, odległa analogia — warto kierować do mocniejszego modelu po wykryciu niepewności.

To propozycja routingu do sprawdzenia, nie twierdzenie, że każdy skonfigurowany Flash wykona ekstrakcję lepiej lub taniej w całym przebiegu. Jeśli tańszy model generuje więcej poprawek, wyszukiwań i odrzuconych tekstów, jego oszczędność jednostkowa może zniknąć.

Kryterium porównania: **koszt doprowadzenia do zaakceptowanego materiału przy utrzymanym poziomie dowodów i wartości redakcyjnej**. Nie cena pojedynczego wejścia do API. Nie zmieniałbym wszystkich ról naraz — wtedy nie wiadomo, skąd bierze się poprawa lub pogorszenie.

### 9.5. Budżet powinien chronić ukończenie materiału

Obecny limit liczby przebiegów dobierania banku jest pośrednią kontrolą: osiem słabych pomysłów i osiem dobrych zużywa ten sam „przebieg”, a artykuły i wydarzenia mają wyjątki. Nie uwzględnia liczby użytecznych kątów ani kosztu ich dokończenia.

Proponuję budżet tematu rozdzielany na odkrywanie, dowody oraz domknięcie. Przed kolejnym wyszukaniem kontroler sprawdza, czy pozostało miejsce na ekstrakcję, weryfikację i pisanie. Gdy brakuje środków, zapisuje stan i wybiera gotowy materiał z banku. Intensywny research nie powinien zostawiać publikacji z samymi URL-ami i zerowym budżetem na ich użycie.

Wielkość uzupełnienia banku powinna wynikać z liczby planowanych miejsc, zużycia w ostatnich dniach, odsetka akceptacji i czasu aktualności. Stałe „znajdź osiem” warto zastąpić zapotrzebowaniem: ile różnych gotowych notek i ilu kandydatów artykułowych faktycznie brakuje.

### 9.6. Obserwować koszt i efekt na poziomie kandydata

calls jest dobrym początkiem księgi kosztów. Brakuje powiązań candidate_id, research_id, source_version_id, numeru próby, wersji promptu oraz wyniku merytorycznego. Sukces HTTP i poprawny JSON nie oznaczają uzyskania użytecznego faktu.

Ponowienia przejściowych błędów odbywają się wewnątrz llm.call; końcowy zapis nie opisuje osobno każdej wcześniejszej próby. Ratunek z samych URL jest zliczony tokenowo razem z pierwotną odpowiedzią. Nieudany końcowy zapis ma koszt 0 i price_verified=0 — tę nieznaną kwotę trzeba raportować jako nieznaną, nie jako darmową pracę. Dla gałęzi wyszukiwania cache_hit jest ustawiany na zero; sama ta kolumna nie pozwoli ocenić rzeczywistej skuteczności cache dostawcy.

Najważniejsze wskaźniki:

- koszt jednego unikalnego, zweryfikowanego kandydata gotowego do użycia;
- koszt researchu przypadający na zaakceptowaną publikację, także koszt odrzuconych prób;
- udział dowodów wykorzystanych ponownie bez nowego wyszukiwania;
- koszt i przyczyna utraty kandydatur: powtórka, brak pokrycia, aktualność, awaria, niewykorzystany zapas;
- koszt uzupełnienia jednej istotnej luki i liczba rund bez przyrostu wiedzy.

Wspólny koszt dokumentu należy przypisywać konsekwentnie, aby nie liczyć go podwójnie w kilku publikacjach ani nie znikał jako „koszt banku”.

## 10. Kolejność zmian i warunki ich odbioru

| Kolejność | Zakres | Kiedy uznać etap za zakończony |
|---|---|---|
| A — spójność banku | B1–B3, B6–B10: wspólna bramka, dopuszczenie wyjaśnień, rezerwacja, ranking i jego feedback | Ten sam kandydat ma ten sam status niezależnie od drogi wejścia; pomiar odbioru nie psuje rankingu; nowi kandydaci są oceniani |
| B — dowód przed pisarzem | R1–R2, R8–R12: znane źródło na wejściu, question_id, cytaty i stan twierdzeń | Każde potwierdzone twierdzenie wskazuje istniejący fragment i właściwy zakres; niepotwierdzony seed nie wraca jako potwierdzony |
| C — zapamiętywanie pracy | R6, K1–K2, K6: źródła, ekstrakcje, zadania i wznowienie | Przerwanie po ekstrakcji nie powoduje ponownego opłacania tego etapu; wiedza jest dostępna mimo braku artykułu |
| D — research według luk | R3–R5, R14: celowane rundy, deduplikacja i walidacja wyników | Nowa runda ma nazwany brak i mierzalny przyrost pokrycia, a duplikaty nie generują dalszych kosztów |
| E — aktualność i pamięć tematów | S1–S5, S8, B4–B5, B12: sygnały niezależnie od zapasu, encje, wersje, nowe kąty | Aktualizacja tego samego produktu nie ginie; obcy fakt nie zamyka wydarzenia; pytanie czytelnika ma drogę do wyboru |
| F — skalowanie jakości i kosztu | K3–K5, rozdział 9: celowany bibliotekarz, budżet zadania, porównanie modeli | Mniejszy koszt użytecznego materiału przy zachowanej kompletności dowodów i ocenie redakcyjnej |

A i B mają najwyższy priorytet. Dalsze optymalizowanie skauta przy niespójnym przyjmowaniu i przechowywaniu kandydatów może po prostu szybciej napełniać wadliwy obieg.

### Jak sprawdzić efekt bez kosztownego eksperymentowania na odbiorcach

Najpierw odtworzyć kontrakty bez sieci na stałych dokumentach. Potem porównać starą i proponowaną ścieżkę na tej samej niewielkiej puli rzeczywistych tematów oraz tych samych źródłach. Pula musi zawierać łatwy fakt, trwałe wyjaśnienie, nową wersję starego produktu, rozbieżne źródła, mylący tytuł, nieaktualny zapis, źródło wtórne oraz PDF z ważnym przypisem.

Ocena ma dotyczyć oddzielnie:

- **Dowodów:** cytat istnieje; wspiera całe twierdzenie; zachowano warunki, jednostki, autorstwo i datę.
- **Odpowiedzi:** najważniejsze pytania są rozstrzygnięte albo uczciwie oznaczone jako niewyjaśnione.
- **Wartości treści:** czytelnik dostaje konkretną nową wiedzę, mechanizm lub zmianę, zamiast wymyślonego mitu i powtarzalnego kąta.
- **Ekonomii:** pełny koszt udanego materiału, naprawy, ponowienia, czas i wykorzystanie wcześniejszych dowodów.

W porównaniu modeli oceniający tekst nie powinien znać ich nazw. Przy małej próbie pokazać pojedyncze przypadki wygranej i porażki; nie zamieniać kilku przykładów w precyzyjny procent poprawy. Wyniki odbiorców warto dołączać później, gdy teksty mają porównywalny czas ekspozycji.

## 11. Rejestr wykonanych odtworzeń

Wszystkie poniższe wejścia były syntetyczne. Transport LLM był zastąpiony atrapą, a zapisy ograniczone do katalogu tymczasowego. Próby pokazują granice kodu przy określonej odpowiedzi modelu, nie prawdopodobieństwo uzyskania takiej odpowiedzi.

| # | Scenariusz | Zaobserwowany wynik |
|---:|---|---|
| 1 | Wyjaśnienie mechanizmu bez wrong_belief | Odrzucone za brak przekonania |
| 2 | Ograniczenie fizyczne opisane ze słowem Nobody | Odrzucone za brak mechanizmu |
| 3 | Zmiana 5.1 → 5.2 oraz 100000 → 200000 | Identyczny klucz faktu |
| 4 | Nowy kandydat po 40 wcześniej ocenionych | Dwa wywołania rankingu, nowy rekord nie pojawił się w żadnym wejściu |
| 5 | Ranga 0 bez kanału kontra 999 z kanału | Wygrała 999; od razu status uzyty |
| 6 | Najpierw kandydat na_artykul=False, potem True | Wybrano pierwszego |
| 7 | Fragment o 97% przy źródle mówiącym wyłącznie o 12 | Fragment przyjęty jako dowód |
| 8 | Ten sam evidence id dwa razy, z różnymi domenami | Bibliotekarz przyjął grupę |
| 9 | Niepuste pomiary w _tabela_odbioru | NameError: statystyki |
| 10 | Cztery pomiary, po podstawieniu brakującej zależności w pamięci | Wszystkie cztery w grupie dobrej i słabej |
| 11 | MODIFIES bez control_url i control_date, ze starym źródłem | Kontrola świeżości zwróciła True |
| 12 | Fakt odrzucony przy zapisie curiosity | Nadal zwrócony do wywołującego |
| 13 | Premiera jednego produktu, znaleziony fakt na inny temat | Wydarzenie zapisane z ile=1, przestało być nowe |
| 14 | Dwa różne produkty, wspólne 5.1 na dwóch kanałach | Jedno wydarzenie premierowe o rdzeniu 5.1 |
| 15 | Notka z użytecznego zapasu banku | Zero wywołań detektora wydarzeń |
| 16 | Pełne posortuj_bank z niepustym feedbackiem | Ocenione 0, wywołań modelu 0, zachowana stara kolejność |
| 17 | Discovery zwraca 15 kopii jednego URL przy pułapie 10 | Przyjęto wszystkie 15 |
| 18 | Klasyfikacja zwraca 15 cytatów po 1000 znaków przy 12 × 700 | Przyjęto wszystkie w pełnej długości |

Dodatkowo sprawdziłem dostępność SQLite FTS5 przez utworzenie tabeli wyłącznie w pamięci; próba się powiodła. Nie uruchamiałem testu współbieżnego zapisu produkcyjnego banku, OCR ani benchmarku płatnych modeli.

**Rekomendacja końcowa:** zbudować jeden bank tematów, twierdzeń i źródeł, który potrafi powiedzieć „wiemy”, „podejrzewamy”, „brakuje dowodu”, „to już wykorzystano” i „to wymaga aktualizacji”. Skaut ma dostarczać pytania warte sprawdzenia, research ma domykać wskazane luki, a pisarz ma dostawać sprawdzony materiał o zakresie odpowiadającym tekstowi. Dzięki temu lepsza jakość i niższy koszt wynikają z tego samego usprawnienia.
