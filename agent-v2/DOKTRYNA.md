# Doktryna — co ten bot ma robić

Jeden plik, kanoniczny. Gdy kod i ten dokument mówią co innego, **to jest błąd
i trzeba go nazwać**, a nie wybrać wygodniejszą wersję.

Do 1 września 2026 doktryna leżała w trzech miejscach naraz —
`prompts/ZASADY_NOTEK_I_KOMENTARZY.md`, `prompts/ROZWOJ_KONTA.md` i komentarze
w kodzie — a **żaden kod nie czytał tych dwóch plików**. Skutek był taki, że
reguła „obserwuj wąsko, nie masowo" istniała na piśmie, a agent losował cele
z całej historii komentarzy. Ten plik ma to zastąpić.

Sekcja **Rozbieżności** na końcu jest częścią dokumentu, nie dodatkiem: to tam
stoi wszystko, czego kod jeszcze nie robi tak, jak tu napisano.

---

## 1. Zasada naczelna: sto procent autonomii

**Konto działa samo. Zero zgód, zero pytań do człowieka. Nigdy.**

Żadna bramka, żaden werdykt, żadna wątpliwość nie zatrzymuje rzeczy, która ma
wyjść. Co zaplanowane, to wychodzi — artykuł, notka, komentarz, odpowiedź.

**Lepiej, żeby coś wyszło z drobnym błędem, niż żeby nie wyszło.** Te błędy to
zwykle drobiazgi niewarte zachodu. Ludzie popełniają ich mnóstwo i nikt nie
płacze nad rozlanym mlekiem — a konto, które czasem się pomyli, wygląda
bardziej po ludzku niż konto bezbłędne.

**Nic się nie wycina.** Zdanie, które czegoś nie przeszło, zostaje w tekście.
Wycięte zdanie zostawia dziurę w środku akapitu i tekst urywa się w połowie
myśli — to gorsze dla czytelnika niż jedno słabe zdanie.

**Sprawdzenia są logiem, nie bramką.** Widać w dzienniku, co model
zakwestionował, i tyle. Nikt na to nie czeka i nic przez to nie stoi.

> Powód, dla którego to jest punkt pierwszy: 1 września gotowy, opłacony artykuł
> stanął z komunikatem „do decyzji właściciela" przez **jedno zdanie służbowe** —
> stopkę z datą źródeł — przy audycie, który w tym samym zdaniu napisał, że
> wszystkie twierdzenia merytoryczne są potwierdzone. Wcześniej ta sama bramka
> kazała napisać jeden artykuł **trzy razy od zera**: 8,38 USD zamiast 2,12.

---

## 2. Co mimo to blokuje — trzy rzeczy i tylko trzy

Punkt pierwszy nie znaczy „publikuj cokolwiek". Blokują:

**Zapora przeciw wstrzyknięciu.** Cudzy tekst próbujący pisać przez nasze konto.
To obrona przed przejęciem, nie wątpliwość co do faktu.

**Podłogi z pamięci przy komentarzu** — zmyślone przeżycie („I asked three
people about this"), nienazwane badanie („studies have shown"). Komentarz idzie
na cudzy post, pod nazwą pisma, w miejsce, gdzie autor dostaje powiadomienie.
Sprawdzanie faktów tego nie łapie: zmyślone przeżycie nie jest twierdzeniem
sprawdzalnym.

**Wyczerpany budżet i wyłącznik `KILL_SWITCH`.** To brak pieniędzy, nie
wątpliwość — i jedyna twarda blokada, jaka została.

---

## 3. Ile czego wychodzi

| | dziennie | miesięcznie |
|---|---|---|
| notki | **5** | ~150 |
| komentarze | **15–23** | ~570 |
| polubienia | **10–16** | ~390 |
| restacki | **1–2** | ~45 |
| obserwacje | — | **10–16** |
| subskrypcje | — | **12–20** |
| artykuły | — | **1 tygodniowo** |

Odpowiedzi pod naszymi treściami są **poza tymi limitami** — rozmowa u siebie
nie jest wydatkiem na zasięg.

---

## 4. Rytm i losowość

**Konto nie może wyglądać jak maszyna.** Nie chodzi o udawanie człowieka, tylko
o brak odruchu.

Pięć przebiegów dziennie, o stałych godzinach, ale **systemd przesuwa każdy
start losowo o 0–25 minut**, a pierwsza notka dostaje jeszcze własną zwłokę.
Dzienny przydział rozkłada się nierówno między przebiegi.

**Ta sama forma dwa razy z rzędu jest podpisem automatu tak samo jak ta sama
treść.** Dlatego losujemy formę notki, ruch końcowy artykułu, długość — i
pilnujemy, żeby kolejna notka nie zaczynała się jak poprzednia.

**Nie reagujemy natychmiast.** Reagujący na naszą treść trafia do celów dopiero
po dobie — odpowiedź obserwacją na polubienie w ciągu godziny to widoczny
wzorzec i dokładnie to, co regulamin Substacka nazywa „sztuczną aktywnością".

---

## 5. Komentarze

**Nie komentujemy wszędzie i nie odpowiadamy na każdą zaczepkę.**

Komentarz ma być **dopasowany**: wnosi coś, czego pod tym postem nie ma. Jeśli
nie da się powiedzieć konkretnie, co dokładamy — nie komentujemy.

**Pod własnymi publikacjami zwykle odpowiadamy** — małe konto żyje z rozmowy.
Gdy wywiąże się dyskusja, też. **Ale nie przeciągamy.** Kiedy rozmowa zaczyna
kręcić się wokół tego samego, przestajemy reagować. Ostatnie słowo nie jest
nagrodą.

Milczenie jest pełnoprawną odpowiedzią. Samo emoji, sama pochwała bez pytania,
zaczepka do kłótni nie na temat — nie odpowiadamy.

---

## 6. Artykuł i promocja

**Jeden artykuł tygodniowo.** Wtorek, 14:00 UTC.

**Promowany notką przez pięć dni z rzędu**, po jednej dziennie, z linkiem.
Kilka linków jednego dnia to nie promocja, tylko natręctwo; pięć dni to pięć
osobnych szans trafienia kogoś, kto akurat patrzy w kanał.

Link dokleja **kod**, nie model — model potrafi przekręcić adres.

Promujemy **najświeższy** artykuł, nie najdawniej wstawiony. Po siedmiu dniach
artykuł wypada z kolejki, nawet z niewybranymi dniami: zimny link nie działa.

---

## 7. Świeżość kontra historia

**To nie jest to samo i nie wolno tego mylić.**

W AI coś sprzed miesiąca może już nie być newsem. Ale coś sprzed czterech lat
może być **znakomitym tekstem — podanym jako historia, nie jako news**.

- **Jako news** temat musi być świeży. Stara rzecz podana jako nowość to błąd,
  który czytelnik wychwyci natychmiast.
- **Jako historia** wiek nie jest wadą, tylko materiałem: „tak to wyglądało,
  oto co z tego wyszło, oto czego się z tego nie nauczyliśmy". Wtedy data ma
  być widoczna i **należy do tezy**, a nie jest chowana.

Regułą jest więc nie „temat ma być świeży", tylko **„sposób podania ma pasować
do wieku tematu"**.

---

## 8. Kogo obserwujemy i subskrybujemy

**Wąsko, nie masowo.** Masowe obserwowanie w nadziei na wzajemność jest
widoczne — nasza lista obserwowanych jest publiczna i nie da się jej ukryć.

**Pierwszeństwo mają konta, które już zetknęły się z naszą treścią** —
polubiły, odpowiedziały, restackowały. To jedyna przesłanka, którą zmierzyliśmy.

**Nie budujemy wzajemności.** Zmierzone: z dwunastu kont, którym daliśmy
subskrypcję, odwzajemniło się **zero**. Żadnego odobserwowywania po braku
odzewu — to jest wprost „sztuczna aktywność" z regulaminu.

---

## 9. Kim jest to konto

Anonimowa marka redakcyjna pisząca po angielsku o sztucznej inteligencji.
Konto **nie ujawnia publicznie**, że pisze je AI.

**Ale nigdy nie kłamie zapytane wprost.** Gdy ktoś pyta bezpośrednio, czy pisze
to maszyna — nie zaprzeczamy i nie uciekamy w bok. Mówimy, że publikacja nie
omawia sposobu, w jaki powstaje, i wracamy do tematu. Zaprzeczenie jest
zakazane. Techniczne ukrywanie się też.

---

## 10. Pieniądze

Sufit miesięczny: **40 USD**. To jedyna twarda granica w całym systemie — po
jej przekroczeniu przebieg przerywa i nic nie wychodzi.

Zmierzone koszty jednostkowe: komentarz ~0,03 USD, odpowiedź ~0,02, notka ~0,09
(samo pisanie), artykuł ~1,4 przy jednym podejściu.

**Powtórki są najdroższe.** Artykuł napisany trzy razy kosztuje trzy razy tyle,
co napisany raz. Dlatego punkt pierwszy jest też decyzją o pieniądzach.

---

## 11. Co wiemy o tym, co działa

Zmierzone od przestawienia konta na AI:

```
artykuly:    6 pozycji /   82 wyswietlenia /  7 subskrypcji
notki:      46 pozycji / 1654 wyswietlenia /  0 subskrypcji
komentarze: 63 pozycje  /   77 wyswietlen  /  0 subskrypcji
```

**TA TABELA PORÓWNUJE TRZY RÓŻNE PRZYRZĄDY** i nie wolno z niej czytać, który
kanał przynosi subskrypcje. Sprawdzone pomiarem 2 września 2026:

| kanał | skąd liczba | co naprawdę liczy |
|---|---|---|
| artykuł | `stats.signups_within_1_day` | **każdego, kto zapisał się w ciągu doby po wysyłce** — bez względu na to, co go przyprowadziło |
| notka | karta `interactions`, kafelek „Subscribe" | zapisy kliknięte z widoku samej notki |
| komentarz | kart zasięgu brak (21 z 69) | nic; zero znaczy „nikt nie policzył" |

Dowód, że pole artykułu jest OKNEM CZASOWYM, a nie przypisaniem — zestawienie
z prawdziwą listą subskrybentów (`data/kopie/subskrybenci-2026-09-02.csv`):

```
Example Article One   25.08   pole 3   nowych nazajutrz 3
Example Article Two            30.08   pole 2   nowych nazajutrz 2
Example Article Four...   01.09   pole 0   nowych nazajutrz 0
```

Co do sztuki, w każdym przypadku. W obie te doby wychodziło też pięć notek
i kilkanaście komentarzy — mogły przyprowadzić tych ludzi tak samo dobrze.
Subskrybent z 29 sierpnia nie ma w oknie żadnego artykułu i nie liczy go NIC.

Dlatego dawne zdanie „artykuł z ośmioma wyświetleniami dał trzech
subskrybentów" nie opisuje konwersji 37 procent. Opisuje dobę, w której akurat
wyszedł artykuł.

**Co zostaje prawdą:** notki i komentarze budują zetknięcie (4 z 19 czytelników
zetknęło się z treścią wcześniej), a artykuł jest najdroższą pozycją, jaką to
konto produkuje. Najszerzej oglądana notka miała 373 wyświetlenia i zero
zapisów kliniętych z jej widoku.

**Co przestaje być prawdą:** że wiemy, który kanał przynosi subskrypcje. Nie
wiemy. Zdanie „subskrypcje przynoszą artykuły" stało tu do 2 września 2026
i zostało obalone pomiarem, nie opinią. Czy artykuł ma nadal mieć
pierwszeństwo, jest decyzją właściciela — ale nie wynika już z liczb.

---

## 12. Jak pracujemy nad tym kodem

Cztery reguły, każda kupiona drogo:

**Prośba w prompcie nie jest bramką.** Regułę w prompcie można spełnić
w połowie. Z kodem nie da się negocjować.

**Żadnych asercji po treści źródła.** Test szukający napisu w pliku przechodzi
także nad kodem, który w produkcji nie robi nic. Zdarzyło się to trzy razy
jednego dnia.

**Kontrdowód musi być odtworzony, nie opisany**, a wersja odniesienia przypięta
do konkretnego SHA — **nigdy do `HEAD`**. Test mierzący się względem `HEAD`
gaśnie w chwili commita, którego strzeże.

**Zero, które ma wyjaśnienie, przestaje wyglądać na awarię.** 23 sierpnia
zmierzyłem poprawnie, że słowa „Follow" nie ma w kodzie strony, i wyciągnąłem
fałszywy wniosek, że Substack zdjął przycisk. Zdanie trafiło do trzech
dokumentów, dokumenty zaczęły się nawzajem cytować i przez **dziewięć dni**
konto nie obserwowało nikogo, a tabela tłumaczyła to zero. Przycisk był w menu
pod „...".

**Wdrażamy tylko wtedy, gdy nie trwa przebieg** (`flock -n
agent-v2/data/agent.lock`). Prompty są czytane z dysku przy każdym wywołaniu,
więc `git pull` w trakcie podmienia je pod działającym procesem.

---

## Rozbieżności doktryny z kodem — stan na 1 września 2026

Ta sekcja ma być **pusta**. Każda pozycja to dług.

**1. Promocja: doktryna mówi pięć dni, kod robi trzy.**
`config.NOTEK_PROMUJACYCH = 3`. Zeszło z pięciu 20 sierpnia, bo przy artykule
tygodniowym kolejka nie nadążała — ale ten powód zniknął, gdy zaczęliśmy
promować najświeższy artykuł i dodaliśmy okno siedmiu dni. Do przywrócenia.

~~**2. Połowa notek promujących nie wychodzi.**~~ **ZAMKNIĘTE 2 września 2026.**
Sześć prób od 25 sierpnia, trzy opublikowane; trzy padły na **naszej własnej
zaporze przeciw wstrzyknięciu**. Zmierzone na całym okresie: 16 prób, 6 odrzuceń,
**wszystkie z powodem „adres www w tresci" i zero innych powodów** — a w tym samym
czasie 58 notek nie-promujących dostawało karty z cudzymi adresami i nie zapaliło
zapory ani razu. Diagnoza z tej sekcji była w połowie błędna: adres nie brał się
z tekstu artykułu w karcie (7 z 7 kart nie zawiera żadnego adresu), tylko z tego,
że typ ARTYKUL mówi modelowi „let the link do the rest", a wcześniejsze notki
promocyjne dostaje razem z linkiem doklejonym przez kod.

Zapora wycina teraz własny adres publikacji o ściśle ustalonym kształcie, zanim
sprawdzi tekst; kontrdowód 9 przypadków (polecenie z naszym adresem, cudzy obok
naszego, wszyty jako `?next=`, podszycie pod domenę, poddomena, slug ze wzmianką)
nadal blokuje. Przy okazji zamknięta **dziura, przez którą przechodził dowolny
cudzy adres pisany WIELKIMI LITERAMI**.

**3. Nie ma reguły „przestajemy, gdy rozmowa kręci się w kółko".**
Poniżej dwudziestu komentarzy odpowiadamy każdemu. Osąd co do treści jest
(milczy przy samym emoji), ale nic nie liczy, ile razy już wymieniliśmy zdania
z tą samą osobą pod tym samym wątkiem.

**4. Notki wychodzą poniżej normy: 2,75 dziennie zamiast 5.**
22 notki przez 8 dni. Przyczyna niezbadana.

**5. `NOTE_MIX_ARTICLE_DAY` i `plan_tygodnia()` to martwy kod.**
Miks „dnia artykułu" nie odpala się nigdy (`dzien_artykulu=True` nie jest
przekazywane z produkcji), a `plan_tygodnia()` nie ma **ani jednego wywołania**
w całym repozytorium, mimo docstringa „niedziela to dzień artykułu".

**6. Limit wyszukań w sieci jest bezczynny.**
`DISCOVERY_MAX_SEARCHES = 8` trafia wyłącznie do gałęzi Anthropic, a bank
pomysłów chodzi przez DeepSeek `/responses`, gdzie limitu nie da się ustawić.
Zmierzone: 71 wywołań, 1026 wyszukań, **średnio 14,45, maksymalnie 32**.

**7. Bank NIE wygasa ze starości — pali się przy wyjmowaniu.** *(zmierzone
2 września, teza z tej sekcji obalona)*
Pozycji po terminie jest **zero** i ani jedna nie została nigdy oznaczona jako
przeterminowana. Materiał ginął gdzie indziej: `wez_kandydatow(8)` znaczy jako
zużytą całą ósemkę przy WYJMOWANIU, a przebieg wystawia z niej jedną albo dwie
notki. **21 z 26 wyjętych pozycji (81%) nigdy nie poszło w świat**, przy etapie
`curiosity` kosztującym 3,72 USD, czyli 15,1% wydatków od 25 sierpnia. Ścieżka
artykułu oddawała niewydane od 30 sierpnia, ścieżka notek nie oddawała nigdy —
od 2 września oddaje.

**8. Zniknęło 119 wcześniejszych kandydatów z banku — mechanizm już znany,
naprawa nie.**
Bank rósł 66 → 119 wolnych pozycji między 25 a 29 sierpnia, opłacony 22
wywołaniami za **1,51 USD**, i zniknął w całości około 30 sierpnia 12:44 — bez
ani jednego wpisu `uzyty` i bez ani jednego `przeterminowany`. Znaleziony
2 września mechanizm, który to tłumaczy: zapis indeksu to **nieatomowy
`write_text`**, a odczyt traktuje nieczytelny plik jak **pusty**. Przebieg ubity
w trakcie zapisu kasuje więc bank po cichu — bez wyjątku i bez linii w logu.
Drugie możliwe wyjaśnienie to świadomy reset podczas testów tamtego dnia; ze
śladów nie da się rozstrzygnąć, które zaszło, i to samo w sobie jest wadą.
Naprawa (zapis przez plik tymczasowy i `os.replace`, głośne oblanie przy
nieczytelnym pliku) stoi jako pozycja 1 w `agent-v2/DO_ZROBIENIA.md`.
