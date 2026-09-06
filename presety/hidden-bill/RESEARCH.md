# Dlaczego The Hidden Bill

Badanie wykonane 6 września 2026. Rozdzielam obserwacje rynku od
decyzji redakcyjnej. Nie mam dostępu do prywatnych statystyk otwarć,
kliknięć i konwersji cudzych publikacji. Publiczne reakcje i rankingi
nie dowodzą, że nowy autor osiągnie podobny wynik.

**Sygnał popytu**

W odczytanym zestawieniu Substack Business BIG by Matt Stoller zajmuje
17. pozycję i ma oznaczenie „hundreds of thousands of subscribers”.
Feed Me jest na 3. pozycji, Noahpinion na 2., a Derek Thompson na 9.
To różne publikacje, których wspólnym obszarem są biznes, ekonomia,
kultura i skutki działania instytucji. Rankingu nie traktuję jako
metodologicznie jednolitego testu klikalności. [Zestawienie Substack Business](https://substack.com/top/business).

BIG pokazuje, że wyjaśnianie wpływu firm i struktury rynku może być
pełnoprawną publikacją dla płacącej publiczności. Jego model obejmuje
także wywiady, badania archiwalne i pracę reporterską, więc sukcesu
nie wolno przypisywać samemu tematowi ani automatycznie przenosić na
bota. [Opis publikacji BIG](https://www.thebignewsletter.com/about).

**Wybór redakcyjny**

Wybieram węższą obietnicę niż „ekonomia” lub „władza korporacji”:
wyjaśnienie jednego zakupu i warunku, który zmienia jego koszt.
Rozpoznawalność biletu, subskrypcji czy naprawy daje dobry punkt wejścia;
specyficzny dokument daje powód, aby doczytać. To hipoteza redakcyjna
do sprawdzenia, a nie gwarancja wiralowości.

| Rozważany kierunek | Potencjał i ograniczenia | Decyzja |
|---|---|---|
| Praktyczne AI | Widoczna publiczność w rankingu; silna konkurencja, potrzeba testowania narzędzi, duże podobieństwo do obecnego presetu | Nie tworzyć drugiego niemal tego samego kanału |
| Relacje i psychologia codzienna | Dużo tematów do dyskusji; ten bot nie ma doświadczenia autora ani procesu pracy właściwego dla porad psychologicznych | Słabsze dopasowanie do obecnego silnika dokumentów |
| Komentarz polityczny | Możliwy wysoki poziom reakcji; silna zależność od głosu autora, bieżącej wiedzy i oryginalnego reportingu | Nie wybierać jako pierwszego niezależnego presetu |
| Warunki codziennych zakupów | Znajome sytuacje, dokumenty pierwotne, długi zapas tematów, miejsce na konkret i uczciwy kontrargument | Wybrany kierunek |

Oceny dopasowania są moją analizą architektury i modelu redakcji,
nie ilościowym rankingiem nisz. Angielski i pierwszeństwo odbiorcy USA
wybrałem ze względu na badaną publiczność oraz dostępne źródła i
angielskie reguły językowe bota. Nie ekstrapoluję praw USA na UK/EU.

**Czy jest z czego regularnie pisać**

Tak, istnieje kilka niezależnych strumieni dokumentów. Przykładowo
FTC opublikowała materiały o ujawnianiu opłat za bilety i krótkie pobyty,
CMA o przejrzystości cen, a Komisja Europejska o naprawie produktów.
Każdy z tych obszarów ma własny zakres i daty. Są to punkty wyjścia do
researchu, a nie uniwersalne twierdzenia o obecnie obowiązujących prawach.
[FTC o opłatach](https://www.ftc.gov/news-events/news/press-releases/2025/05/ftc-rule-unfair-or-deceptive-fees-take-effect-may-12-2025),
[CMA o cenach](https://www.gov.uk/government/publications/price-transparency-cma209),
[Komisja Europejska o naprawach](https://commission.europa.eu/law/law-topic/consumer-protection-law/directive-repair-goods_en).

Istotny przeciwwzorzec dla taniej sensacji daje raport CMA o cenach
lojalnościowych: jego ustalenia nie wspierają tezy, że wszystkie takie
rabaty są fikcją. To materiał na wyjaśnienie dwóch różnych porównań,
zamiast na kolejny tekst o „oszukiwaniu klientów”.
[Raport CMA, podsumowanie z 27 listopada 2024](https://www.gov.uk/government/publications/review-of-loyalty-pricing-in-the-groceries-sector/executive-summary).

W źródłach uwzględniłem organy publiczne, autorów analiz, organizację
zajmującą się prawami cyfrowymi oraz firmę naprawczą. Ich role są różne:
komunikat urzędu nie zastępuje orzeczenia, stanowisko organizacji nie
jest neutralnym eksperymentem, a blog sprzedawcy narzędzi ma własny
interes. Scout otrzymuje sygnały; research musi dotrzeć do dokumentu.

**Feed rzeczywiście skonfigurowany w TOML-u**

Każdy z poniższych adresów zwrócił HTTP 200 i poprawny XML z wpisami
w próbie 6 września 2026. Liczba wpisów oznacza zawartość pobranego
feedu, nie dzienną produkcję. Sprawdzenie połączenia nie jest oceną
prawdziwości wszystkich wpisów ani obietnicą przyszłej dostępności.

| Feed | Format / wpisy | Rola i ograniczenie |
|---|---|---|
| [FTC Consumer Protection](https://www.ftc.gov/feeds/press-release-consumer-protection.xml) | RSS / 30 | Oficjalne komunikaty; rozdzielać zarzuty, rozstrzygnięcia i terminy |
| [CMA Announcements](https://www.gov.uk/government/organisations/competition-and-markets-authority.atom) | Atom / 20 | Oficjalne informacje UK; odfiltrować sprawy bez związku z zakupem konsumenta |
| [BIG](https://www.thebignewsletter.com/feed) | RSS / 20 | Sygnały i kontekst; odnaleźć własne dokumenty i odrębne pytanie |
| [Pluralistic](https://pluralistic.net/feed/) | RSS / 30 | Tropienie ograniczeń cyfrowego dostępu; nie kopiować ocen ani charakterystycznego stylu |
| [EFF](https://www.eff.org/rss/updates.xml) | RSS / 50 | Prawa cyfrowe i postępowania; organizacja rzecznicza, konieczne filtrowanie |
| [iFixit](https://www.ifixit.com/News/rss) | RSS / 10 | Naprawy i testy; podmiot komercyjny, sprawdzać metodę i dokumentację producenta |

FTC sama publikuje katalog swoich feedów.
[Oficjalna lista RSS FTC](https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds).
Adres iFixit zapisano po rozpoznanym przekierowaniu z `/News/feed`
na `/News/rss`.

Odrzucone z konfiguracji: testowane feedy CFPB, FCC i BLS zwróciły 403;
część zgadywanych adresów alertów konsumenckich FTC zwróciła 404.
Nie obchodzono blokad. Blog CMA działał, ale jego najnowszy odczytany
wpis był z kwietnia 2026; wybrano świeższy feed organizacji.
Nie dołączono dwóch feedów z tym samym zestawem komunikatów FTC.

Preferowane domeny w TOML-u to mapa miejsc do szukania dowodów,
nie obietnica, że każdy adres jest odczytywany automatycznie. Dokument
niedostępny dla narzędzia nie staje się źródłem tylko dlatego, że jego
domena znajduje się na liście. Trzeba znaleźć dostępną publikację
pierwotną, zawęzić temat albo go odrzucić.

**Granice automatyzacji**

Preset nie ma udawać dziennikarza, który osobiście robił zakupy,
kontaktował się z firmą lub prowadził rozmowy. Bazuje na dostępnych
dokumentach i jasno opisuje użycie AI. Tematy wymagające samodzielnego
eksperymentu lub prywatnego dowodu pozostają propozycjami do dodatkowej
pracy. Aktualność przepisu i status sprawy trzeba sprawdzić przed
każdym tekstem; wpis z 2025 r. nie jest wiadomością z tego tygodnia.

Ocena, czy kierunek rzeczywiście działa, wymaga pierwszych publikacji
i rzetelnych danych o odbiorze. Preset zawiera kryteria pomiaru i pełne
materiały potrzebne do rozpoczęcia takiego sprawdzenia.
