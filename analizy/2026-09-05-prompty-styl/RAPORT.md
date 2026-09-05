# Prompty i styl NIA: co model naprawdę dostaje i jak przebudować pisanie

Analiza lokalnego stanu z 5 września 2026. Zakres: artykuły, notki, komentarze, odpowiedzi, próbki stylu oraz sprzężenie między pisarzem i oceną tekstu.

**Wniosek:** głos publikacji jest rozdzielony między instrukcje, które mają różne cele. Jedne uczą wyjaśniania, inne wymuszają demaskowanie, inne konkretny układ, jeszcze inne optymalizują powierzchowne oznaki „niebrzmienia jak bot”. Do tego forma bywa przydzielana bez sprawdzenia, czy materiał może ją wypełnić. Model ma jednocześnie dochować wierności dowodom, trafić w normę długości, użyć wskazanego zabiegu i uniknąć zabiegów pokazanych w przykładach. To jest problem projektu zlecenia redakcyjnego, nie brak kolejnego zakazu w słowniku.

## Co rzeczywiście sprawdziłem

- Odczytałem instrukcje systemowe i sposób składania promptów w `stages.py`, reguły w `config.py`, loader `style.py`, kontrole `gates.py` oraz szablony pisania i oceniania.
- Wczytałem pięć rzeczywistych, przypiętych próbek lokalnego korpusu przez `style.load_examples()`. Przeanalizowałem ich funkcję, zamiast opierać się wyłącznie na nazwach OPENING/ENDING. W raporcie nie reprodukuję całych fragmentów.
- Uruchomiłem rzeczywiste funkcje `note`, `write`, `comment_on`, `reply_to`, przechwytując ich wejście na granicy `llm.call`. Płatny transport nie został uruchomiony. Materiał wejściowy, posty i karta w tym odtworzeniu są syntetyczne; marka i nisza są neutralnymi zastępnikami.
- Przechwyciłem dziewięć konfiguracji promptu. Historię publikacji zastąpiłem pustą, aby odseparować reguły stałe. Złożyłem wariant artykułu zarówno bez próbek, jak i z prawdziwymi próbkami.
- Sprawdziłem zachowanie funkcji liczącej gęstość „przekonań” na syntetycznych danych. To pomiar reguły, a nie ocena jakości prawdziwego artykułu.
- Lokalna tabela `articles` była pusta w chwili sprawdzenia. Nie ma tu podstaw do twierdzenia, że nowy prompt już poprawił opublikowane artykuły. Skutki stylistyczne opisane niżej są diagnozą redakcyjną wynikającą z kontraktów; wymagają porównania generacji.

Metoda pomiaru: przechwycenie argumentów prawdziwych funkcji na granicy `llm.call`, z zastąpioną historią i syntetycznym materiałem. Poniżej zachowano wyniki pomiaru. Tymczasowe pliki odtworzenia i osobne szkice promptów zostały usunięte na życzenie użytkownika. Jedynym pozostawionym rezultatem pracy jest ten raport. Kod bota, aktywne prompty i konfiguracja nie zostały przeze mnie zmienione.

## 1. Rzeczywista architektura instrukcji

| Forma | Co składa się na wejście |
|---|---|
| Artykuł | Krótki `WRITER_SYSTEM`; `pisarz.md`; pasmo długości i jego uzasadnienie; losowane zakończenie; losowana liczba paraleli; pięć stałych próbek; profil pozytywny; profil negatywny; uwagi z dwóch wcześniejszych tekstów; karta dowodowa |
| Notka | `NOTE_SYSTEM`; `notka.md`; opis typu; opis formy wybieranej kalendarzowo; sekcje interpunkcji, zastrzeżeń i zakazanego słownictwa z `po_ludzku.md`; ostatnie pierwsze słowa; materiał; czasem dodatkowy blok z przykładami powtarzanego ruchu „nie X, tylko Y” |
| MYSL | Wszystko z notki, a dodatkowo losowany wewnętrzny kształt myśli. Dostaje więc dwa niezależne polecenia dotyczące konstrukcji |
| Komentarz | `COMMENT_SYSTEM`; `komentarz.md`; przydzielona postawa; niezależnie losowane otwarcie i długość; wspólne zakazy; pierwsze słowa wcześniejszych komentarzy; treść posta; ewentualne ustalenie `co_dodamy` |
| Odpowiedź | `REPLY_SYSTEM`; `odpowiedz.md`; losowane otwarcie i długość; wspólne zakazy; komentarz czytelnika; ograniczony kontekst własnej wypowiedzi |

Istotna różnica: `_pola_wspolne` przygotowuje pola, ale do danego promptu wchodzą wyłącznie pola użyte w jego szablonie. Nie należy liczyć wszystkich reguł w `config.py` jako kontekstu każdego modelu.

### Dokument stylu, który nie steruje botem

`style-profiles/CLAUDE_INSTRUKCJA_NATURALNEGO_PISANIA.md` ma 5742 słowa. Nie jest ładowany przez badaną ścieżkę bota. `style.load_profiles()` ładuje tylko `ARTICLE_STYLE_PROFILE_V1.md` i `ARTICLE_NEGATIVE_STYLE_PROFILE_V1.md`. Nie znalazłem odwołania do dużej instrukcji w kodzie Pythona bota ani narzędzi.

To ma znaczenie merytoryczne: duża instrukcja zaleca strukturę wynikającą z argumentu i zakazuje mechanicznego rytmu krótkie–długie–krótkie. Aktywne prompty wracają do nakazanych form i ogólnych poleceń przeplatania długości. Poprawianie dużego dokumentu samo w sobie nie zmieni tekstów. Nie proponuję jednak wklejenia go w całości: zawiera objaśnienia, bibliografię i warianty do wyboru. Trzeba wyprowadzić z niego krótki obowiązujący kontrakt.

### Ile tekstu dostaje model

Pomiar słów przez `split()`, nie tokenów dostawcy. Zawiera minimalny materiał syntetyczny. Historia pusta; wyniki produkcyjne będą inne w zależności od karty i pamięci.

| Scenariusz | Słowa w wiadomości użytkownika | Słowa w systemie |
|---|---:|---:|
| CIEKAWOSTKA / PROSTA | 1546 | 27 |
| CIEKAWOSTKA / LISTA | 1606 | 27 |
| MYSL / LICZBA, wewnętrzny kształt TEZA | 1941 | 27 |
| MYSL / LISTA, wewnętrzny kształt TEZA | 1859 | 27 |
| DYSKUSJA / PYTANIE | 1629 | 27 |
| Komentarz CIEKAWOSC + otwarcie od sprzeciwu, cel 12 słów | 1367 | 49 |
| Odpowiedź z otwarciem pytaniem, cel 12 słów | 1186 | 29 |
| Artykuł THIN, pusta karta, bez próbek | 3475 | 32 |
| Ten sam artykuł z pięcioma przypiętymi próbkami | 3853 | 32 |

Sam stosunek wejścia do wyjścia nie dowodzi złej jakości. Ważniejsze jest, że spora część tego kontekstu opisuje spory o formę, zamiast pomagać sformułować konkretną myśl. Pięć próbek wnosi 368 słów właściwej prozy; reszta różnicy to etykiety i formatowanie. Usunięcie próbek oszczędza mało względem całego promptu i może zabrać najbardziej użyteczny wzorzec.

## 2. Notki: jeden tekst dostaje kilka niezgodnych zadań

### 2.1. Deklarowana różnorodność kończy się obowiązkiem demaskowania

`notka.md` na początku mówi, że demaskowanie jest jedną z opcji i nie może stać się odruchem. W sekcji `What every note must do` wymaga: **„Break a belief the reader is carrying.”** Każe też wymyślić wewnętrznie jedno zdanie opisujące błędne przekonanie czytelnika; bez tego uznaje materiał za trivia.

To nie jest tylko sprzeczny ton. Na poziomie zadania pisarz ma znaleźć przeciwnika dla każdej obserwacji, również gdy dostaje ciekawostkę wyjaśniającą działanie czegoś. Instrukcja później walczy z produktem tej decyzji: `note()` dokleja ostrzeżenie przeciwko seryjnym konstrukcjom „X, not Y”.

Przewidywany efekt: model usuwa widoczne słowo „not”, ale dalej buduje każdą notkę na korekcie rzekomego czytelnika. Zmieniasz objaw językowy, a zachowujesz mechanizm powtarzalności.

**Zmiana:** obowiązek wykazania różnicy wobec przekonania przenieść wyłącznie do SPROSTOWANIA i tylko wtedy, gdy materiał dokumentuje samo przekonanie. CIEKAWOSTKA ma wyjaśnić jedno ustalenie, DYSKUSJA postawić stanowisko oparte na ustaleniu, MYSL rozwinąć myśl bez faktów. Zaskoczenie może wynikać z przyczyny, skali lub konsekwencji; nie musi pochodzić z obalenia mitu.

### 2.2. Typ, forma i materiał są dobierane oddzielnie

`notki_dnia()` wybiera formy przez indeks dnia roku i pozycję notki. Dopiero później pobiera materiał. Nie ma warunku: LICZBA tylko dla materiału z interpretowalną wielkością, LISTA tylko dla co najmniej trzech odrębnych ustaleń.

Odtworzone pary:

| Para | Jedno polecenie | Drugie polecenie |
|---|---|---|
| MYSL + LICZBA | Bez faktów, liczb, dat i dowodów | Otwórz samą liczbą; wyjaśnij, co mierzy i kto zdecydował |
| MYSL + LISTA | Bez sprawdzalnych faktów | Trzy wiersze, każdy z nowym faktem |
| CIEKAWOSTKA + LISTA | Jedna udokumentowana ciekawostka | Trzy osobne fakty w trzech wierszach |
| DYSKUSJA + PYTANIE | Stanowisko; „Not a question” | Osobna linia z pytaniem do czytelnika |
| MYSL / wewnętrzne PYTANIE | Nie odpowiadaj na pytanie, którego nie można rozstrzygnąć | Ogólny prompt wymaga, żeby druga połowa odpowiedziała na duże pytanie konkretnym dowodem |

W trzeciej i czwartej parze da się czasem znaleźć kompromis, lecz kontrakt nie daje jednej odpowiedzialnej decyzji o tym kompromisie. Dwie pierwsze są zasadniczo niezgodne.

Szczególnie dotkliwy jest schemat MYSL. Otrzymuje własny kształt z `KSZTALTY_MYSLI` i ogólną formę notki. Może zostać poproszony jednocześnie o trzy kroki rozumowania TEZY, trzy fakty LISTY i brak jakichkolwiek faktów. Nawet idealnie posłuszny model nie spełni wszystkiego.

**Zmiana:** MYSL ma własny prompt, bez ogólnych wymogów notki faktograficznej i bez formularza `fact_used` wymagającego faktu. Dla innych typów najpierw materiał → dostępne formy → wybór spośród pasujących. Rotacja zostaje, lecz działa w obrębie zgodnych opcji. Dla myśli pola faktu i źródła w obecnym JSON można jawnie ustawiać na pusty napis.

### 2.3. Zmienność pierwszych słów nie jest zmiennością myślenia

Pamięć otwarć zabrania pierwszych słów wcześniejszych notek. Taki test nie rozróżnia dwóch różnych zdań zaczynających się od tego samego słowa i dwóch identycznych zabiegów zaczynających się inaczej. Przykładowo „A rule can…” i „A measurement…” mogą rozwijać różne pomysły. „Most people…”, „Everyone assumes…” i „You probably think…” są trzema początkami tej samej sztuczki.

`NOTE_CANDIDATES` wynosi 1. Sortowanie kandydatów pod kątem pierwszego słowa i kupletu korekcyjnego nie wybiera więc lepszego wariantu przy tym ustawieniu. Oddziałuje głównie instrukcja zakazująca, a nie porównanie jakości wyjść.

**Zmiana:** pamiętać niedawne ruchy redakcyjne i ich częstotliwość: korekta założenia, wyjaśnienie przyczyny, scena, pomiar z interpretacją, pytanie. Pierwsze słowo traktować jako słabą wskazówkę. Nie płacić za ponowne napisanie sensownego komentarza wyłącznie dlatego, że zaczyna się tak samo jak inny.

### 2.4. MYSL wymusza personę bardziej, niż pozwala na obserwację

Opis typu proponuje osobiste sformułowania w rodzaju „I just realised” i nazywanie czegoś, co „wszyscy czuli, ale nikt nie powiedział”. Jednocześnie tekst ma nie zawierać sprawdzalnych twierdzeń i nie może udawać osobistych doświadczeń. Twierdzenie o tym, co czują wszyscy, jest uogólnieniem empirycznym; fikcyjny moment osobistego olśnienia jest zabiegiem persony, nie dowodem autorskiego myślenia.

**Zmiana:** pozwolić na jawną preferencję, stanowisko, hipotetyczną sytuację i nierozstrzygnięte pytanie. Własny głos wynika z wyboru i rozumowania. Nie wymaga biograficznego „właśnie zrozumiałem”.

## 3. Artykuły: mechanizm staje się obowiązkową konstrukcją

### 3.1. Najpierw wymagasz krótszego tekstu, potem dłuższego zabiegu

`write()` losuje liczbę paraleli przed pisaniem. Dla THIN i SINGLE dostępne są 1 lub 2; zera nie ma. Opis jedynki wymaga dwóch akapitów o innym obszarze. Jednocześnie `pisarz.md` mówi, że przy pustych paralelach należy pisać krótko.

W odtworzonym przypadku karta miała `parallel_mechanisms: []`, tekst miał cel 420 słów, a polecenie nakazywało jedną rozwiniętą paralelę i zakończenie o alternatywnym projekcie. Brakowało materiału zarówno na porównanie, jak i na ten finał. To nie jest kwestia gustu: model dostaje żądanie zawartości, której nie ma w danych.

**Zmiana:** rozdzielić analogię objaśniającą od porównania faktograficznego. Pierwsza może być jawnie hipotetyczna. Drugie wymaga dowodów po obu stronach. Liczba wynika z funkcji w wywodzie, obejmuje zero. Długość wynika z pracy wyjaśniającej, a nie liczby równoległych branż.

### 3.2. Zakończenie może żądać nowej tezy na ostatnim metrze

Losowane finały wymagają m.in. wskazania beneficjenta, ceny awarii, alternatywnego projektu i jego kosztu albo zadania obserwacyjnego dla czytelnika. Każde z tych zakończeń może być dobre, kiedy wynika z materiału. W aktualnej funkcji wybór nie dostaje karty i nie może tego ustalić.

Przewidywany efekt: dopisany morał, wymuszony poszkodowany lub improwizowany kontrfaktyczny koszt. Model najpierw domyka temat, a potem jeszcze spełnia polecenie końcowe.

**Zmiana:** dopuszczalne zakończenia wyprowadzić z krótkiego briefu redakcyjnego. Finał nie może wprowadzać twierdzenia, które wymaga osobnego researchu. Krótki tekst może skończyć się ostatnim wyjaśnieniem bez osobnej puenty.

### 3.3. „Say each thing once” jest zbyt szeroką definicją powtórzenia

Prompt mówi: kiedy zaczynasz wspierać zamiast posuwać naprzód, idź dalej; gdy czytelnik już wierzy, kolejne dowody go nie poruszają. To trafne ostrzeżenie przed rozwlekłością, ale jako ogólna reguła usuwa z pola widzenia, po co pisze się środek artykułu.

Drugie przedstawienie zjawiska nie zawsze jest drugim powiedzeniem tego samego. Konkret może umożliwić zrozumienie abstrakcyjnej reguły. Kontrprzykład może ustalić jej granicę. Drugi pomiar może rozdzielić dwie konkurujące przyczyny. Te akapity nie muszą dodawać oddzielnego „przekonania”, żeby być potrzebne.

**Zmiana:** odróżnić redundancję od rozwoju. Akapit zostaje, kiedy wnosi dowód dla spornego związku, umożliwia zrozumienie procesu, rozdziela wyjaśnienia albo określa zasięg wniosku. Usuwa się go wtedy, gdy nie spełnia żadnej z tych funkcji. To daje redaktorowi powód cięcia, a nie sam zakaz.

### 3.4. Jeden akapit ograniczeń jest drugim szablonem wewnątrz artykułu

Jednoczesne wymagania: dokładnie jeden akapit ograniczeń; umieść go tam, gdzie pojawia się luka; nie powtarzaj; czasem ograniczenie może stać pojedynczo w innym akapicie. Gdy dwie niezależne tezy mają różne ograniczenia, model musi albo odsunąć któreś od jego tezy, albo naruszyć nakaz jednego akapitu.

**Zmiana:** ograniczenie idzie przy twierdzeniu, które zawęża. Łączymy powtórzenia tego samego zastrzeżenia, ale nie różne zastrzeżenia do różnych twierdzeń. Jeżeli ograniczenia są sednem artykułu, nie traktujemy ich ilości jako dowodu nadmiernej długości.

### 3.5. Precyzja terminologii i atrybucja są zbyt mechaniczne

Limit dwóch terminów specjalistycznych na cały tekst może wymuszać nieprecyzyjne synonimy w dobrym artykule wyjaśniającym trzy odrębne pojęcia. Reguła źródła w każdym zdaniu z liczbą może z kolei produkować rytm noty urzędowej, gdy kilka kolejnych zdań rozwija to samo badanie.

**Zmiana:** pierwsze użycie terminu wyjaśnia jego sens, kolejne zachowują tę samą nazwę. Pierwsze istotne użycie pomiaru określa producenta i warunki. Następne zdania muszą mieć jednoznaczną atrybucję, ale nie zawsze potrzebują powtórzenia pełnej nazwy instytucji. Zmiana źródła wymaga jawnego oznaczenia. To zachowuje rygor i pozwala pisać płynnie.

### 3.6. Karta dla pisarza miesza dowody, archiwum i ocenę własnej wartości

Tu potrzebne jest doprecyzowanie wcześniejszej odpowiedzi w rozmowie: pisarz **nie jest ograniczony wyłącznie do ośmiu twierdzeń**. Limit dotyczy `confirmed_claims`, lecz ścieżka artykułu dodaje `unused_evidence` ze wszystkimi przekazanymi fragmentami i liczbami po klasyfikacji. Nie odejmuje fragmentów użytych w syntezie. To etykieta archiwalna, a nie rzeczywisty wynik pomiaru, czego artykuł nie wykorzystał — tekst jeszcze nie istnieje.

Następnie dopisywane jest `ocena_ciekawosci`, czyli cały wynik oceny, razem z `werdykt`, powodami i wskazówką ratunku. `karta_dla_pisarza()` usuwa w pewnych warunkach wyłącznie uwagę o dacie. Pozostałe pola docierają do `write()`. Odtworzenie na syntetycznej karcie potwierdziło, że pola `unused_evidence` i `ocena_ciekawosci` pozostają w wejściu pisarza.

Powstają trzy problemy związane bezpośrednio z pisaniem:

1. Fragmenty mogą się powtarzać w syntezie i archiwum, powiększając wejście bez dostarczenia nowego materiału.
2. Pisarz widzi dodatkowe liczby, ale ogólna instrukcja pozwala używać tylko `citable_numbers`. Nie ma jasnej reguły, czy wolno mu samodzielnie wydobyć nowy fakt z dodatkowego fragmentu, czy ma uznać go za odłożony.
3. Model z zadaniem „napisz” może dostać w karcie werdykt `ODLOZ` i wyjaśnienie, dlaczego materiał nie daje czytelnikowi powodu do zainteresowania. To nie jest dowód o świecie ani gotowa decyzja redakcyjna. To konkurencyjne zadanie, które może skłaniać do asekuracji i metakomentarza o słabości materiału.

**Zmiana:** zapisywana karta archiwalna może pozostać bogata. Widok pisarza powinien być osobnym, świadomie złożonym obiektem: zatwierdzony zakres, wybrane dowody z identyfikatorami, konkretna interpretacja do rozwinięcia i ograniczenia. Ocena przydatności steruje formatem przed pisaniem; do pisarza wchodzi decyzja „wyjaśnij ten jeden mechanizm w krótkiej formie”, a nie surowa ocena „nie ma tu ciekawości”. Nie należy przerzucać magazynu do promptu tylko dlatego, że oba obiekty są słownikami.

## 4. Rzeczywiste próbki stylu uczą czegoś innego niż reguły

`style.load_examples()` zawsze zwraca po jednym przypiętym akapicie dla pięciu funkcji. To stały zestaw, nie dobór do pytania, rodzaju artykułu lub potrzeb konkretnego fragmentu. Trzy z pięciu próbek dotyczą tej samej dyskusji o cenach i przypisywaniu ich wzrostu chciwości firm. Jest to wąski zestaw sposobów myślenia, nawet jeśli same akapity są sprawne.

| Próbka | Co rzeczywiście robi | Napięcie z resztą stosu |
|---|---|---|
| OPENING | Zaczyna od znajomego przypisania winy, uznaje jego intuicyjność i częściową słuszność | Ocena formy zgłasza uwagę za znajomą tezę pierwszego akapitu; pisarz ma od razu stawiać duże wyjaśnienie |
| CONCRETE_TO_SYSTEM | Wraca do wcześniej opowiedzianego przykładu i przez analogię przechodzi do szerszego ograniczenia | Wyrwany fragment nie pokazuje wcześniejszego konkretu. Słaba karta może sprowokować imitowanie przejścia bez zbudowanego początku |
| MECHANISM | Pytanie prowadzi do przyczyny, a celowo nietrafny hipotetyczny model ujawnia rolę doboru zmiennych | Obowiązkowa zewnętrzna paralela jest innym zabiegiem niż przykład wyjaśniający wewnątrz mechanizmu. Model nie dostaje tego rozróżnienia |
| COUNTERARGUMENT | Rozważa konkurującą interpretację i rozwija ją przez kilka warunkowych zdań | Presja gęstości nowych przekonań i ograniczania zastrzeżeń może potraktować tę pracę jako zbyt mało postępu |
| ENDING | Przyjmuje nierozstrzygnięcie sporu i wyprowadza zalecenie wspólne dla dwóch interpretacji; używa długiego zdania | Finał jest sensowny dzięki wcześniejszemu sporowi. Losowane zakończenie nie musi mieć takiego oparcia |

**Nie usuwałbym automatycznie tych przykładów.** Wartość mechanizmu i kontrargumentu polega właśnie na wyjaśnianiu, któremu inne reguły przeszkadzają. Problemem jest brak instrukcji, co należy przenieść, oraz przypisywanie jednego akapitu do każdej pracy tej samej kategorii.

Proponuję bank przykładów opisanych przez: funkcję, warunki użycia, cechę głosu do zachowania i element, którego nie należy kopiować. Początkowo wystarczy 8–12 krótkich zatwierdzonych próbek, wybór 2–3 do danego zadania. To propozycja skali startowej, nie próg udowodniony eksperymentalnie.

Przykład adnotacji: „Ta próbka pokazuje uczciwe rozwinięcie alternatywnego wyjaśnienia. Użyj tylko, gdy karta zawiera konkurujące interpretacje. Przenieś cierpliwość wywodu i wyraźne warunki; nie przynoś sporu gospodarczego ani jego zakończenia do innego tematu”.

Dobór powinien uczyć relacji z czytelnikiem: jaka wiedza jest zakładana, kiedy wyjaśnić, kiedy pozwolić mu wyciągnąć wniosek, jak stanowczo postawić interpretację. Same parametry interpunkcji tego nie tworzą.

## 5. Ocena stylu wzmacnia szablon, z którym pisarz ma walczyć

### 5.1. Proza wyjaśniająca jest rozliczana z liczby przekonań

`forma.md` każe scalać przekonania, jeżeli jedno tylko wspiera drugie lub jest jego bezpośrednią konsekwencją. `gates.uwagi_z_formy()` dzieli liczbę słów przez liczbę tak scalonych przekonań i zgłasza uwagę powyżej 150 słów.

Przy docelowych długościach próg oznacza co najmniej:

- 3 przekonania dla THIN / 420 słów;
- 5 dla SINGLE / 650 słów;
- 8 dla RICH / 1075 słów.

W odtworzeniu 650 słów i dwa przekonania dały uwagę `GESTOSC_BEATOW`. Nie trzeba żadnego modelu, żeby to stwierdzić. Nie wynika z tego natomiast, że taki artykuł jest zły: może bardzo dobrze tłumaczyć jeden złożony problem.

To szczególnie ważne przy karcie z limitem ośmiu potwierdzonych twierdzeń. Twierdzenie i przekonanie to różne jednostki, ale pisarz ma jednocześnie ograniczony zestaw faktów i presję wielu niezależnych „olśnień”. Paralele stają się sposobem dostarczenia kolejnych olśnień zamiast wyjaśniania głównego problemu.

**Zmiana:** gęstość pozostawić metryką opisową do porównań podobnych form, nie uniwersalnym zarzutem redakcyjnym. Recenzent wskazuje konkretny akapit do skrócenia i wyjaśnia, co czytelnik traci lub nie traci po usunięciu.

### 5.2. Kontrola formy nie jest wyłącznie obserwatorem

System mówi, że model ma tylko raportować fizycznie obecną treść, bez oceny. Tymczasem pytania o to, co czytelnik wcześniej wierzył, co jest już szeroko znane i czy fakt jest dostatecznie mocny, wymagają interpretacji oraz założeń o odbiorcy. Cytat dowodzi obecności zdania; nie dowodzi trafności modelu w ocenie jego znajomości.

Automatyczny zarzut za brak osobistego „reader moment” skłania każdy artykuł do tego samego zwrotu do czytelnika. Zarzut `BRAK_ESKALACJI` za ten sam rejestr najważniejszego faktu i procedury premiuje zmianę temperatury także wtedy, gdy spokojne zestawienie liczb jest najmocniejszym sposobem ich podania.

**Zmiana:** brak „you”, spokojny rejestr i znajome otwarcie nie są wadami samymi w sobie. Wada wymaga opisu skutku: czytelnik nie wie, dlaczego przykład ma znaczenie; nie rozumie związku; obietnica otwarcia nie zostaje spełniona. To są powody redakcyjne, które da się ocenić na tekście.

### 5.3. Uwagi wracają bez rozstrzygnięcia, czy były trafne

`ostatnie_uwagi()` bierze uwagi z dwóch najnowszych plików i przekazuje je następnemu pisarzowi. To nie jest wyłącznie informacja z obserwacji formy: przechodzą różne kody uwag, z wyjątkiem DLUGOSC i RECENZJA. Brakuje informacji „ten zarzut zaakceptowano”, rodzaju poprzedniego artykułu i tego, jaka poprawka była udana.

Powstaje pętla: reguła wymaga „czytelnika przyłapanego”, tekst go nie ma, następny dostaje zarzut i zaczyna go dodawać. Potem profil zaczyna być monotonny, więc dochodzi nowy zakaz. Liczba reguł rośnie, a nie powstaje stabilny głos.

**Zmiana:** pamięć redakcyjna przechowuje zaakceptowany problem, warunki jego wystąpienia i krótką skuteczną poprawkę. Pisarz dostaje najwyżej kilka uwag pasujących do obecnego zadania. Hipoteza automatycznego sędziego nie staje się trwałą regułą tylko dlatego, że pojawiła się dwa razy.

### 5.4. Docelowy głos redakcyjny jest za wąski względem deklarowanego tematu

Zestaw ocen stale szuka tych samych właściwości: człowiek lub instytucja decydująca, błędne przekonanie, wyczuwalna wielkość, inny obszar, koszt, osobisty związek czytelnika. To pasuje do publicystyki o regułach i bodźcach. Nie obejmuje równie dobrze tekstu wyjaśniającego działanie zjawiska, historii odkrycia albo porównania sposobów rozumowania.

Dobry tekst o tym, dlaczego pewna metoda działa, może nie mieć winnego, poszkodowanego, drugiego kraju ani błędnego przekonania masowego odbiorcy. Może zainteresować przez pokazanie precyzyjnego związku. Obecny stos traktuje brak własnych ulubionych elementów jako brak głębi, a potem każe je dokładać.

**Proponowana definicja głosu:** ciekawy świata, konkretny, zdolny do wyjaśnienia związku i postawienia własnego wniosku; ostry wtedy, gdy wniosek wymaga ostrości. **Proponowana definicja rozwoju tekstu:** zmiana rozumienia przez przyczynę, warunek, rozróżnienie, przebieg zdarzeń, porównanie albo kontrargument. Demaskowanie jest jednym z ruchów, nie warunkiem autorskości.

Warto pokazać sędziemu dopuszczalne gatunki, aby nie oceniał wszystkich jedną miarą. Wyjaśnienie mechanizmu ocenia się przez kompletność związku i zrozumiałość. Porównanie przez uczciwe wspólne kryterium. Rekonstrukcję zdarzeń przez to, czy kolejne zdarzenia zmieniają sytuację. Polemikę przez trafne przedstawienie stanowiska i rzeczywistą odpowiedź. Nie trzeba dopasowywać świata do jednego formularza.

## 6. Komentarze i odpowiedzi: kosztowne losowanie osobowości

`losowa_postawa()` i `losowe_otwarcie()` są niezależne. Odtworzyłem CIEKAWOSC („nie korygujesz”) z otwarciem „zacznij od sprzeciwu”. Możliwe są też KONKRET („podaj szczegół bez ramy i lekcji”) z ogólnym nakazem powiedzenia, dlaczego to ma znaczenie dla czytelnika. Odpowiedź na pytanie ma dać odpowiedź w pierwszym zdaniu, ale może dostać otwarcie kolejnym pytaniem.

Przy komentarzu o docelowych 12 słowach dochodzą: obecność I/you/we, jedna konkretna rzecz, stanowisko, zadana postawa, zadane otwarcie i długi blok zakazów. Każda dodatkowa reguła zabiera część bardzo małej przestrzeni wypowiedzi. Rezultatem może być zdanie skompresowane w slogan zamiast zwykłej, celnej odpowiedzi.

Istnieje już lepszy punkt wyjścia: `co_dodamy`, czyli konkretne uzasadnienie wyboru posta. To ono powinno sterować postawą. Jeśli wkładem jest pytanie, komentarz pyta. Jeśli brakujące ogniwo argumentu, wyjaśnia. Różnorodność wynika z wyboru różnych wkładów, a nie z losowania sprzeciwu wobec dowolnego tekstu.

Nie proponuję tu cofnięcia aktualnej polityki pisania komentarzy pod wybranymi postami ani dodania zgód człowieka. Propozycja promptu zachowuje pięć obecnych powodów milczenia. Zmienia formułowanie wkładu i usuwa konflikt postawy z otwarciem.

W odpowiedziach własny artykuł bywa reprezentowany samym nagłówkiem, co sam prompt uczciwie opisuje. Nie da się promptem nakazać trafnej obrony argumentu, którego model nie dostał. Dla odpowiedzi o treści artykułu trzeba dołączyć odpowiedni fragment i powiązane dowody. Inaczej stanowczość może dotyczyć wymyślonej wersji tezy, a ostrożność zamieni się w wielokrotne „musiałbym sprawdzić”.

## 7. Recenzent sprawdza pochodzenie zdań, lecz nie redaguje argumentu

Obecny `review()` czyta cały artykuł zdanie po zdaniu i zwraca każde zdanie w JSON. `forma()` jeszcze raz czyta tekst, szuka cytatów i opisuje kilka cech. Płatne wyjścia w dużej części reprodukują już opłacony tekst.

Mimo tej pracy brakuje zadania: „Czy krok drugi faktycznie prowadzi do kroku trzeciego?”, „Czy analogia coś wyjaśnia?”, „Czy ten akapit da się usunąć bez straty?”, „Które dobre zdania trzeba zachować?”. Nie jest to więc pełna redakcja literacka ani argumentacyjna.

Reguła `INFERENCE never fails` ma słuszny cel ochrony interpretacji, ale operuje na całych zdaniach. W zdaniu opinii może siedzieć fałszywa przesłanka faktograficzna. Samo „moim zdaniem” nie naprawia tej przesłanki. To wpływa na głos: model dostaje bodziec, by zamieniać trudne twierdzenia w opinie zamiast je lepiej uzasadnić.

**Zmiana:** oceniać klauzule faktograficzne również wewnątrz interpretacji. Ocena redakcyjna zwraca konkretne fragmenty z wadą, skutek dla czytelnika i najmniejszą potrzebną zmianę; nie katalog każdego zdania. Dodać pole `preserve`, aby redaktor nie wygładzał wszystkiego. W pierwszym porównaniu zastąpić tym zadaniem `forma`, pozostawiając osobno obecną weryfikację faktów. Dopiero gdy porównanie wykaże równoważną wykrywalność błędów, rozważać łączenie etapów.

Naprawa krótkiego tekstu ma osobny problem: obecny prompt każe zachować wszystkie niezakwestionowane zdania dosłownie. Jeśli zmiana faktu podważa dalszą puentę, zachowana puenta może już nie wynikać z poprawionego zdania. Zakres poprawki powinien obejmować zakwestionowaną przesłankę i zależny od niej wniosek, z zachowaniem pozostałej prozy. Nie chodzi o przepisywanie całości.

## 8. Proponowany nowy podział odpowiedzialności

1. **Materiał dowodowy:** identyfikatory twierdzeń i fragmentów, zakres, daty, ograniczenia, dopuszczone wartości liczbowe. Bez reguł stylu i ocen „mocny/słaby”.
2. **Brief redakcyjny:** pytanie czytelnika, odpowiedź możliwa do obrony, istotny związek, ograniczenie zmieniające sens, format uzasadniony materiałem. Może powstawać zamiast obecnej oceny `warto_pisac`, a nie jako kolejny obowiązkowy model w łańcuchu.
3. **Stały głos:** krótki wspólny kontrakt, bez słownika kar, kalendarza i historii awarii.
4. **Zlecenie gatunkowe:** osobno artykuł, notka faktograficzna, myśl, komentarz, odpowiedź. Jeden gatunek nie dziedziczy obowiązków innego.
5. **Przykłady:** mały dobór pasujący do zadania, z opisem tego, czego uczą.
6. **Redakcja:** kontrola funkcji i powiązań, bez obowiązku olśnienia co 150 słów i bez automatycznego wymuszania „you”.

Jest to podział danych i instrukcji. Nie wymaga sześciu nowych wywołań modeli. Deterministyczne składanie promptu ma rozwiązywać konflikty przed wysłaniem.

Przykładowe reguły zgodności w kodzie:

- LICZBA jest dostępna, gdy materiał ma wielkość z jednostką i znaczeniem, a nie sam identyfikator lub rok.
- LISTA jest dostępna, gdy są trzy różne ustalenia potrzebne tej samej myśli. Nie trzy parafrazy.
- SPROSTOWANIE wymaga nazwanego, udokumentowanego twierdzenia do skorygowania.
- MYSL korzysta wyłącznie z własnych form.
- Zakończenie nie wymaga nowego faktu, którego karta nie zawiera.
- Otwieranie komentarza wynika z wybranego wkładu; nie jest losowane niezależnie.

## 9. Konkretne propozycje brzmienia — wyłącznie część raportu

Poniższe fragmenty są propozycją do oceny. Nie zostały wprowadzone do bota. Nie są też kompletnymi zamiennikami jego szablonów; pokazują, jak zmienić kontrakt bez dokładania kolejnej warstwy sprzecznych reguł.

### Wspólny głos

> Make the reader understand something worth understanding. Choose the exact observation, explain the connection that makes it matter, and stop when the thought is complete. Authority comes from what you can explain and support.
>
> Use familiar language without flattening distinctions. Introduce a necessary technical term through its meaning, then use it consistently. Let sentence length follow the thought. A short sentence can carry a consequence; a longer one can hold a condition and its result together.
>
> Factual assertions must be supported by the supplied evidence. Preserve scope, attribution, uncertainty and time. An interpretation may connect established facts, but a phrase such as “I think” does not turn an unsupported factual premise into an opinion.

Ten fragment definiuje relację z czytelnikiem i sposób wyjaśniania. Nie narzuca rodzaju puenty, liczby terminów ani stałego stopnia ostrości.

### Rozwijanie artykułu zamiast limitu nowych przekonań

> Develop one central argument. Supporting evidence earns its place when it establishes a disputed link, makes an unfamiliar process understandable, distinguishes competing explanations, or shows how far the conclusion reaches. Cut passages that repeat an already established point without doing one of those jobs. Do not replace explanation with a parade of new facts.

To zastępuje ogólne „gdy wspierasz zamiast posuwać naprzód, idź dalej”. Wymaga funkcji akapitu i zachowuje prawo do objaśnienia.

### Paralele i finał artykułu

> Use an outside comparison only if it clarifies a particular step or reveals a meaningful limit. A factual comparison needs supplied evidence for both sides. A hypothetical analogy must be recognisably hypothetical and must not imply evidence about another industry or institution. Zero comparisons is a complete choice.
>
> End when the argument has reached its useful consequence, answered its question, or exposed its remaining limit. That final movement may need a paragraph, a sentence, or no separate ending. It must follow from the article. Do not invent a victim, a beneficiary, an alternative design or a task for the reader to satisfy a closing device.

### Notka faktograficzna

> Say one worthwhile thing clearly. The first sentence should carry either the finding or a concrete reason to care about the question it answers. Use the remaining space to explain the connection or condition that makes the finding mean what it means. Stop there.
>
> Correct a belief only when the assignment includes evidence of that belief. A mechanism explained plainly, an unexpected result, or a precise consequence can carry a Note without a reversal. Choose only a form the supplied material can support.

### MYSL

> This assignment carries no factual evidence. Make a precise judgement, ask a sincere question, or examine a clearly hypothetical choice. Give the reader something definite to consider. Do not assert statistics, named events, causal claims about real systems, what most people feel, or a shared experience you cannot establish.
>
> First person may state a preference or position. Do not invent a recent realisation, a conversation, a memory or an emotion as something you experienced. You do not need to settle an open question, break a belief or introduce a number.

Oddzielny prompt dla MYSL powinien jawnie dopuszczać puste pola `fact_used` i `source_url`. To odrębna specyfikacja gatunku, nie wyjątek ukryty pod wszystkimi wymogami notki z faktami.

### Komentarz

> Address the selected contribution directly. Its nature determines the opening: answer a question, explain a missing link, offer a supported example, or state a specific disagreement. Do not adopt a contrary position because a random style instruction asks for one.
>
> One contribution is enough. Write to the person and the point, using a pronoun when it helps; there is no required “I” or “you”. Use only the amount of explanation the contribution needs. Do not stretch a clear sentence to meet a target.

### Redaktor

> Report only consequential issues. Every finding must quote the affected text exactly, explain the loss to the reader, and state the smallest adequate change. If a needed fact is absent, identify the missing evidence; do not invent replacement prose.
>
> Additional support is useful when it establishes a disputed link, explains an unfamiliar process or separates alternatives. Flag repetition only when removing it loses none of those functions.
>
> Identify up to two passages whose specificity, explanation or rhythm should be preserved. A dash, a long sentence, a technical term or lack of “you” is not a defect by itself. Do not suggest rewriting a sound article merely to make it different.

To zmienia pytanie z „czy artykuł ma wszystkie nasze zabiegi?” na „co w konkretnym miejscu przeszkadza czytelnikowi i co warto zachować?”.

### Przykład różnicy na tym samym materiale

Poniższe dane są **wymyślonym przypadkiem demonstracyjnym**, nie twierdzeniem o konkretnym produkcie i nie wynikiem wywołania modelu. Karta zawiera test tego samego modelu na tych samych 100 pytaniach: 60 poprawnych odpowiedzi bez dostępu do źródła, 80 z dostępem; brak pomiarów innych zadań. Warunki poza dostępem do źródła są takie same.

Wersja ilustrująca wymuszoną retorykę:

> You think a better score means a smarter model. It doesn't. It means better access. The real intelligence was in the setup all along.

Problemy: przypisuje czytelnikowi nieudokumentowane przekonanie, uogólnia pojedynczy test i kończy efektownym zdaniem o „prawdziwej inteligencji”, którego karta nie ustala. Usunięcie pauz lub zmiana pierwszego słowa nie naprawi niczego z tej listy.

Wersja ilustrująca pożądany kierunek:

> Give the same model its source material and, in this test, correct answers rose from 60 to 80 out of 100. The result belongs to a setup: the model, the questions and what it could consult.

Druga wersja zachowuje warunek „w tym teście” i podaje konkret. Ostatnie zdanie wnosi interpretację: przy porównaniu wyniku liczy się także konfiguracja zadania. Nie dopisuje niezbadanego przekonania czytelnika ani wszechobejmującej tezy o inteligencji. Może nie wygrać każdego porównania stylistycznego; pokazuje kryterium jakości, które da się wskazać w zdaniach.

W artykule rozwinięcie nie wymagałoby automatycznie analogii z inną branżą. Przy wystarczającym materiale można wyjaśnić, do czego model miał dostęp, jak zadano pytania, co uznano za poprawną odpowiedź i czego to porównanie nie rozdziela. To rozwija ten sam problem. Jeśli karta tego nie zawiera, forma powinna pozostać krótka.

Nie przenosiłbym bezwarunkowego zakazu każdego słowa z `Banned vocabulary`. Na przykład „robust” może być pustym przymiotnikiem albo precyzyjnym określeniem omawianej własności. Redaktor powinien usuwać pustą funkcję słowa, a nie wymuszać mniej trafny synonim. Zakazy oczywistych pustych formuł pozostają użytecznym zabezpieczeniem, ale nie stanowią definicji głosu.

## 10. Jak udowodnić poprawę bez kupowania wielkiego eksperymentu

Pierwszy etap już wykonany: bezpłatne odtworzenie promptów ujawnia konflikty niezależne od modelu. Nie trzeba wydać pieniędzy, żeby stwierdzić, że notka bez liczb nie powinna dostać nakazu otwarcia liczbą.

Drugi etap to mały test na identycznych materiałach, nie porównanie różnych publikacji:

1. Sześć kart: krótki mechanizm, pomiar z istotnym warunkiem, dwie konkurujące interpretacje, chronologia zmiany, jeden słaby fakt i materiał bogaty w sensowne rozwinięcia. Dla notek dodać myśl bez faktów oraz ciekawostkę bez liczby.
2. To samo źródło/karta, ten sam model i ustawienia. Najpierw obecny prompt przeciw poprawionemu bez zmiany researchu. Zmiana modelu jednocześnie ze zmianą promptu nie pozwoli przypisać efektu.
3. Ocena bez etykiet wariantu: co czytelnik rozumie, gdzie potrzebuje brakującego związku, który akapit można usunąć bez straty, czy tekst obiecuje więcej niż dowodzi, czy głos jest konkretny i czy chce się czytać dalej.
4. Oddzielnie porównać factualność: zakres, atrybucję, czas i liczby. Tekst brzmiący lepiej, ale słabiej oparty, nie wygrywa.
5. Zapisać koszt wejścia, wyjścia, rozumowania i poprawek, kiedy dostawca je raportuje. Skrócenie promptu o połowę nie oznacza o połowę tańszego artykułu.
6. Na dwóch kartach powtórzyć generację, żeby pojedynczy szczęśliwy wynik nie rozstrzygnął całości. Rozszerzać próbkę dopiero, gdy wynik jest niejednoznaczny.

Po wyborze promptu można przeprowadzić drugie porównanie: ten sam poprawiony kontrakt na dwóch modelach. Najpierw trzeba przestać płacić modelowi za rozstrzyganie sprzecznych instrukcji. W tym projekcie to bardziej uzasadniony pierwszy krok niż podnoszenie klasy modelu lub dokładanie jeszcze jednej rundy recenzji.

### Gdzie dokładnie szukać oszczędności

| Zmiana | Co może zmniejszyć koszt | Co chroni jakość |
|---|---|---|
| Oddzielny prompt MYSL | Mniej niepasujących instrukcji i prób spełnienia kontraktu faktograficznego | Własna specyfikacja refleksji bez wymuszonych liczb |
| Dobór formy po materiale | Mniej prób ponawianych po niewykonalnym zleceniu | Forma nie wymaga faktów spoza materiału |
| Osobny widok karty dla pisarza | Mniej powtórzonych cytatów i administracyjnego JSON-a | Zachowanie wszystkich fragmentów potrzebnych bieżącemu wywodowi |
| Usunięcie niezależnego losowania otwarć | Mniej ponowień z powodów powierzchownych | Wkład komentarza określa adekwatne pierwsze zdanie |
| Redaktor zwracający tylko istotne problemy | Mniej wyjścia kopiującego wszystkie zdania artykułu | Konkretny cytat, problem i najmniejsza poprawka; test wykrywalności błędów przed łączeniem etapów |
| Krótki stały głos | Mniej powtarzanego wejścia | Zachowanie dobrych próbek i precyzyjnych granic twierdzeń |

Nie ma podstaw do podania procentowej oszczędności całego rachunku przed pomiarem. Różni dostawcy inaczej rozliczają wejście, wyjście, rozumowanie i cache. Szczególnie ważne: nie usuwać tanich dowodów lub próbek tylko po to, żeby zredukować wejście, jeśli skutkiem będzie dodatkowe kosztowne pisanie.

## Mapa miejsc do sprawdzenia w kodzie

Odnośniki wskazują lokalne pliki. Numery linii dotyczą stanu odczytanego przy końcowej weryfikacji; podczas analizy w repozytorium istniały także zmiany z innych prac.

| Obserwacja | Miejsce |
|---|---|
| Co naprawdę ładuje się jako styl | [style.load_profiles](<D:/Nia bot/agent-v2/style.py:163>) |
| Pięć stałych próbek | [style.load_examples](<D:/Nia bot/agent-v2/style.py:116>) |
| Składanie całego promptu artykułu | [stages.write](<D:/Nia bot/agent-v2/stages.py:653>) |
| Karta z archiwum i oceną | [karta_dla_pisarza](<D:/Nia bot/agent-v2/stages.py:556>), [dodawanie fragmentów](<D:/Nia bot/agent-v2/artykul_z_puli.py:664>) |
| Przydział form przed materiałem | [notki_dnia](<D:/Nia bot/agent-v2/stages.py:3447>) |
| Drugi kształt dla MYSL | [_opis_typu](<D:/Nia bot/agent-v2/stages.py:2611>) |
| Pamięć otwarć i blok antykupletowy | [note](<D:/Nia bot/agent-v2/stages.py:2627>) |
| Losowanie postawy komentarza | [losowa_postawa](<D:/Nia bot/agent-v2/config.py:1355>) |
| Niezależne losowanie otwarcia | [losowe_otwarcie](<D:/Nia bot/agent-v2/config.py:1377>) |
| Losowanie finału artykułu | [losowy_ruch_koncowy](<D:/Nia bot/agent-v2/config.py:3077>) |
| Brak zera w liczbie paraleli | [losowa_liczba_paraleli](<D:/Nia bot/agent-v2/config.py:3085>) |
| Licznik przekonań i obowiązek czytelnika | [uwagi_z_formy](<D:/Nia bot/agent-v2/gates.py:380>) |
| Informacja zwrotna dla kolejnego pisarza | [ostatnie_uwagi](<D:/Nia bot/agent-v2/stages.py:411>) |
| Obowiązek obalania przekonania | [notka.md](<D:/Nia bot/agent-v2/prompts/notka.md:77>) |
| Presja na postęp zamiast wsparcia | [pisarz.md](<D:/Nia bot/agent-v2/prompts/pisarz.md:163>) |
| Nakaz jednego akapitu granic | [pisarz.md](<D:/Nia bot/agent-v2/prompts/pisarz.md:218>) |
| Zwolnienie interpretacji z oceny | [recenzent.md](<D:/Nia bot/agent-v2/prompts/recenzent.md:26>) |

## Kolejność pracy

**Największy wpływ:** oddzielić MYSL; dobierać formę do danych; usunąć powszechny obowiązek demaskowania; przestać losować niepodparte zakończenia i paralele; zastąpić gęstość przekonań oceną rozwoju argumentu.

**Następnie:** wspólny krótki głos; selekcja próbek i adnotacje; celowana pamięć uwag; komentarze sterowane wkładem; redaktor zachowujący dobre fragmenty.

**Dopiero na końcu:** strojenie słownika, interpunkcji i parametrów modeli. Te zmiany mają sens, kiedy model dostaje spójne zadanie i wystarczający materiał.
